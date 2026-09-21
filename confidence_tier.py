"""Deterministic confidence signals from retrieval structure and answer text (no LLM).

Offline-only for now: not imported by main.py or any request path.

Two independent signals, deliberately not merged:
  * tier         -- LOW / STANDARD, from the router's matched-entity count and
                    retrieval health.
  * answer_type  -- "refusal" / "substantive" / "empty", from string patterns on
                    the generated answer.

Evidence (see evaluation/confidence_tier.md): zero matched entities held up on
both the 45-item gold set and a 20-query smoke test. Context count and the
entities == 1 "verify" tier were tested and dropped.
"""
import re
from typing import Dict

LOW = "LOW"            # retrieval failed / degraded / no entity matched
STANDARD = "STANDARD"  # no structural warning (NOT the same as verified)

REFUSAL = "refusal"
SUBSTANTIVE = "substantive"
EMPTY = "empty"

# Phrasings taken from real refusals in the eval outputs. Matched
# case-insensitively; curly apostrophes and non-breaking hyphens are
# normalised first.
_DENIAL_PATTERNS = [
    # "The graph (facts) does not contain/provide/list ..."
    r"\b(graph|graph facts|facts|evidence|context|documents?|sources?|knowledge base)\b[^.\n]{0,40}"
    r"\b(does not|do not|doesn't|don't|cannot|can't)\s+(contain|provide|list|include|specify|mention|have|offer|support|describe|address|state)\b",
    # "It does not provide ..." after a substantive first sentence
    r"\b(it|this|that)\s+(does not|doesn't)\s+(provide|contain|specify|list|mention)\b",
    r"\bno (relevant |specific )?(information|evidence|data)\b",
    r"\b(information|data|evidence)\s+(is\s+|was\s+)?(not available|unavailable|missing|not found|not provided)\b",
    r"\bI\s+(do not|don't)\s+have\b",
    r"\bI(?:'m| am) sorry\b",
    r"\b(unable|not able) to (find|answer|determine)\b",
]
_DENIAL_RE = [re.compile(p, re.I) for p in _DENIAL_PATTERNS]
_FIRST_SENTENCE_RE = re.compile(r"^(.+?[.!?])(\s|$)", re.S)


def _normalise(text: str) -> str:
    return text.replace("\u2019", "'").replace("\u2011", "-").strip()


def confidence_tier(
    entity_count: int,
    degraded: bool = False,
    retrieval_error: bool = False,
) -> str:
    if degraded or retrieval_error or entity_count == 0:
        return LOW
    return STANDARD


def contains_denial(answer: str) -> bool:
    """A denial phrase appears anywhere (also true for substantive answers
    that add 'the graph does not list X' partway through)."""
    text = _normalise(answer or "")
    return any(p.search(text) for p in _DENIAL_RE)


def classify_answer(answer: str) -> str:
    """'refusal' when the answer opens with a denial, i.e. its first sentence
    matches a denial pattern; 'empty' for blank output; else 'substantive'."""
    text = _normalise(answer or "")
    if not text:
        return EMPTY
    m = _FIRST_SENTENCE_RE.match(text)
    first = m.group(1) if m else text
    return REFUSAL if any(p.search(first) for p in _DENIAL_RE) else SUBSTANTIVE


def assess(
    entity_count: int,
    answer: str,
    degraded: bool = False,
    retrieval_error: bool = False,
) -> Dict[str, object]:
    return {
        "tier": confidence_tier(entity_count, degraded, retrieval_error),
        "answer_type": classify_answer(answer),
        "contains_denial": contains_denial(answer),
    }
