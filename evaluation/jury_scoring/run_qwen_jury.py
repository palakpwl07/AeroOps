# run_qwen_jury.py
#
# Automates the third jury leg (Qwen3.8 Max) via OpenRouter, following the
# exact same instructions given manually to Claude Code/Opus 5 and
# Codex/GPT-5.6 for the other two legs (see PROMPT.md in this folder) --
# this one's cheap enough (~$0.05 for all 45 items in one call, confirmed
# against OpenRouter's listed $2/M input, $6/M output pricing) and
# mechanical enough to not need a human at the keyboard for it.
#
# Deliberately NOT a general eval-harness script: single purpose, matches
# the exact prompt/output contract the other two judges were given, so
# all three score files are directly comparable when aggregated.
#
# Usage:
#   python evaluation/jury_scoring/run_qwen_jury.py

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import tomllib
except ImportError:
    import tomli as tomllib

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent

_secrets_path = _REPO_ROOT / ".streamlit" / "secrets.toml"
if _secrets_path.exists():
    with open(_secrets_path, "rb") as f:
        for k, v in tomllib.load(f).items():
            os.environ.setdefault(k, str(v))
    print(f"Secrets loaded from {_secrets_path}")

from openai import OpenAI

MODEL = "qwen/qwen3.8-max-0902"
ANSWERS_PATH = _HERE / "answers_for_jury.json"
OUTPUT_PATH = _HERE / "scores_qwen38max.json"

# Same judging contract given to the other two judges in PROMPT.md --
# kept word-for-word so all three legs are scoring against identical
# instructions, just delivered differently (paste-in vs. API call).
INSTRUCTIONS = """For each item, judge each of `system_a_answer`, `system_b_answer`, `system_c_answer` independently against `expected_answer`, on **answer quality only**: does it convey the same essential facts, correctly? That is the only thing being scored here.

Explicitly OUT OF SCOPE for this judgment -- do not score, penalize, or even comment on any of these, they are measured separately elsewhere:
- Whether the answer cites a source at all, cites the "right" chunk/page, or cites enough sources (citation accuracy/recall)
- Citation format or style ([CITE: file p.N] vs [chunk_id] vs no citation at all -- ignore this entirely, it's a structural artifact of which system produced the answer, not a quality signal)
- How much was retrieved, how many sources were used, or how the answer is formatted/organized

Minor wording differences, extra detail, or omitting a side detail the expected answer includes do NOT count against an answer -- only judge whether the core factual content matches and nothing stated is factually wrong. If a system's answer explicitly says the information isn't available/found while the expected answer says otherwise, that counts as incorrect for that system on that item.

You are not told which system (naive RAG / GraphRAG / an agentic router) produced which answer -- judge each on its own merits, not by guessing the source.

Respond with a JSON array only, no other text, no markdown code fences, one object per item, in this exact shape, covering ALL items in the same order as the input:
[
  {"id": "FH01", "system_a_correct": true, "system_b_correct": false, "system_c_correct": true, "notes": "one short sentence on any non-obvious call, empty string if none"}
]
"""


BATCH_SIZE = 15  # 45 items -> 3 batches. Smaller, faster, individually
# retryable calls instead of one big one -- the first attempt (all 45 in
# one call) hung for 15+ minutes with no response and had to be killed;
# no way to tell from outside whether that was normal load or a genuine
# stall. Batching bounds the blast radius of any one call misbehaving and
# gives real incremental progress instead of an opaque all-or-nothing wait.
REQUEST_TIMEOUT_SECONDS = 150


