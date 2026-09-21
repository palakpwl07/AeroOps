"""Regression tests for the N-CMAPSS false denial (smoke query #7).

Root cause: FailureMode-star retrieval never reads MODELS / ENABLES /
SUPPORTS edges, so the only chunk stating "N-CMAPSS MODELS hardware
deterioration" (D2_c05) never reached the generator.

No Neo4j is reachable offline, so `_run` is stubbed with an in-memory
evaluation of the same predicate over knowledgebase/aeroops_knowledgegraph.md
(the graph's own export). This tests the plumbing and the edge-type coverage
guard; the Cypher itself is verified separately against the live graph.
"""
import json
import pathlib
import re
import sys

import types

import pytest

try:  # the driver is only needed to construct a live retriever, never here
    import neo4j  # noqa: F401
except ImportError:
    sys.modules["neo4j"] = types.SimpleNamespace(GraphDatabase=None)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from answer_generator_groq import AnswerGenerator  # noqa: E402
from context_builder import ContextBuilder  # noqa: E402
from graphretriever_v5 import GraphRetriever  # noqa: E402

KG = json.loads((ROOT / "knowledgebase/aeroops_knowledgegraph.md").read_text(encoding="utf-8"))
NAMES = {n["id"]: n["name"] for v in KG["nodes"].values() for n in v}
CHUNKS = {c["chunk_id"]: c for c in KG["chunks"]}

def _retriever(base_result, fail=False):
    r = object.__new__(GraphRetriever)

    def run(cypher, params):
        if fail:
            raise RuntimeError("neo4j down")
        rows = []
        for rel in KG["relationships"]:
            p = rel.get("properties") or {}
            if not p.get("claim_id") or rel["type"] in params["star_types"]:
                continue
            for a in params["ids"]:
                if a in (rel["from"], rel["to"]):
                    o = rel["to"] if a == rel["from"] else rel["from"]
                    rows.append(dict(
                        anchor_id=a, anchor_name=NAMES[a], outgoing=(a == rel["from"]),
                        rel=rel["type"], other_id=o, other_name=NAMES[o],
                        claim_id=p["claim_id"], confidence=p.get("confidence"),
                        chunks=p.get("source_chunk_ids")))
        return rows

    r._run = run
    r._retrieve_base = lambda e: dict(base_result)
    r.fetch_chunks = lambda ids: [
        dict(chunk_id=i, text=CHUNKS[i]["text"], doc_id=CHUNKS[i]["doc_id"]) for i in ids]
    return r


BASE = dict(retrieval_type="query_plan_recall_heavy_graph_context", results=[],
            chunk_ids=["D1_c11", "D2_c02"], chunks=[])


def test_star_edge_types_match_star_cypher():
    """The exclusion list must equal the edge types _STAR_MATCHES reads, or
    edges would be double-counted / silently dropped."""
    in_cypher = set(re.findall(r"\[\w+:([A-Z_]+)\]", GraphRetriever._STAR_MATCHES))
    in_cypher |= set(re.findall(r"IN \[([^\]]+)\]", GraphRetriever._STAR_MATCHES)[0].replace("'", "").replace(" ", "").split(","))
    assert set(GraphRetriever._STAR_EDGE_TYPES) == in_cypher


def test_audit_finds_exactly_the_five_unreachable_claim_edges():
    r = _retriever(BASE)
    every_id = list(NAMES)
    rels = r.fetch_anchor_relations(every_id)
    assert {x["claim_id"] for x in rels} == {"CL067", "CL069", "CL071", "CL072", "CL073"}
    assert len(rels) == 5  # no duplicates although both endpoints are anchors


def test_ncmapss_query_now_carries_the_real_edge_and_chunk():
    r = _retriever(BASE)
    res = dict(BASE)
    r._attach_anchor_relations(res, ["ME_ncmapss"])
    rel = res["anchor_relations"][0]
    assert (rel["source_id"], rel["rel"], rel["target_id"], rel["claim_id"]) == (
        "ME_ncmapss", "MODELS", "FM_hardware_deterioration", "CL071")
    assert res["chunk_ids"][0] == "D2_c05"            # anchor evidence first
    assert res["chunk_ids"][1:] == BASE["chunk_ids"]  # existing evidence untouched
    assert [c["chunk_id"] for c in res["chunks"]][0] == "D2_c05"


@pytest.mark.parametrize("anchor,claim,chunk", [
    ("ME_ncmapss", "CL071", "D2_c05"),
    ("FM_hardware_deterioration", "CL071", "D2_c05"),  # incoming direction
    ("ME_fadec", "CL073", "D5_c01"),
])
def test_relation_surfaces_from_either_endpoint(anchor, claim, chunk):
    r = _retriever(BASE)
    res = dict(BASE)
    r._attach_anchor_relations(res, [anchor])
    assert claim in {x["claim_id"] for x in res["anchor_relations"]}
    assert chunk in res["chunk_ids"]


def test_no_change_when_anchor_has_only_star_edges():
    r = _retriever(BASE)
    res = dict(BASE)
    r._attach_anchor_relations(res, ["FM_compressor_surge"])
    assert res == BASE  # untouched: no anchor_relations key, same chunk ids


def test_neo4j_failure_leaves_result_intact():
    r = _retriever(BASE, fail=True)
    res = dict(BASE)
    r._attach_anchor_relations(res, ["ME_ncmapss"])
    assert res["chunk_ids"] == BASE["chunk_ids"] and "anchor_relations" not in res
    assert "neo4j down" in res["anchor_relations_error"]


def test_relation_reaches_the_generator_prompt():
    r = _retriever(BASE)
    res = dict(BASE, chunks=[])
    r._attach_anchor_relations(res, ["ME_ncmapss"])
    ctx = ContextBuilder().build("How is the N-CMAPSS dataset used for engine prognostics?", res)
    line = "N-CMAPSS run-to-failure dataset --[MODELS]--> Hardware deterioration / blade distress [D2_c05]"
    assert ctx["direct_relations"] == [line]
    assert "D2_c05" in ctx["citations"]
    gen = object.__new__(AnswerGenerator)
    skeleton = AnswerGenerator.build_factual_skeleton(gen, ctx)
    assert line in skeleton
    assert "[D2_c05]" in skeleton and "7 possible failure modes" in skeleton
