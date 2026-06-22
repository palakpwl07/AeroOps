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

ACCENT_NAIVE = "#4FC3F7"
ACCENT_GRAPH = "#FFB000"
BG = "#0A0E14"
PANEL_BG = "#131A24"


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

tab_compare, tab_about, tab_queries = st.tabs(["Compare", "About AeroOps", "Sample Queries"])

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