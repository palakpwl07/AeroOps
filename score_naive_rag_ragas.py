# score_naive_rag_ragas.py
#
# Reads naive_rag_ragas_inputs.json (output of run_naive_rag_eval.py)
# and runs RAGAS Faithfulness + Context Recall scoring on it.
#
# Judge model: openai/gpt-4o-mini via OpenRouter (paid, ~$0.30 total for
# both naive RAG and GraphRAG runs combined). Switched off free-tier models
# after hitting, in order: a dead deprecated model (404), a daily token cap,
# a per-minute token cap, and an overloaded free-queue timeout wall -- four
# different failure modes across three different free providers. gpt-4o-mini
# is not a reasoning model, so none of those token-burn-driven failures
# apply, and it's cheap enough that "free" was never actually saving money,
# just costing hours. Requires OPENROUTER_API_KEY.
#
# No pipeline runs here -- just scoring pre-generated outputs.
#
# Usage:
#   python score_naive_rag_ragas.py
#
# Output:
#   ragas_outputs_naive_rag/aeroops_naive_rag_ragas_results.xlsx

from __future__ import annotations

import json
import math
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Same fix as score_graphrag_ragas.py -- prevents a print() on an
# ordinary non-ASCII character from crashing under Windows cp1252.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

INPUT_JSON   = "naive_rag_ragas_inputs.json"
OUTPUT_DIR   = Path("ragas_outputs_naive_rag")
OUTPUT_XLSX  = OUTPUT_DIR / "aeroops_naive_rag_ragas_results.xlsx"
OUTPUT_JSON  = OUTPUT_DIR / "aeroops_naive_rag_ragas_results.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Load secrets so OPENROUTER_API_KEY (and anything else in the file) is
# available via os.environ
# ---------------------------------------------------------------------------
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
if tomllib and secrets_path.exists():
    with open(secrets_path, "rb") as f:
        for k, v in tomllib.load(f).items():
            os.environ.setdefault(k, str(v))
    print(f"Secrets loaded from {secrets_path}")


