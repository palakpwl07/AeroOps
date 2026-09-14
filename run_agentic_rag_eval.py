# run_agentic_rag_eval.py
#
# Runs all 45 questions from the frozen gold set through agentic_rag() --
# the wired routing system (structural_pattern_router.route() -> naive_rag
# or graph_rag) -- and saves outputs in RAGAS-compatible format, identical
# in shape to run_naive_rag_eval.py / run_graphrag_eval.py's output so
# score_graphrag_ragas.py can score it unmodified, with the same judge,
# for genuine three-way comparability.
#
# Mirrors run_graphrag_eval.py's structure closely on purpose: same UTF-8
# stdout fix, same secrets loading, same st.cache_resource -> lru_cache
# patch (applied to BOTH naive_rag._build_index and graph_rag._get_pipeline,
# since agentic_rag() can route any given item to either backend), same
# per-item try/except shape.
#
# Extra fields this run captures that neither prior eval recorded:
#   - Routing decision: which backend was chosen, which layer decided it
#     (pattern vs default).
#   - Latency broken 3 ways: routing_time (structural_pattern_router.route()
#     itself), retrieval_time, generation_time (both from the chosen
#     backend's own returned dict -- naive_rag() and graph_rag() both
#     already report these under the same key names).
#
# One disclosed methodological workaround: naive_rag()'s own returned
# dict does not include the raw retrieved chunk text (only source
# citations -- source_file/page/title, no "quote"/page_content), unlike
# graph_rag()'s sources which do include "quote". For a naive-routed
# item, this script makes one extra READ-ONLY call to
# naive_rag.hybrid_retrieve(question, k=5) -- the same function
# naive_rag() calls internally, same k -- purely to reconstruct the
# "Retrieved Contexts" RAGAS needs. This call is NOT timed and does not
# affect any latency number reported; it exists only so Context Recall
# is computable for naive-routed items without modifying naive_rag.py.
#
# Usage:
#   cd C:\Users\palak\OneDrive\Desktop\.aeroops
#   python run_agentic_rag_eval.py
#
# Output:
#   agentic_rag_ragas_inputs.json   -- feed into score_graphrag_ragas.py
#   agentic_rag_eval_results.xlsx   -- human-readable for manual review

from __future__ import annotations

import functools
import json
import os
import sys
import time

# Same fix as run_graphrag_eval.py -- an ordinary non-ASCII character in
# a generated answer (e.g. U+2011 non-breaking hyphen) crashes print() on
# Windows' cp1252 console codepage otherwise, and gets mistaken for a
# real pipeline failure inside the per-item try/except below.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Load secrets from .streamlit/secrets.toml into os.environ BEFORE any
# other imports, so NEO4J_*, OPENROUTER_API_KEY etc. are
# visible to naive_rag.py and graph_rag.py.
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
# Patch st.cache_resource with a REAL lru_cache, same reasoning as both
# prior eval scripts: without this, either backend's cached pipeline
# build (index build for naive, Neo4j connection for GraphRAG) could
# rebuild on every question instead of once. Applied once, before either
# naive_rag or graph_rag is imported -- agentic_rag() imports both, and
# either one can be hit on any given item depending on the route.
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

# Now import agentic_rag -- the patched decorators are in place for both
# naive_rag.py's and graph_rag.py's cached pipeline builders.
from agentic_rag import agentic_rag
from naive_rag import hybrid_retrieve

EVAL_PATH = os.getenv(
    "AEROOPS_EVAL_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "evaluation", "gold_set", "aeroops_goldset_v1_frozen.json")
)
OUTPUT_JSON = "agentic_rag_ragas_inputs.json"
OUTPUT_XLSX = "agentic_rag_eval_results.xlsx"
SLEEP_BETWEEN = 1.2   # seconds between questions -- rate-limit courtesy


def load_eval_set(path: str):
    """Same flat-array schema as the other two eval scripts."""
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


def _naive_contexts(question: str) -> list:
    """Read-only reconstruction of retrieved context text for a
    naive-routed item -- see module docstring. Not timed."""
    docs = hybrid_retrieve(question, k=5)
    return [doc.page_content for doc in docs]


