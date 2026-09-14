# eval_common.py
#
# Shared building blocks for the fixed AeroOps evaluation harness, split
# across two scripts on purpose (mirrors this project's existing
# run_*_eval.py / score_*.py separation):
#   run_final_eval.py   -- generates naive/graphrag/agentic answers +
#                           mechanical (non-LLM) metrics, saves to disk.
#                           Cheap, fast, no jury cost.
#   score_final_eval.py -- loads a saved generation file and runs the
#                           jury-of-3 correctness verdict over it. The
#                           expensive, separately-rerunnable step.
#
# Design constraint: every metric here is computable identically for
# naive_rag() and graph_rag() output, at the coarsest common granularity
# (filename, page) -- naive RAG can only ever identify a page, never a
# specific chunk within it, so chunk-level matching would hand GraphRAG a
# finer measuring stick than naive can be held to. GraphRAG-only
# diagnostics (node recall, chain coverage, edge authenticity -- no naive
# equivalent exists) are computed separately and never mixed into the
# head-to-head numbers.

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOLD_PATH = os.path.join(_BASE_DIR, "evaluation", "gold_set", "aeroops_goldset_v1_frozen.json")
GRAPH_EXPORT_PATH = os.path.join(_BASE_DIR, "knowledgebase", "aeroops_knowledgegraph.md")

NAIVE_CITE_RE = re.compile(r"\[CITE:\s*([^\]]+?)\s+p\.(\d+)\]")
GRAPHRAG_CITE_RE = re.compile(r"[\[【]([A-Za-z0-9_,\s]+)[\]】]")

# doc_id -> filename is an EXPLICIT table, not title-string matching. Tried
# matching aeroops_knowledgegraph.md's document titles against
# naive_rag.DOC_CONFIG's document_title values first -- only 3 of 7 matched
# exactly. The other 4 differ by real content, not formatting: D2 spells
# out "RUL" as "Remaining Useful Life" in one place and not the other,
# D4/D5 carry a parenthetical NASA report number in the graph export that
# DOC_CONFIG omits, D7's graph title is the full handbook citation while
# DOC_CONFIG uses a shortened chapter title. None of that is safely
# fixable with normalization without risking a silent wrong match on some
# future document -- verified by hand against both sources instead.
DOC_ID_TO_FILENAME = {
    "D1": "EngineMaintenanceConcepts.pdf",
    "D2": "FaultPrognosisofTurbofanEngines.pdf",
    "D3": "TurbofanEngineFamilization.pdf",
    "D4": "PERFORMANCE_DETERIORATION_of_turbofan_engines.pdf",
    "D5": "AircraftTurbineEngineControlResearchatNASAGlennResearchCenter.pdf",
    "D6": "AIforTurbofanEngines.pdf",
    "D7": "TurbofanEnginMaintenanceandOperation.pdf",
}


def build_chunk_filepage_map(doc_config: Dict[str, Any]) -> Dict[str, Tuple[str, int]]:
    with open(GRAPH_EXPORT_PATH, encoding="utf-8") as f:
        graph = json.load(f)

    unknown = set(DOC_ID_TO_FILENAME.values()) - set(doc_config.keys())
    if unknown:
        raise ValueError(
            f"DOC_ID_TO_FILENAME references filenames not in naive_rag.DOC_CONFIG: {unknown}"
        )

    chunk_map = {}
    for chunk in graph["chunks"]:
        filename = DOC_ID_TO_FILENAME.get(chunk["doc_id"])
        if filename and chunk.get("page") is not None:
            chunk_map[chunk["chunk_id"]] = (filename, chunk["page"])
    return chunk_map


def load_gold() -> List[Dict[str, Any]]:
    with open(GOLD_PATH, encoding="utf-8") as f:
        return json.load(f)


def gold_filepages(item: Dict[str, Any], chunk_map: Dict[str, Tuple[str, int]]) -> Set[Tuple[str, int]]:
    return {chunk_map[cid] for cid in item.get("source_chunk_ids", []) if cid in chunk_map}


def naive_retrieved_filepages(sources: List[Dict[str, Any]]) -> Set[Tuple[str, int]]:
    return {(s["source_file"], s["page"]) for s in sources
            if s.get("source_file") and s.get("page") is not None}


def naive_cited_filepages(answer: str) -> Set[Tuple[str, int]]:
    return {(fname.strip(), int(page)) for fname, page in NAIVE_CITE_RE.findall(answer or "")}


