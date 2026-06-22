# src/retrieval/naive_rag.py
#
# Cloud-deployable conversion of aeroops_v2_generation_layer_patched.ipynb
#
# Changes vs notebook: ChatOllama -> Groq, ChromaDB rebuilds fresh at
# startup instead of loading a committed binary, setup wrapped in
# @st.cache_resource, KNOWLEDGEBASE_PATH is relative.
#
# Changes from today's review:
#   - DRIVE_VIEW_URLS added; format_sources() now includes view_url
#     so naive RAG's citation panel can link out, same as GraphRAG's.
#   - build_context_with_sources() now tags each chunk with
#     [CITE: filename p.N] instead of [Source N], so the model's
#     inline citations name the actual document.
#   - GENERATION_PROMPT_TEMPLATE rewritten: dropped the rigid
#     "Procedure: numbered steps" framing that was forcing every
#     answer (including simple factual ones) into a long forced
#     step-list. Now defaults to 2-4 sentences, procedure format only
#     when the question actually asks for steps.

from __future__ import annotations

import os
import re
import tempfile
import time
from typing import Any, Dict, List, Optional

import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

KNOWLEDGEBASE_PATH = os.getenv("AEROOPS_KB_PATH", "./knowledgebase")

GROQ_MODEL = os.getenv("NAIVE_RAG_GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ---------------------------------------------------------------------------
# >>> PASTE YOUR EXISTING DOC_CONFIG DICT HERE, UNCHANGED <
# (the 7-entry dict with document_title, doc_type, key_topics, etc.
#  per PDF filename -- not reproduced here, see note above)
# ---------------------------------------------------------------------------

DRIVE_VIEW_URLS = {
    "AirTrafficControlResearch.pdf": "https://drive.google.com/file/d/19oEvsgRnuSDZVsbzeA0tiBK-A5O0lV7H/view",
    "EngineMaintenanceConcepts.pdf": "https://drive.google.com/file/d/1fWN-VIWURIoBXAHZu3wglGNCEvF5gUfa/view",
    "PERFORMANCE_DETERIORATION_of_turbofan_engines.pdf": "https://drive.google.com/file/d/1wHWZxLghnbFmXXl7MwVxtxThc4GW1dk-/view",
    "AIforTurbofanEngines.pdf": "https://drive.google.com/file/d/10j8JCJDB3GP7n-RBuHd6kAxPeK_LGhHi/view",
    "FaultPrognosisofTurbofanEngines.pdf": "https://drive.google.com/file/d/1xEPKcPxd2SHRvoYCBMvj6WPXj7ZcQ0nK/view",
    "TurbofanEnginMaintenanceandOperation.pdf": "https://drive.google.com/file/d/1L4vsCNdJlCZ1bLjAm3LWRc0tI-uo9SJJ/view",
    "TurbofanEngineFamiliarization.pdf": "https://drive.google.com/file/d/1ok4A2LyWIsRfDurEvfNHB3OG5ZZuQigP/view",
}

DOC_CONFIG = {

    "AirTrafficControlResearch.pdf": {
        "document_title": "Aircraft Turbine Engine Control Research at NASA Glenn Research Center",
        "doc_type": "technical_report",
        "domain": "diagnostics",
        "subdomain": "control_law_and_diagnostics_research",
        "asset_type": "turbofan_engine",
        "manufacturer": "General Electric, Pratt & Whitney",
        "authority": "NASA",
        "engine_family": "JT9D, F100, F414, CFM56",
        "aircraft_family": "F-15, F-18, Commercial Aircraft",
        "major_components": [
            "FADEC",
            "sensors",
            "actuators",
            "fuel metering valve",
            "variable bleed valve",
            "variable stator vanes",
            "fan",
            "compressor",
            "combustor",
            "turbines"
        ],
        "major_topics": [
            "engine control systems",
            "full authority digital engine control",
            "model-based diagnostics",
            "distributed engine control",
            "active stall control",
            "active combustion control"
        ],
        "key_acronyms": ["FADEC", "GRC", "CDB", "EGT", "EPR", "PLA", "VBV", "VSV", "LQR"],
        "procedures_present": [
            "burst-chop test",
            "sensor validation checks",
            "performance restoration",
            "fault management",
            "model tuning parameter selection"
        ],
        "failure_modes": [
            "rotor overspeed",
            "compressor stall",
            "combustor blowout",
            "turbine overtemperature",
            "sensor fault",
            "component degradation"
        ],
        "inspection_methods": [
            "on-wing health monitoring",
            "built-in test functions",
            "sensor and actuator validation checks",
            "gas path diagnostics"
        ],
        "regulatory_references": [
            "FAA certification requirements",
            "International Traffic in Arms Regulations (ITAR)"
        ]
    },

    "EngineMaintenanceConcepts.pdf": {
        "document_title": "Engine Maintenance Concepts for Financiers",
        "doc_type": "technical_report",
        "domain": "maintenance",
        "subdomain": "maintenance_economics_and_planning",
        "asset_type": "turbofan_engine",
        "manufacturer": "General Electric, SNECMA, Rolls-Royce, Pratt & Whitney",
        "authority": "FAA",
        "engine_family": "CFM56, V2500",
        "aircraft_family": "Boeing 757, Boeing 767, MD-87/88",
        "major_components": [
            "Fan",
            "Low Pressure Compressor (LPC)",
            "High Pressure Compressor (HPC)",
            "Combustor",
            "High Pressure Turbine (HPT)",
            "Low Pressure Turbine (LPT)",
            "Accessory Drives",
            "Life Limited Parts (LLPs)"
        ],
        "major_topics": [
            "Direct Maintenance Costs",
            "Time On-Wing",
            "performance restoration",
            "on-condition monitoring",
            "workscope planning",
            "Parts Manufacturer Approval",
            "maintenance reserves"
        ],
        "key_acronyms": ["DMC", "TOW", "EGT", "EGTM", "LLP", "PMA", "SVR", "RSVR", "FHA"],
        "procedures_present": [
            "performance restoration shop visit",
            "on-condition monitoring",
            "borescope inspection",
            "engine water washing",
            "workscope management",
            "maintenance reserve development"
        ],
        "failure_modes": [
            "EGT margin deterioration",
            "LLP expiry",
            "hardware deterioration",
            "foreign object damage",
            "high oil consumption",
            "engine vibration",
            "airfoil erosion"
        ],
        "inspection_methods": [
            "borescope inspection",
            "video borescope",
            "performance trend monitoring",
            "visual inspection",
            "piece-part inspection"
        ],
        "regulatory_references": ["FAR 21.303", "Order 8110.42", "Airworthiness Directives"]
    },

    "PERFORMANCE_DETERIORATION_of_turbofan_engines.pdf": {
        "document_title": "Performance Deterioration of Commercial High-Bypass Ratio Turbofan Engines",
        "doc_type": "technical_report",
        "domain": "diagnostics",
        "subdomain": "performance_loss_analysis",
        "asset_type": "turbofan_engine",
        "manufacturer": "Pratt & Whitney, General Electric",
        "authority": "NASA",
        "engine_family": "JT9D, CF6",
        "aircraft_family": "Boeing 747, Douglas DC-10",
        "major_components": [
            "Fan",
            "Compressor",
            "High Pressure Turbine (HPT)",
            "Low Pressure Turbine (LPT)",
            "Combustion system",
            "turbine nozzle",
            "nacelle"
        ],
        "major_topics": [
            "performance deterioration mechanisms",
            "specific fuel consumption increase",
            "blade tip rubs",
            "flight loads influence",
            "clearance increases"
        ],
        "key_acronyms": ["SFC", "EGT", "FOD", "NASTRAN", "ACEE", "ECI", "HPT", "LPT"],
        "procedures_present": [
            "engine testing",
            "production acceptance",
            "cruise performance recording",
            "hardware inspection",
            "simulated aerodynamic load test",
            "flight test",
            "analytical teardown"
        ],
        "failure_modes": [
            "blade tip rubs",
            "airfoil surface roughness",
            "erosion",
            "thermal distortion",
            "clearance increases",
            "foreign object damage"
        ],
        "inspection_methods": [
            "X-ray facility",
            "laser proximity probes",
            "thermocouples",
            "pressure taps",
            "magnetic particle inspection",
            "fluorescent penetrant inspection"
        ],
        "regulatory_references": ["NASA Aircraft Energy Efficiency (ACEE) program"]
    },

    "AIforTurbofanEngines.pdf": {
        "document_title": "Explainable Artificial Intelligence for Exhaust Gas Temperature of Turbofan Engines",
        "doc_type": "research_paper",
        "domain": "prognostics",
        "subdomain": "engine_health_monitoring",
        "asset_type": "turbofan_engine",
        "manufacturer": "GE",
        "authority": "Not in source",
        "engine_family": "GEnx",
        "aircraft_family": "Boeing 787-10",
        "major_components": [
            "High Pressure Turbine (HPT)",
            "High Pressure Compressor (HPC)",
            "Low Pressure Turbine (LPT)",
            "Fuel Splitting Valve",
            "Variable Bleed Valve",
            "Engine Booster"
        ],
        "major_topics": [
            "symbolic regression",
            "explainable AI",
            "EGT modeling",
            "genetic programming",
            "continuous engine operating data"
        ],
        "key_acronyms": ["EGT", "SR", "GP", "CEOD", "MGGP", "EHM", "PHM", "MAE", "RMSE"],
        "procedures_present": [
            "data preprocessing",
            "symbolic regression experiments",
            "correlation analysis",
            "normalization",
            "model validation on unseen flight data"
        ],
        "failure_modes": [
            "isentropic efficiency deterioration",
            "gas path component deterioration",
            "sensor malfunction"
        ],
        "inspection_methods": [
            "continuous engine operating data analysis",
            "snapshot data analysis"
        ],
        "regulatory_references": ["SAE Aerospace Standard AS755"]
    },

    "FaultPrognosisofTurbofanEngines.pdf": {
        "document_title": "Fault Prognosis of Turbofan Engines: Eventual Failure Prediction and Remaining Useful Life Estimation",
        "doc_type": "research_paper",
        "domain": "prognostics",
        "subdomain": "health_management",
        "asset_type": "turbofan_engine",
        "manufacturer": "Not in source",
        "authority": "NASA",
        "engine_family": "N-CMAPSS simulated",
        "aircraft_family": "Not in source",
        "major_components": [
            "Fan",
            "Low-pressure compressor (LPC)",
            "High-pressure compressor (HPC)",
            "Low-pressure turbine (LPT)",
            "High-pressure turbine (HPT)"
        ],
        "major_topics": [
            "Remaining Useful Life estimation",
            "fault prognosis",
            "deep learning",
            "PCA orthogonalization",
            "ANN-Flux"
        ],
        "key_acronyms": ["PHM", "RUL", "N-CMAPSS", "PCA", "ANN", "RMSE", "BCE", "AUROC"],
        "procedures_present": [
            "feature extraction",
            "min-max normalization",
            "PCA orthogonalization",
            "supervised training of ANNs",
            "customized loss function optimization"
        ],
        "failure_modes": [
            "mechanical component efficiency failure",
            "flow failure"
        ],
        "inspection_methods": [
            "simulated sensor measurement analysis"
        ],
        "regulatory_references": [" "]
    },

    "TurbofanEnginMaintenanceandOperation.pdf": {
        "document_title": "Engine Maintenance & Operation",
        "doc_type": "maintenance_manual",
        "domain": "maintenance",
        "subdomain": "overhaul_and_inspection_procedures",
        "asset_type": "turbofan_engine",
        "manufacturer": "Not in source",
        "authority": "FAA",
        "engine_family": "Not in source",
        "aircraft_family": "Not in source",
        "major_components": [
            "crankshaft",
            "cylinders",
            "pistons",
            "rings",
            "valves",
            "valve springs",
            "fuel nozzles",
            "turbine disc",
            "turbine blades",
            "compressor blades",
            "jetcal analyzer"
        ],
        "major_topics": [
            "engine overhaul",
            "non-destructive testing",
            "visual inspection",
            "cleaning and degreasing",
            "engine testing",
            "troubleshooting",
            "turbine engine instrumentation"
        ],
        "key_acronyms": ["TBO", "NDT", "CPM", "CAT", "EGT", "EPR", "RPM", "TIT", "ITT", "TAT", "FADEC"],
        "procedures_present": [
            "receiving inspection",
            "disassembly",
            "cleaning",
            "structural inspection",
            "magnetic particle inspection",
            "dye penetrant inspection",
            "eddy current inspection",
            "ultrasonic inspection",
            "X-ray inspection",
            "dimensional inspection",
            "cylinder grinding",
            "valve lapping",
            "magneto safety check",
            "cold cylinder check",
            "turbine blade replacement"
        ],
        "failure_modes": [
            "abrasion",
            "brinelling",
            "burning",
            "corrosion",
            "cracks",
            "erosion",
            "galling",
            "pitting",
            "scoring",
            "detonation",
            "pre-ignition",
            "backfiring",
            "hydraulic lock",
            "stress rupture cracks"
        ],
        "inspection_methods": [
            "visual inspection",
            "magnetic particle inspection",
            "dye penetrant inspection",
            "eddy current inspection",
            "ultrasonic inspection",
            "X-ray",
            "dimensional evaluation",
            "cold cylinder check",
            "jetcal analyzer check"
        ],
        "regulatory_references": ["14 CFR part 39", "section 39.27", "FAA-H-8083-30"]
    },

    "TurbofanEngineFamiliarization.pdf": {
        "document_title": "Airplane Turbofan Engine Operation and Malfunctions: Basic Familiarization for Flight Crews",
        "doc_type": "technical_report",
        "domain": "maintenance",
        "subdomain": "flight_crew_operations",
        "asset_type": "turbofan_engine",
        "manufacturer": "Not in source",
        "authority": "Not in source",
        "engine_family": "Not in source",
        "aircraft_family": "Boeing 747, 757, 767; Airbus A300, A310",
        "major_components": [
            "Compressor",
            "N1",
            "N2",
            "Combustor",
            "Turbine",
            "Accessory Drive Gearbox",
            "Fuel Nozzles",
            "Igniters",
            "Bleed Valves",
            "Fan"
        ],
        "major_topics": [
            "propulsion principles",
            "engine systems",
            "cockpit instrumentation",
            "malfunction diagnosis"
        ],
        "key_acronyms": ["EPR", "EGT", "RPM", "FADEC", "EEC", "IFSD", "FOD", "EICAS", "ECAM"],
        "procedures_present": [
            "engine start-up",
            "in-flight restart",
            "fire shutdown",
            "tailpipe fire dry motoring",
            "retarding thrust lever for surge recovery"
        ],
        "failure_modes": [
            "compressor surge",
            "compressor stall",
            "flameout",
            "engine fire",
            "tailpipe fire",
            "hot start",
            "bird ingestion",
            "engine seizure",
            "engine separation"
        ],
        "inspection_methods": [
            "cockpit gauge monitoring",
            "EPR monitoring",
            "N1 monitoring",
            "N2 monitoring",
            "EGT monitoring",
            "chip detection",
            "fire loops testing"
        ],
        "regulatory_references": ["AFM"]
    }
}
# ---------------------------------------------------------------------------
# Index setup (cached -- runs once per app instance, not per query)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Tokenizer for BM25. Keeps technical tokens like CFM56-5B, N-CMAPSS intact."""
    return re.findall(r"\b[a-zA-Z0-9]+(?:[-\u2013][a-zA-Z0-9]+)*\b", text.lower())


@st.cache_resource(show_spinner="Building naive RAG index (PDFs -> chunks -> embeddings + BM25)...")
def _build_index():
    all_docs = []

    for file in sorted(os.listdir(KNOWLEDGEBASE_PATH)):
        if not file.endswith(".pdf"):
            continue

        path = os.path.join(KNOWLEDGEBASE_PATH, file)
        loader = PyPDFLoader(path)
        docs = loader.load()

        metadata = DOC_CONFIG.get(file, {})

        for doc in docs:
            doc.metadata["source_file"] = file
            for key, value in metadata.items():
                doc.metadata[key] = value

        all_docs.extend(docs)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(all_docs)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    persist_dir = tempfile.mkdtemp(prefix="aeroops_chroma_")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
    )

    bm25_corpus = [_tokenize(doc.page_content) for doc in chunks]
    bm25 = BM25Okapi(bm25_corpus)

    return {
        "chunks": chunks,
        "vectorstore": vectorstore,
        "bm25": bm25,
    }


