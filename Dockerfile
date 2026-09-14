# Dockerfile for main.py -- the FastAPI GraphRAG service (not app.py's
# Streamlit demo). Explicit COPY lines instead of `COPY . .` on purpose:
# this repo root also holds a venv (Lib/, Scripts/, Include/) and years of
# eval-run scratch output living directly alongside the source, and a
# blanket copy would either bake that into the image or require a
# dockerignore precise enough to be a liability. Copying exactly what
# main.py's import graph needs is the safer default.
#
# GraphRAG-only: naive RAG and the agentic router were archived (see
# archive_naive_agentic/README.md), so this image no longer needs
# libgomp1 (that was for faiss-cpu/torch, both dropped from
# requirements.txt) or the raw PDF corpus (GraphRAG reads everything from
# Neo4j; the PDFs were only ever read by naive_rag's FAISS indexing).

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py graph_rag.py graphretriever_v5.py \
     context_builder.py answer_generator_groq.py \
     query_understanding_v3.py tracing_setup.py ./
COPY static/ ./static/
COPY templates/ ./templates/

# No secrets.toml is copied in -- NEO4J_*, OPENROUTER_API_KEY,
# LANGCHAIN_* etc. must be supplied as real environment variables at run
# time (docker-compose env vars locally, EC2 instance environment / an
# env file loaded by systemd in production). main.py's own secrets-loading
# only activates when .streamlit/secrets.toml exists on disk, so its
# absence here is what makes it fall through to os.environ correctly.

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
