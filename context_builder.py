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

    # Edge types the retriever's _STAR_MATCHES/_STAR_RETURN actually
    # traverse for the causes/mitigations/leads_to/degrades/restores/
    # indicating_symptoms/detected_by fields -- every one of these
    # carries a claim_id (extracted and verified from a document). Any
    # edge NOT in this set (chiefly MENTIONED_IN, an Entity->Chunk
    # structural edge with no claim_id, and HAS_CHUNK) means two things
    # merely co-occur in a chunk/document, not that a relationship
    # between them was asserted anywhere.
    #
    # Today, only `reasoning_chain` (built by retrieve_path()'s
    # unrestricted `shortestPath((start)-[*1..N]-(end))`, which does not
    # filter by relationship type) can actually contain a structural
    # hop -- the causes/mitigations/etc fields are populated exclusively
    # from these real edge types by the retriever's star queries. The
    # `claim_id` check below is still applied to every field, not just
    # reasoning_chain, as a defensive tag rather than an assumption, so
    # a future retriever change that starts passing structural items
    # through those fields doesn't silently regress this fix.
    REAL_EDGE_TYPES = {
        "MANIFESTS_AS", "CAUSES", "INFLUENCES", "LEADS_TO", "MITIGATES",
        "AFFECTS", "DEGRADES", "RESTORES", "INDICATES", "DETECTS",
    }

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

        If the item has no claim_id -- meaning it's a structural
        co-occurrence, not an extracted/verified relationship -- that is
        called out explicitly rather than presented the same as a real
        claim. See REAL_EDGE_TYPES above for why this matters.
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
        if not item.get("claim_id"):
            parts.append("(co-occurrence only, not a stated relationship)")

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

    @classmethod
    def _tag_chain_step(cls, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        retrieve_path()'s shortestPath traversal matches ANY relationship
        type, not just the semantic ones -- so a path between two
        entities with no real edge connecting them can be stitched
        together via a shared Chunk node through MENTIONED_IN (an
        Entity->Chunk edge, not Entity->Entity). Confirmed bug: the
        generator narrated exactly this kind of stitched path as a
        causal claim (e.g. OS04's boost-pump-failure -> fuel-filter-
        clogging chain, where the graph's actual connection was two
        entities co-occurring in nearby chunks, not a CAUSES edge).
        Each step is tagged here with whether the edge INTO it is one of
        REAL_EDGE_TYPES and carries a claim_id -- both must hold, since
        an edge_type could in principle be spoofed/missing while a
        claim_id is present or vice versa, and the generator downstream
        should not have to re-derive this itself from raw edge_type
        strings.
        """
        edge_type = step.get("edge_type")
        claim_id = step.get("edge_claim_id")
        is_stated_relationship = bool(edge_type) and edge_type in cls.REAL_EDGE_TYPES and bool(claim_id)
        return {
            **step,
            "is_stated_relationship": is_stated_relationship,
        }

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
                # Fixed 2026-08-30: this row's own MANIFESTS_AS symptoms
                # were never read into graph_facts at all -- only
                # indicating_symptoms (the separate INDICATES relation,
                # added deliberately below) made it through. _chunk_ids_
                # from_rows already walked "symptoms" for citation
                # purposes, so the source text was reachable in the flat
                # EVIDENCE CHUNKS block, but never as a labeled fact
                # under the failure mode it belongs to. Caught via OS06:
                # FM_hot_start's entire identity in this graph is "it
                # manifests as high EGT" (D3_c25, its only real edge) --
                # with this missing, that row rendered as an almost-bare
                # entry (no causes, no mitigations, its one defining fact
                # invisible) sitting next to compressor surge's much
                # richer entry, and the generator gravitated toward the
                # richer one despite correct ranking. answer_generator_
                # groq.py's build_factual_skeleton() already reads and
                # renders a "symptoms" key -- it was only ever missing on
                # this side.
                "symptoms": [
                    self._fmt_with_provenance(s, "symptom")
                    for s in row.get("symptoms", [])
                    if s.get("symptom") is not None
                ],
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

            # v5 addition: symptoms that INDICATE this failure mode (a
            # separate relationship from MANIFESTS_AS -- the failure mode
            # doesn't manifest AS these, but their presence is evidence
            # the failure mode is occurring), and what mitigations/methods
            # DETECT it. Both were previously invisible at the retriever
            # level; passing them through here too, or they'd reach this
            # point correctly but still never surface to the generator.
            indicating_symptoms = row.get("indicating_symptoms", [])
            if indicating_symptoms:
                fact["indicating_symptoms"] = [
                    self._fmt_with_provenance(i, "symptom")
                    for i in indicating_symptoms
                    if i.get("symptom") is not None
                ]

            detected_by = row.get("detected_by", [])
            if detected_by:
                fact["detected_by"] = [
                    self._fmt_with_provenance(d, "detector")
                    for d in detected_by
                    if d.get("detector") is not None
                ]

            # Pass through the reasoning chain if the retriever provided
            # one, with each hop tagged so the generator can tell a real
            # asserted edge from a structural MENTIONED_IN/HAS_CHUNK
            # co-occurrence hop -- see _tag_chain_step.
            chain = row.get("reasoning_chain")
            if chain:
                fact["reasoning_chain"] = [self._tag_chain_step(step) for step in chain]

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