def graphrag_retrieved_filepages(sources: List[Dict[str, Any]],
                                  chunk_map: Dict[str, Tuple[str, int]]) -> Set[Tuple[str, int]]:
    out = set()
    for s in sources:
        cid = s.get("chunk_id")
        if cid in chunk_map:
            out.add(chunk_map[cid])
    return out


def graphrag_cited_filepages(answer: str, chunk_map: Dict[str, Tuple[str, int]]) -> Set[Tuple[str, int]]:
    out = set()
    for bracket in GRAPHRAG_CITE_RE.findall(answer or ""):
        for cid in bracket.split(","):
            cid = cid.strip()
            if cid in chunk_map:
                out.add(chunk_map[cid])
    return out


def safe_ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return round(numerator / denominator, 3)


def score_naive_mechanical(output: Dict[str, Any], gold_fp: Set[Tuple[str, int]]) -> Dict[str, Any]:
    answer = output.get("answer", "")
    sources = output.get("sources") or []
    retrieved = naive_retrieved_filepages(sources)
    cited = naive_cited_filepages(answer)
    return {
        "answer": answer,
        "retrieval_time": output.get("retrieval_time"),
        "generation_time": output.get("generation_time"),
        "degraded": bool(output.get("generation_error")),
        "retrieval_recall": safe_ratio(len(retrieved & gold_fp), len(gold_fp)),
        "citation_recall": safe_ratio(len(cited & gold_fp), len(gold_fp)),
        "citation_precision": safe_ratio(len(cited & gold_fp), len(cited)),
        "overfetch_ratio": round(len(retrieved) / len(gold_fp), 2) if gold_fp else None,
        "num_retrieved": len(retrieved),
        "retrieved_filepages": sorted(f"{f}|p{p}" for f, p in retrieved),
        "cited_filepages": sorted(f"{f}|p{p}" for f, p in cited),
    }


def score_graphrag_mechanical_core(output: Dict[str, Any], gold_fp: Set[Tuple[str, int]],
                                    chunk_map: Dict[str, Tuple[str, int]]) -> Dict[str, Any]:
    answer = output.get("answer", "")
    sources = output.get("sources") or []
    retrieved = graphrag_retrieved_filepages(sources, chunk_map)
    cited = graphrag_cited_filepages(answer, chunk_map)
    degraded = bool(output.get("retrieval_error") or output.get("context_build_error")
                     or output.get("generation_error"))
    return {
        "answer": answer,
        "retrieval_time": output.get("retrieval_time"),
        "generation_time": output.get("generation_time"),
        "degraded": degraded,
        "retrieval_recall": safe_ratio(len(retrieved & gold_fp), len(gold_fp)),
        "citation_recall": safe_ratio(len(cited & gold_fp), len(gold_fp)),
        "citation_precision": safe_ratio(len(cited & gold_fp), len(cited)),
        "overfetch_ratio": round(len(retrieved) / len(gold_fp), 2) if gold_fp else None,
        "num_retrieved": len(retrieved),
        "retrieved_filepages": sorted(f"{f}|p{p}" for f, p in retrieved),
        "cited_filepages": sorted(f"{f}|p{p}" for f, p in cited),
    }


def graphrag_diagnostics(item: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
    """GraphRAG-only structural diagnostics -- delegated to the existing
    mechanical scorer, never mixed into the symmetric core metrics above."""
    from score_graphrag_mechanical import (
        score_node_coverage, score_chain_coverage, score_edge_authenticity,
    )
    gt_nodes = set(item.get("ground_truth_nodes") or [])
    row = {
        "Matched Entities": output.get("matched_entities") or [],
        "Path Nodes": output.get("path_nodes") or [],
        "Reasoning Chain": output.get("reasoning_chain") or [],
    }
    node = score_node_coverage(row, gt_nodes)
    chain = score_chain_coverage(row, item.get("expected_chain") or [])
    edges = score_edge_authenticity(row)
    return {
        "node_recall": node["node_recall"],
        "node_precision": node["node_precision"],
        "chain_coverage": chain["chain_coverage"],
        "edge_authenticity_rate": edges["edge_authenticity_rate"],
    }


CORE_METRIC_KEYS = ["retrieval_recall", "citation_recall", "citation_precision",
                    "overfetch_ratio", "retrieval_time", "generation_time"]


def mean_of(key: str, items: List[Dict[str, Any]]) -> Optional[float]:
    vals = [it[key] for it in items if it.get(key) is not None]
    return round(sum(vals) / len(vals), 3) if vals else None
