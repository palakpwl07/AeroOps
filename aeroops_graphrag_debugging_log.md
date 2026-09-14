# AeroOps GraphRAG Debugging Log

A complete record of every bug found, diagnosed, and fixed while building
the GraphRAG evaluation pipeline and chasing an honest Faithfulness /
Context Recall comparison against naive RAG. Kept as a reference for
future work on this codebase, and as raw material for anything written
about this project later (interview prep, portfolio writeup, etc).

**Final result:** GraphRAG Faithfulness 0.51 / Context Recall 0.64 vs
Naive RAG Faithfulness 0.68 / Context Recall 0.48, both fully complete
(45/45), both independently verified. GraphRAG's recall advantage is real
and concentrated exactly where its design should produce it
(multi_hop_causal, operational_scenario). Its faithfulness deficit on
cross_document and aggregation_fanout is real and still open.

---

## Part 1 — Infrastructure

### 1.1 Neo4j AuraDB Free — paused, then deleted
AuraDB Free auto-pauses on inactivity and, if missed, auto-deletes after
an inactivity email goes unanswered. Hit both: a pause mid-session during
jury verification, and a full deletion later in the project. Considered
migrating the retriever to an in-memory graph (NetworkX, loaded from the
JSON export) to remove the dependency entirely; ultimately resolved by
restoring the instance with fresh credentials and relying on a keep-alive
cron going forward (same pattern already used for SentinelSCM).

