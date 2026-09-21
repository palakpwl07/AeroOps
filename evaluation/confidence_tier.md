# Confidence signals for AeroOps answers

**What this is, plainly: the tier is scope detection only. It does not verify that an answer is correct, and it must never be read as a correctness or confidence-in-the-answer score.** `LOW` means "no known engine entity was matched (or retrieval failed)", i.e. the question is probably outside what this knowledge graph covers. `STANDARD` means only "no scope warning": an answer can be `STANDARD` and still wrong (gold CD08 is a clean, fully-cited path with a fabricated claim). The guardrail that covers correctness is the persistent on-screen disclaimer in the UI, *"AeroOps is a decision-support tool. Verify outputs against approved maintenance documentation before any maintenance action."* -- not this tier.

Status: **live in `/query`** (2026-09). The response carries `scope_flag` (`LOW` / `STANDARD`), `answer_type` (`refusal` / `substantive` / `empty`) and `matched_entity_count`. The field is deliberately named `scope_flag`, not `confidence`. The UI shows a "Possibly outside AeroOps' scope" notice for `LOW`. Tests: `tests/test_confidence_tier.py`, `tests/test_main_scope_flag.py`.

No LLM is involved in either signal. Both are deterministic functions of things the pipeline already computes.

## Design

Two independent signals, deliberately not merged, because a refusal and a low-confidence substantive answer need different handling downstream.

| Signal | Values | Rule |
|---|---|---|
| `tier` | `LOW`, `STANDARD` | `LOW` if zero entities matched by `QueryRouter`, or retrieval failed / answer degraded. Otherwise `STANDARD`. |
| `answer_type` | `refusal`, `substantive`, `empty` | `refusal` if the answer's **first sentence** matches a denial pattern ("does not contain/provide...", "no information", "information not available", "I don't have...", etc.). `empty` for None/blank. Otherwise `substantive`. |
| `contains_denial` | bool | A denial pattern appears anywhere. Marks substantive answers that also say "the graph does not list X" part-way through (gold: DA04, DA06; smoke: #3). |

`STANDARD` means "no structural warning". It does **not** mean the answer was verified.

## What was tried and dropped

Two rounds of validation, both read-only.

**Round 1: 45-item gold set, grid search** against `aggregated_jury_scores.json` (6 jury-wrong answers; 12 counting split votes).

- Entity count carried nearly all the signal; the best rules flagged 42 to 49% of items for 4 to 5 of 6 wrong answers.
- Context count was no better than about 1 of 6 on its own. Its "<= 3" clause was a per-item patch for DA06 and OS04.
- Nothing beat the "entities <= 1 OR contexts <= 3" rule on both recall and flag rate, but that rule's false-positive rate was high.
- Zero entities never occurred on the gold set, so it produced no false alarms there (and no true positives either).

**Round 2: 20 new queries** through the live `/query` endpoint (12 in-domain, 8 random, adjacent-domain, malformed or broad).

- Zero entities was `LOW` for 8 of 20: sourdough, World Cup, piston engine, turboprop gearbox, lithium-ion battery, "engine bad noise what do", plus two in-domain queries that hit the vocabulary gap (below).
- `entities == 1` flagged 9 of 12 in-domain queries. Most were correct answers.
- **Context count is disproven as a signal.** Retrieval always returns something: turboprop gearbox, battery life and "tell me everything" retrieved 9 to 10 chunks despite matching no entity.

Result: context count and the `entities == 1` "VERIFY" tier are removed. About 40 to 45% of `entities == 1` flags fell on correct answers in both samples.

## Refusal detection: what the two data sets showed

- **Gold set (45):** no answer is a refusal. AF05's stored answer is `None` with `degraded: False`, so the `empty` class catches a jury-wrong item that the degraded flag missed. DA04 and DA06 are substantive answers that end with a partial denial.
- **Smoke test (20):** 9 refusals (#7, 9, 12, 13, 14, 15, 16, 17, 19). Three of them (#7, 9, 12) are `STANDARD`, so a refusal cannot be inferred from the tier.
- Both directions are real: `LOW` includes substantive answers (#2, #20), and `STANDARD` includes refusals.
- #7 (N-CMAPSS) was a false denial (about 1 in 3 identical requests): the `MODELS` edge to hardware deterioration (claim CL071, chunk D2_c05) was never retrieved, because star retrieval only read certain edge types. Fixed 2026-09-21 by `fetch_anchor_relations` (retrieval) plus prompt rule 16 (generation must state a direct relationship only as far as its own line and chunk say). Refusal detection flags such an answer as a refusal, which is what a downstream check needs, but it cannot tell a correct refusal from a false one.
- #16 opens with a refusal and then pads with unrelated failure modes. First-sentence detection labels it `refusal`; the padding is only visible through `contains_denial` plus reading the text.

## Known limitations

1. **ENTITY_MAP vocabulary gaps inflate LOW false positives.** "Fuel burn" (smoke #2) and "tell me everything about turbofans" (#20) match zero entities although they are in-domain. #2 received a reasonable grounded answer yet is `LOW`. "Hot section" is also unmatched (smoke #3). Until `ENTITY_MAP` is extended (a separate change), `LOW` partly measures phrasing, not just domain coverage. The two affected smoke queries are pinned in the tests as `KNOWN_GAP` and should be removed from that set when the map is fixed, not silently re-baselined.
2. **`STANDARD` is not a correctness claim.** A clean path with real edges and multiple entities can still contain a fabricated claim (gold CD08 is the example).
3. **Entity map fit.** `ENTITY_MAP` was built alongside the gold set; entity counts on unseen phrasing may behave differently, and the smoke test shows this in both directions.
4. **Denial patterns are English string matches** derived from the refusals seen so far (gold and smoke). They will miss new phrasings, and could match a substantive first sentence that happens to contain a denial.
5. **Neither signal is a correctness label.** The tier is scope detection and `answer_type` is string matching; the UI disclaimer, not these fields, is the guardrail for correctness. Also: refusal is not a correctness label. A correct refusal on out-of-scope questions and a false refusal (#7) look identical to the detector.
6. **Small samples.** The gold set has 6 wrong answers; the smoke test is 20 hand-written queries judged by one reader (not the jury). Treat all figures as directional.
7. **Zero-entity queries still cost an LLM call** with whatever chunks the keyword fallback returns (about $0.00005 to $0.00014 per query, plus 2 to 7 seconds of latency), and irrelevant chunks can induce padding (#16). A pre-generation gate is a separate, not-yet-implemented change that depends on limitation 1 being fixed first.