@st.cache_resource(show_spinner=False)
def _get_groq_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("GROQ_API_KEY", ""),
        base_url=GROQ_BASE_URL,
    )


# ---------------------------------------------------------------------------
# Hybrid retrieval (BM25 + vector + metadata filter)
# ---------------------------------------------------------------------------

def _metadata_match(doc, metadata_filter: Optional[Dict[str, Any]]) -> bool:
    if metadata_filter is None:
        return True
    for key, expected_value in metadata_filter.items():
        if doc.metadata.get(key) != expected_value:
            return False
    return True


def _infer_metadata_filter(query: str) -> Optional[Dict[str, Any]]:
    q = query.lower()

    if any(term in q for term in [
        "fadec", "full authority digital engine control", "eec",
        "electronic engine control", "engine control",
        "distributed engine control", "control law", "sensor validation",
        "actuator validation", "model-based diagnostics",
    ]):
        return {"source_file": "AircraftTurbineEngineControlResearchatNASAGlennResearchCenter.pdf"}

    if any(term in q for term in [
        "rul", "remaining useful life", "fault prognosis", "failure prediction",
        "ann-flux", "n-cmapss", "pca", "deep learning", "symbolic regression",
        "explainable ai", "machine learning", "health management",
        "health monitoring", "predictive maintenance", "prognostics",
    ]):
        return {"domain": "prognostics"}

    if any(term in q for term in [
        "fadec", "engine control", "sensor", "actuator", "diagnostics",
        "egt", "epr", "performance deterioration", "performance loss",
        "blade tip rub", "specific fuel consumption", "stall control",
        "combustion control", "engine degradation", "gas path",
    ]):
        return {"domain": "diagnostics"}

    if any(term in q for term in [
        "inspection", "compression test", "borescope", "overhaul",
        "maintenance", "repair", "troubleshooting", "hot start", "flameout",
        "surge", "stall", "fire", "blade replacement", "magnetic particle",
        "dye penetrant", "eddy current", "ultrasonic inspection",
        "x-ray inspection", "engine start", "engine operation",
    ]):
        return {"domain": "maintenance"}

    return None


