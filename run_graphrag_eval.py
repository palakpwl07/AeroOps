# run_graphrag_eval.py
#
# Runs all 45 questions from the frozen gold set through graph_rag() and
# saves outputs in RAGAS-compatible format. Builds the GraphRAG pipeline
# (Neo4j connection + retriever + generator) ONCE via graph_rag.py's own
# st.cache_resource, reused for all 45.
#
# Mirrors run_naive_rag_eval.py's structure closely on purpose -- keeps
# both harnesses structurally identical so the naive-vs-GraphRAG comparison
# is apples-to-apples at the harness level, not just the scoring level.
#
# Unlike naive_rag_eval.py, there's no separate warm-up call here:
# graph_rag() does retrieval AND generation in one call, so a warm-up
# would mean paying for a real LLM generation on item 0 twice. The first
# loop iteration naturally builds the cached pipeline on its own, just
# slower than the rest (Neo4j connection setup).
#
# Usage:
#   cd C:\Users\palak\OneDrive\Desktop\.aeroops
#   python run_graphrag_eval.py
#
# Output:
#   graphrag_ragas_inputs.json   -- feed into score_graphrag_ragas.py
#   graphrag_eval_results.xlsx   -- human-readable for manual review

from __future__ import annotations

import functools
import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# Force stdout/stderr to UTF-8. Without this, on Windows, print() uses the
# console's codepage (cp1252 here), and a real generated answer containing
# an ordinary character the model likes to use -- e.g. U+2011 NON-BREAKING
# HYPHEN, U+202F NARROW NO-BREAK SPACE -- raises UnicodeEncodeError. That
# happened INSIDE the per-item try block below, before the item's real
# answer was appended to ragas_rows, so the except clause silently replaced
# a perfectly good generated answer with "ERROR: 'charmap' codec can't
# encode...". Confirmed against a real run: 25 of 45 items were corrupted
# this way, RAGAS-unscoreable, despite retrieval and generation both having
# actually succeeded. errors="replace" (not "strict") so a truly
# unencodable character degrades to a placeholder in the console log
# instead of crashing again -- the JSON/xlsx outputs are unaffected either
# way since they're written with explicit encoding="utf-8".
# ---------------------------------------------------------------------------
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Load secrets from .streamlit/secrets.toml into os.environ BEFORE any
# other imports, so NEO4J_*, OPENROUTER_API_KEY etc. are visible to graph_rag.py.
# graph_rag.py's own _get_secret() tries st.secrets first, then falls back
# to os.getenv -- outside a real `streamlit run` context, st.secrets access
# raises and is caught, so this os.environ population is what actually
# supplies the values.
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
# Patch st.cache_resource with a REAL lru_cache, same reasoning as
# run_naive_rag_eval.py: without this, _get_pipeline() (which opens the
# Neo4j driver) could rebuild on every single question instead of once.
# ---------------------------------------------------------------------------
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

# Now import graph_rag -- the patched decorators are in place.
from graph_rag import graph_rag

EVAL_PATH = os.getenv(
    "AEROOPS_EVAL_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "aeroops_goldset_v1_frozen.json")
)
OUTPUT_JSON = "graphrag_ragas_inputs.json"
OUTPUT_XLSX = "graphrag_eval_results.xlsx"
SLEEP_BETWEEN = 1.2   # seconds between questions -- rate-limit courtesy


def load_eval_set(path: str):
    """Same flat-array schema as run_naive_rag_eval.py's load_eval_set --
    reads directly from the frozen, jury-verified 45-item gold set."""
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
    print("Note: item 1 will be slower than the rest -- it's the one that "
          "builds the cached GraphRAG pipeline (Neo4j connection, retriever, "
          "generator), which every later item reuses.\n")

    ragas_rows = []
    result_rows = []

    for i, item in enumerate(items):
        qid = item["id"]
        question = item["question"]
        print(f"[{i+1:02d}/{len(items)}] {qid}: {question[:70]}...")

        t0 = time.time()
        try:
            output = graph_rag(question)
            answer = output.get("answer", "")
            sources = output.get("sources", []) or []
            contexts = [s.get("quote", "") for s in sources if s.get("quote")]
            elapsed = round(time.time() - t0, 2)

            print(f"    {answer[:80]}...")
            print(f"    {len(contexts)} contexts | retrieval_type="
                  f"{output.get('retrieval_type')} | {elapsed}s")

            retrieval_error = output.get("retrieval_error")
            generation_error = output.get("generation_error")
            if retrieval_error:
                print(f"    RETRIEVAL ERROR (caught, answer is a fallback "
                      f"string): {retrieval_error}")
            if generation_error:
                print(f"    GENERATION ERROR (caught, answer is a fallback "
                      f"string): {generation_error}")

        except Exception as exc:
            elapsed = round(time.time() - t0, 2)
            answer = f"ERROR: {exc}"
            contexts = []
            output = {}
            retrieval_error = str(exc)
            generation_error = None
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
            # GraphRAG-specific extras -- not used by RAGAS, but kept so the
            # later mechanical scoring layer (node/edge recall against
            # ground_truth_nodes, path-order against expected_chain,
            # citation precision) doesn't require rerunning the pipeline.
            "Retrieval Type": output.get("retrieval_type"),
            "Reasoning Chain": output.get("reasoning_chain", []),
            "Matched Entities": output.get("matched_entities", []),
            "Path Nodes": output.get("path_nodes", []),
            "Path Edges": output.get("path_edges", []),
            "Retrieval Error": retrieval_error,
            "Generation Error": generation_error,
        })

        result_rows.append({
            "ID": qid,
            "Category": item["category"],
            "Question": question,
            "Expected Answer": item["ground_truth"],
            "Model Answer": answer,
            "Num Contexts": len(contexts),
            "Retrieval Type": output.get("retrieval_type"),
            "Time (s)": elapsed,
        })

        if i < len(items) - 1:
            time.sleep(SLEEP_BETWEEN)

    # Save RAGAS-compatible JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(ragas_rows, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved RAGAS inputs  -> {OUTPUT_JSON}")

    # Save human-readable xlsx
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "GraphRAG Results"
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

    n_errors = sum(1 for r in ragas_rows
                   if r["Retrieval Error"] or r["Generation Error"])
    n_empty = sum(1 for r in ragas_rows if not str(r["Model Answer"]).strip())
    print(f"\nDone. {len(ragas_rows)}/{len(items)} items evaluated.")
    print(f"Items with a caught retrieval/generation error: {n_errors}")
    print(f"Items with an empty answer: {n_empty}")
    if n_errors or n_empty:
        print("Check these before scoring -- same lesson as naive RAG: an "
              "error or empty answer will just come back as unscoreable "
              "NaN rather than a crash, easy to miss unless checked first.")
    print("\nNext: run score_graphrag_ragas.py to get GraphRAG RAGAS scores.")


if __name__ == "__main__":
    run_eval()
