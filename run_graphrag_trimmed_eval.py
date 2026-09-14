# run_graphrag_trimmed_eval.py
#
# Runs all 45 gold-set questions through graph_rag() with
# graphretriever_v5.py's MAX_RECALL_CHUNKS trimmed 16 -> 10 (context-size
# experiment, see that file's comment), to measure the latency/quality
# impact against the original graphrag_ragas_inputs.json before deciding
# whether to keep the trim.
#
# Mirrors run_graphrag_eval.py exactly (same secrets loading, same
# st.cache_resource -> lru_cache patch, same per-item flow, same output
# field names) so the two runs are directly comparable and the existing
# score_graphrag_mechanical.py can score this one unmodified, just
# pointed at a different input file.
#
# Output: graphrag_trimmed_ragas_inputs.json

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
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            ".streamlit", "secrets.toml")
if tomllib and os.path.exists(secrets_path):
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
from graphretriever_v5 import GraphRetriever

EVAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "evaluation", "gold_set", "aeroops_goldset_v1_frozen.json")
# Filename carries the live MAX_RECALL_CHUNKS value so two back-to-back runs
# (one per cap value, run close together to avoid the time-of-day/infra
# confound) never collide or get mixed up.
OUTPUT_JSON = f"graphrag_cap{GraphRetriever.MAX_RECALL_CHUNKS}_ragas_inputs.json"
SLEEP_BETWEEN = 1.2


def load_eval_set(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for q in data:
        items.append({
            "id": q["id"],
            "category": q.get("category", ""),
            "hop_count": q.get("hop_count"),
            "question": q["question"],
            "ground_truth": q.get("expected_answer", ""),
            "expected_chain": q.get("expected_chain", []),
            "source_chunks": q.get("source_chunk_ids", []),
            "ground_truth_nodes": q.get("ground_truth_nodes", []),
        })
    return items


def run_eval():
    print(f"\nLoading eval set from: {EVAL_PATH}")
    items = load_eval_set(EVAL_PATH)
    print(f"Loaded {len(items)} items.\n")

    ragas_rows = []

    for i, item in enumerate(items):
        qid = item["id"]
        question = item["question"]
        print(f"[{i+1:02d}/{len(items)}] {qid}: {question[:70]}...")

        t0 = time.time()
        output = {}
        try:
            output = graph_rag(question)
            answer = output.get("answer", "")
            sources = output.get("sources", []) or []
            contexts = [s.get("quote", "") for s in sources if s.get("quote")]
            elapsed = round(time.time() - t0, 2)
            retrieval_type = output.get("retrieval_type")
            retrieval_error = output.get("retrieval_error")
            generation_error = output.get("generation_error")
            retrieval_time = output.get("retrieval_time")
            generation_time = output.get("generation_time")
            print(f"    backend=graphrag retrieval_type={retrieval_type} | "
                  f"{len(contexts)} contexts | retrieval={retrieval_time}s "
                  f"generation={generation_time}s | {elapsed}s total")
        except Exception as exc:
            elapsed = round(time.time() - t0, 2)
            answer = f"ERROR: {exc}"
            contexts = []
            retrieval_type = None
            retrieval_error = str(exc)
            generation_error = None
            retrieval_time = None
            generation_time = None
            print(f"    UNCAUGHT ERROR: {exc}")

        ragas_rows.append({
            "ID": qid,
            "Category": item["category"],
            "Hop Count": item.get("hop_count"),
            "Question": question,
            "Ground Truth": item["ground_truth"],
            "Expected Chain": item.get("expected_chain", []),
            "Model Answer": answer,
            "Retrieved Contexts": contexts,
            "Source Chunks": ", ".join(item["source_chunks"]),
            "Ground Truth Nodes": item.get("ground_truth_nodes", []),
            "Time (s)": elapsed,
            "Retrieval Type": retrieval_type,
            "Reasoning Chain": output.get("reasoning_chain", []),
            "Matched Entities": output.get("matched_entities", []),
            "Path Nodes": output.get("path_nodes", []),
            "Path Edges": output.get("path_edges", []),
            "Retrieval Error": retrieval_error,
            "Generation Error": generation_error,
            "Retrieval Time (s)": retrieval_time,
            "Generation Time (s)": generation_time,
        })

        if i < len(items) - 1:
            time.sleep(SLEEP_BETWEEN)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(ragas_rows, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved -> {OUTPUT_JSON}")


if __name__ == "__main__":
    run_eval()
