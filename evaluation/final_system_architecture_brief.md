# AeroOps Architecture Decision Brief

**Purpose:** working document sourcing the "Final System" tab of the evaluation report. Every claim below is sourced to a specific file, line, or dataset already in this repo (or the project's Notion dev log, "Aeroops Development," last edited 2026-09-07). Numbers are stated exactly as measured, not rounded or smoothed. Anywhere a claim in the original request couldn't be verified against a source file, that's flagged explicitly rather than invented.

---

## 1. Why RAGAS Stopped Being Trusted as the Sole Scoring Method

RAGAS wasn't rejected as worthless — it was demoted from sole authority to one signal among several, once its specific failure modes were understood and documented. Three separate, independently-discovered problems drove that demotion.

### 1a. Judge instability: identical input, drifting scores

Three RAGAS runs were executed back-to-back against the exact same 45 GraphRAG answers — confirmed identical, not just assumed: comparing `Model Answer` text across `ragas_outputs_graphrag/first run/`, `2nd run/`, and `3rd run/` shows **45/45 items with byte-identical model-answer text across all three runs**. Retrieval was deterministic (same graph, same query), so any score difference between runs is pure judge-scoring variance, not a difference in what was being judged.

It was not small variance. The worst case:

- **AF03** ("What are the distinctly identified root causes that can result in an engine flameout?") — Faithfulness scored **0.0, then 0.667, then 0.0** across the three runs, on the identical answer: *"Fuel starvation or interruption, compressor surge or stall, and fuel-filter clogging are the distinct root causes that can lead to an engine flameout. [D3_c08] [D3_c09] [D3_c30]"* — an answer that cites three specific evidence chunks and matches the gold ground truth almost exactly. A **0.667-point swing on a single unchanged answer** is the headline instability number.
- **OS03** — Context Recall scored **1.0, 1.0, then 0.0** across the three runs on identical retrieved contexts (retrieval doesn't change run to run). A binary metric flipping from perfect to zero on unchanged input is not a quality signal, it's judge noise.
- Other items with large Faithfulness swings on identical answers: FH02 (1.0 → 0.5 → 0.5), CD03 (0.5 → 0.5 → 0.0), FH04 (1.0 → 0.667 → 1.0), OS06 (0.667 → 0.333 → 0.667).

Aggregate Faithfulness across the three runs also drifted on its own: **0.5891 → 0.5773 → 0.5617** (mean over all 45 items, each run). A ~0.03 point drift in the *overall* mean, entirely from re-scoring identical content, means any single RAGAS run's headline number carries real, unquantified noise. *(Source: `ragas_outputs_graphrag/{first run,2nd run,3rd run}/aeroops_graphrag_ragas_results.json`, `Faithfulness` and `Context Recall` fields, cross-referenced against `Model Answer` for identity.)*

### 1b. Structural blindness to graph-verified multi-hop claims

RAGAS's Faithfulness metric checks whether each claim in an answer is attributable to the flat list of retrieved text chunks it's shown (`Retrieved Contexts`). It has no visibility into GraphRAG's actual grounding mechanism — the graph traversal and its `Reasoning Chain`, where a multi-hop causal claim is backed by real, claim-ID-tagged edges (`CAUSES`, `LEADS_TO`, `MANIFESTS_AS`, etc.), not by an inference the model drew on its own from prose. A legitimately graph-verified multi-hop synthesis reads to a chunk-level judge as an unsupported leap.

- **MH03** ("How could the failure of a single fuel tank boost pump potentially cause a multiple-engine flameout?") — GraphRAG's answer narrates a real 3-hop chain, each hop cited to a specific chunk: boost-pump failure → filter clogging (`D3_c29`) → flameout (`D3_c30`), with flameout's own cause stated separately (`D3_c08`). This is exactly the graph's own `MANIFESTS_AS`/`LEADS_TO` structure, cross-referenced against `evaluation/aeroops_evaluation_report.md`'s Section 4 breakdown of this same item: backing edges `MANIFESTS_AS` (claim `CL024`, confidence 0.95), `LEADS_TO` (claim `CL028`, confidence 0.85), `MANIFESTS_AS` (claim `CL053`, confidence 0.8) — three real, document-sourced, claim-ID-backed relationships. Faithfulness still scored **0.333**. *(Source: `ragas_outputs_graphrag/first run/aeroops_graphrag_ragas_results.json`, item MH03; `evaluation/aeroops_evaluation_report.md` lines ~114–151.)*
- **OS08** — a near-trivial single-word answer ("The continuous ignition system prevented a **flameout**.") to a question that essentially states its own premise, backed by a 4-step reasoning chain. Faithfulness scored **0.0** — despite Context Recall scoring a perfect 1.0 on the same item, confirming the retrieval was correct; only the chunk-level faithfulness check penalized it. *(Source: same file, item OS08.)*

The evaluation report itself is explicit that this isn't purely "GraphRAG is disadvantaged" — one item (MH03, per Section 4's own note) shows naive RAG's Faithfulness also collapsing to 0.0 on the same causal-attribution language, meaning the judge is broadly harsh on multi-hop causal phrasing regardless of backend, just harsher and more often on GraphRAG's synthesized style. *(Source: `evaluation/aeroops_evaluation_report.md`, line 151.)*

### 1c. The refusal-artifact bug in `router_ground_truth.json`

The router's own training/evaluation target was originally built by averaging each backend's Faithfulness + Context Recall and picking the higher score as the per-item "winner" (v1 rule). This produced a specific, diagnosable bug: **RAGAS scores a refusal as trivially faithful**, because a refusal makes no factual claims, so none can be judged unfaithful. On items where naive RAG returned a boilerplate non-answer ("The provided context does not contain information on...") or crashed, the refusal's artificial ~1.0 Faithfulness beat GraphRAG's real, cited, substantively correct answer.

`build_router_ground_truth.py`'s own header names the two cases that surfaced this: **AF03 and MH03** — the exact two items covered in section 1b above — were both mislabeled "naive wins" under the raw-score v1 rule, purely because naive's answer was a refusal artifact. The fix (v2, `is_refusal()` detection: near-empty answers under 15 characters, caught pipeline exceptions surfacing as `"ERROR: ..."` text, and three boilerplate refusal phrases matched as substrings) changed the labeling rule to: if exactly one backend refuses, the other wins outright, RAGAS scores aren't consulted at all for that item. Running this rebuild flipped **9 of 45 labels** relative to the raw-score version, per the Notion dev log's own account of the fix (item "4. 3-layer cascade router," "Refusal-aware ground truth rebuild"). Cross-checking the *current* `archive_naive_agentic/router_ground_truth.json` against the two named items confirms both now read `"winner": "graphrag"` — consistent with the fix. *(Source: `archive_naive_agentic/build_router_ground_truth.py`, lines 1–47 (design rationale) and lines 90–97 (`is_refusal()` implementation); `archive_naive_agentic/router_ground_truth.json`; Notion "Aeroops Development," item 4.)*

**Update — the 21/45 figure has since been independently verified against a real file, closing the sourcing gap flagged in the previous pass of this brief.** The earlier note below is left struck through rather than deleted, since the investigation that closed it is itself worth keeping on record.

~~Note on a number that could not be re-verified from a file in this repo: the Notion log states naive_rag "refused or gave empty answers on 21/45 gold items." The raw naive-RAG RAGAS results file that would substantiate this count directly (`evaluation/naive_rag/aeroops_naive_rag_ragas_results.json`, per `build_router_ground_truth.py`'s own `NAIVE_RESULTS_PATH` constant) is not present at that path in the current repo — only `ragas_outputs_naive_rag/aeroops_naive_rag_ragas_results_patched.json` exists, a differently-named/located file not confirmed identical to the one the router-ground-truth build actually consumed. The 21/45 figure is reported here as sourced from the Notion dev log, not independently re-derived from a file in this pass.~~

**What was actually wrong:** the file *does* exist at `evaluation/naive_rag/aeroops_naive_rag_ragas_results.json` — the previous pass's claim that it was missing was a search error, not a real gap. `git log --all --oneline -- '*naive_rag_ragas_results*'` shows it was added in commit `4f4272c` ("Organize evaluation deliverables into evaluation/ folder," 2026-08-31) and it is present in `HEAD` and the current working tree (`git status` on that path: clean). `build_router_ground_truth.py`'s `NAIVE_RESULTS_PATH` constant resolves to exactly this path when the script is run from the repo root — where it lived at the time the ground truth was originally built, before being archived into `archive_naive_agentic/` during the GraphRAG-only simplification.

**Confirmed as the right file, not just present at the right path:** compared directly against `ragas_outputs_naive_rag/aeroops_naive_rag_ragas_results_patched.json` (45 items each, identical ID set and order). 42/45 `Model Answer` fields are byte-identical between the two files; the 3 that differ are **CD04, OS02, OS04** — exactly the three items `build_router_ground_truth.py`'s own header comment (lines 30–32) names as the cases where "`naive_rag.py` returned a literally empty string." The "patched" file is a later correction of those three empty-string cases; `evaluation/naive_rag/aeroops_naive_rag_ragas_results.json` is the original, pre-patch data — i.e., the exact input the refusal-detection logic was actually built and run against.

**Independent re-derivation:** re-implemented `is_refusal()` verbatim (near-empty answer under 15 characters, `"ERROR:"`-prefixed text, and the three boilerplate refusal-phrase substrings) and ran it directly against all 45 `Model Answer` fields in `evaluation/naive_rag/aeroops_naive_rag_ragas_results.json`. Result: **21/45** — matching the Notion log's figure exactly, not a different number. The 21 items: MH03, MH04, MH05, MH06, MH07, MH08, CD04, CD07, AF02, AF03, AF05, DA01, DA03, DA06, OS02, OS04, OS06, OS08, PR01, PR02, PR03. AF03 and MH03 — the two items already cited in this section as the refusal-flip motivating cases — are confirmed present in this independently-derived list, consistent with every other claim in this section. *(Source: `evaluation/naive_rag/aeroops_naive_rag_ragas_results.json`, all 45 `Model Answer` fields, `is_refusal()` re-run 2026-09-14; cross-checked against `ragas_outputs_naive_rag/aeroops_naive_rag_ragas_results_patched.json`; `git log --all --oneline -- '*naive_rag_ragas_results*'` → commit `4f4272c`.)*

### Conclusion for this section

RAGAS wasn't thrown out. It surfaced real, useful signal (Context Recall in particular proved more stable, see Section 3). But Faithfulness specifically was demoted from "the score" to "one noisy, structurally-limited signal among several" — the fixed jury-scored harness described in Section 3, and the deterministic mechanical scorer described in Section 4, exist directly because of the three failure modes documented above.

---

## 2. Choosing Agentic Over GraphRAG-Only — A Reasonable Decision at the Time

The agentic router was not a wrong turn taken carelessly. It was built because the *best evidence available at the time* said naive RAG won specific categories outright, and it was undone only once *better* evidence superseded that original evidence — not because anyone refused to revisit it.

### 2a. The original case for a router

The router's target — `router_ground_truth.json` — was originally built from RAGAS-scored comparisons of naive vs. GraphRAG per item (the raw v1 rule described in Section 1c, before the refusal-detection fix existed). Under that raw scoring, naive RAG won a real, non-trivial share of items — enough to justify the engineering cost of building a per-query router rather than picking one backend outright. Building a router in response to that evidence was the correct move given what was known at the time.

### 2b. The router's own five-round iteration history — failures included, not smoothed over

This history is documented directly in `archive_naive_agentic/structural_pattern_router.py`'s header comment (lines 1–83) and corroborated in the Notion dev log's "Router Design Iterations" section:

| Round | Approach | Result | Outcome |
|---|---|---|---|
| 1 | Embedding-centroid router: MiniLM centroid similarity over the 7 gold-set categories, category → backend mapping | **31% 7-way category accuracy, 60% backend accuracy** (leave-one-out) | Discarded — solving the wrong problem (7-way classification when only a binary decision was needed) |
| 2 | Entity-count router: `QueryRouter`'s matched-entity count, 2+ → GraphRAG | **51.3%** against `router_ground_truth.json` | Discarded — entity count was diagnosed as an `ENTITY_MAP` alias-inflation artifact (a single failure mode could match 6 near-synonym aliases, inflating the count with nothing structurally multi-entity about the actual question), not a real property of the question |
| 3 | Keyword-pattern router: hand-written relational/causal keywords (why, causes, leads to, mitigated by, detected by, etc.) → GraphRAG, else naive | **56.4%** | Diagnosed further: comparison language ("compare"/"distinguish") was 4/4 wrong as a standalone GraphRAG signal (all 4 cases it fired alone were actually naive wins); 5 misses had zero trigger words but needed GraphRAG anyway |
| 4 | 3-layer cascade: pattern match → MiniLM semantic nearest-neighbor fallback (against a 39-question reference pool) → entity-count last resort | **74.4%**, then **85%** after two corrections | The two corrections were: (i) the refusal-aware ground-truth rebuild from Section 1c (9/45 labels flipped), and (ii) narrowing the comparison-language rule to fire only when paired with procedure/action language |
| 5 (final, shipped) | Pattern match → default to GraphRAG (semantic layer dropped entirely) | **87.5%** (35/40 scorable) | One point *better* than the 4-round cascade, and simpler |

Round 5's semantic layer was dropped specifically after a real, tested liability was found: probing it with out-of-domain junk queries (e.g. "What color is the sky?") showed it still returned a confident-looking nearest-neighbor match at similarity scores as low as ~0.07–0.19 — indistinguishable in shape from a real decision unless the raw similarity number was inspected. For a router meant to generalize to unseen queries, that's a real correctness risk, not a cosmetic one. *(Source: `structural_pattern_router.py`, lines 28–44.)*

### 2c. Why the 87.5% number was itself built on an unreliable target

This is the crux of why revisiting the router later wasn't a reversal of a mistake, but a natural consequence of better evidence arriving. The 87.5% figure was scored against `router_ground_truth.json` — the same file whose labeling logic is described in Section 1c, built from RAGAS Faithfulness/Context Recall comparisons (refusal-corrected, but still ultimately anchored to RAGAS scores for the non-refusal majority of items). Section 1's own findings — judge-scoring variance large enough to swing an individual item's Faithfulness by 0.667 on unchanged input, and RAGAS's structural blindness to graph-verified multi-hop claims — apply just as much to the ground-truth-building comparisons as they do to any other RAGAS score. An 87.5%-accurate router, measured against a target itself built on a metric later shown to have real, undiagnosed instability, is a real number describing a real router's behavior against *that specific target* — but the target's own reliability had not yet been independently stress-tested at the time the number was reported.

**The decision that mattered:** building the router on the best evidence available was reasonable. The mistake would have been treating 87.5% as a permanent, settled fact once the jury-scored harness (Section 3) produced better, more directly interpretable evidence about whether the router was earning its complexity. That's exactly what happened next.

*(Note on `structural_pattern_router.py`'s "Accepted misses" list, lines 64–83: five items — FH03, MH01, CD03, AF01, AF04 — are documented as diagnosed-and-left-unfixed, with the honest reasoning that a rule fitted to any of them would either require knowing the answer before routing, or would overfit to a single example. This is disclosed directly in the router's own header, not discovered independently in this pass — cited here as evidence the 87.5% figure was reported with its own known gaps stated up front, not polished.)*

---

## 3. The 3-Way Jury Harness — Realizing Agentic Wasn't Worth It

### 3a. Why a jury of models, not a single RAGAS-style judge

Section 1 established that a single automated judge scoring a single run carries real, measured instability (a 0.667-point Faithfulness swing on identical input; a full 0-to-1 Context Recall flip). The standard mitigation for single-judge unreliability in LLM evaluation is a **panel of independent judges scored by majority vote**, rather than trusting any one model's single pass — this is the same principle behind the "Panel of LLM evaluators" (PoLL) approach described in evaluation literature (e.g., Verga et al., "Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Evaluators," 2024): a panel of diverse, independent judges scoring by majority vote reduces single-judge idiosyncrasy and is both cheaper and, on their benchmarks, better-correlated with human judgment than one large single judge. *(This citation is general research context, not a project-internal source — flagged as such.)*

This project had already established that exact pattern independently: the frozen gold set's own `expected_answer` and `jury_agreement` fields (e.g. `evaluation/gold_set/aeroops_goldset_v1_frozen.json`, item FH01's `jury_agreement: "unanimous"`) were built via a 3-model jury — Claude Code/Opus 5, Codex/GPT-5.6, and Qwen, each prompted through their own native interface — reaching majority-vote agreement on what the *correct* answer to each gold question actually is. The harness scoring naive/GraphRAG/agentic's answers reused that exact same methodology and the same three judges, rather than defaulting to a cheaper single-model or fully-automated API judge, specifically to keep the scoring standard consistent with how the gold set itself was built. *(Source: `evaluation/gold_set/aeroops_goldset_v1_frozen.json`; `evaluation/jury_scoring/PROMPT.md`; Notion dev log, item 14.)*

### 3b. Harness design

- **Blinded**: `evaluation/jury_scoring/answers_for_jury.json` anonymizes each of the three systems' answers as System A/B/C per item; the real identity mapping lives only in `evaluation/jury_scoring/answer_key.json`, never shown to a judge.
- **Scoped to answer quality only**: `evaluation/jury_scoring/PROMPT.md` explicitly instructs judges NOT to score citation accuracy, citation format/style, or retrieval volume — those are covered separately by the deterministic mechanical metrics (Section 4) and would double-count or contaminate a pure correctness judgment otherwise.
- **Symmetric core metrics feeding the same harness** (`eval_common.py`, described fully in Section 4): retrieval_recall and citation_recall/precision computed at **(filename, page)** granularity — the coarsest resolution both backends can be held to equally, since naive RAG can never resolve finer than a page, so chunk-level matching would hand GraphRAG an unfairly finer measuring stick.
- **Three judges**: Opus 5 and GPT-5.6 run manually (matching the gold set's own original methodology); Qwen3.8 Max (`qwen/qwen3.8-max-0902`) automated via OpenRouter, real cost ≈$0.09 for all 45 items across 3 batches. *(Source: `evaluation/jury_scoring/run_qwen_jury.py`, `scores_opus5.json`, `scores_gpt56sol.json`, `scores_qwen38max.json`.)*

### 3c. Full results

From `evaluation/jury_scoring/aggregated_jury_scores.json`, majority vote across all 3 judges, answer-quality only, n=45:

| System | Correct rate | n correct | Unanimous rate |
|---|---|---|---|
| **naive** | **0.511** | 23/45 | 0.867 |
| **graphrag** | **0.867** | 39/45 | 0.867 |
| **agentic** | **0.867** | 39/45 | 0.844 |

Naive lost **every one of the 7 question categories**, including its own best case:

| Category | n | naive | graphrag | agentic |
|---|---|---|---|---|
| factual_single_hop | 6 | **0.833** | **1.000** | 1.000 |
| multi_hop_causal | 8 | 0.750 | 0.875 | 0.875 |
| aggregation_fanout | 6 | 0.500 | 0.833 | 0.833 |
| operational_scenario | 8 | 0.625 | 1.000 | 1.000 |
| provenance | 3 | 0.667 | 1.000 | 1.000 |
| disambiguation | 6 | 0.167 | 0.667 | 0.667 |
| cross_document | 8 | 0.125 | 0.750 | 0.750 |

`factual_single_hop` — single fact, single source, naive's structurally easiest case — is the category with the *smallest* gap (naive 0.833 vs. GraphRAG's perfect 1.0), and naive still lost it outright. It was never ahead anywhere.

**Agentic and GraphRAG tied exactly (0.867 both, 39/45 both)** overall. The router only ever diverted 2 of the 45 items to naive — **DA04 and DA05**, both `aggregation_fanout`. On exactly those 2 items, the only ones where the router's decision could possibly have mattered: naive's correct rate = **0.5**, GraphRAG's correct rate = **0.5** — an exact tie, n=2. *(Source: `evaluation/jury_scoring/aggregated_jury_scores.json`, `naive_routed_items_comparison` block.)*

### 3d. The conclusion, stated plainly

The router added real, ongoing complexity — a pattern-matching decision layer, a dependency on `naive_rag.py`'s entire FAISS/BM25/embeddings stack, `DOC_CONFIG` maintenance, a ~90-second cold-start index build — for **zero measured benefit**: agentic's overall score equals GraphRAG's exactly, and on the only items the router's decision was ever load-bearing for, the two backends it was choosing between tied. The caveat is stated plainly in the Notion log itself and repeated here: n=2 for the routed-items comparison is small enough that a coin flip wouldn't be surprising as noise on its own — but it isn't contradicted by the much larger sample (naive's 0.511 overall vs. GraphRAG's 0.867 across all 45 items), it's corroborated by it.

---

## 4. Final Decision — GraphRAG Only

### 4a. What was cut, and what was archived vs. deleted

**Archived, not deleted** (moved into `archive_naive_agentic/`, zipped, gitignored — kept as a private local reference, not shipped as if it were the live architecture): `naive_rag.py`, `agentic_rag.py`, `structural_pattern_router.py`, `router_ground_truth.json`, `build_router_ground_truth.py`, the pre-simplification `main.py`, and the runtime router-decision log (`agentic_router_log.jsonl`). *(Source: `archive_naive_agentic/README.md`.)*

**Dependencies removed from `requirements.txt`**: `faiss-cpu`, `rank-bm25`, `sentence-transformers`, `langchain-huggingface` — confirmed via grep that these were only ever imported by `naive_rag.py`, nothing else in the active codebase depended on them.

**`main.py` rewritten**: `/query` now calls `graph_rag()` directly instead of routing through `agentic_rag()`; `/compare` removed entirely (nothing left to compare naive against); `/health` dropped the naive-specific OpenRouter-client check, kept the real Neo4j connectivity check. The frontend's Agentic/Compare mode toggle and naive-answer panel were also removed from `static/app.js`/`templates/index.html` — not originally in scope for the naive-removal task alone, but required once `/compare` no longer existed, to avoid shipping a UI that referenced a dead endpoint.

### 4b. Two real product bugs found in `naive_rag.py` — cost evidence, not just accuracy evidence

These surfaced specifically because the fixed evaluation harness (Section 3) needed a reliable `(filename, page)` ground truth to score naive's citations against — not something a normal per-run eval would have caught, and not router-accuracy evidence at all. They are independent, additional cost-of-keeping-naive evidence:

- **`DOC_CONFIG` filename mismatches** — 2 of 7 source documents had dictionary keys that didn't match the real on-disk filenames (e.g. `"AirTrafficControlResearch.pdf"` vs. the real `AircraftTurbineEngineControlResearchatNASAGlennResearchCenter.pdf`). This silently meant those two documents carried **no title/domain metadata at all** in the live product for as long as this went unnoticed. *(Source: `archive_naive_agentic/naive_rag.py`, lines 46, 52, 57, 394 — the corrected filenames now in place.)*
- **Page-number off-by-one** — PyPDFLoader's page metadata is 0-indexed; confirmed directly against real PDF content (raw metadata said `page=17` for text beginning with the printed heading "18"). **Every citation `naive_rag.py` had ever shown a real user was one page off**, silently, until fixed with a `_display_page()` helper (`archive_naive_agentic/naive_rag.py`, lines 649–657) applied consistently everywhere a page number is surfaced.

Both bugs are the kind that ship silently and are never caught by accuracy metrics alone — they're maintenance-cost evidence, distinct from and additional to the router-accuracy case in Sections 2–3.

### 4c. The causal-fabrication fix — sourced, with a timing correction

The original request framed this as "found post-simplification via the deterministic mechanical layer." Having checked git history, the Notion dev log, and all mechanical-scoring source files, the best-documented match for "a causal-fabrication bug traced to a specific unfiltered graph traversal, fixed and verified" is git commit `672fa9e` ("Fix GraphRAG retrieval/generation bugs found during faithfulness audit," 2026-08-31) — **but it predates the GraphRAG-only simplification, it did not follow it.** Stated plainly rather than smoothed over:

`graphretriever_v5.py`'s `retrieve_path()` originally let Neo4j's `shortestPath` traverse **any** relationship type between two entities, including the structural `MENTIONED_IN`/`HAS_CHUNK` co-occurrence edges — edges that mean only "these two things appear in the same source chunk," carrying no `claim_id` and asserting no actual causal or directional relationship. An unfiltered traversal could therefore surface a path that looked like a causal chain (and get narrated as one in the generated answer) when the only real "connection" between the two entities was that they happened to appear in the same paragraph. The fix restricts `shortestPath` to the real semantic edge types only (`CAUSES`, `LEADS_TO`, `MANIFESTS_AS`, etc.) — documented directly in the code comment at `graphretriever_v5.py` (the "Fixed 2026-08-30" note, still present in the current file). *(Source: `git show 672fa9e` — commit message and diff; `graphretriever_v5.py`, in-code comment preserved from that fix.)*

This is precisely the failure mode `score_graphrag_mechanical.py`'s **`edge_authenticity_rate`** metric exists to catch: it checks every hop in a reasoning chain against `REAL_EDGE_TYPES` (the same real-edge set, requiring both a real edge type *and* a `claim_id`) and reports the fraction of hops that are genuinely document-sourced rather than co-occurrence dressed up as causation (`score_graphrag_mechanical.py`, lines 67–188). The existing evaluation report shows edge_authenticity scoring a perfect 1.0 "everywhere it applies" as of that report's writing (`evaluation/aeroops_evaluation_report.md`, line 176) — consistent with the Aug 31 fix holding, not with a new instance of the bug found afterward. No separate, later "post-simplification" recurrence of this specific bug was found in this pass — if one exists, it is not present in git history, the Notion log (last edited 2026-09-07), or any mechanical-scoring output file checked here.

### 4d. Real numbers from the self-hosted deployment — 44-item live batch

Self-hosted Neo4j Community Edition on the same EC2 instance (`t3.small`) as the FastAPI app, replacing AuraDB free tier's instability/auto-pause risk. All numbers below are from a clean, isolated 45-item run through the **live public `/query` endpoint** (not a bypassed direct call) on 2026-09-11, cross-checked against LangSmith's independently-logged token data with **zero mismatches** across all comparable items. **1 of 45 items (MH01) excluded** — its LLM call itself succeeded (tokens generated, logged in LangSmith) but the API layer 500'd on a downstream response-validation bug (a null-content edge case in `main.py`'s non-optional `answer: str` field, unrelated to retrieval or generation quality) — flagged as a follow-up fix, not corrected in that measurement pass. All aggregates below are **n=44**.

