# src/generation/answer_generator_groq.py
#
# Drop-in replacement for answer_generator_v3.py.
#
# ROUTING CHANGE (2026-08-29): moved off Groq's own endpoint onto
# OpenRouter, same provider score_graphrag_ragas.py's RAGAS judge already
# uses (build_ragas_judge()) -- this file's client setup mirrors that
# function's base_url/default_headers so both halves of the pipeline hit
# OpenRouter the same way. Reasons:
#   1. Groq's own 8000 TPM (tokens-per-minute) account cap -- independent
#      of any daily/spend cap -- produced a real 429 mid-eval-run (AF02,
#      2026-08-29 run) even though gpt-oss-20b was well within budget.
#      OpenRouter's per-provider rate limits are separate from Groq's.
#   2. OpenRouter can route gpt-oss-20b to a cheaper backing provider
#      (e.g. Darkbloom: $0.02/M input, $0.10/M output) than Groq charges
#      directly for the same model ($0.075/M input, $0.30/M output) --
#      roughly 3-4x cheaper per token, not just a rate-limit fix.
# The module name/filename kept as-is (answer_generator_groq.py) to avoid
# churning every import site for a routing change; the class itself no
# longer talks to Groq at all.
#
# Setup:
#   pip install openai
#   set OPENROUTER_API_KEY=sk-or-v1-your_key_here
#
# Usage in graph_rag.py:
#   from answer_generator_groq import AnswerGenerator

from __future__ import annotations

import os
from typing import Any, Dict, List

from openai import OpenAI


