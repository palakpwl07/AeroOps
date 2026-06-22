# AeroOps

**GraphRAG vs Naive RAG over a turbofan engine maintenance knowledge graph**

A side-by-side comparison system built to test whether graph-structured retrieval outperforms flat-chunk retrieval on multi-hop reasoning over aerospace maintenance documentation.

[**Live Demo →**](https://aeroops.streamlit.app) &nbsp;|&nbsp; [**Source Documents →**](https://drive.google.com/drive/folders/1masPUYiArHj2LrOGIkWn1O7S2pmQc_C4?usp=sharing)

---

## What it does

AeroOps answers turbofan engine maintenance questions using two retrieval architectures in parallel, so you can compare the results directly:

- **Naive RAG** — hybrid BM25 + vector retrieval over chunked PDF text, Groq-powered generation
- **GraphRAG** — entity-typed knowledge graph (Neo4j AuraDB) with path traversal, provenance-traced claims, and graph-context grounding

The GraphRAG pipeline encodes 267 nodes and 560 relationships across 12 entity types: FailureMode, Symptom, Cause, Mitigation, Parameter, OperatingFactor, Method, Part, Module, Engine, Claim, and Document. Every claim traces to its exact source chunk, page, and document.

---

## Why GraphRAG

Flat-chunk retrieval retrieves by term overlap. It struggles when:
- The answer requires chaining across multiple nodes (e.g. flight loads → blade tip rub → clearance increase → EGT margin deterioration)
- Two failure modes present similarly but require different crew actions (disambiguation)
- The question asks which specific source supports a specific claim (provenance)

The knowledge graph lets the retriever walk typed edges instead of guessing at similarity — the reasoning path is explicit, not inferred.

---

## Knowledge graph

Built from 7 turbofan maintenance documents (NASA technical reports, FAA handbooks, operator guides):

| Document | Type |
|---|---|
| Engine Maintenance Concepts for Financiers (Ackert) | Operator guide |
| Performance Deterioration of Commercial High-Bypass Ratio Turbofan Engines (NASA TM-81552) | Technical report |
| Airplane Turbofan Engine Operation and Malfunctions: Basic Familiarization for Flight Crews (FAA/Boeing) | Operations manual |
| Aircraft Turbine Engine Control Research at NASA Glenn Research Center | Technical report |
| AI for Turbofan Engines | Research paper |
| Fault Prognosis of Turbofan Engines | Research paper |
| Turbofan Engine Maintenance and Operation | Maintenance manual |

Graph statistics: **267 nodes · 560 relationships**

---

## Evaluation

Evaluated against a 35-item custom ground-truth set spanning 7 reasoning categories:

| Category | Score |
|---|---|
| Multi-hop causal | 99% |
| Provenance | 77% |
| Single-hop factual | 71% |
| Aggregation / fan-out | 66% |
| Disambiguation | 66% |
| Operational scenarios | 53% |

The gradient is intentional. Harder categories score lower because the eval set was designed to stress-test the system, not flatter it. Multi-hop causal reasoning — the primary differentiator of GraphRAG — scores highest.

RAGAS (faithfulness + context recall) was also run as a standard benchmark. A detailed analysis of where RAGAS undercounts graph-structured retrieval (flat-context-bag assumption, textual entailment vs. graph-verified truth, path-order blindness) is documented separately.

---

## Stack

| Component | Technology |
|---|---|
| Knowledge graph | Neo4j AuraDB Free |
| Graph retrieval | Custom path traversal + star-pattern retrieval |
| Naive RAG retrieval | BM25 + FAISS vector search (hybrid) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Generation | Groq API (`llama-3.1-8b-instant`) |
| Frontend | Streamlit |
| Deployment | Streamlit Community Cloud |

---

## Project structure

```
app.py                      # Streamlit frontend
graph_rag.py                # GraphRAG pipeline wrapper
naive_rag.py                # Naive RAG pipeline
query_understanding_v3.py   # Deterministic entity router
graphretriever_v5.py        # Neo4j path traversal + star retrieval
context_builder.py          # Graph facts → LLM context
answer_generator_groq.py    # Groq generation
knowledgebase/              # 7 source PDFs
requirements.txt
packages.txt
```

---

## Local setup

```bash
git clone https://github.com/palakpwl07/AeroOps.git
cd AeroOps
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
NEO4J_URI = "neo4j+s://your-instance.databases.neo4j.io"
NEO4J_USERNAME = "your-username"
NEO4J_PASSWORD = "your-password"
NEO4J_DATABASE = "your-database"
GROQ_API_KEY = "gsk_your-key"
```

```bash
streamlit run app.py
```

---

## Built by

Palak Porwal · [LinkedIn](https://www.linkedin.com/in/palakporwal) · [Substack](https://palakporwal.substack.com)