def _vector_retrieve(vectorstore, query: str, metadata_filter=None, k=10, fetch_k=20):
    search_kwargs = {"k": k, "fetch_k": fetch_k}
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter

    retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs=search_kwargs)
    return retriever.invoke(query)


def _bm25_retrieve(bm25, chunks, query: str, metadata_filter=None, k=10):
    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results = []
    for idx in ranked_indices:
        doc = chunks[idx]
        if not _metadata_match(doc, metadata_filter):
            continue
        results.append(doc)
        if len(results) >= k:
            break

    return results


def _deduplicate_docs(docs):
    seen = set()
    unique_docs = []
    for doc in docs:
        key = (
            doc.metadata.get("source_file"),
            doc.metadata.get("page"),
            doc.page_content[:160],
        )
        if key not in seen:
            seen.add(key)
            unique_docs.append(doc)
    return unique_docs


def hybrid_retrieve(query: str, k=5, vector_k=10, bm25_k=10):
    index = _build_index()
    chunks, vectorstore, bm25 = index["chunks"], index["vectorstore"], index["bm25"]

    metadata_filter = _infer_metadata_filter(query)

    vector_results = _vector_retrieve(
        vectorstore, query, metadata_filter=metadata_filter,
        k=vector_k, fetch_k=max(vector_k * 2, 20),
    )
    bm25_results = _bm25_retrieve(
        bm25, chunks, query, metadata_filter=metadata_filter, k=bm25_k,
    )

    merged_results = _deduplicate_docs(vector_results + bm25_results)
    return merged_results[:k]