def run_eval():
    print(f"\nLoading eval set from: {EVAL_PATH}")
    if not os.path.exists(EVAL_PATH):
        print(f"ERROR: eval file not found at {EVAL_PATH}")
        sys.exit(1)

    items = load_eval_set(EVAL_PATH)
    print(f"Loaded {len(items)} items.\n")
    print("Note: item 1 will be slower than the rest -- it may build "
          "either or both cached pipelines (naive's index, GraphRAG's "
          "Neo4j connection) depending on which backend(s) the first "
          "few items route to.\n")

    ragas_rows = []
    result_rows = []

    for i, item in enumerate(items):
        qid = item["id"]
        question = item["question"]
        print(f"[{i+1:02d}/{len(items)}] {qid}: {question[:70]}...")

        t0 = time.time()
        backend = None
        decided_by = None
        matched_patterns = []
        routing_time = None
        retrieval_time = None
        generation_time = None
        crashed = False
        crash_detail = None
        try:
            output = agentic_rag(question)
            answer = output.get("answer", "")
            backend = output.get("backend")
            routing = output.get("routing", {})
            decided_by = routing.get("decided_by")
            matched_patterns = routing.get("matched_patterns", [])
            routing_time = routing.get("routing_time")

            backend_output = output.get("backend_output", {}) or {}
            retrieval_time = backend_output.get("retrieval_time")
            generation_time = backend_output.get("generation_time")

            if backend == "graphrag":
                sources = backend_output.get("sources", []) or []
                contexts = [s.get("quote", "") for s in sources if s.get("quote")]
                retrieval_error = backend_output.get("retrieval_error")
                generation_error = backend_output.get("generation_error")
            else:
                contexts = _naive_contexts(question)
                retrieval_error = None
                generation_error = backend_output.get("generation_error")

            elapsed = round(time.time() - t0, 2)

            # MH01 crashed with "ERROR: 'NoneType' object is not
            # subscriptable" in the prior router-diagnosis pass (a raw
            # exception surfacing as the answer text, not a caught
            # graph_rag() fallback). Flag it explicitly if the pipeline
            # itself returned that pattern rather than raising here.
            if isinstance(answer, str) and answer.startswith("ERROR:"):
                crashed = True
                crash_detail = answer

            print(f"    {answer[:80]}...")
            print(f"    backend={backend} (decided_by={decided_by}) | "
                  f"{len(contexts)} contexts | {elapsed}s")
            if retrieval_error:
                print(f"    RETRIEVAL ERROR (caught, fallback answer): {retrieval_error}")
            if generation_error:
                print(f"    GENERATION ERROR (caught, fallback answer): {generation_error}")
            if crashed:
                print(f"    *** CRASH DETECTED IN ANSWER TEXT: {crash_detail}")

        except Exception as exc:
            elapsed = round(time.time() - t0, 2)
            answer = f"ERROR: {exc}"
            contexts = []
            retrieval_error = str(exc)
            generation_error = None
            crashed = True
            crash_detail = str(exc)
            print(f"    UNCAUGHT ERROR (raised out of agentic_rag()): {exc}")

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
            # Routing/latency extras -- not used by RAGAS, kept so the
            # comparison in this eval's own summary doesn't require
            # rerunning the pipeline.
            "Backend": backend,
            "Decided By": decided_by,
            "Matched Patterns": matched_patterns,
            "Routing Time (s)": routing_time,
            "Retrieval Time (s)": retrieval_time,
            "Generation Time (s)": generation_time,
            "Crashed": crashed,
            "Crash Detail": crash_detail,
            "Retrieval Error": retrieval_error,
            "Generation Error": generation_error,
        })

        result_rows.append({
            "ID": qid,
            "Category": item["category"],
            "Question": question,
            "Expected Answer": item["ground_truth"],
            "Model Answer": answer,
            "Backend": backend,
            "Decided By": decided_by,
            "Num Contexts": len(contexts),
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
        ws.title = "Agentic RAG Results"
        headers = list(result_rows[0].keys())
        ws.append(headers)
        for row in result_rows:
            ws.append([row[h] for h in headers])
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 28
        wb.save(OUTPUT_XLSX)
        print(f"Saved readable results -> {OUTPUT_XLSX}")
    except ImportError:
        print("openpyxl not installed -- xlsx skipped, JSON is complete.")

    n_errors = sum(1 for r in ragas_rows
                   if r["Retrieval Error"] or r["Generation Error"])
    n_crashed = sum(1 for r in ragas_rows if r["Crashed"])
    n_empty = sum(1 for r in ragas_rows if not str(r["Model Answer"]).strip())
    n_naive = sum(1 for r in ragas_rows if r["Backend"] == "naive")
    n_graphrag = sum(1 for r in ragas_rows if r["Backend"] == "graphrag")
    print(f"\nDone. {len(ragas_rows)}/{len(items)} items evaluated.")
    print(f"Routed to naive: {n_naive} | Routed to graphrag: {n_graphrag}")
    print(f"Items with a caught retrieval/generation error: {n_errors}")
    print(f"Items with a crash surfaced as answer text or raised uncaught: {n_crashed}")
    print(f"Items with an empty answer: {n_empty}")
    mh01 = next((r for r in ragas_rows if r["ID"] == "MH01"), None)
    if mh01:
        if mh01["Crashed"]:
            print(f"\nMH01 CRASHED AGAIN: {mh01['Crash Detail']}")
            print("This reproduces the prior router-diagnosis pass's failure -- "
                  "confirmed as a reproducible bug in graph_rag.py, not transient.")
        else:
            print(f"\nMH01 succeeded this run (backend={mh01['Backend']}, "
                  f"answer starts: {str(mh01['Model Answer'])[:80]}...). "
                  "This is evidence the prior crash was likely transient "
                  "(rate-limit/timing), not structural.")
    print("\nNext: run score_graphrag_ragas.py against this run's "
          "graphrag_ragas_inputs.json (copy/rename as needed) to score it "
          "with the same judge as naive/GraphRAG.")


if __name__ == "__main__":
    run_eval()
