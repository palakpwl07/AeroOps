# tracing_setup.py
#
# One-time bridge so LangSmith env vars can live in .streamlit/secrets.toml
# (the same place GROQ_API_KEY/OPENROUTER_API_KEY already live) instead of
# real OS environment variables -- the langsmith SDK itself only reads
# os.environ, so this copies st.secrets -> os.environ once at import time,
# before any @traceable-decorated function or wrap_openai() client can run.
#
# Import this before importing anything that calls langsmith, i.e. at the
# top of agentic_rag.py / graph_rag.py / naive_rag.py.

from __future__ import annotations

import os

try:
    import streamlit as st
    _HAS_STREAMLIT_SECRETS = True
except Exception:
    _HAS_STREAMLIT_SECRETS = False

_VARS = (
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "LANGCHAIN_ENDPOINT",
)


def _load_into_environ() -> None:
    for key in _VARS:
        if os.getenv(key):
            continue
        value = None
        if _HAS_STREAMLIT_SECRETS:
            try:
                value = st.secrets[key]
            except Exception:
                value = None
        if value:
            os.environ[key] = str(value)

    # Sensible default so tracing doesn't silently land in LangSmith's
    # "default" project when a key is configured but the project isn't.
    os.environ.setdefault("LANGCHAIN_PROJECT", "aeroops")


_load_into_environ()

TRACING_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and bool(
    os.getenv("LANGCHAIN_API_KEY")
)


def add_metadata(fields: dict) -> None:
    """Attach arbitrary key/value fields to the currently-running
    @traceable span (e.g. retrieval_type, retrieval_time, generation_time,
    routing decision). No-ops if tracing isn't configured or no run is
    currently active."""
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is None:
            return
        run.add_metadata(fields)
    except Exception:
        pass


def tag_degraded(reason_key: str, detail: str) -> None:
    """
    Mark the currently-running @traceable span as a degraded/fallback
    path, not a clean success -- called from inside the except blocks in
    graph_rag.py, naive_rag.py, and answer_generator_groq.py so a request
    that returned a fallback string is visibly distinguishable in the
    LangSmith UI (tagged "degraded", metadata carries which stage and
    why) instead of looking identical to a normal completed trace.
    No-ops if tracing isn't configured or no run is currently active.
    """
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is None:
            return
        run.add_tags(["degraded"])
        run.add_metadata({"degraded": True, reason_key: detail})
    except Exception:
        pass