# ---------------------------------------------------------------------------
# Context assembly, source formatting, numeric-preservation guardrail
# ---------------------------------------------------------------------------

def build_context_with_sources(results) -> str:
    context_blocks = []
    for doc in results:
        source = doc.metadata.get("source_file", "Unknown source")
        page = doc.metadata.get("page", "Unknown page")
        title = doc.metadata.get("document_title", "Unknown title")
        cite_tag = f"{source} p.{page}"

        block = f"""
[CITE: {cite_tag}]
Title: {title}

{doc.page_content}
"""
        context_blocks.append(block)

    return "\n\n".join(context_blocks)


def format_sources(results) -> List[Dict[str, Any]]:
    seen = set()
    sources = []
    for doc in results:
        key = (doc.metadata.get("source_file"), doc.metadata.get("page"))
        if key not in seen:
            seen.add(key)
            source_file = doc.metadata.get("source_file")
            sources.append({
                "source_file": source_file,
                "page": doc.metadata.get("page"),
                "title": doc.metadata.get("document_title"),
                "view_url": DRIVE_VIEW_URLS.get(source_file),
            })
    return sources


CRITICAL_NUMBER_PATTERN = re.compile(
    r"""
    (?:
        \b\d+(?:\.\d+)?\s*(?:to|-|\u2013)\s*\d+(?:\.\d+)?\s*
        (?:psi|PSI|in\.?\s*Hg|["\u201d]\s*Hg|rpm|RPM|\u00b0C|percent|%)?
    )
    |
    (?:
        \b\d+(?:\.\d+)?\s*
        (?:psi|PSI|in\.?\s*Hg|["\u201d]\s*Hg|rpm|RPM|\u00b0C|percent|%)\b
    )
    """,
    re.VERBOSE,
)


