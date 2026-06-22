# src/generation/answer_generator_groq.py
#
# Drop-in replacement for answer_generator_v3.py.
# Uses Groq API (free tier, ~300 tok/s) instead of local Ollama.
# Everything else — prompt, skeleton, interface — is identical.
#
# Setup:
#   pip install openai
#   set GROQ_API_KEY=gsk_your_key_here
#
# Usage in graph_rag_v1.py:
#   from answer_generator_groq import AnswerGenerator

from __future__ import annotations

import os
from typing import Any, Dict, List

from openai import OpenAI


class AnswerGenerator:
    def __init__(
        self,
        model: str = "llama-3.1-8b-instant",
        api_key: str = None,
        base_url: str = "https://api.groq.com/openai/v1",
    ):
        self.model = model
        self.client = OpenAI(
            api_key=api_key or os.getenv("GROQ_API_KEY"),
            base_url=base_url,
        )

    # ------------------------------------------------------------------
    # Formatting helpers (unchanged from v3)
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_list(items: List[Any]) -> str:
        if not items:
            return "  (none in graph)"

        lines: List[str] = []
        for item in items:
            if isinstance(item, str):
                lines.append(f"  - {item}")
            elif isinstance(item, dict):
                value = (
                    item.get("name")
                    or item.get("cause")
                    or item.get("mitigation")
                    or item.get("symptom")
                    or item.get("affected_name")
                    or item.get("failure_mode")
                    or item.get("parameter")
                    or str(item)
                )
                lines.append(f"  - {value}")
            else:
                lines.append(f"  - {item}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Build the factual skeleton the LLM must ground on
    # ------------------------------------------------------------------

    def build_factual_skeleton(self, context: Dict[str, Any]) -> str:
        graph_facts = context.get("graph_facts", [])
        chunks = context.get("evidence_chunks", [])

        sections: List[str] = []

        for idx, item in enumerate(graph_facts, start=1):
            failure_mode = item.get("failure_mode", "Unknown")
            severity = item.get("severity", "unknown")
            causes = item.get("causes", [])
            mitigations = item.get("mitigations", [])
            leads_to = item.get("leads_to", [])
            degrades = item.get("degrades", [])
            restores = item.get("restores", [])
            symptoms = item.get("symptoms", [])
            affected = item.get("affected_components", [])
            chain = item.get("reasoning_chain", [])

            parts: List[str] = [
                f"Failure Mode {idx}: {failure_mode}",
                f"  Severity: {severity}",
                "",
                f"  Causes:",
                self._fmt_list(causes),
                "",
                f"  Mitigations:",
                self._fmt_list(mitigations),
            ]

            if leads_to:
                parts += ["", "  Leads to (downstream consequences):", self._fmt_list(leads_to)]
            if degrades:
                parts += ["", "  Degrades (parameters):", self._fmt_list(degrades)]
            if restores:
                parts += ["", "  Restored by:", self._fmt_list(restores)]
            if symptoms:
                parts += ["", "  Symptoms:", self._fmt_list(symptoms)]
            if affected:
                parts += ["", "  Affected components:", self._fmt_list(affected)]
            if chain:
                chain_str = " → ".join(
                    f"{step.get('name', '?')} ({step.get('label', '?')})"
                    + (f" --[{step.get('edge_type', '')}]-->" if step.get("edge_type") else "")
                    for step in chain
                )
                parts += ["", f"  Reasoning chain: {chain_str}"]

            sections.append("\n".join(parts))

        facts_block = "\n\n".join(sections) if sections else "(no graph facts retrieved)"

        evidence_lines = [
            f"[{ch.get('chunk_id', '?')}] {ch.get('text', '')}"
            for ch in chunks
        ]
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "(no evidence chunks)"

        return f"""QUESTION:
{context.get("question")}

GRAPH FACTS:
{facts_block}

EVIDENCE CHUNKS:
{evidence_block}"""

    # ------------------------------------------------------------------
    # Build the prompt
    # ------------------------------------------------------------------

    def build_prompt(self, context: Dict[str, Any]) -> str:
        skeleton = self.build_factual_skeleton(context)

        return f"""You are AeroOps, a turbofan maintenance assistant.
Answer the QUESTION below using ONLY the GRAPH FACTS and EVIDENCE CHUNKS provided.

Rules:
1. Answer the question directly. Do not restate the question.
2. Use only facts from the GRAPH FACTS block. Do not invent causes, mitigations, parameters, or failure modes.
3. Cite evidence inline using chunk IDs like [D1_c03] when making a claim.
4. If the graph facts include a "Reasoning chain", use it to explain the step-by-step sequence.
5. If the graph facts include "Leads to", "Degrades", or "Restored by", incorporate them when relevant to the question.
6. If information is missing, say so briefly. Do not guess.
7. Keep the answer concise and direct. No boilerplate headings unless the question asks for a list.
8. Do not say "as an AI model".

{skeleton}"""

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def generate(self, context: Dict[str, Any]) -> str:
        prompt = self.build_prompt(context)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
        )

        return response.choices[0].message.content
