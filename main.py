# main.py
#
# Minimal FastAPI wrapper around graph_rag(query) so it's reachable over
# HTTP (Fargate + a real frontend later). No business logic here -- this
# file only does request/response schemas, a health check, and a
# boundary-level exception handler. graph_rag.py is untouched.
#
# Simplified to GraphRAG-only: naive RAG and the agentic router were
# archived (see archive_naive_agentic/README.md) after the jury-scored
# evaluation harness showed naive losing to GraphRAG on every question
# category and the router adding no measured benefit over calling GraphRAG
# directly. The /compare endpoint (naive vs. graphrag side by side) was
# dropped along with naive -- there's nothing left to compare against.
#
# Run locally:
#   uvicorn main:app --reload

from __future__ import annotations

import functools
import os
import time
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Load secrets from .streamlit/secrets.toml into os.environ BEFORE any other
# import -- mirrors every run_*_eval.py script's own bootstrap. graph_rag.py
# and tracing_setup.py both read NEO4J_*, OPENROUTER_API_KEY, LANGCHAIN_* via
# os.getenv() as their fallback when st.secrets isn't backed by a real
# Streamlit context, which is exactly the case here.
# ---------------------------------------------------------------------------
try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib

_secrets_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml"
)
if os.path.exists(_secrets_path):
    with open(_secrets_path, "rb") as f:
        for k, v in tomllib.load(f).items():
            os.environ.setdefault(k, str(v))

# ---------------------------------------------------------------------------
# st.cache_resource is built for a real `streamlit run` ScriptRunContext,
# which doesn't exist under uvicorn. Every run_*_eval.py script in this repo
# already patches it to a real functools.lru_cache before importing
# graph_rag/naive_rag for exactly this reason -- reusing that established
# pattern here rather than inventing a new one for the API layer.
# ---------------------------------------------------------------------------
import streamlit as st


def _real_cache_resource(**kwargs):
    def decorator(func):
        @functools.lru_cache(maxsize=1)
        def cached(*args, **kw):
            return func(*args, **kw)
        return cached
    return decorator


st.cache_resource = _real_cache_resource
st.cache_data = lambda **kwargs: (lambda f: f)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

import logging

from graph_rag import graph_rag, _get_pipeline as _get_graphrag_pipeline