def extract_critical_numbers(text: str) -> set:
    return {match.group(0).strip() for match in CRITICAL_NUMBER_PATTERN.finditer(text)}


def check_numeric_preservation(context: str, answer: str) -> Dict[str, Any]:
    context_numbers = extract_critical_numbers(context)
    answer_numbers = extract_critical_numbers(answer)
    missing_numbers = sorted(context_numbers - answer_numbers)

    return {
        "context_numbers": sorted(context_numbers),
        "answer_numbers": sorted(answer_numbers),
        "missing_numbers": missing_numbers,
        "numeric_preservation_passed": len(missing_numbers) == 0,
    }


GENERATION_PROMPT_TEMPLATE = """
You are AeroOps, an aircraft maintenance documentation assistant.

Your job is to extract the exact answer from the retrieved maintenance context.
You are NOT allowed to use outside knowledge.

Critical rules:
1. Use ONLY the provided context.
2. Answer directly and concisely. Default to 2-4 sentences. Only use a numbered
   step-by-step procedure if the question explicitly asks for steps, a procedure,
   or "how to" instructions -- do not force every answer into a procedure format.
3. Preserve every maintenance-critical number, unit, pressure, range, limit, and
   condition exactly as written.
4. Do not invent setup steps, safety steps, test conditions, causes, tools, or
   interpretations that are not stated in the context.
5. Do not combine unrelated chunks unless they directly continue the same point.
6. Cite claims inline using the exact [CITE: ...] tag shown above the source block
   you drew from, e.g. [CITE: EngineMaintenanceConcepts.pdf p.17].
7. If the answer is not in the context, say so in one sentence. Do not guess or
   pad the answer with tangential context to fill space.
8. Do not say "as an AI model".

Context:
{context}

Question:
{query}

Answer:
"""


