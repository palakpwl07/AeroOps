# run_live_api_eval.py
#
# Measurement run only: posts all 45 frozen gold-set questions to the
# LIVE deployed /query endpoint (not a direct graph_rag() call) so the
# numbers reflect exactly what the frontend and the real API path
# produce -- retrieval_time, generation_time, prompt_tokens,
# completion_tokens, estimated_cost_usd, provider -- against the current
# self-hosted-Neo4j-on-the-same-EC2-instance topology, for the MRO
# business case's aggregate numbers. No gold-set content or graph_rag.py
# logic touched; this only calls the already-running HTTP endpoint.
#
# Usage:
#   python run_live_api_eval.py

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://100.53.229.19:8000"
GOLD_PATH = Path("evaluation/gold_set/aeroops_goldset_v1_frozen.json")
OUTPUT_PATH = Path("evaluation/harness_runs") / f"live_api_run_{int(time.time())}.json"
REQUEST_TIMEOUT_SECONDS = 90


def post_query(question: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}/query",
        data=json.dumps({"question": question}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        return {"status": resp.status, "body": json.loads(resp.read())}


def main() -> None:
    with open(GOLD_PATH, encoding="utf-8") as f:
        gold = json.load(f)
    print(f"Loaded {len(gold)} gold-set items. Target: {BASE_URL}/query\n")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = []

    for i, item in enumerate(gold):
        qid = item["id"]
        question = item["question"]
        print(f"[{i+1:02d}/{len(gold)}] {qid}: {question[:65]}...")

        t0 = time.time()
        try:
            result = post_query(question)
            wall_time = time.time() - t0
            body = result["body"]
            row = {
                "id": qid,
                "category": item.get("category"),
                "question": question,
                "http_status": result["status"],
                "wall_time": round(wall_time, 2),
                "answer": body.get("answer"),
                "retrieval_time": body.get("retrieval_time"),
                "generation_time": body.get("generation_time"),
                "prompt_tokens": body.get("prompt_tokens"),
                "completion_tokens": body.get("completion_tokens"),
                "estimated_cost_usd": body.get("estimated_cost_usd"),
                "provider": body.get("provider"),
                "degraded": body.get("degraded"),
                "degraded_fields": body.get("degraded_fields"),
                "num_sources": len(body.get("sources") or []),
                "error": None,
            }
            print(f"    OK  wall={row['wall_time']}s retrieval={row['retrieval_time']}s "
                  f"generation={row['generation_time']}s cost=${row['estimated_cost_usd']} "
                  f"provider={row['provider']} degraded={row['degraded']}")
        except urllib.error.HTTPError as exc:
            wall_time = time.time() - t0
            body_text = exc.read().decode("utf-8", errors="replace")
            row = {
                "id": qid, "category": item.get("category"), "question": question,
                "http_status": exc.code, "wall_time": round(wall_time, 2),
                "answer": None, "retrieval_time": None, "generation_time": None,
                "prompt_tokens": None, "completion_tokens": None,
                "estimated_cost_usd": None, "provider": None,
                "degraded": None, "degraded_fields": None, "num_sources": 0,
                "error": f"HTTP {exc.code}: {body_text[:300]}",
            }
            print(f"    HTTP ERROR {exc.code}: {body_text[:200]}")
        except Exception as exc:
            wall_time = time.time() - t0
            row = {
                "id": qid, "category": item.get("category"), "question": question,
                "http_status": None, "wall_time": round(wall_time, 2),
                "answer": None, "retrieval_time": None, "generation_time": None,
                "prompt_tokens": None, "completion_tokens": None,
                "estimated_cost_usd": None, "provider": None,
                "degraded": None, "degraded_fields": None, "num_sources": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(f"    FAILED: {type(exc).__name__}: {exc}")

        results.append(row)

        # Incremental save -- a later failure shouldn't lose earlier results.
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"base_url": BASE_URL, "items": results}, f, indent=2, ensure_ascii=False)

        time.sleep(0.5)

    print(f"\nSaved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