def load_inputs(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    print(f"Loaded {len(rows)} items from {path}")
    return rows


def strip_citations(answer: str) -> str:
    """
    Same fix applied to score_graphrag_ragas.py: naive RAG's answers embed
    "[CITE: filename.pdf p.N]" tags inline. A bracketed citation tag isn't
    itself a factual claim, but RAGAS's statement decomposer can treat it
    as one -- no context chunk literally contains "CITE: filename.pdf
    p.17" as prose, so that fragment fails grounding and drags the whole
    faithfulness score down for reasons unrelated to answer quality. This
    script never had this fix even though score_graphrag_ragas.py's
    identical fix was already in place -- confirmed the on-disk naive RAG
    RAGAS results were scored with these tags still embedded.
    """
    return re.sub(r"\s*\[CITE:[^\]]*\]", "", answer).strip()


def prepare_contexts(contexts: List[str], max_contexts: int = 15,
                     max_chars: int = 1200) -> List[str]:
    cleaned = []
    for c in contexts:
        if not c:
            continue
        text = " ".join(str(c).split())
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + " ..."
        cleaned.append(text)
        if len(cleaned) >= max_contexts:
            break
    return cleaned


def build_ragas_judge():
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        raise RuntimeError("OPENROUTER_API_KEY not set.")

    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    model = os.getenv("RAGAS_JUDGE_MODEL", "openai/gpt-4o-mini")
    judge = ChatOpenAI(
        model=model,
        api_key=openrouter_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
        timeout=180,
        max_retries=3,
        max_tokens=4000,
        # gpt-4o-mini is NOT a reasoning model -- no internal chain-of-thought
        # burning unpredictable output tokens, no reasoning_effort param to
        # configure or get wrong. Claim verification doesn't need anywhere
        # near its 16,384 ceiling; 4000 is generous headroom for this task.
        # Paid, multi-provider-served on OpenRouter -- not a deprioritized
        # free-tier queue, so no more multi-minute stalls or 504 timeouts.
        # Also the exact model RAGAS's own docs use as their canonical
        # llm_factory example -- well-trodden, not experimental.
        default_headers={
            "HTTP-Referer": "https://palakporwal.site",
            "X-Title": "AeroOps RAGAS Eval",
        },
    )
    print(f"RAGAS judge: OpenRouter / {model}")
    return LangchainLLMWrapper(judge)


def run_ragas(rows: List[Dict[str, Any]]):
    from ragas import evaluate
    from datasets import Dataset

    try:
        from ragas.metrics import faithfulness, context_recall
        metrics = [faithfulness, context_recall]
        dataset = Dataset.from_list([
            {
                "question":     r["Question"],
                "answer":       strip_citations(r["Model Answer"]),
                "contexts":     prepare_contexts(r.get("Retrieved Contexts") or []),
                "ground_truth": r["Ground Truth"],
            }
            for r in rows
        ])
        schema = "legacy"
    except Exception:
        from ragas.metrics import Faithfulness, LLMContextRecall
        metrics = [Faithfulness(), LLMContextRecall()]
        dataset = Dataset.from_list([
            {
                "user_input":          r["Question"],
                "response":            strip_citations(r["Model Answer"]),
                "retrieved_contexts":  prepare_contexts(r.get("Retrieved Contexts") or []),
                "reference":           r["Ground Truth"],
            }
            for r in rows
        ])
        schema = "new"

    print(f"Running RAGAS ({schema} schema) on {len(rows)} items...")

    try:
        from ragas.run_config import RunConfig
        run_config = RunConfig(max_workers=1, timeout=180, max_retries=3)
    except Exception:
        run_config = None

    judge = build_ragas_judge()

    kwargs = {"dataset": dataset, "metrics": metrics,
              "llm": judge, "raise_exceptions": False}
    if run_config:
        kwargs["run_config"] = run_config

    return evaluate(**kwargs)


def merge_scores(ragas_result, rows):
    try:
        df = ragas_result.to_pandas()
        scores = df.to_dict(orient="records")
    except Exception:
        scores = [{} for _ in rows]

    merged = []
    for i, row in enumerate(rows):
        s = scores[i] if i < len(scores) else {}
        # Same fix as score_graphrag_ragas.py's merge_scores: `a or b`
        # discards a genuine 0.0 score (falsy) and falls through to the
        # wrong-cased key, which never exists -- silently turning a real
        # 0.0 judgment into None. Confirmed the on-disk naive RAG results
        # were merged with this bug still in place.
        f_val = s.get("faithfulness")
        if f_val is None:
            f_val = s.get("Faithfulness")
        r_val = s.get("context_recall")
        if r_val is None:
            r_val = s.get("LLMContextRecall")
        merged.append({
            **row,
            "Faithfulness":    f_val,
            "Context Recall":  r_val,
        })
    return merged


def save_excel(rows, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "Naive RAG RAGAS"

    headers = ["ID", "Category", "Question", "Expected Answer",
               "Model Answer", "Faithfulness", "Context Recall", "Time (s)"]

    hfont = Font(bold=True, color="FFFFFF")
    hfill = PatternFill("solid", fgColor="2F5496")
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = hfont
        c.fill = hfill
        c.alignment = Alignment(horizontal="center", wrap_text=True)

    for i, row in enumerate(rows):
        ws.append([
            row.get("ID"), row.get("Category"), row.get("Question"),
            row.get("Ground Truth"), row.get("Model Answer"),
            row.get("Faithfulness"), row.get("Context Recall"),
            row.get("Time (s)"),
        ])
        for cell in ws[i + 2]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    for col, width in zip("ABCDEFGH", [8, 18, 50, 50, 50, 14, 14, 10]):
        ws.column_dimensions[col].width = width

    ws.freeze_panes = "A2"
    wb.save(path)
    print(f"Saved Excel -> {path}")


def print_summary(rows):
    # Same fix as score_graphrag_ragas.py: `is not None` doesn't catch
    # RAGAS's float('nan') return for a metric call that failed at the
    # API level (raise_exceptions=False returns NaN, not an exception or
    # None). One transient API failure would silently zero out the mean
    # for all 45 items via statistics.mean() propagating NaN.
    def mean(key):
        vals = [float(r[key]) for r in rows
                if r.get(key) is not None and not math.isnan(float(r[key]))]
        skipped = sum(1 for r in rows if r.get(key) is None
                      or (isinstance(r.get(key), float) and math.isnan(r[key])))
        if skipped:
            print(f"  ({skipped} item(s) excluded from {key} mean -- "
                  f"missing/NaN score, not a real 0)")
        return round(statistics.mean(vals), 3) if vals else "N/A"

    print("\n======= NAIVE RAG RAGAS SUMMARY =======")
    print(f"Items evaluated: {len(rows)}")
    print(f"Faithfulness mean:   {mean('Faithfulness')}")
    print(f"Context recall mean: {mean('Context Recall')}")
    print("========================================\n")


def main():
    rows = load_inputs(INPUT_JSON)
    ragas_result = run_ragas(rows)
    rows_scored = merge_scores(ragas_result, rows)

    save_excel(rows_scored, OUTPUT_XLSX)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows_scored, f, indent=2, ensure_ascii=False,
                  default=str)
    print(f"Saved JSON  -> {OUTPUT_JSON}")

    print_summary(rows_scored)


if __name__ == "__main__":
    main()
