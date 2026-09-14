# patch_failed_items.py
#
# Reruns only the items that failed with retrieval_type=error (Neo4j
# connection reset during run_graphrag_trimmed_eval.py's cap=10 pass)
# and patches clean results back into graphrag_cap10_ragas_inputs.json,
# so the mechanical-score comparison isn't corrupted by an unrelated
# infrastructure fault.

from __future__ import annotations

import functools
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import tomllib
except ImportError:
    import tomli as tomllib

secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    with open(secrets_path, "rb") as f:
        for k, v in tomllib.load(f).items():
            os.environ.setdefault(k, str(v))

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

TARGET_FILE = "graphrag_cap10_ragas_inputs.json"

with open(TARGET_FILE, encoding="utf-8") as f:
    rows = json.load(f)

failed_ids = [r["ID"] for r in rows if r.get("Retrieval Type") == "error"]
print(f"Found {len(failed_ids)} failed items to rerun: {failed_ids}")

by_id = {r["ID"]: r for r in rows}

for qid in failed_ids:
    row = by_id[qid]
    question = row["Question"]
    print(f"Rerunning {qid}: {question[:70]}...")
    t0 = time.time()
    try:
        output = graph_rag(question)
        answer = output.get("answer", "")
        sources = output.get("sources", []) or []
        contexts = [s.get("quote", "") for s in sources if s.get("quote")]
        elapsed = round(time.time() - t0, 2)
        row["Model Answer"] = answer
        row["Retrieved Contexts"] = contexts
        row["Time (s)"] = elapsed
        row["Retrieval Type"] = output.get("retrieval_type")
        row["Reasoning Chain"] = output.get("reasoning_chain", [])
        row["Matched Entities"] = output.get("matched_entities", [])
        row["Path Nodes"] = output.get("path_nodes", [])
        row["Path Edges"] = output.get("path_edges", [])
        row["Retrieval Error"] = output.get("retrieval_error")
        row["Generation Error"] = output.get("generation_error")
        row["Retrieval Time (s)"] = output.get("retrieval_time")
        row["Generation Time (s)"] = output.get("generation_time")
        print(f"    OK retrieval_type={row['Retrieval Type']} "
              f"{len(contexts)} contexts | {elapsed}s")
    except Exception as exc:
        print(f"    STILL FAILING: {exc}")
    time.sleep(1.2)

with open(TARGET_FILE, "w", encoding="utf-8") as f:
    json.dump(list(by_id.values()), f, indent=2, ensure_ascii=False, default=str)
print(f"\nPatched and saved -> {TARGET_FILE}")
