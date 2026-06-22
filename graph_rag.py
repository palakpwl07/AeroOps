# src/pipeline/graph_rag.py
#
# Collapses the GraphRAG pipeline (QueryRouter -> GraphRetriever ->
# ContextBuilder -> AnswerGenerator) into one callable, matching
# naive_rag.py's naive_rag(query, k=5) -> dict contract so both
# pipelines sit symmetrically in the Streamlit app.

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import streamlit as st

from query_understanding_v3 import QueryRouter
from graphretriever_v5 import GraphRetriever
from context_builder import ContextBuilder
from answer_generator_groq import AnswerGenerator


def _get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """st.secrets first, env var fallback -- same lookup for local + cloud."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


@st.cache_resource(show_spinner="Connecting to AeroOps knowledge graph...")
def _get_pipeline():
    """
    Built once per app instance, reused across every query in the
    session -- mirrors naive_rag.py's caching pattern, and avoids
    re-opening a Neo4j driver connection on every single query.
    """
    router = QueryRouter()

    retriever = GraphRetriever(
        uri=_get_secret("NEO4J_URI"),
        username=_get_secret("NEO4J_USERNAME", "neo4j"),
        password=_get_secret("NEO4J_PASSWORD"),
        database=_get_secret("NEO4J_DATABASE", "aeroops"),
    )

    builder = ContextBuilder()

    generator = AnswerGenerator(
        model=_get_secret("GRAPHRAG_GROQ_MODEL", "llama-3.1-8b-instant"),
        api_key=_get_secret("GROQ_API_KEY"),
    )

    return router, retriever, builder, generator

def _split_chain(chain):
    if not chain:
        return [], []
    path_nodes = [
        {"id": step.get("id") or f"n{i}", "name": step.get("name"), "label": step.get("label")}
        for i, step in enumerate(chain)
    ]
    path_edges = []
    for i, step in enumerate(chain):
        if step.get("edge_type") and i + 1 < len(chain):
            path_edges.append({
                "source": path_nodes[i]["id"],
                "target": path_nodes[i + 1]["id"],
                "type": step.get("edge_type"),
            })
    return path_nodes, path_edges

def _build_star(results):
    if not results:
        return [], []
    row = results[0]
    fm_id = "center"
    nodes = [{"id": fm_id, "name": row.get("failure_mode") or "Unknown", "label": "FailureMode"}]
    edges = []

    def extract_name(item, candidate_keys):
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            for key in candidate_keys:
                if item.get(key):
                    return item.get(key)
            return item.get("name")
        return None

    def add_group(items, candidate_keys, edge_type, reverse=False):
        for idx, item in enumerate(items or []):
            name = extract_name(item, candidate_keys)
            if not name:
                continue
            node_id = f"{edge_type}_{idx}"
            nodes.append({"id": node_id, "name": name, "label": edge_type})
            edges.append(
                {"source": node_id, "target": fm_id, "type": edge_type} if reverse
                else {"source": fm_id, "target": node_id, "type": edge_type}
            )

    add_group(row.get("causes"), ["cause", "name"], "CAUSES", reverse=True)
    add_group(row.get("mitigations"), ["mitigation", "name"], "MITIGATED_BY")
    add_group(row.get("symptoms"), ["symptom", "name"], "MANIFESTS_AS")
    add_group(row.get("leads_to"), ["failure_mode", "name"], "LEADS_TO")
    add_group(row.get("degrades"), ["parameter", "name"], "DEGRADES")
    add_group(row.get("restores"), ["parameter", "name"], "RESTORED_BY", reverse=True)

    return nodes[:9], edges[:8]

def _build_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Pulled from the retriever's raw fetch_chunks() output
    (graph_result["chunks"]), not from context_builder's
    evidence_chunks -- context_builder strips everything but
    chunk_id/text for the LLM prompt, dropping the page/title/view_url
    metadata the citation panel needs.
    """
    return [
        {
            "chunk_id": ch.get("chunk_id"),
            "doc_id": ch.get("doc_id"),
            "title": ch.get("document_title"),
            "page": ch.get("page"),
            "section": ch.get("section"),
            "quote": ch.get("text"),
            "view_url": ch.get("view_url"),
        }
        for ch in chunks
    ]


def graph_rag(query: str) -> Dict[str, Any]:
    """
    Single entrypoint. Shares query/answer/retrieval_time/
    generation_time/sources with naive_rag()'s output shape, plus
    GraphRAG-only extras for the reasoning trace.
    """
    router, retriever, builder, generator = _get_pipeline()

    start = time.time()
    try:
        parsed = router.understand(query)
        graph_result = retriever.retrieve(parsed.entity_id)
    except Exception as exc:
        return {
            "query": query,
            "answer": "Retrieval failed before an answer could be generated.",
            "retrieval_time": round(time.time() - start, 2),
            "generation_time": 0,
            "sources": [],
            "retrieval_type": "error",
            "path_nodes": [],
            "path_edges": [],
            "reasoning_chain": [],
            "matched_entities": [],
            "retrieval_error": str(exc),
        }
    retrieval_time = time.time() - start

    context = builder.build(query, graph_result)

    gen_start = time.time()
    generation_error = None
    try:
        answer = generator.generate(context)
    except Exception as exc:
        answer = "Answer generation failed after retrieval completed."
        generation_error = str(exc)
    generation_time = time.time() - gen_start

    results = graph_result.get("results", [])
    reasoning_chain = results[0].get("reasoning_chain", []) if results else []
    if reasoning_chain:
        path_nodes, path_edges = _split_chain(reasoning_chain)
    else:
        try:
            path_nodes, path_edges = _build_star(results)
        except Exception:
            path_nodes, path_edges = [], []
    import json
    print("DEBUG row:", json.dumps(results[0], default=str, indent=2)[:2000] if results else "EMPTY RESULTS")
    output = {
        "query": query,
        "answer": answer,
        "retrieval_time": round(retrieval_time, 2),
        "generation_time": round(generation_time, 2),
        "sources": _build_sources(graph_result.get("chunks", [])),
        "retrieval_type": graph_result.get("retrieval_type"),
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "reasoning_chain": reasoning_chain,
        "matched_entities": parsed.matched_entities,
    }

    if generation_error:
        output["generation_error"] = generation_error

    return output

