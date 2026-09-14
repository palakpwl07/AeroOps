# Jury scoring prompt

Paste this into each judge tool (Claude Code / Opus 5, Codex / GPT-5.6, Qwen), one at a time, in this repo. Replace `<judge_name>` in the output filename with a short tag for whichever tool/model you're running it in (e.g. `opus5`, `gpt56`, `qwen`).

---

Read `evaluation/jury_scoring/answers_for_jury.json`. It's a list of 45 items, each with:

- `id`, `category`, `question`
- `expected_answer` -- the known-correct reference answer
- `system_a_answer`, `system_b_answer`, `system_c_answer` -- three different systems' answers to the same question, anonymized (you are not told which system is which -- judge each on its own merits, not by guessing the source)

For each item, judge each of `system_a_answer`, `system_b_answer`, `system_c_answer` independently against `expected_answer`, on **answer quality only**: does it convey the same essential facts, correctly? That is the only thing being scored here.

Explicitly OUT OF SCOPE for this judgment -- do not score, penalize, or even comment on any of these, they are measured separately elsewhere:
- Whether the answer cites a source at all, cites the "right" chunk/page, or cites enough sources (citation accuracy/recall)
- Citation format or style (`[CITE: file p.N]` vs `[chunk_id]` vs no citation at all -- ignore this entirely, it's a structural artifact of which system produced the answer, not a quality signal)
- How much was retrieved, how many sources were used, or how the answer is formatted/organized

Minor wording differences, extra detail, or omitting a side detail the expected answer includes do NOT count against an answer -- only judge whether the core factual content matches and nothing stated is factually wrong. If a system's answer explicitly says the information isn't available/found while the expected answer says otherwise, that counts as incorrect for that system on that item.

Write your verdicts to `evaluation/jury_scoring/scores_<judge_name>.json` as a JSON array, one object per item, in this exact shape:

```json
[
  {
    "id": "FH01",
    "system_a_correct": true,
    "system_b_correct": false,
    "system_c_correct": true,
    "notes": "one short sentence on any non-obvious call, empty string if none"
  }
]
```

All 45 items must appear in the output, in the same order as the input file. Don't modify `answers_for_jury.json` or read `answer_key.json` -- that file exists for scoring afterward, not for judging.
