# app.py

import os
import streamlit as st

st.set_page_config(page_title="AeroOps", page_icon="🛩️", layout="wide")

# Sync st.secrets into os.environ so naive_rag.py's plain os.getenv()
# lookups see the same values graph_rag.py's st.secrets-first lookup does.
for key, value in st.secrets.items():
    os.environ[key] = str(value)

from naive_rag import naive_rag, DOC_CONFIG
from graph_rag import graph_rag
import pandas as pd
ACCENT_NAIVE = "#4FC3F7"
ACCENT_GRAPH = "#FFB000"
BG = "#0A0E14"
PANEL_BG = "#131A24"
# -----------------------------------------------------------------------
# RAGAS EVALUATION TAB
# Add this function to app.py, then add the tab below.
#
# In your tab definitions, change:
#   tab_compare, tab_about, tab_queries = st.tabs(["Compare", "About AeroOps", "Sample Queries"])
# to:
#   tab_compare, tab_about, tab_queries, tab_ragas = st.tabs(["Compare", "About AeroOps", "Sample Queries", "RAGAS Evaluation"])
#
# Then add at the bottom:
#   with tab_ragas:
#       render_ragas_tab()
# -----------------------------------------------------------------------

def render_ragas_tab():
    st.markdown("## RAGAS Evaluation")
    st.write(
        "Both pipelines were evaluated against a 35-question ground-truth benchmark "
        "using RAGAS Faithfulness and Context Recall — two standard RAG evaluation "
        "metrics. RAGAS was run offline using Groq `llama-3.1-8b-instant` as the judge LLM "
        "against the same question set used throughout development."
    )

    # --- Headline numbers ---
    st.markdown("### Overall scores")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="panel-badge" style="background:{ACCENT_NAIVE}">NAIVE RAG</div>',
            unsafe_allow_html=True,
        )
        m1, m2 = st.columns(2)
        m1.metric("Faithfulness", "0.710", help="Mean across 32 scored items")
        m2.metric("Context Recall", "0.939", help="Mean across 22 scored items")
    with col2:
        st.markdown(
            f'<div class="panel-badge" style="background:{ACCENT_GRAPH}">GRAPHRAG</div>',
            unsafe_allow_html=True,
        )
        m3, m4 = st.columns(2)
        m3.metric("Faithfulness", "0.462", help="Mean across 35 scored items")
        m4.metric("Context Recall", "0.522", help="Mean across 35 scored items")

    st.divider()

    # --- Per-category breakdown ---
    st.markdown("### Per-category breakdown")

    CATEGORIES = [
        "factual_single_hop",
        "multi_hop_causal",
        "aggregation_fanout",
        "cross_document",
        "disambiguation",
        "provenance",
        "operational_scenario",
    ]

    # Naive RAG per-category scores
    NAIVE_FAITH = {
        "factual_single_hop":    0.870,
        "multi_hop_causal":      0.717,
        "aggregation_fanout":    0.722,
        "cross_document":        0.800,
        "disambiguation":        0.775,
        "provenance":            0.579,
        "operational_scenario":  0.451,
    }
    NAIVE_RECALL = {
        "factual_single_hop":    1.000,
        "multi_hop_causal":      0.929,
        "aggregation_fanout":    1.000,
        "cross_document":        0.833,
        "disambiguation":        0.875,
        "provenance":            1.000,
        "operational_scenario":  None,  # rate limit — not scored
    }

    # GraphRAG per-category scores
    GRAPH_FAITH = {
        "factual_single_hop":    0.444,
        "multi_hop_causal":      0.346,
        "aggregation_fanout":    0.653,
        "cross_document":        0.455,
        "disambiguation":        0.500,
        "provenance":            0.333,
        "operational_scenario":  0.471,
    }
    GRAPH_RECALL = {
        "factual_single_hop":    0.500,
        "multi_hop_causal":      0.333,
        "aggregation_fanout":    0.662,
        "cross_document":        0.167,
        "disambiguation":        0.667,
        "provenance":            0.667,
        "operational_scenario":  0.727,
    }

    CATEGORY_LABELS = {
        "factual_single_hop":    "Factual single-hop",
        "multi_hop_causal":      "Multi-hop causal",
        "aggregation_fanout":    "Aggregation / fan-out",
        "cross_document":        "Cross-document",
        "disambiguation":        "Disambiguation",
        "provenance":            "Provenance",
        "operational_scenario":  "Operational scenario",
    }

    # Faithfulness table
    st.markdown("**Faithfulness by category**")
    faith_header = ["Category", "Naive RAG", "GraphRAG", "Difference"]
    faith_rows = []
    for cat in CATEGORIES:
        naive_f = NAIVE_FAITH.get(cat)
        graph_f = GRAPH_FAITH.get(cat)
        diff = round(naive_f - graph_f, 3) if naive_f and graph_f else "—"
        faith_rows.append([
            CATEGORY_LABELS[cat],
            f"{naive_f:.3f}" if naive_f else "—",
            f"{graph_f:.3f}" if graph_f else "—",
            f"+{diff:.3f}" if isinstance(diff, float) and diff > 0
            else (f"{diff:.3f}" if isinstance(diff, float) else diff),
        ])

    import pandas as pd
    faith_df = pd.DataFrame(faith_rows, columns=faith_header)
    st.dataframe(faith_df, use_container_width=True, hide_index=True)

    # Context Recall table
    st.markdown("**Context Recall by category**")
    recall_rows = []
    for cat in CATEGORIES:
        naive_r = NAIVE_RECALL.get(cat)
        graph_r = GRAPH_RECALL.get(cat)
        if naive_r is not None and graph_r is not None:
            diff = round(naive_r - graph_r, 3)
            diff_str = f"+{diff:.3f}" if diff > 0 else f"{diff:.3f}"
        else:
            diff_str = "—"
        recall_rows.append([
            CATEGORY_LABELS[cat],
            f"{naive_r:.3f}" if naive_r is not None else "not scored*",
            f"{graph_r:.3f}" if graph_r is not None else "—",
            diff_str,
        ])

    recall_df = pd.DataFrame(recall_rows, columns=["Category", "Naive RAG", "GraphRAG", "Difference"])
    st.dataframe(recall_df, use_container_width=True, hide_index=True)
    st.caption("* Operational scenario context recall for Naive RAG not scored due to Groq rate limits during evaluation run.")

    st.divider()

    # --- Interpretation ---
    st.markdown("### How to read these numbers")
    st.write(
        "Naive RAG scores higher overall on both RAGAS metrics. This is expected — "
        "and it is not evidence that Naive RAG is the better system. It reflects a known "
        "architectural mismatch between RAGAS and GraphRAG that we documented during development."
    )

    with st.expander("Why RAGAS systematically undercounts GraphRAG", expanded=False):
        st.markdown("""
**RAGAS was designed for flat-chunk retrieval.** It checks whether the model's answer is textually entailed by the retrieved text chunks. GraphRAG's answer generator is grounded in two channels: raw chunk text *and* structured graph facts pulled from typed edges (CAUSES, MITIGATES, LEADS_TO). The graph facts are not raw chunk text — they are structured, curated claims extracted from the documents. RAGAS has no visibility into this channel, so claims grounded in graph facts get scored as "unfaithful" even when they are graph-verified correct.

**Context Recall checks concept presence, not causal correctness.** For multi-hop causal questions, RAGAS scores whether the right concepts appear anywhere in retrieved context — not whether those concepts are correctly connected in a causal chain. Naive RAG retrieving the right vocabulary scores the same as GraphRAG walking the correct causal path. This is why Naive RAG's multi-hop causal recall (0.929) looks strong despite not actually reasoning about causality.

**What RAGAS does measure accurately:** whether flat retrieved text supports a flat answer. This is genuinely useful for Naive RAG. For GraphRAG, a more accurate evaluation is the manual 35-item benchmark, which scored multi-hop causal reasoning at 99% — the category where RAGAS gives GraphRAG its lowest score (0.346 faithfulness, 0.333 recall).

These limitations are [documented in the AeroOps evaluation notes](https://github.com/palakpwl07/AeroOps).
        """)

    st.markdown("### Evaluation setup")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions", "35")
    c2.metric("Categories", "7")
    c3.metric("Judge model", "llama-3.1-8b-instant")
    c4.metric("Provider", "Groq")
    st.caption(
        "Metrics: RAGAS Faithfulness (is the answer grounded in retrieved context?) "
        "and Context Recall (does the retrieved context cover the ground-truth answer?). "
        "Both measured using LLM-as-judge. Ground truth was hand-verified, not LLM-generated."
    )