### 1.2 Groq model deprecation — `llama-3.1-8b-instant`
Fully shut down by Groq on August 16, not just deprecated. Caused
`404 model_not_found` everywhere it was hardcoded as a default:
`naive_rag.py`'s `GROQ_MODEL`, `score_naive_rag_ragas.py`'s
`RAGAS_JUDGE_MODEL`, and `graph_rag.py`'s `GRAPHRAG_GROQ_MODEL`. Fixed by
switching to `openai/gpt-oss-20b` (Groq's own migration recommendation).

### 1.3 Reasoning-model token budget collisions
`gpt-oss-20b` is a reasoning model — it spends real output tokens on
internal chain-of-thought before producing an answer.
- Unset `max_tokens` → `LLMDidNotFinishException` (truncated mid-reasoning).
  Fixed by setting `max_tokens=16000`.
- `reasoning_effort` passed inside `model_kwargs` → LangChain warning, and
  Claude Code independently sent the literal string `"high"`, which
  TokenRouter's Qwen endpoint didn't accept (`xhigh`/`medium`/`low` only) →
  400 error. Fixed by passing `reasoning_effort` as a direct kwarg, not
  nested.
- `max_tokens=16000` in a single request exceeded Groq's account-level
  **8000 TPM** (tokens-per-minute) cap outright, independent of the
  separate 200K/day cap → 413 `Request too large`. This was on a fresh
  day, so it wasn't the daily cap reappearing, it was a second, tighter,
  previously-undiscovered ceiling.

**Eventual fix for the RAGAS judge specifically:** moved off Groq
entirely, onto `openai/gpt-4o-mini` via OpenRouter — not a reasoning
model, no token-burn unpredictability, paid (~$0.40 total for the whole
project), multi-provider-served (no free-tier queue instability).

### 1.4 Model selection detour (jury verification phase)
Explored DeepSeek V4 (TokenRouter), then a "stealth" model called Ox
Alpha — confirmed via search this was **not** Qwen (different tokenizer
signature; likely an unreleased GLM checkpoint) and was an anonymous,
time-limited preview, rejected as a jury member for exactly that reason:
not nameable, not stable, not citable later. Settled on Qwen3.8 Max
(free tier, TokenRouter).

### 1.5 Routing Claude Code through TokenRouter (Qwen jury pass)
Multiple compounding issues before this worked:
- LiteLLM config file placed in the wrong folder (`.aeroops` vs
  `.aeroops\knowledgebase`).
- PowerShell `$env:VAR = "value"` syntax vs bash `export VAR=value`
  confusion, repeated more than once.
- Confirmed talking to the **Claude Desktop app**, not the actual `claude`
  CLI — env vars set in one didn't apply to the other, and the model
  self-identified as "Claude Opus 5" because requests were quietly
  bypassing the proxy entirely.
- `ANTHROPIC_MODEL` env var required in addition to `ANTHROPIC_BASE_URL`/
  `ANTHROPIC_AUTH_TOKEN` — Claude Code has hardcoded "opus"/"sonnet"/
  "haiku" aliases and needs to be told explicitly to request a different
  model name from the gateway.
- Desktop app's "Configure Third-Party Inference" panel turned out to be
  version-gated / not present — abandoned in favor of the standalone
  terminal `claude` CLI, which is the mechanism that's actually
  well-documented and works.
- Free-tier 503 `ServiceUnavailable` errors under load — mitigated with
  batching (5 batches of 9 questions, explicit append-not-overwrite
  instructions between batches) and accepting that free-tier stability
  isn't guaranteed.

### 1.6 Neo4j node/relationship count scare
The live README stated 267 nodes / 560 relationships; every JSON export
used all night showed 111 nodes / 112 relationships. Resolved by running
label and relationship-type breakdowns directly against the live database:
the 10 domain-entity categories (FailureMode, Symptom, Cause, Mitigation,
etc.) matched **exactly**, 111 = 111. The gap was `Claim` (75) + `Chunk`
(74) + `Document` (7) nodes = 156, and `MENTIONED_IN` / `HAS_SUBJECT` /
`HAS_OBJECT` / `DERIVED_FROM` / `HAS_CHUNK` provenance edges = 448 —
real, correct, but represented as separate JSON arrays in the export
rather than folded into `nodes_total`/`relationships_total`. Not a data
gap. A counting-convention difference. Confirmed with exact arithmetic
before trusting it.

---

## Part 2 — RAGAS Scoring Pipeline Bugs

### 2.1 The truthiness bug (the big one)
`merge_scores()` in both `score_naive_rag_ragas.py` and
`score_graphrag_ragas.py` (copy-pasted, so the bug existed in both):

```python
"Faithfulness": s.get("faithfulness") or s.get("Faithfulness"),
```

In Python, `0.0 or X` evaluates to `X`, because `0.0` is falsy. Any item
that genuinely scored a real `0.0` got silently converted to `None`
(`s.get("Faithfulness")`, capital F, doesn't exist in RAGAS's output —
that's the tell). This was mistaken for hours as "missing scores" /
"API failures" requiring retries, when the scores had actually been
computed correctly the entire time and were just being discarded on
merge. Confirmed by checking raw JSON: `None` values (the bug) vs actual
`NaN` values (genuine failures) are distinguishable, and the vast
majority of "missing" data across both naive RAG and GraphRAG's first
scoring passes turned out to be this bug, not real failures.

**Fix:** explicit `is None` check instead of `or`.

### 2.2 Retry script cross-metric contamination
`retry_failed_*_items.py`'s original `rescore_missing()` pulled the
**entire row** into one combined RAGAS call whenever *either*
Faithfulness or Context Recall was missing — meaning an item only
missing one metric still had its other, already-real metric sent through
the judge a second time. Confirmed real regressions this caused:
`CD02`'s Context Recall went from a real `0.5` to `0.0`; `MH03`/`MH08`'s
Faithfulness changed on items that didn't need touching.

**Fix:** split rescoring into three separate calls — faithfulness-only,
recall-only, both-missing — so a real score is never re-exposed to the
judge.

### 2.3 Citation-bracket hypothesis (tested, wrong)
Hypothesized RAGAS's claim-decomposition step choked on inline
`[D3_c32]`-style citation tags, treating them as ungroundable pseudo-claims.
Built and tested a `strip_citations()` fix. Result: no meaningful change
(0.400 → 0.409 faithfulness). Ruled out. Kept the strip anyway since it's
harmless and arguably cleaner, but it was not the actual fix.

### 2.4 The real mechanism behind "known-correct answers scoring 0"
Confirmed directly: `D3_c32`'s actual chunk text was correctly cited in
`graph_facts` (a real mitigation, real confidence, real source) but was
**not present** in the flat `Retrieved Contexts` list fed to RAGAS for
scoring. RAGAS's Faithfulness/Context Recall can only check claims
against what's in that flat list — it has no visibility into the
separate, structured `graph_facts` channel. A correct, well-grounded
answer can score `0` simply because the metric was never shown the
evidence it needed to agree. This is the same architecture-mismatch
finding from the original AeroOps debugging session weeks earlier,
now reproduced and confirmed at the pipeline level, not just in one
hand-traced example.

---

## Part 3 — GraphRAG Retrieval & Generation Bugs

### 3.1 Generator fabrication (pre-fix)
Item-level review of early GraphRAG answers found the generator inventing
specific mechanisms not present in retrieval (a "bleed air / active
clearance control" explanation on FH03 that turned out to *actually* be
real, just mis-cited at the time; an invented "water washing" procedure
on CD01; an added "FOD" classification label on CD02 not explicit in
evidence) and conflating facts across unrelated chunks into false causal
links (MH01 attached a flameout-context symptom to a bearing-failure
chain).

**Fix:** tightened `answer_generator_groq.py`'s prompt with three new
rules — an explicit grounding check before stating any specific
mechanism/procedure, a hard citation whitelist (never cite an ID not
actually provided), and a rule against inferring causal connections
between two independently-true facts unless the evidence states the
connection directly.

### 3.2 Citation whitelist gap
The whitelist that rule 3.1 depends on originally only pulled valid chunk
IDs from the flat `evidence_chunks` list — not from citations embedded
inside `graph_facts` (which `context_builder.py` formats as strings like
`"Active clearance control [D3_c32]"`, not dicts with a `.chunks` field
by the time they reach the generator). This meant a legitimately-grounded
citation could be excluded from its own whitelist and effectively
unusable.

**Fix:** parse chunk IDs out of the bracketed tags in the formatted
strings, in addition to the flat evidence list.

### 3.3 Word-order-brittle entity matching (the big retrieval fix)
`ENTITY_MAP` phrase matching was exact contiguous substring only. FH03's
natural phrasing — "control the clearance between the rotor blade tips" —
never puts "tip" and "clearance" adjacent, the order `ENTITY_MAP`'s
`"tip clearance"` / `"blade-tip clearance"` phrases require. Verified
directly against live code: **9 of 45 questions (20%) matched zero
entities** for this exact reason, not a small edge case.

**Fix:** added a fallback pass to `_extract_keywords` — for any
`ENTITY_MAP` phrase that didn't match as an exact substring, check
whether all of its significant words appear anywhere in the question, in
any order. Verified: fixed 4 of 9 directly, plus caught two more
previously-undetected misses on already-partially-working questions
(`OS08`'s "fluctuations in EPR" → `SY_epr_fluctuation`) as a side effect.

### 3.4 ENTITY_MAP coverage gaps (separate problem, same symptom)
The remaining 5 of 9 zero-match questions weren't word-order issues —
they were genuine missing vocabulary: fuel puddling / tailpipe fire / dry
motoring (MH07), blade scrap rate / overhaul (CD03), an aggregated
"bearing monitoring parameters" concept spanning 4 separate entities
(AF04), NASA TM-81552 provenance references (PR01), and cooling-hole
blockage specificity vs a too-generic environmental-factor match (FH04).

**Fix:** delegated to Claude Code for a systematic audit (not just
patching the 5 known cases) — checked all 111 graph nodes for phrase
coverage, found 31 with zero coverage, deliberately left 24 unmapped with
documented reasoning (avoiding the same over-broad-expansion mistake that
caused 3.5 below), added targeted coverage for the rest. Verified against
all 45 questions, not just the 9, to catch side effects.

### 3.5 PR02/PR03 entity collision (regression from 3.4)
The "NASA TM-81552" provenance expansion added in 3.4 was a
document-level trigger — it fired identically for *any* question citing
that document, regardless of which specific claim within it the question
actually needed. This collapsed two different questions (PR02: residual/
unrestored SFC penalty, 0.2%; PR03: total long-term deterioration,
2.5-3.0%) into matching the same entity set. PR02's retrieval was
overwritten by PR03's evidence, and the generator confidently answered
PR02 with PR03's number.

**Fix:** subtractive, not additive. Confirmed the offending phrase
(`'clearance increases'`, arriving via `TERM_EXPANSIONS["tm 81552"]`) was
the sole cause, confirmed the rest of that expansion entry was redundant
with phrases already matching directly from each question's own text,
and removed the entry entirely rather than patching around it.

### 3.6 `retrieve_path()`'s FailureMode-only success check
Even after 3.5's fix, PR02 still failed. Root cause, confirmed line by
line: `retrieve_by_query_plan()`'s path-success check
(`if path_result.get("results"):`) only considers the path successful if
it produced at least one enriched, FailureMode-anchored row. But
`retrieve_path()` separately and correctly collects real chunk evidence
from the path's own edge provenance (`extra_chain_chunks`), independent
of whether any FailureMode node is on the path at all. PR02's actual path
— `MI_performance_restoration -[:RESTORES]-> PA_sfc` — is a direct
one-hop edge between a Mitigation and a Parameter, no FailureMode
involved. `chunk_ids` correctly contained `D4_c11`; `results` was `[]`;
the check saw the empty list, decided the path attempt failed, and threw
away the correct evidence in favor of a broader, wrong fallback search
that landed on an unrelated failure mode.

**Fix:** `if path_result.get("results") or path_result.get("chunk_ids"):`
— trust real, sourced evidence even when it has no FailureMode-anchored
row to attach it to. Known side effect, not fixed: the path's
reasoning-chain narrative still only attaches to `rows[0]`, so this case
gets the right answer with the right citation, but without the tidy
step-by-step trace GraphRAG normally provides.

---

## Part 4 — Verification Methodology Notes

Patterns worth reusing on future debugging, not just this project:

- **A "missing" score and a "real zero" score look identical unless you
  check the raw value type, not just whether it's falsy.** The
  truthiness bug (2.1) cost hours specifically because `None` and
  genuine `0.0` were being treated as the same signal.
- **A hypothesis that explains the data is still just a hypothesis until
  tested against live code and live data.** Two hypotheses tonight were
  wrong despite sounding plausible (citation-bracket parsing, 8-entity
  cap collision) and were only caught by actually running the current
  code against the current question text rather than reasoning from
  memory of earlier debugging sessions.
- **A fix that changes matching/retrieval behavior needs a full
  regression check, not just confirmation that the target case improved.**
  Every entity-matching fix in Part 3 was checked against all 45
  questions, not just the ones it was meant to fix — this is what caught
  3.5 as a side effect of 3.4, and what confirmed 3.3 and 3.6 didn't
  break anything that was already working.
- **Partial/incomplete eval runs bias toward the easy cases.** Every
  "gap-filled" number tonight came in lower than the corresponding
  partial number, across both systems, independently. Never trust an
  average computed on less than the full set without checking why the
  rest is missing.