| Metric | Mean | Median | Min | Max |
|---|---|---|---|---|
| Cost per query (USD) | $0.000106 | $0.000103 | $0.000056 | $0.000180 |
| Total tokens | 2195 | 2217 | 1398 | 2880 |
| Retrieval time (s) | 0.039 | 0.030 | 0.010 | 0.290 |
| Generation time (s) | 3.400 | 3.120 | 1.290 | 7.810 |

Total cost across the 44 successful items: **$0.0046**. Retrieval time under 0.1s for 42/44 items, confirming the same-machine (Docker bridge network, not public internet) topology explanation rather than an unusual fluke. Pricing (OpenRouter, `openai/gpt-oss-20b`) verified live from `https://openrouter.ai/api/v1/models/openai/gpt-oss-20b/endpoints` at measurement time — all 44 successful calls in this specific batch were served by a single provider, Parasail ($0.03/M prompt, $0.15/M completion tokens), though OpenRouter's routing has been observed to vary across other historical batches. *(Source: `evaluation/harness_runs/live_api_run_1789121032.json`; this session's LangSmith cross-check.)*

### 4e. Net result

Naive RAG and the agentic router are gone from the live system. What remains is a single GraphRAG pipeline, verified end-to-end on real infrastructure the project fully owns, with real per-query cost/latency numbers pulled from an actual production run rather than estimated — and an honest paper trail of every dead end (three failed router designs), every silent bug (two in naive_rag.py, one in graph traversal, one in the live API's error handling), and every reversal (RAGAS's demotion, the router's retirement) that got there.
