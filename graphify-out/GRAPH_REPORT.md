# Graph Report - .aeroops  (2026-08-28)

## Corpus Check
- 46 files · ~279,435 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 344 nodes · 544 edges · 36 communities (25 shown, 11 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 27 edges (avg confidence: 0.87)
- Token cost: 0 input · 229,185 output

## Community Hubs (Navigation)
- GraphRAG Pipeline & Evals
- Fault Modes & Symptoms
- Naive RAG & Streamlit UI
- Graph Retriever
- Performance Deterioration & Maintenance
- Engine Core Components & ML
- Answer Generation & DeepSeek Jury
- Query Understanding
- Qwen Jury Evaluation
- GraphRAG Retry Handling
- Naive RAG Retry Handling
- GraphRAG RAGAS Scoring
- Context Builder
- Naive RAG RAGAS Scoring
- Project Branding & Banner
- Engine Models (CF6/CFM56/JT9D/V2500)
- Environmental Erosion Damage
- Tailpipe Fire Path
- Blade Cracking Inspection
- Engine Fire Response
- LLP Life Limits
- Oil Leak Monitoring
- Fuel Flow Anomalies
- N1 Speed Anomalies
- Dependency Configuration
- Combustion Corrosion
- Engine Maintenance Concepts Doc
- Fault Prognosis Doc
- Turbofan Familization Doc
- Performance Deterioration Doc
- NASA Turbine Control Doc
- AI for Turbofan Doc
- Turbofan Maintenance Operation Doc
- Judge Call Test
- LiteLLM Qwen Config
- RAGAS vs GraphRAG Comparison

## God Nodes (most connected - your core abstractions)
1. `GraphRetriever` - 23 edges
2. `graph_rag()` - 18 edges
3. `QueryRouter` - 15 edges
4. `hybrid_retrieve()` - 11 edges
5. `generate_answer_with_citations()` - 11 edges
6. `Compressor surge / stall` - 10 edges
7. `_get_pipeline()` - 9 edges
8. `AnswerGenerator` - 8 edges
9. `High-Pressure Turbine (HPT)` - 8 edges
10. `EGT margin deterioration` - 8 edges

## Surprising Connections (you probably didn't know these)
- `_get_pipeline()` --uses--> `AnswerGenerator`  [INFERRED]
  graph_rag.py → answer_generator_groq.py
- `_get_pipeline()` --uses--> `ContextBuilder`  [INFERRED]
  graph_rag.py → context_builder.py
- `_get_pipeline()` --uses--> `GraphRetriever`  [INFERRED]
  graph_rag.py → graphretriever_v5.py
- `_get_pipeline()` --uses--> `QueryRouter`  [INFERRED]
  graph_rag.py → query_understanding_v3.py
- `main()` --calls--> `graph_rag()`  [EXTRACTED]
  retest_fixed_generator.py → graph_rag.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Blade-tip clearance to EGT-margin degradation mechanism** — knowledgebase_aeroops_knowledgegraph_c_blade_tip_wear, knowledgebase_aeroops_knowledgegraph_fm_blade_tip_rub, knowledgebase_aeroops_knowledgegraph_fm_tip_clearance_increase, knowledgebase_aeroops_knowledgegraph_fm_egt_margin_deterioration, knowledgebase_aeroops_knowledgegraph_pa_egt_margin [EXTRACTED 1.00]
- **Compressor surge to catastrophic damage failure cascade** — knowledgebase_aeroops_knowledgegraph_c_compressor_airfoil_stall, knowledgebase_aeroops_knowledgegraph_c_fod_ingestion, knowledgebase_aeroops_knowledgegraph_fm_compressor_surge, knowledgebase_aeroops_knowledgegraph_fm_flameout, knowledgebase_aeroops_knowledgegraph_fm_severe_engine_damage [EXTRACTED 1.00]
- **PHM / predictive-maintenance ML methods stack** — knowledgebase_aeroops_knowledgegraph_me_phm, knowledgebase_aeroops_knowledgegraph_me_ann_flux, knowledgebase_aeroops_knowledgegraph_me_pca, knowledgebase_aeroops_knowledgegraph_me_ncmapss, knowledgebase_aeroops_knowledgegraph_mi_predictive_maintenance [EXTRACTED 1.00]

## Communities (36 total, 11 thin omitted)

### Community 0 - "GraphRAG Pipeline & Evals"
Cohesion: 0.09
Nodes (24): _build_sources(), _build_star(), _get_pipeline(), _get_secret(), graph_rag(), Any, cache_resource, Pulled from the retriever's raw fetch_chunks() output (graph_result["chunks"]),… (+16 more)

### Community 1 - "Fault Modes & Symptoms"
Cohesion: 0.07
Nodes (33): Bearing distress, Fuel boost-pump debris, Compressor airfoil aerodynamic stall, Foreign object / bird ingestion, Fuel starvation / interruption, Bearing failure, Compressor surge / stall, Fan unbalance (+25 more)

### Community 2 - "Naive RAG & Streamlit UI"
Cohesion: 0.12
Nodes (26): build_trace_dot(), render_panel(), render_sources(), _bm25_retrieve(), build_context_with_sources(), _build_index(), check_numeric_preservation(), _deduplicate_docs() (+18 more)

### Community 3 - "Graph Retriever"
Cohesion: 0.25
Nodes (7): GraphRetriever, Any, Generic retrieval for any non-FM, non-SY node (Cause, Parameter, Part, Module,…, Find shortest path(s) between two entities and return enriched results for…, When no path connects two entities, retrieve both independently., Collect chunk ids while preserving the order they were encountered (i.e. rank…, Backward-compatible entrypoint. Accepts: - 'SY_...' -> symptom star - 'FM_...'…

### Community 4 - "Performance Deterioration & Maintenance"
Cohesion: 0.09
Nodes (23): Blade tip wear, Flight loads (aerodynamic + inertial), Hot rotor reburst (thermal transient), Rotor / case interference, Thermal stress / high core temperature, Blade tip rub, EGT margin deterioration, Thermal distortion / vane warpage (+15 more)

### Community 5 - "Engine Core Components & ML"
Cohesion: 0.10
Nodes (23): Turbofan engine, Hardware deterioration / blade distress, Accessory drive gearbox, Combustor, Core / hot section (HPC + combustor + HPT), High-Pressure Compressor (HPC), High-Pressure Turbine (HPT), Low-Pressure Turbine (LPT) (+15 more)

### Community 6 - "Answer Generation & DeepSeek Jury"
Cohesion: 0.16
Nodes (15): AnswerGenerator, Any, build_context(), call_deepseek(), expand_graph(), get_evidence_chunk_ids(), load_graph(), main() (+7 more)

### Community 7 - "Query Understanding"
Cohesion: 0.20
Nodes (6): Any, QueryRouter, QueryUnderstanding, # NOTE: "egt margin" intentionally removed from this list (see, # NOTE: a "tm 81552" -> [...] expansion was tried here to catch, Deterministic, recall-heavy query understanding for AeroOps GraphRAG.

### Community 8 - "Qwen Jury Evaluation"
Cohesion: 0.22
Nodes (14): answer_one(), build_context(), call_qwen(), expand_graph(), get_evidence_chunk_ids(), load_graph(), main(), match_entities() (+6 more)

### Community 9 - "GraphRAG Retry Handling"
Cohesion: 0.29
Nodes (13): build_ragas_judge(), is_real(), load_rows(), main(), prepare_contexts(), print_summary(), Any, retry_failed_graphrag_items.py Two-stage repair for the GraphRAG RAGAS results,… (+5 more)

### Community 10 - "Naive RAG Retry Handling"
Cohesion: 0.35
Nodes (11): build_ragas_judge(), is_real(), load_rows(), main(), prepare_contexts(), print_summary(), Any, retry_failed_naive_rag_items.py Two-stage repair for the naive RAG RAGAS… (+3 more)

### Community 11 - "GraphRAG RAGAS Scoring"
Cohesion: 0.30
Nodes (11): build_ragas_judge(), load_inputs(), main(), merge_scores(), prepare_contexts(), print_summary(), Any, Removes inline citation tags like [D3_c32] or [D1_c15, D3_c27] from an answer… (+3 more)

### Community 12 - "Context Builder"
Cohesion: 0.33
Nodes (5): ContextBuilder, Any, Turn a retriever dict like {"cause": "Blade tip wear", "chunks": ["D1_c03"],…, Format a LEADS_TO downstream consequence with provenance., Format a DEGRADES edge to a parameter with provenance.

### Community 13 - "Naive RAG RAGAS Scoring"
Cohesion: 0.38
Nodes (9): build_ragas_judge(), load_inputs(), main(), merge_scores(), prepare_contexts(), print_summary(), Any, run_ragas() (+1 more)

### Community 14 - "Project Branding & Banner"
Cohesion: 0.53
Nodes (6): AeroOps Project, Aviation / Aircraft Maintenance Domain, AeroOps Banner Image, Business Jet Aircraft, Turbofan Jet Engine (Close-up), Airport Tarmac Scene

### Community 15 - "Engine Models (CF6/CFM56/JT9D/V2500)"
Cohesion: 0.40
Nodes (5): General Electric CF6, CFM56, High-bypass ratio turbofan, Pratt & Whitney JT9D, V2500

### Community 16 - "Environmental Erosion Damage"
Cohesion: 0.50
Nodes (4): Particulate / dust / sand ingestion, Airfoil erosion / surface roughness, Blocked HPT cooling holes, Operating environment (dusty / erosive / temperate)

### Community 17 - "Tailpipe Fire Path"
Cohesion: 0.67
Nodes (3): Fuel puddling in tailpipe, Tailpipe fire, Dry motoring the engine

### Community 18 - "Blade Cracking Inspection"
Cohesion: 0.67
Nodes (3): Blade cracking / chipping, Borescope inspection, Non-destructive testing (NDT) inspection

### Community 19 - "Engine Fire Response"
Cohesion: 0.67
Nodes (3): Engine (nacelle) fire, Engine shutdown, Fire warning

### Community 20 - "LLP Life Limits"
Cohesion: 0.67
Nodes (3): Life-Limited Part (LLP) expiry, LLP replacement, Short-haul / high-cycle operation

### Community 21 - "Oil Leak Monitoring"
Cohesion: 0.67
Nodes (3): Oil leak / oil loss, Oil quantity, Steady decrease in oil quantity

### Community 22 - "Fuel Flow Anomalies"
Cohesion: 0.67
Nodes (3): Fuel flow, Abnormally high fuel flow, Rising fuel flow

### Community 23 - "N1 Speed Anomalies"
Cohesion: 0.67
Nodes (3): N1 fan speed, Low N1, Fluctuating N1

### Community 24 - "Dependency Configuration"
Cohesion: 0.67
Nodes (3): AeroOps system packages (packages.txt), AeroOps Python dependencies (requirements.txt), Pinned Python runtime (python-3.11)

## Knowledge Gaps
- **80 isolated node(s):** `RAGAS vs GRAPH RAG`, `Explainable Artificial Intelligence for Exhaust Gas Temperature of Turbofan Engines`, `Aircraft Turbine Engine Control Research at NASA Glenn Research Center (NASA TM-2013-217821)`, `Engine Maintenance Concepts for Financiers`, `Fault Prognosis of Turbofan Engines: Eventual Failure Prediction and RUL Estimation` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GraphRetriever` connect `Graph Retriever` to `GraphRAG Pipeline & Evals`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `graph_rag()` connect `GraphRAG Pipeline & Evals` to `GraphRAG Retry Handling`, `Naive RAG & Streamlit UI`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `QueryRouter` connect `Query Understanding` to `GraphRAG Pipeline & Evals`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **What connects `RAGAS vs GRAPH RAG`, `Explainable Artificial Intelligence for Exhaust Gas Temperature of Turbofan Engines`, `Aircraft Turbine Engine Control Research at NASA Glenn Research Center (NASA TM-2013-217821)` to the rest of the system?**
  _80 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `GraphRAG Pipeline & Evals` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._
- **Should `Fault Modes & Symptoms` be split into smaller, more focused modules?**
  _Cohesion score 0.06818181818181818 - nodes in this community are weakly interconnected._
- **Should `Naive RAG & Streamlit UI` be split into smaller, more focused modules?**
  _Cohesion score 0.12096774193548387 - nodes in this community are weakly interconnected._