def inject_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG}; }}
    h1, h2, h3 {{ font-family: 'Helvetica Neue', Arial, sans-serif; letter-spacing: -0.02em; }}
    .panel-badge {{
        display: inline-block;
        padding: 4px 14px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: #0A0E14;
        margin-bottom: 10px;
    }}
    .latency-readout {{
        font-family: 'Courier New', monospace;
        font-size: 12px;
        color: #8A93A3;
    }}
    code {{
        font-family: 'Courier New', monospace !important;
        background-color: #1A2332 !important;
        color: {ACCENT_GRAPH} !important;
    }}
    [data-testid="stExpander"] {{
        background-color: {PANEL_BG};
        border: 1px solid #232C3A;
        border-radius: 6px;
    }}
    </style>
    """, unsafe_allow_html=True)


def build_trace_dot(path_nodes, path_edges) -> str:
    lines = [
        "digraph G {", "rankdir=LR;", 'bgcolor="transparent";',
        f'node [shape=box style="rounded,filled" fillcolor="{PANEL_BG}" '
        f'fontcolor="#E8E8E8" color="{ACCENT_GRAPH}" fontname="Helvetica" fontsize=11 margin=0.15];',
        f'edge [color="{ACCENT_GRAPH}" fontcolor="{ACCENT_GRAPH}" fontname="Helvetica" fontsize=9];',
    ]
    id_map = {}
    for i, node in enumerate(path_nodes):
        gid = f"n{i}"
        id_map[node.get("id")] = gid
        label = str(node.get("name") or node.get("id") or f"node{i}").replace('"', "'")
        lines.append(f'{gid} [label="{label}"];')
    for edge in path_edges:
        src, tgt = id_map.get(edge.get("source")), id_map.get(edge.get("target"))
        if src and tgt:
            etype = str(edge.get("type", "")).replace('"', "'")
            lines.append(f'{src} -> {tgt} [label="{etype}"];')
    lines.append("}")
    return "\n".join(lines)


def render_sources(sources, key_prefix: str):
    if not sources:
        st.caption("No sources returned.")
        return
    with st.expander("Sources", expanded=False):
        for i, src in enumerate(sources):
            chip = src.get("chunk_id") or f"{src.get('source_file', 'source')} p.{src.get('page', '?')}"
            title = src.get("title") or "Untitled"
            st.markdown(f"**`{chip}`** — {title}")
            meta_bits = []
            if src.get("page") is not None:
                meta_bits.append(f"page {src['page']}")
            if src.get("section"):
                meta_bits.append(src["section"])
            if meta_bits:
                st.caption(" · ".join(meta_bits))
            if src.get("quote"):
                st.markdown(f"> {src['quote']}")
            if src.get("view_url"):
                st.markdown(f"[Open source ↗]({src['view_url']})")
            if i < len(sources) - 1:
                st.divider()


def render_panel(label: str, accent: str, result: dict, show_trace: bool):
    st.markdown(
        f'<div class="panel-badge" style="background:{accent}">{label}</div>',
        unsafe_allow_html=True,
    )

    if result.get("retrieval_error"):
        st.error(f"Retrieval failed: {result['retrieval_error']}")
        return
    if result.get("generation_error"):
        st.warning(f"Generation issue: {result['generation_error']}")

    st.write(result.get("answer", ""))

    rt = result.get("retrieval_time", 0)
    gt = result.get("generation_time", 0)
    st.markdown(f'<span class="latency-readout">⏱ {rt}s retrieval · {gt}s generation</span>',
                unsafe_allow_html=True)

    if show_trace:
        header = "Reasoning path" if result.get("retrieval_type") == "path_traversal" else "Related graph context"
        st.markdown(f"**{header}**")
        path_nodes = result.get("path_nodes") or []
        matched = result.get("matched_entities") or []
        if path_nodes:
            st.graphviz_chart(build_trace_dot(path_nodes, result.get("path_edges") or []))
        elif matched:
            st.caption("No single traversed path for this query — matched entities:")
            st.markdown(" ".join(f"`{e['name']}`" for e in matched))
        else:
            st.caption("No graph path or matched entities for this query.")

    render_sources(result.get("sources", []), key_prefix=label)


SAMPLE_QUERIES = [
    {
        "no": 1,
        "question": "What causes a tailpipe fire?",
        "type": "Factual",
        "ground_truth": "Fuel puddling in the turbine casings/exhaust during start-up or shutdown, which then ignites.",
    },
    {
        "no": 2,
        "question": "Approximately how much do HPT clearance increases contribute to short-term performance deterioration?",
        "type": "Factual",
        "ground_truth": "Over 90 percent of total short-term deterioration (for the CF6-6D).",
    },
    {
        "no": 3,
        "question": "A sustained compressor surge is not corrected. What two distinct severe outcomes can follow?",
        "type": "Multi-hop causal",
        "ground_truth": "Severe engine damage (turbine overheat, compressor-blade damage) and flameout.",
    },
    {
        "no": 4,
        "question": "Starting from rotor/case interference, explain how engine efficiency (EGT margin) is lost.",
        "type": "Multi-hop causal",
        "ground_truth": "Rotor/case interference → blade tip rub → blade-tip clearance increase → degrades EGT margin.",
    },
    {
        "no": 5,
        "question": "Which operating factors accelerate EGT margin deterioration, and which single operational lever reduces it?",
        "type": "Multi-hop causal",
        "ground_truth": "Accelerators: high thrust rating, high OAT, short flight/sector length. Reducer: take-off derate.",
    },
    {
        "no": 6,
        "question": "Low oil pressure can accompany which failure mode, and is it a primary or secondary indicator?",
        "type": "Disambiguation",
        "ground_truth": "Flameout. Low oil pressure is secondary — EGT, core speed, and EPR drop are the primary signs.",
    },
    {
        "no": 7,
        "question": "On take-off rotation after a bird strike: loud bang, yaw, EGT spike. Identify the event, trigger, immediate crew action, and what happens if uncorrected.",
        "type": "Operational scenario",
        "ground_truth": "Compressor surge triggered by bird/FOD ingestion. Action: retard thrust lever. If uncorrected: severe engine damage or flameout.",
    },
    {
        "no": 8,
        "question": "A turbofan engine experiences a hot rotor reburst. Which engine module is primarily affected, and what design feature mitigates it?",
        "type": "Operational scenario",
        "ground_truth": "The High-Pressure Turbine (HPT) is primarily affected by tip clearance increase. Mitigation: active clearance control / case cooling bleed.",
    },
    {
        "no": 9,
        "question": "What are the three levels of workscopes specified by turbofan engine manufacturers, and what tasks are required during a Full Overhaul?",
        "type": "Procedural",
        "ground_truth": "Minimum Level, Performance Level, Full Overhaul Level. Full Overhaul: disassemble to piece-parts, full serviceability inspection of every part, replace or repair as required.",
    },
    {
        "no": 10,
        "question": "What are the acceptable procedures and limitations for repairing minor damage (nicks/dents) on an axial-flow compressor blade?",
        "type": "Procedural",
        "ground_truth": "Damage must be well-rounded, in the outer half of the blade, within manufacturer limits. Rework by hand using stones/files/emery cloth, parallel to blade length. No power tools. Surface finish must match a new blade.",
    },
    {
        "no": 11,
        "question": "During a hot section inspection, what do stress rupture cracks on turbine blades look like, and what do they indicate?",
        "type": "Procedural",
        "ground_truth": "Minute hairline cracks on/across leading or trailing edge, at right angles to the edge length. Indicates an over-temperature condition.",
    },
    {
        "no": 12,
        "question": "What specific mechanism causes over 90% of short-term HPT performance deterioration in the CF6-6D, and what abnormal event triggers it?",
        "type": "Factual",
        "ground_truth": "HPT clearance increases caused by hot rotor reburst — a thermal transient causing rotor/case interference and blade rubs due to different thermal growth rates between rotating and stationary structures.",
    },
]


def render_sample_queries_tab():
    st.markdown("## Sample Queries & Ground Truth")
    st.write(
        "Not familiar with turbofan maintenance? These 12 questions span the range of reasoning "
        "types AeroOps was built and evaluated on — factual lookups, multi-hop causal chains, "
        "disambiguation, procedural retrieval, and operational scenarios. Copy any question "
        "into the Compare tab to see how both systems respond."
    )

    type_colors = {
        "Factual": ACCENT_NAIVE,
        "Multi-hop causal": ACCENT_GRAPH,
        "Disambiguation": "#A78BFA",
        "Operational scenario": "#34D399",
        "Procedural": "#F87171",
    }

    for item in SAMPLE_QUERIES:
        color = type_colors.get(item["type"], "#8A93A3")
        with st.expander(f"**{item['no']}.** {item['question']}", expanded=False):
            st.markdown(
                f'<span style="display:inline-block;padding:2px 10px;border-radius:4px;'
                f'background:{color};color:#0A0E14;font-size:11px;font-weight:700;'
                f'font-family:monospace;letter-spacing:0.08em;">{item["type"].upper()}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**Ground truth:** {item['ground_truth']}")


def render_about_tab():
    st.markdown("## About AeroOps")
    st.write(
        "AeroOps is a GraphRAG system built over a turbofan engine maintenance knowledge graph, "
        "designed to compare graph-grounded retrieval against naive flat-chunk RAG on the same "
        "seven source documents. The graph encodes failure modes, causes, mitigations, symptoms, "
        "parameters, and operating factors as typed entities and relationships, with every claim "
        "traceable to its exact source chunk and page."
    )

    st.markdown("### Knowledge graph")
    c1, c2, c3 = st.columns(3)
    c1.metric("Nodes", "267")
    c2.metric("Relationships", "560")
    c3.metric("Source documents", "7")
    st.caption(
        "Entity types: FailureMode, Symptom, Cause, Mitigation, Parameter, "
        "OperatingFactor, Method, Part, Module, Engine, plus Claim and Document "
        "provenance nodes."
    )

    st.markdown("### Source documents")
    st.markdown(
        "All seven source documents are publicly available — "
        "[view the full document library on Google Drive ↗](https://drive.google.com/drive/folders/1masPUYiArHj2LrOGIkWn1O7S2pmQc_C4?usp=sharing)"
    )
    rows = []
    for filename, meta in DOC_CONFIG.items():
        rows.append({
            "Title": meta.get("document_title", filename),
            "Type": meta.get("doc_type", ""),
            "File": filename,
        })
    st.table(rows)


inject_css()

# Banner image
if os.path.exists("banner.jpg"):
    st.image("banner.jpg", use_container_width=True)

tab_compare, tab_about, tab_queries, tab_ragas = st.tabs(["Compare", "About AeroOps", "Sample Queries", "RAGAS Evaluation & Comparison"])

with tab_compare:
    st.markdown("# AeroOps")
    st.caption("Naive RAG vs GraphRAG over turbofan engine maintenance documents")
    st.markdown(
        """
        <p style="font-size: 0.82rem; color: #6b7280; margin-top: -0.4rem;">
        Demo note: The first query takes longer while the index warms up.
        If GraphRAG returns a Neo4j connection error, rerunning the query usually resolves it.
        </p>
        """,
        unsafe_allow_html=True,
    )

    with st.form("query_form"):
        query = st.text_input(
            "Ask a maintenance question. Not sure what to ask? See the Sample Queries tab for 12 questions with their ground truth for you to compare.",
            placeholder="e.g. What causes a compressor surge?",
        )
        submitted = st.form_submit_button("Compare")

    if submitted and query.strip():
        col1, col2 = st.columns(2)

        with col1:
            with st.spinner("Running naive RAG..."):
                naive_result = naive_rag(query)
            render_panel("NAIVE RAG", ACCENT_NAIVE, naive_result, show_trace=False)

        with col2:
            with st.spinner("Running GraphRAG..."):
                graph_result = graph_rag(query)
            render_panel("GRAPHRAG", ACCENT_GRAPH, graph_result, show_trace=True)

with tab_about:
    render_about_tab()

with tab_queries:
    render_sample_queries_tab()

with tab_ragas:
    render_ragas_tab()
