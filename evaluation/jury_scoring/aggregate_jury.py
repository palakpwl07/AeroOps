# aggregate_jury.py
#
# Combines the three independent jury verdicts (Claude Code/Opus 5,
# Codex/GPT-5.6, Qwen3.8 Max) into a majority-vote correctness score per
# system per item, decoded via answer_key.json (never shown to the
# judges). Same "don't trust one judge" principle used throughout this
# project -- majority of 3 wins, and how often all 3 agreed is reported
# alongside the score, not hidden, since a low-agreement item is a weaker
# data point than a unanimous one even if the majority verdict is used
# the same way in the aggregate.
#
# Usage:
#   python evaluation/jury_scoring/aggregate_jury.py

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent

JUDGE_FILES = {
    "opus5": "scores_opus5.json",
    "gpt56sol": "scores_gpt56sol.json",
    "qwen38max": "scores_qwen38max.json",
}
SYSTEMS = ["system_a", "system_b", "system_c"]


def load_judge_scores():
    scores = {}
    for judge, fname in JUDGE_FILES.items():
        path = _HERE / fname
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        scores[judge] = {it["id"]: it for it in data}
    return scores


def main():
    answer_key = json.load(open(_HERE / "answer_key.json", encoding="utf-8"))
    answers = json.load(open(_HERE / "answers_for_jury.json", encoding="utf-8"))
    judge_scores = load_judge_scores()

    judges = list(JUDGE_FILES.keys())
    n_items = len(answers)

    per_item_results = []
    for item in answers:
        qid = item["id"]
        row = {"id": qid, "category": item["category"], "question": item["question"]}
        for system in SYSTEMS:
            key = f"{system}_correct"
            votes = []
            for judge in judges:
                verdict = judge_scores[judge].get(qid)
                if verdict is None:
                    print(f"WARNING: {judge} has no verdict for {qid}")
                    continue
                votes.append(bool(verdict[key]))
            yes_count = sum(votes)
            majority_correct = yes_count > len(votes) / 2 if votes else None
            agreement = (
                "unanimous" if votes and yes_count in (0, len(votes)) else "split"
            )
            real_system = answer_key[system]
            row[real_system] = {
                "correct": majority_correct,
                "agreement": agreement,
                "votes": {judge: judge_scores[judge][qid][key] for judge in judges if qid in judge_scores[judge]},
            }
        per_item_results.append(row)

    # ---- Aggregate summary ----
    def rate_for(system_name: str, items=None) -> dict:
        rows = items if items is not None else per_item_results
        scored = [r[system_name]["correct"] for r in rows if r[system_name]["correct"] is not None]
        unanimous = [r for r in rows if r[system_name]["agreement"] == "unanimous"]
        return {
            "n_items": len(scored),
            "correct_rate": round(sum(scored) / len(scored), 3) if scored else None,
            "n_correct": sum(scored),
            "unanimous_rate": round(len(unanimous) / len(rows), 3) if rows else None,
        }

    real_systems = sorted(set(answer_key.values()))
    overall_summary = {sys_name: rate_for(sys_name) for sys_name in real_systems}

    categories = sorted({r["category"] for r in per_item_results})
    per_category_summary = {}
    for cat in categories:
        cat_items = [r for r in per_item_results if r["category"] == cat]
        per_category_summary[cat] = {sys_name: rate_for(sys_name, cat_items) for sys_name in real_systems}

    # Direct answer to "is agentic's routing earning its keep": compare
    # agentic's correct_rate against graphrag's correct_rate on ONLY the
    # items agentic actually routed to naive -- that's the marginal value
    # naive is contributing, isolated from the 43 items where agentic and
    # graphrag are identical by construction (same backend, same answer).
    naive_routed_ids = set()
    # Re-derive routing from the original generation file if available;
    # otherwise this section is skipped with a note.
    gen_files = sorted((_HERE.parent / "harness_runs").glob("generation_*.json"))
    routing_note = None
    if gen_files:
        gen_data = json.load(open(gen_files[-1], encoding="utf-8"))
        naive_routed_ids = {
            it["id"] for it in gen_data["per_item"] if it["agentic"].get("routed_to") == "naive"
        }
    else:
        routing_note = "No generation_*.json found -- couldn't isolate naive-routed items."

    naive_routed_comparison = None
    if naive_routed_ids:
        routed_rows = [r for r in per_item_results if r["id"] in naive_routed_ids]
        naive_routed_comparison = {
            "item_ids": sorted(naive_routed_ids),
            "naive_correct_rate_on_these": rate_for("naive", routed_rows)["correct_rate"],
            "graphrag_correct_rate_on_these": rate_for("graphrag", routed_rows)["correct_rate"],
        }

    report = {
        "overall": overall_summary,
        "per_category": per_category_summary,
        "naive_routed_items_comparison": naive_routed_comparison or {"note": routing_note},
        "per_item": per_item_results,
    }

    out_path = _HERE / "aggregated_jury_scores.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("======= OVERALL (majority of 3 judges, answer quality only) =======")
    for sys_name in real_systems:
        s = overall_summary[sys_name]
        print(f"  {sys_name:10s} correct_rate={s['correct_rate']}  ({s['n_correct']}/{s['n_items']})  "
              f"unanimous_rate={s['unanimous_rate']}")

    if naive_routed_comparison:
        print(f"\n======= THE ACTUAL QUESTION: is naive's upkeep earning its keep? =======")
        print(f"  Items agentic routed to naive: {naive_routed_comparison['item_ids']}")
        print(f"  naive's correct_rate on these:    {naive_routed_comparison['naive_correct_rate_on_these']}")
        print(f"  graphrag's correct_rate on these: {naive_routed_comparison['graphrag_correct_rate_on_these']}")

    print(f"\nFull results (per-item, per-category) saved -> {out_path}")


if __name__ == "__main__":
    main()
