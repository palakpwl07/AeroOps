"""
verify_entity_map_expansion.py

Narrow, targeted check on exactly 3 items after the ENTITY_MAP expansion:
MH01, PR02, PR03. These are the ones whose matched-entity count grew even
though they were already matching correctly before -- more entities isn't
automatically better, MH01 in particular was a hard-won fix earlier
tonight (the INDICATES/DETECTS traversal fix) that depended on a clean,
single-entity retrieval path. This checks whether the expanded entity set
pushed it into the noisier multi-entity query-plan path and changed the
actual answer quality, not just whether "more entities matched."

Not a full rerun. Prints old (known-good) vs new answer for MH01, and the
new answer against gold for PR02/PR03, for direct manual comparison.

Usage:
    cd C:\\Users\\palak\\OneDrive\\Desktop\\.aeroops
    python verify_entity_map_expansion.py
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
if secrets_path.exists():
    with open(secrets_path, "rb") as f:
        for k, v in tomllib.load(f).items():
            os.environ.setdefault(k, str(v))
    print(f"Secrets loaded from {secrets_path}")

import streamlit as st

def _real_cache_resource(**kwargs):
    def decorator(func):
        @functools.lru_cache(maxsize=1)
        def cached(*args, **kw):
            return func(*args, **kw)
        return cached
    return decorator

st.cache_resource = _real_cache_resource
st.cache_data = lambda **kwargs: (lambda f: f)

from graph_rag import graph_rag

# MH01's verified-correct answer from earlier tonight, before this
# entity-map expansion -- the baseline this check is protecting.
MH01_OLD_ANSWER = (
    "A bearing that is in distress can fail, producing debris that "
    "accumulates in the oil system. When that debris clogs the oil "
    "filter, the engine's bypass system activates, giving the cockpit "
    "an oil-filter-bypass indication. The failure also raises vibration "
    "levels. [D3_c18] [D3_c20] [D3_c17]"
)

TARGETS = ["MH01", "PR02", "PR03"]


def main():
    with open("aeroops_goldset_v1_frozen.json") as f:
        gold = {item["id"]: item for item in json.load(f)}

    for qid in TARGETS:
        item = gold[qid]
        question = item["question"]

        print("=" * 70)
        print(qid, "|", item["category"])
        print("Q:", question)
        print()
        print("GOLD:", item["expected_answer"][:250])
        print()

        if qid == "MH01":
            print("OLD (verified correct, pre-expansion):", MH01_OLD_ANSWER[:250])
            print()

        output = graph_rag(question)
        new_answer = output.get("answer", "")
        matched = output.get("matched_entities", [])
        sources = output.get("sources", []) or []
        valid_ids = [s.get("chunk_id") for s in sources if s.get("chunk_id")]

        print("NEW:", new_answer[:400])
        print()
        print("Matched entities this run:", [m.get("id") for m in matched] if matched else matched)
        print("Retrieval type:", output.get("retrieval_type"))
        print("Retrieved chunk IDs:", valid_ids)
        print()


if __name__ == "__main__":
    main()
