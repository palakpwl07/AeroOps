# run_final_eval.py
#
# Generation phase of the fixed AeroOps evaluation harness. Runs all three
# systems -- naive_rag(), graph_rag(), and agentic_rag() -- over the same
# frozen gold-set questions and saves their raw answers plus mechanical
# (non-LLM) metrics to disk. No jury/LLM-judge calls here on purpose: this
# step is cheap and fast to rerun on its own whenever the pipelines
# change, and its output feeds score_final_eval.py (the separate,
# expensive jury-scoring pass) without needing to regenerate answers.
#
# agentic_rag() doesn't do its own retrieval -- it routes to whichever
# backend the router picks and returns that backend's full output under
# backend_output. Its mechanical metrics are therefore computed the exact
# same way as that backend's (naive-style if routed to naive, graphrag-
# style if routed to graphrag), tagged with which backend/route it used so
# that's visible in the report, not hidden.
#
# Usage:
#   python run_final_eval.py                 # full 45-item run
#   python run_final_eval.py --limit 6        # smaller run

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import tomllib
except ImportError:
    import tomli as tomllib

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_secrets_path = os.path.join(_BASE_DIR, ".streamlit", "secrets.toml")
if os.path.exists(_secrets_path):
    with open(_secrets_path, "rb") as f:
        for k, v in tomllib.load(f).items():
            os.environ.setdefault(k, str(v))
    print(f"Secrets loaded from {_secrets_path}")

import functools
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

from naive_rag import DOC_CONFIG
from agentic_rag import agentic_rag
from graph_rag import graph_rag
from naive_rag import naive_rag, hybrid_retrieve

import eval_common as ec

OUTPUT_DIR = Path(_BASE_DIR) / "evaluation" / "harness_runs"

# No timeout is configured anywhere on the Neo4j driver or the OpenRouter
# client in this codebase -- a dropped AuraDB connection (the same
# instability documented throughout this project) can block a call
# forever instead of raising, which stalled a real 45-item run on item 1's
# agentic_rag() call (confirmed via a flat CPU trace: no progress for 3+
# minutes on a call that normally takes single-digit seconds). Rather than
# add a timeout inside graph_rag.py itself (production code, out of scope
# here), this wraps each call at the harness level in its own thread with
# a hard deadline -- a timed-out item gets recorded as such and the run
# moves on, instead of the whole batch hanging indefinitely on one stuck
# request.
CALL_TIMEOUT_SECONDS = 90


def call_with_timeout(fn, *args, timeout=CALL_TIMEOUT_SECONDS):
    # A fresh single-worker executor per call, not a shared one -- a
    # stuck thread can never be force-killed, so reusing one executor
    # across calls would mean a single timed-out call permanently blocks
    # every call submitted after it (they'd queue behind the one worker
    # slot that never frees up). shutdown(wait=False) here means we never
    # block waiting for an abandoned thread to actually finish either.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args)
    try:
        result = future.result(timeout=timeout)
        executor.shutdown(wait=False)
        return result, None
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False)
        return None, f"timed out after {timeout}s"
    except Exception as exc:
        executor.shutdown(wait=False)
        return None, str(exc)


def _timed_out_stub(reason: str) -> Dict[str, Any]:
    return {"answer": "", "retrieval_time": None, "generation_time": None,
            "timed_out": True, "error": reason}