class AnswerGenerator:
    def __init__(
        self,
        model: str = "openai/gpt-oss-20b",
        api_key: str = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.model = model
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=base_url,
            # Same attribution headers as score_graphrag_ragas.py's
            # build_ragas_judge() -- OpenRouter uses these for app
            # identification/rankings, not auth.
            default_headers={
                "HTTP-Referer": "https://palakporwal.site",
                "X-Title": "AeroOps GraphRAG Generator",
            },
        )

    # ------------------------------------------------------------------
    # Formatting helpers (unchanged)
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

    @staticmethod
    def _fmt_chain_step(step: Dict[str, Any]) -> str:
        """
        Render one reasoning-chain hop. context_builder.py tags each
        step with is_stated_relationship (a real CAUSES/LEADS_TO/etc
        edge backed by a claim_id) vs. a structural MENTIONED_IN/
        HAS_CHUNK co-occurrence hop -- the arrow notation here makes
        that distinction visually unmistakable in the prompt itself
        (`--[...]-->` for a stated relationship vs. `~~[...]~~>` for
        co-occurrence-only), rather than relying on the model to notice
        an edge_type string it has no instructed reason to treat
        differently. See rule 12 in build_prompt.
        """
        node = f"{step.get('name', '?')} ({step.get('label', '?')})"
        edge_type = step.get("edge_type")
        if not edge_type:
            return node
        if step.get("is_stated_relationship"):
            claim_id = step.get("edge_claim_id")
            tag = f"--[{edge_type}" + (f", claim {claim_id}" if claim_id else "") + "]-->"
        else:
            tag = f"~~[{edge_type}: CO-OCCURRENCE ONLY, not a stated relationship]~~>"
        return f"{node} {tag}"

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
            indicating_symptoms = item.get("indicating_symptoms", [])
            detected_by = item.get("detected_by", [])

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
            if indicating_symptoms:
                parts += ["", "  Also indicated by (separate from symptoms this "
                              "failure mode directly manifests as):",
                           self._fmt_list(indicating_symptoms)]
            if detected_by:
                parts += ["", "  Detected by:", self._fmt_list(detected_by)]
            if chain:
                chain_str = " -> ".join(self._fmt_chain_step(step) for step in chain)
                parts += ["", f"  Reasoning chain: {chain_str}"]

            sections.append("\n".join(parts))

        facts_block = "\n\n".join(sections) if sections else "(no graph facts retrieved)"

        evidence_lines = [
            f"[{ch.get('chunk_id', '?')}] {ch.get('text', '')}"
            for ch in chunks
        ]
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "(no evidence chunks)"

        # Valid citation IDs must include BOTH the flat evidence_chunks
        # AND every chunk ID cited inside graph_facts itself. By the time
        # graph_facts reaches this point, context_builder.py has already
        # reformatted causes/mitigations/etc from dicts into citation-bound
        # strings like "Active clearance control [D3_c32]", not dicts with
        # a "chunks" key -- so IDs have to be parsed out of the bracketed
        # tag in the string itself, not read off a field that no longer
        # exists at this stage. Missing this caused a real, legitimately
        # grounded citation (a mitigation sourced to D3_c32) to be
        # excluded from the whitelist and silently dropped from an answer
        # that had every right to cite it.
        import re
        valid_ids = set(ch.get("chunk_id", "?") for ch in chunks)
        for item in graph_facts:
            for group_key in ("causes", "mitigations", "symptoms",
                              "leads_to", "degrades", "restores",
                              "indicating_symptoms", "detected_by"):
                for entry in item.get(group_key, []) or []:
                    if isinstance(entry, str):
                        # pull every bracketed group, split on commas --
                        # context_builder.py joins multi-chunk citations
                        # as "[D1_c03, D1_c04]"
                        for bracket in re.findall(r"\[([^\]]+)\]", entry):
                            for cid in bracket.split(","):
                                cid = cid.strip()
                                if cid:
                                    valid_ids.add(cid)
                    elif isinstance(entry, dict):
                        # defensive: handle the raw-dict shape too, in case
                        # this ever runs against retriever output directly
                        # rather than context_builder's formatted strings
                        for cid in entry.get("chunks", []) or []:
                            valid_ids.add(cid)
        valid_ids_block = ", ".join(sorted(valid_ids)) if valid_ids else "(none)"

        return f"""QUESTION:
{context.get("question")}

GRAPH FACTS:
{facts_block}

EVIDENCE CHUNKS:
{evidence_block}

VALID CITATION IDS (the only IDs you are allowed to cite): {valid_ids_block}"""

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
4. If the graph facts include a "Reasoning chain", only hops marked `--[EDGE_TYPE, claim ...]-->` are a stated relationship you may narrate as a causal step. A hop marked `~~[EDGE_TYPE: CO-OCCURRENCE ONLY, not a stated relationship]~~>` means the two entities on either side of it merely appear in the same source passage -- it is NOT evidence of any causal, mitigating, or directional relationship. Do not narrate a co-occurrence hop as a step in a causal sequence, and do not skip over it silently to imply the entities on either side are directly connected -- if the only path between two facts in the chain is a co-occurrence hop, say the graph does not establish a relationship between them rather than inferring one.
5. If the graph facts include "Leads to", "Degrades", or "Restored by", incorporate them when relevant to the question.
6. If information is missing, say so briefly. Do not guess.
7. Keep the answer concise and direct. No boilerplate headings unless the question asks for a list.
8. Do not say "as an AI model".
9. GROUNDING CHECK -- before writing any specific mechanism, procedure, technical term, or classification (e.g. a named process, a maintenance action, a category label), confirm that exact content appears in the GRAPH FACTS or EVIDENCE CHUNKS above. If it does not appear there, even if you know it to be true from general aviation knowledge, do not include it. Describe only what the provided facts and evidence actually state, nothing more specific than that.
10. NEVER cite a chunk ID that is not listed in VALID CITATION IDS above. If you are not certain which provided ID supports a claim, do not attach a citation to it rather than guessing one.
11. Do not connect two separate facts into a single causal claim (X causes Y, X leads to Y, X is the reason for Y) unless the GRAPH FACTS or a single EVIDENCE CHUNK explicitly states that connection. Two facts appearing near each other in the retrieved evidence does not mean they are causally linked -- only state a causal connection if it is the evidence's own claim, not an inference you are drawing between two independently true facts.
12. Some items in GRAPH FACTS are marked "(co-occurrence only, not a stated relationship)", and some Reasoning chain hops use the `~~[...]~~>` marker instead of `--[...]-->` (see rule 4) -- both mean the same thing: the entities involved merely appear in the same source chunk or document, not that any relationship between them was asserted. You may mention such facts near each other in your answer (e.g. "the graph also notes X in the same context") but you must NEVER connect them with causal or directional language -- "causes," "leads to," "results in," "triggers," "which in turn," "therefore," "as a result," etc. -- unless that specific connection is separately backed by a stated relationship (a real edge type with its own claim_id, shown without the co-occurrence marker) elsewhere in GRAPH FACTS.
13. Preserve the evidence's own direction of statement, and write every claim as a COMPLETE sentence naming the failure mode/entity as the grammatical subject -- never a bare noun-phrase fragment or bulleted label with no verb (e.g. not "- High EGT", but "A compressor surge can produce high EGT readings"). This matters most for "what are the signs/indications of X" questions: if the evidence says "X can produce/be accompanied by Y" (X -> Y), write it that way -- do not invert it into "Y indicates/means X is occurring" (Y -> X), and do not leave it as an unstated fragment that reads as an inversion by implication. A list is fine; every item in it must still be its own complete X -> Y sentence in the evidence's own direction.
14. Do not add evaluative, prescriptive, or hedging words -- "recommended," "primary," "main," "best," "most effective," "most likely," "probably," "likely due to" -- unless that exact word or an equivalent judgment appears in the graph facts or evidence chunks. State only what the evidence itself asserts, not your own framing of its significance or your own confidence about an unstated cause.
15. If the question's scenario describes a specific triggering event (e.g. "a hard landing," "bird ingestion") and no graph fact or evidence chunk connects that specific event to the mechanism you are about to describe, do not mention the named event's causal role at all -- not even hedged ("likely caused by," "consistent with"), and do not add commentary about what the graph does or doesn't establish either, since that is itself a claim the evidence doesn't state. Simply describe the graph-backed mechanism on its own, omitting any link to the scenario's named trigger.

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
