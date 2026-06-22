# src/retrieval/context_builder.py  (v2)
#
# What changed:
#   Causes and mitigations are no longer bare name strings.
#   Each item is formatted as "Name [chunk_ids] (confidence: X)"
#   so the LLM sees which source chunk supports which specific claim.
#
#   Output shape is identical: graph_facts[].causes and .mitigations
#   are still List[str], so answer_generator_v2.py works unchanged.
#   graphretriever_v3.py is also unaffected (upstream).

from typing import Any, Dict, List


class ContextBuilder:

    # ------------------------------------------------------------------
    # Internal: format a single graph-retrieved item with its provenance
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_with_provenance(item: Dict[str, Any], name_key: str) -> str:
        """
        Turn a retriever dict like
            {"cause": "Blade tip wear", "chunks": ["D1_c03"],
             "confidence": 0.85, "claim_id": "CL003"}
        into a citation-bound string:
            "Blade tip wear [D1_c03]"
        so the LLM knows which chunk supports this specific fact.
        """
        name = item.get(name_key, "Unknown")

        # Attach chunk IDs inline.
        chunks = item.get("chunks") or item.get("source_chunk_ids") or []
        if isinstance(chunks, list) and chunks:
            chunk_tag = "[" + ", ".join(str(c) for c in chunks) + "]"
        else:
            chunk_tag = ""

        parts = [name]
        if chunk_tag:
            parts.append(chunk_tag)

        return " ".join(parts)

    @staticmethod
    def _fmt_leads_to(item: Dict[str, Any]) -> str:
        """Format a LEADS_TO downstream consequence with provenance."""
        name = item.get("failure_mode", "Unknown")
        severity = item.get("severity", "")
        chunks = item.get("chunks") or []
        chunk_tag = "[" + ", ".join(str(c) for c in chunks) + "]" if chunks else ""
        parts = [name]
        if severity:
            parts.append(f"(severity: {severity})")
        if chunk_tag:
            parts.append(chunk_tag)
        return " ".join(parts)

    @staticmethod
    def _fmt_degrades(item: Dict[str, Any]) -> str:
        """Format a DEGRADES edge to a parameter with provenance."""
        name = item.get("parameter", "Unknown")
        chunks = item.get("chunks") or []
        chunk_tag = "[" + ", ".join(str(c) for c in chunks) + "]" if chunks else ""
        return f"{name} {chunk_tag}".strip()

    # ------------------------------------------------------------------
    # Public: build the context dict for the answer generator
    # ------------------------------------------------------------------

    def build(self, question: str, graph_result: Dict[str, Any]) -> Dict[str, Any]:

        graph_facts = []
        citations = []

        for row in graph_result["results"]:

            fact: Dict[str, Any] = {
                "failure_mode": row.get("failure_mode"),
                "severity": row.get("severity"),
                "causes": [
                    self._fmt_with_provenance(c, "cause")
                    for c in row.get("causes", [])
                    if c.get("cause") is not None
                ],
                "mitigations": [
                    self._fmt_with_provenance(m, "mitigation")
                    for m in row.get("mitigations", [])
                    if m.get("mitigation") is not None
                ],
            }

            # v3 retriever may supply these; include when present.
            # If absent (v2 retriever), these keys simply won't appear,
            # and the answer generator's _fmt_list handles empty lists.
            leads_to = row.get("leads_to", [])
            if leads_to:
                fact["leads_to"] = [
                    self._fmt_leads_to(lt)
                    for lt in leads_to
                    if lt.get("failure_mode") is not None
                ]

            degrades = row.get("degrades", [])
            if degrades:
                fact["degrades"] = [
                    self._fmt_degrades(d)
                    for d in degrades
                    if d.get("parameter") is not None
                ]

            restores = row.get("restores", [])
            if restores:
                fact["restores"] = [
                    self._fmt_with_provenance(r, "parameter")
                    for r in restores
                    if r.get("parameter") is not None
                ]

            # Pass through the reasoning chain if the retriever provided one.
            chain = row.get("reasoning_chain")
            if chain:
                fact["reasoning_chain"] = chain

            graph_facts.append(fact)

        # ------ Evidence chunks ------
        chunk_texts = []

        for chunk in graph_result.get("chunks", []):
            chunk_texts.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                }
            )
            citations.append(chunk["chunk_id"])

        return {
            "question": question,
            "graph_facts": graph_facts,
            "evidence_chunks": chunk_texts,
            "citations": sorted(set(citations)),
        }