def strip_code_fence(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


def call_with_timeout(fn, *args, timeout=REQUEST_TIMEOUT_SECONDS):
    # OpenAI(timeout=...) turned out not to actually bound this call --
    # a real run sat past 150s (confirmed via process CPU/liveness checks,
    # no timeout error ever raised) with no visible progress and had to be
    # killed manually. This wraps the call in its own thread with a hard
    # deadline instead, the same fix already proven reliable for a similar
    # hang in run_final_eval.py. A fresh executor per call (not shared) --
    # a stuck thread can't be force-killed, so reusing one executor would
    # mean a timed-out call blocks every call after it.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args)
    try:
        result = future.result(timeout=timeout)
        executor.shutdown(wait=False)
        return result
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False)
        raise TimeoutError(f"timed out after {timeout}s")
    except Exception:
        executor.shutdown(wait=False)
        raise


def score_batch(client: OpenAI, batch: list, attempt_label: str) -> list:
    prompt = (
        f"{INSTRUCTIONS}\n\nHere is the input data (the list of items to judge):\n\n"
        f"{json.dumps(batch, ensure_ascii=False)}"
    )
    print(f"  [{attempt_label}] calling {MODEL} for {len(batch)} item(s)...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        # Qwen3.8 Max reasons internally before answering (confirmed via a
        # test call: reasoning_tokens counted separately but drawn from
        # the same max_tokens budget as the actual content). A first
        # attempt at 8000 max_tokens came back with EMPTY content --
        # reasoning through all 45 items apparently consumed the whole
        # budget before any answer text was written. Fixed with a larger
        # budget and effort="low" (this is bulk yes/no classification,
        # not a task that needs deep reasoning).
        max_tokens=16000,
        extra_body={"reasoning": {"effort": "low"}},
    )
    raw = response.choices[0].message.content or ""
    text = strip_code_fence(raw)

    usage = getattr(response, "usage", None)
    if usage:
        print(f"    token usage: {usage}")
    if not text.strip():
        reasoning_text = getattr(response.choices[0].message, "reasoning", None)
        print("    WARNING: empty content.")
        if reasoning_text:
            print(f"    model's reasoning (first 300 chars): {reasoning_text[:300]}")
        raise ValueError("empty content from model")

    return json.loads(text)


def main():
    with open(ANSWERS_PATH, encoding="utf-8") as f:
        items = json.load(f)
    print(f"Loaded {len(items)} items from {ANSWERS_PATH}")

    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://palakporwal.site",
            "X-Title": "AeroOps Jury Scoring (Qwen3.8 Max)",
        },
    )

    batches = [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    all_scores = []

    for batch_idx, batch in enumerate(batches):
        label = f"batch {batch_idx + 1}/{len(batches)}"
        try:
            scores = call_with_timeout(score_batch, client, batch, label)
        except Exception as exc:
            print(f"  {label} FAILED ({exc}); retrying once...")
            try:
                scores = call_with_timeout(score_batch, client, batch, f"{label} retry")
            except Exception as exc2:
                print(f"  {label} FAILED AGAIN ({exc2}); skipping this batch.")
                print(f"  Missing ids: {[it['id'] for it in batch]}")
                continue
        all_scores.extend(scores)
        print(f"  {label} done: {len(scores)} item(s) scored.")

        # Save after every batch, not just at the end -- partial progress
        # survives even if a later batch fails outright.
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_scores, f, indent=2, ensure_ascii=False)

    # Same validation applied to the two manually-produced score files
    # before trusting them -- count, ids, required keys all present.
    input_ids = [it["id"] for it in items]
    output_ids = [it.get("id") for it in all_scores]
    missing_keys = [
        it for it in all_scores
        if not all(k in it for k in ("id", "system_a_correct", "system_b_correct", "system_c_correct"))
    ]

    print(f"\nReceived {len(all_scores)}/{len(items)} scored item(s) total.")
    if set(output_ids) != set(input_ids):
        print("WARNING: output ids don't match input ids exactly.")
        print(f"  missing from output: {set(input_ids) - set(output_ids)}")
        print(f"  unexpected in output: {set(output_ids) - set(input_ids)}")
    if missing_keys:
        print(f"WARNING: {len(missing_keys)} item(s) missing required keys.")

    print(f"Saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