def score_agentic(item, agentic_output, gold_fp, chunk_map):
    backend = agentic_output["backend"]
    backend_output = agentic_output["backend_output"]
    if backend == "naive":
        mech = ec.score_naive_mechanical(backend_output, gold_fp)
    else:
        mech = ec.score_graphrag_mechanical_core(backend_output, gold_fp, chunk_map)
    mech["routed_to"] = backend
    mech["decided_by"] = agentic_output["routing"]["decided_by"]
    mech["matched_patterns"] = agentic_output["routing"]["matched_patterns"]
    return mech


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="Only run the first N gold-set items")
    args = ap.parse_args()

    gold = ec.load_gold()
    if args.limit:
        gold = gold[: args.limit]
    print(f"Loaded {len(gold)} gold-set item(s).\n")

    chunk_map = ec.build_chunk_filepage_map(DOC_CONFIG)
    print(f"Resolved {len(chunk_map)} chunk_id -> (filename, page) mappings.\n")

    # Built once, here, OUTSIDE the per-item timeout loop -- naive_rag's
    # FAISS/BM25 index build routinely takes 90-150s on this machine
    # (confirmed repeatedly this session), which is longer than
    # CALL_TIMEOUT_SECONDS. Without this warmup, item 1's naive_rag() call
    # would eat that one-time cost AND get judged against the same 90s
    # timeout meant for a single query, falsely recording it as "timed
    # out" when nothing was actually hung. Same pattern
    # run_naive_rag_eval.py already uses for the same reason.
    print("Warming naive RAG's index (one-time cost, not timed)...")
    t0 = time.time()
    hybrid_retrieve(gold[0]["question"], k=5)
    print(f"Index ready in {round(time.time()-t0, 1)}s.\n")

    per_item = []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"generation_{int(time.time())}.json"

    for i, item in enumerate(gold):
        qid = item["id"]
        question = item["question"]
        gfp = ec.gold_filepages(item, chunk_map)
        print(f"[{i+1:02d}/{len(gold)}] {qid}: {question[:70]}...")

        t0 = time.time()
        naive_out, naive_err = call_with_timeout(naive_rag, question)
        if naive_err:
            print(f"    naive    TIMED OUT/ERROR after {round(time.time()-t0, 2)}s: {naive_err}")
            naive_score = _timed_out_stub(naive_err)
        else:
            print(f"    naive    done in {round(time.time()-t0, 2)}s")
            naive_score = ec.score_naive_mechanical(naive_out, gfp)

        t0 = time.time()
        graphrag_out, graphrag_err = call_with_timeout(graph_rag, question)
        if graphrag_err:
            print(f"    graphrag TIMED OUT/ERROR after {round(time.time()-t0, 2)}s: {graphrag_err}")
            graphrag_score = _timed_out_stub(graphrag_err)
            graphrag_score["diagnostics"] = {}
        else:
            print(f"    graphrag done in {round(time.time()-t0, 2)}s")
            graphrag_score = ec.score_graphrag_mechanical_core(graphrag_out, gfp, chunk_map)
            graphrag_score["diagnostics"] = ec.graphrag_diagnostics(item, graphrag_out)

        t0 = time.time()
        agentic_out, agentic_err = call_with_timeout(agentic_rag, question)
        if agentic_err:
            print(f"    agentic  TIMED OUT/ERROR after {round(time.time()-t0, 2)}s: {agentic_err}")
            agentic_score = _timed_out_stub(agentic_err)
        else:
            print(f"    agentic  done in {round(time.time()-t0, 2)}s (routed_to={agentic_out['backend']})")
            agentic_score = score_agentic(item, agentic_out, gfp, chunk_map)

        per_item.append({
            "id": qid, "category": item.get("category"), "question": question,
            "expected_answer": item.get("expected_answer"),
            "naive": naive_score, "graphrag": graphrag_score, "agentic": agentic_score,
        })

        print(f"    retrieval_recall  naive={naive_score.get('retrieval_recall')} "
              f"graphrag={graphrag_score.get('retrieval_recall')} "
              f"agentic={agentic_score.get('retrieval_recall')}")

        # Saved after every item, not just at the end -- a later stall
        # (same AuraDB instability this timeout guard exists for) shouldn't
        # throw away everything completed so far.
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"per_item": per_item}, f, indent=2, ensure_ascii=False)

        time.sleep(1.0)

    print(f"\nSaved generation output -> {out_path}")
    print("Next: python score_final_eval.py --input " + str(out_path))


if __name__ == "__main__":
    main()
