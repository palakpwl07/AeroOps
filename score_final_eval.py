# score_final_eval.py
#
# Scoring phase of the fixed AeroOps evaluation harness. Loads a
# generation-phase output file (from run_final_eval.py -- naive/graphrag/
# agentic answers + mechanical metrics already computed) and adds the
# jury-of-3 answer-correctness verdict: 3 independent models
# (deepseek/qwen/gpt-4o-mini, all via OpenRouter) each vote on whether a
# system's answer conveys the same essential facts as the gold set's own
# expected_answer, majority wins. Same "don't trust one judge" principle
# the gold set itself was built and validated with (see its own
# jury_agreement field) -- applied here so the harness doesn't repeat
# RAGAS Faithfulness's single-judge-variance problem under a new name.
#
# Kept separate from generation on purpose: this is the expensive step
# (3 judge calls x 3 systems x N items) and the one most worth rerunning
# in isolation -- e.g. to add a 4th judge model, or re-score an existing
# generation run without re-paying for retrieval+generation.
#
# Usage:
#   python score_final_eval.py --input evaluation/harness_runs/generation_<ts>.json
#   python score_final_eval.py                 # uses the most recent generation_*.json

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional

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

from openai import OpenAI
import eval_common as ec

OUTPUT_DIR = Path(_BASE_DIR) / "evaluation" / "harness_runs"
SYSTEMS = ["naive", "graphrag", "agentic"]
JURY_MODELS = ["deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct", "openai/gpt-4o-mini"]

JURY_PROMPT = """You are checking whether a system's answer conveys the same essential facts as a known-correct expected answer, for the given question.

QUESTION: {question}

EXPECTED ANSWER: {expected}

SYSTEM'S ANSWER: {actual}

Does the system's answer convey the same essential facts as the expected answer? Minor wording differences, extra detail, or a different citation style do NOT count against it -- only judge whether the core factual content matches. Respond with exactly one word: YES or NO."""

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://palakporwal.site",
                "X-Title": "AeroOps Eval Harness Jury",
            },
        )
    return _client


def jury_verdict(question: str, expected: str, actual: str) -> Dict[str, Any]:
    client = get_client()
    votes, raw = [], {}
    for model in JURY_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": JURY_PROMPT.format(
                    question=question, expected=expected, actual=actual or "(empty answer)")}],
                temperature=0,
                max_tokens=5,
            )
            text = (resp.choices[0].message.content or "").strip().upper()
            votes.append(text.startswith("Y"))
            raw[model] = text
        except Exception as exc:
            raw[model] = f"ERROR: {exc}"
    if not votes:
        return {"correct": None, "votes": raw, "agreement": None}
    yes_count = sum(votes)
    return {
        "correct": yes_count > len(votes) / 2,
        "votes": raw,
        "agreement": "unanimous" if yes_count in (0, len(votes)) else "split",
    }


def latest_generation_file() -> str:
    candidates = sorted(glob.glob(str(OUTPUT_DIR / "generation_*.json")))
    if not candidates:
        print(f"ERROR: no generation_*.json found in {OUTPUT_DIR}. Run run_final_eval.py first.")
        sys.exit(1)
    return candidates[-1]


def summarize(system_key: str, per_item: list) -> Dict[str, Any]:
    rows = [it[system_key] for it in per_item]
    summary = {k: ec.mean_of(k, rows) for k in ec.CORE_METRIC_KEYS}
    summary["degraded_rate"] = ec.safe_ratio(sum(1 for r in rows if r.get("degraded")), len(rows))
    jury_scored = [r for r in rows if r.get("jury", {}).get("correct") is not None]
    if jury_scored:
        summary["answer_correct_rate"] = ec.safe_ratio(
            sum(1 for r in jury_scored if r["jury"]["correct"]), len(jury_scored)
        )
        agreement_counts = Counter(r["jury"]["agreement"] for r in jury_scored)
        summary["jury_unanimous_rate"] = ec.safe_ratio(agreement_counts.get("unanimous", 0), len(jury_scored))
    summary["n_items"] = len(rows)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="generation_*.json from run_final_eval.py")
    args = ap.parse_args()

    input_path = args.input or latest_generation_file()
    print(f"Scoring: {input_path}")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    per_item = data["per_item"]
    print(f"Loaded {len(per_item)} item(s). Jury models: {', '.join(JURY_MODELS)}\n")

    for i, item in enumerate(per_item):
        qid = item["id"]
        print(f"[{i+1:02d}/{len(per_item)}] {qid}")
        for system in SYSTEMS:
            row = item[system]
            row["jury"] = jury_verdict(item["question"], item.get("expected_answer", ""), row.get("answer", ""))
            print(f"    {system:9s} correct={row['jury']['correct']} ({row['jury']['agreement']})")
        time.sleep(0.5)

    report = {
        "core_summary": {system: summarize(system, per_item) for system in SYSTEMS},
        "graphrag_only_diagnostics": {
            k: ec.mean_of(k, [it["graphrag"]["diagnostics"] for it in per_item if "diagnostics" in it["graphrag"]])
            for k in ["node_recall", "node_precision", "chain_coverage", "edge_authenticity_rate"]
        },
        "per_item": per_item,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"scored_{int(time.time())}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n======= CORE METRICS (head-to-head, symmetric) =======")
    for system in SYSTEMS:
        print(f"\n{system.upper()}")
        for k, v in report["core_summary"][system].items():
            print(f"  {k:24s} {v}")
    print("\n======= GRAPHRAG-ONLY DIAGNOSTICS (not part of head-to-head) =======")
    for k, v in report["graphrag_only_diagnostics"].items():
        print(f"  {k:24s} {v}")
    print(f"\nFull results saved -> {out_path}")


if __name__ == "__main__":
    main()
