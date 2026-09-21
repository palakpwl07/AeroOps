"""Read-only checks for confidence_tier against the 45 gold-set items and the
20-query smoke test (tests/fixtures/smoke20.json, recorded from the live API).

Entity counts come from a live QueryRouter run, so if ENTITY_MAP changes these
tests move too -- that is intended. The two smoke queries marked KNOWN_GAP are
in-domain but currently match zero entities (vocabulary gap); when the map is
fixed they should be removed from that set, not silently re-baselined.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from confidence_tier import (  # noqa: E402
    EMPTY, LOW, REFUSAL, STANDARD, SUBSTANTIVE,
    assess, classify_answer, confidence_tier, contains_denial,
)
from query_understanding_v3 import QueryRouter  # noqa: E402

EV = ROOT / "evaluation"


def _load(p):
    return json.loads((EV / p).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def router():
    return QueryRouter()


# ---------- pure-function cases ----------

def test_tier_rules():
    assert confidence_tier(0) == LOW
    assert confidence_tier(3, degraded=True) == LOW
    assert confidence_tier(3, retrieval_error=True) == LOW
    assert confidence_tier(1) == STANDARD  # entities == 1 is NOT a warning
    assert confidence_tier(2) == STANDARD


@pytest.mark.parametrize("answer", [
    "The graph facts do not contain any information about X.",
    "The graph does not provide any failure modes that are specific to Y. The only ...",
    "Information not available.",
    "Information is missing.",
    "I\u2019m sorry, but I don\u2019t have any information on that.",
    "I'm sorry, but I don't have any information on that.",
])
def test_refusal_detected(answer):
    assert classify_answer(answer) == REFUSAL


@pytest.mark.parametrize("answer", [
    "A steady drop in oil quantity indicates an oil leak. [D3_c19]",
    "Dust blocks cooling holes [D1_c08]. The graph does not list any mitigations.",
    "In a flameout the EGT does not rise; EPR is low [D3_c13].",
])
def test_substantive_not_refusal(answer):
    assert classify_answer(answer) == SUBSTANTIVE


def test_denial_later_in_substantive_answer():
    a = "Dust blocks cooling holes [D1_c08]. The graph does not list any mitigations."
    assert classify_answer(a) == SUBSTANTIVE and contains_denial(a)
    assert not contains_denial("A steady drop in oil quantity indicates an oil leak.")


@pytest.mark.parametrize("answer", [None, "", "   \n"])
def test_empty(answer):
    assert classify_answer(answer) == EMPTY
    assert not contains_denial(answer)


def test_assess_keeps_signals_separate():
    r = assess(2, "The graph does not provide any information about Z.")
    assert r == {"tier": STANDARD, "answer_type": REFUSAL, "contains_denial": True}
    r = assess(0, "Tell-me-everything style answer with content [D1_c01].")
    assert r["tier"] == LOW and r["answer_type"] == SUBSTANTIVE


# ---------- 45-item gold set ----------

@pytest.fixture(scope="module")
def gold(router):
    inputs = {x["ID"]: x for x in _load("graphrag/graphrag_ragas_inputs.json")}
    gen = {x["id"]: x["graphrag"] for x in _load("harness_runs/generation_1788715370.json")["per_item"]}
    jury = {x["id"]: x for x in _load("jury_scoring/aggregated_jury_scores.json")["per_item"]}
    out = {}
    for i, it in inputs.items():
        ne = len(router.understand(it["Question"]).matched_entities)
        out[i] = dict(
            **assess(ne, gen[i]["answer"], gen[i]["degraded"]),
            wrong=not jury[i]["graphrag"]["correct"],
        )
    return out


def test_gold_covers_45(gold):
    assert len(gold) == 45


def test_gold_never_low(gold):
    """Zero-entity LOW has no false alarms on the gold set."""
    assert [i for i, v in gold.items() if v["tier"] == LOW] == []


def test_gold_only_empty_answer_is_af05(gold):
    """AF05 (jury-wrong) has answer=None with degraded=False; the empty check
    catches it. No gold answer is a refusal."""
    assert [i for i, v in gold.items() if v["answer_type"] == EMPTY] == ["AF05"]
    assert not [i for i, v in gold.items() if v["answer_type"] == REFUSAL]


def test_gold_partial_denials(gold):
    assert sorted(i for i, v in gold.items() if v["contains_denial"]) == ["DA04", "DA06"]


# ---------- 20-query smoke test ----------

SMOKE = json.loads((ROOT / "tests/fixtures/smoke20.json").read_text(encoding="utf-8"))
OUT_OF_DOMAIN_LOW = {13, 14, 15, 16, 17, 19}
KNOWN_GAP = {2, 20}  # in-domain phrasing, zero entities matched today ("fuel burn", "tell me everything")
EXPECTED_REFUSAL = {7, 9, 12, 13, 14, 15, 16, 17, 19}


@pytest.fixture(scope="module")
def smoke(router):
    return {
        x["n"]: assess(len(router.understand(x["question"]).matched_entities), x["answer"], x["degraded"])
        for x in SMOKE
    }


def test_smoke_low_set(smoke):
    low = {n for n, v in smoke.items() if v["tier"] == LOW}
    assert low == OUT_OF_DOMAIN_LOW | KNOWN_GAP


def test_smoke_in_domain_standard(smoke):
    std = {n for n, v in smoke.items() if v["tier"] == STANDARD}
    assert std == set(range(1, 21)) - OUT_OF_DOMAIN_LOW - KNOWN_GAP


def test_smoke_refusals(smoke):
    assert {n for n, v in smoke.items() if v["answer_type"] == REFUSAL} == EXPECTED_REFUSAL


def test_smoke_refusal_is_independent_of_tier(smoke):
    """Refusals occur in both tiers (7/9/12 are STANDARD), and LOW includes
    substantive answers (2, 20): the two signals must not be merged."""
    assert {smoke[n]["tier"] for n in (7, 9, 12)} == {STANDARD}
    assert {smoke[n]["answer_type"] for n in KNOWN_GAP} == {SUBSTANTIVE}
