# run_naive_rag_eval.py
#
# Runs all 45 questions from the frozen gold set (aeroops_goldset_v1_frozen.json)
# through naive_rag() and saves outputs in RAGAS-compatible format. Builds
# the index ONCE, reuses it for all 45.
#
# Usage:
#   cd C:\Users\palak\OneDrive\Desktop\.aeroops
#   python run_naive_rag_eval.py
#
# Output:
#   naive_rag_ragas_inputs.json   -- feed into score_naive_rag_ragas.py
#   naive_rag_eval_results.xlsx   -- human-readable for manual review

from __future__ import annotations

import functools
import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# Load secrets from .streamlit/secrets.toml into os.environ BEFORE any
# other imports, so OPENROUTER_API_KEY is visible to naive_rag.py.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Patch st.cache_resource with a REAL lru_cache so _build_index() runs
# exactly once (not on every call). No-op patching caused a full index
# rebuild on every question -- ~60-130s per question instead of ~8s.
# ---------------------------------------------------------------------------
import streamlit as st

def _real_cache_resource(**kwargs):
    """Replace st.cache_resource with lru_cache so the index is built once."""
    def decorator(func):
        @functools.lru_cache(maxsize=1)
        def cached(*args, **kw):
            return func(*args, **kw)
        return cached
    return decorator

st.cache_resource = _real_cache_resource
st.cache_data = lambda **kwargs: (lambda f: f)

# Now import naive_rag -- the patched decorators are in place.
from naive_rag import (
    hybrid_retrieve,
    generate_answer_with_citations,
)

EVAL_PATH = os.getenv(
    "AEROOPS_EVAL_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "aeroops_goldset_v1_frozen.json")
)
OUTPUT_JSON = "naive_rag_ragas_inputs.json"
OUTPUT_XLSX = "naive_rag_eval_results.xlsx"
SLEEP_BETWEEN = 1.2   # seconds between questions -- avoids Groq 429


def load_eval_set(path: str):
    """Loads the frozen gold set (flat array, 45 items). Replaces the old
    load_eval_set that expected {"questions": [...], "operational_scenarios":
    [...]} -- that was the 35-item eval file's schema, not this one's.

    Carries hop_count, expected_chain, and ground_truth_nodes through even
    though naive RAG's own scoring doesn't use them yet, GraphRAG's run
    will, and keeping the two output files structurally identical now
    means comparing them later doesn't need a reconciliation step.
    """
    with open(path) as f:
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
    if not os.path.exists(EVAL_PATH):
        print(f"ERROR: eval file not found at {EVAL_PATH}")
        sys.exit(1)

    items = load_eval_set(EVAL_PATH)
    print(f"Loaded {len(items)} items.\n")

    # Build the index ONCE here before the loop.
    print("Building index (this runs once only)...")
    t0 = time.time()
    _ = hybrid_retrieve(items[0]["question"], k=5)
    print(f"Index ready in {round(time.time()-t0, 1)}s.\n")

    ragas_rows = []
    result_rows = []

    for i, item in enumerate(items):
        qid = item["id"]
        question = item["question"]
        print(f"[{i+1:02d}/{len(items)}] {qid}: {question[:70]}...")

        t0 = time.time()
        try:
            # Retrieve once -- reuse for both generation and RAGAS contexts.
            docs = hybrid_retrieve(question, k=5)
            contexts = [doc.page_content for doc in docs]

            output = generate_answer_with_citations(question, docs)
            answer = output.get("answer", "")
            elapsed = round(time.time() - t0, 2)

            print(f"    {answer[:80]}...")
            print(f"    {len(contexts)} contexts | {elapsed}s")

        except Exception as exc:
            elapsed = round(time.time() - t0, 2)
            answer = f"ERROR: {exc}"
            contexts = []
            print(f"    ERROR: {exc}")

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
        })

        result_rows.append({
            "ID": qid,
            "Category": item["category"],
            "Question": question,
            "Expected Answer": item["ground_truth"],
            "Model Answer": answer,
            "Num Contexts": len(contexts),
            "Time (s)": elapsed,
        })

        if i < len(items) - 1:
            time.sleep(SLEEP_BETWEEN)

    # Save RAGAS-compatible JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(ragas_rows, f, indent=2, ensure_ascii=False)
    print(f"\nSaved RAGAS inputs  -> {OUTPUT_JSON}")

    # Save human-readable xlsx
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Naive RAG Results"
        headers = list(result_rows[0].keys())
        ws.append(headers)
        for row in result_rows:
            ws.append([row[h] for h in headers])
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 32
        wb.save(OUTPUT_XLSX)
        print(f"Saved readable results -> {OUTPUT_XLSX}")
    except ImportError:
        print("openpyxl not installed -- xlsx skipped, JSON is complete.")

    print(f"\nDone. {len(ragas_rows)}/{len(items)} items evaluated.")
    print("\nNext: open Ragas_eval_groq_stable.py, change the input path to:")
    print(f'    "{OUTPUT_JSON}"')
    print("then run it to get naive RAG RAGAS scores.")

if __name__ == "__main__":
    run_eval()