def generate_answer_with_citations(query: str, results) -> Dict[str, Any]:
    context = build_context_with_sources(results)
    prompt = GENERATION_PROMPT_TEMPLATE.format(context=context, query=query)

    client = _get_groq_client()

    start = time.time()
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
        )
    except Exception as exc:
        generation_time = time.time() - start
        generation_error = f"Groq generation failed. Details: {exc}"
        return {
            "query": query,
            "answer": "Answer generation failed after retrieval completed. See generation_error for details.",
            "generation_time": round(generation_time, 2),
            "context_length": len(context),
            "sources": format_sources(results),
            "generation_error": generation_error,
            "numeric_check": check_numeric_preservation(context, ""),
        }

    generation_time = time.time() - start
    answer = response.choices[0].message.content

    numeric_check = check_numeric_preservation(context, answer)

    return {
        "query": query,
        "answer": answer,
        "generation_time": round(generation_time, 2),
        "context_length": len(context),
        "sources": format_sources(results),
        "numeric_check": numeric_check,
    }


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def naive_rag(query: str, k: int = 5) -> Dict[str, Any]:
    start = time.time()
    results = hybrid_retrieve(query, k=k)
    retrieval_time = time.time() - start

    output = generate_answer_with_citations(query, results)
    output["retrieval_time"] = round(retrieval_time, 2)

    return output