logger = logging.getLogger("aeroops.main")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="AeroOps Agentic RAG API")
app.mount("/static", StaticFiles(directory=os.path.join(_BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(_BASE_DIR, "templates"))

# Appended as ?v=... on every /static asset URL in index.html so a
# redeploy always forces a fresh fetch -- process start time is a cheap
# stand-in for a real content hash, good enough since every deploy here
# recreates the container (and therefore restarts the process) anyway.
# Added after repeatedly hitting the *_no_heuristic_cache_for_static
# middleware alone not being enough: a browser that already cached
# style.css/app.js from BEFORE that header existed keeps reusing that
# cached copy under its own heuristic-freshness rules regardless of what
# Cache-Control later responses carry -- only a URL change forces a
# guaranteed fresh request, which is what actually needs to happen for a
# frontend that's still being actively iterated on.
STATIC_VERSION = str(int(time.time()))


@app.middleware("http")
async def _no_heuristic_cache_for_static(request: Request, call_next):
    # StaticFiles sets Last-Modified/ETag but no Cache-Control -- with no
    # explicit freshness directive, browsers fall back to RFC 7234
    # heuristic caching (roughly 10% of the file's age since
    # Last-Modified) and will silently keep serving a stale style.css/
    # app.js for hours after a redeploy, with zero network request to
    # even check. Confirmed hitting this directly: after pushing a CSS
    # fix and rebuilding the container, a fresh page load still rendered
    # the OLD rule because the browser never re-asked the server, while a
    # manually cache-busted fetch() got the new one immediately. no-cache
    # (not no-store) still lets the browser keep the file and do a cheap
    # conditional GET each time -- a 304 when nothing changed, a real 200
    # the moment it has -- rather than paying full download cost or
    # risking staleness.
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response

# CORS: not configured. No frontend exists yet to call this cross-origin --
# the new UI is served by this same FastAPI process (templates + /static),
# so browser requests to /query are same-origin. Revisit only if a
# separately-hosted frontend calls this API later; adding CORSMiddleware
# then is a five-line change, not a redesign.

DEGRADED_KEYS = ("retrieval_error", "context_build_error", "generation_error")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    query: str
    answer: str
    retrieval_time: Optional[float] = None
    generation_time: Optional[float] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    degraded: bool
    degraded_fields: List[str] = Field(default_factory=list)
    # Real per-request counts read off the OpenAI-compatible response
    # object at generation time (answer_generator_groq.py's
    # AnswerGenerator._extract_usage) -- not estimated. estimated_cost_usd
    # can be None even when tokens are present, if OpenRouter's response
    # didn't carry a recognized `provider` to price against (see
    # PRICING_PER_TOKEN_USD's sourcing note in answer_generator_groq.py).
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    # The specific OpenRouter backing provider that served this exact
    # call (e.g. "Parasail", "Darkbloom") -- varies per request since
    # OpenRouter routes gpt-oss-20b dynamically, which is also why cost
    # varies between otherwise-similar queries. None under the same
    # conditions as estimated_cost_usd being None.
    provider: Optional[str] = None


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = graph_rag(request.question)
    except Exception as exc:
        # graph_rag() already degrades known failure modes (retrieval,
        # context-build, generation) into a fallback string instead of
        # raising -- so anything that reaches here is something the
        # hardening didn't anticipate. Surface it as a real 500 with the
        # actual error, not a 200 wrapping a fallback string or a silent
        # unhandled exception.
        raise HTTPException(
            status_code=500, detail=f"graph_rag failed unexpectedly: {exc}"
        ) from exc

    degraded_fields = [k for k in DEGRADED_KEYS if result.get(k)]

    return QueryResponse(
        query=request.question,
        answer=result.get("answer", ""),
        retrieval_time=result.get("retrieval_time"),
        generation_time=result.get("generation_time"),
        sources=result.get("sources") or [],
        degraded=bool(degraded_fields),
        degraded_fields=degraded_fields,
        prompt_tokens=result.get("prompt_tokens"),
        completion_tokens=result.get("completion_tokens"),
        estimated_cost_usd=result.get("estimated_cost_usd"),
        provider=result.get("provider"),
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"static_version": STATIC_VERSION})


@app.get("/health")
def health():
    # Neo4j: a real round-trip (verify_connectivity), not just "the driver
    # object exists" -- catches a dead/reset connection, which is the
    # actual failure mode this project has hit repeatedly with AuraDB Free.
    try:
        _, retriever, _, _ = _get_graphrag_pipeline()
        retriever.driver.verify_connectivity()
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Neo4j connectivity check failed: {exc}"
        ) from exc

    return {"status": "ok"}


@app.on_event("startup")
def _warm_pipelines() -> None:
    # Pre-builds graph_rag's expensive one-time resources at process
    # startup instead of on whichever request happens to land first --
    # a real user's first query shouldn't pay that cost.
    _, retriever, _, _ = _get_graphrag_pipeline()

    # AuraDB Free auto-pauses the instance after inactivity; opening the
    # driver and verify_connectivity() (used in /health) can both succeed
    # against a paused instance without actually resuming it -- only a
    # real Cypher query does that, and the resume itself can take a few
    # seconds. Running one harmless, real round-trip here (matches nothing
    # -- "SY_" is a real prefix retrieve_by_symptom expects, the id itself
    # is not) means the wake-up latency lands during startup, not during
    # the first real user request. Failure here is logged, not fatal --
    # AuraDB connection instability is a known, pre-existing issue this
    # warmup can't fully solve, and the app already degrades gracefully
    # (graph_rag.py's own retrieval try/except) if Neo4j is still
    # unreachable on the first real query.
    try:
        retriever.retrieve("SY_warmup_ping")
    except Exception as exc:
        logger.warning("AuraDB warmup query failed (non-fatal): %s", exc)
