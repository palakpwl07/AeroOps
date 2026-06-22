# src/retrieval/graph_retriever.py  (v3)
#
# What changed from v2:
#   1. Star queries now include LEADS_TO downstream consequences and
#      DEGRADES / RESTORES edges to Parameters.
#   2. New retrieve_path() walks variable-length chains between two
#      entities and returns the same row format the pipeline expects.
#   3. retrieve() dispatches on C_, PA_, P_, M_, ME_, OF_ prefixes
#      (not just SY_ and FM_), so the query router can anchor on any
#      node type.
#   4. retrieve_by_query_plan() detects multi-entity queries and
#      automatically runs a path traversal when two anchors exist.
#
# Output contract is identical to v2: every public method returns
#   {"retrieval_type": str,
#    "results":  [row, ...],      # same row schema
#    "chunk_ids": [str, ...],
#    "chunks":   [chunk, ...]}
# so context_builder.py and answer_generator_v2.py work unchanged.

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase


class GraphRetriever:
    PLAN_PREFIX = "PLAN::"

    # Caps applied ONLY to the recall-heavy query-plan path, to stop it
    # over-fetching failure modes and flooding the LLM context with
    # loosely-related chunks. Path traversal and single-entity stars are
    # unaffected (they are already precise).
    MAX_RECALL_ROWS = 4       # keep top-N ranked failure modes
    MAX_RECALL_CHUNKS = 12    # cap chunks sent to the LLM on this path

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database or os.getenv("NEO4J_DATABASE", "aeroops")

        if not self.password:
            raise ValueError("NEO4J_PASSWORD is missing.")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
        )

    def close(self) -> None:
        self.driver.close()

    # ------------------------------------------------------------------
    # Internal helpers (unchanged from v2)
    # ------------------------------------------------------------------

    def _run(self, cypher: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(cypher, params)
            return [dict(record) for record in result]

    @staticmethod
    def _flatten_chunk_ids(values) -> list[str]:
        """
        Collect chunk ids while preserving the order they were
        encountered (i.e. rank order from _rank_rows, then field order
        within each row). This matters because downstream callers may
        slice this list with MAX_RECALL_CHUNKS — alphabetical sorting
        here would silently favor whichever document name sorts first
        (e.g. D1_*) over the actually-most-relevant chunk, regardless
        of ranking. Order-preserving + de-duped is correct; the final
        fetch_chunks() re-sorts by doc_id/page for display anyway.
        """
        chunk_ids: list[str] = []
        seen: set[str] = set()

        def walk(x):
            if x is None:
                return
            if isinstance(x, str):
                if x.startswith("D") and "_c" in x and x not in seen:
                    seen.add(x)
                    chunk_ids.append(x)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for item in x:
                    walk(item)

        walk(values)
        return chunk_ids

    @staticmethod
    def _clean_items(items: list[dict], required_key: str) -> list[dict]:
        return [item for item in items if item and item.get(required_key) is not None]

    @staticmethod
    def _dedupe_rows_by_failure(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}

        def merge_list(existing: list, new: list, key: str) -> list:
            seen = {item.get(key) for item in existing if isinstance(item, dict)}
            for item in new or []:
                if not isinstance(item, dict):
                    continue
                marker = item.get(key)
                if marker in seen:
                    continue
                existing.append(item)
                seen.add(marker)
            return existing

        for row in rows:
            failure_id = row.get("failure_id") or row.get("failure_mode")
            if failure_id not in merged:
                merged[failure_id] = dict(row)
                continue

            target = merged[failure_id]
            target["matched_terms"] = sorted(
                set(target.get("matched_terms", []) + row.get("matched_terms", []))
            )
            target["matched_entity_ids"] = sorted(
                set(
                    target.get("matched_entity_ids", [])
                    + row.get("matched_entity_ids", [])
                )
            )
            for field, key in [
                ("symptoms", "symptom_id"),
                ("causes", "cause_id"),
                ("mitigations", "mitigation_id"),
                ("affected_components", "affected_id"),
                ("leads_to", "failure_id"),
                ("degrades", "parameter_id"),
                ("restores", "parameter_id"),
            ]:
                target[field] = merge_list(
                    target.get(field, []), row.get(field, []), key
                )

        return list(merged.values())

    def _postprocess_rows(self, rows: List[Dict[str, Any]]) -> None:
        for row in rows:
            row["mitigations"] = self._clean_items(
                row.get("mitigations", []), "mitigation"
            )
            row["causes"] = self._clean_items(row.get("causes", []), "cause")
            row["symptoms"] = self._clean_items(row.get("symptoms", []), "symptom")
            row["symptom_evidence"] = self._clean_items(
                row.get("symptom_evidence", []), "chunks"
            )
            row["affected_components"] = self._clean_items(
                row.get("affected_components", []), "affected_name"
            )
            row["leads_to"] = self._clean_items(
                row.get("leads_to", []), "failure_mode"
            )
            row["degrades"] = self._clean_items(
                row.get("degrades", []), "parameter"
            )
            row["restores"] = self._clean_items(
                row.get("restores", []), "parameter"
            )

    def _chunk_ids_from_rows(self, rows: List[Dict[str, Any]]) -> List[str]:
        return self._flatten_chunk_ids(
            [row.get("symptoms") for row in rows]
            + [row.get("causes") for row in rows]
            + [row.get("mitigations") for row in rows]
            + [row.get("affected_components") for row in rows]
            + [row.get("symptom_evidence") for row in rows]
            + [row.get("leads_to") for row in rows]
            + [row.get("degrades") for row in rows]
            + [row.get("restores") for row in rows]
            + [row.get("reasoning_chain") for row in rows]
        )

    def _rank_rows(
        self,
        rows: List[Dict[str, Any]],
        entity_ids: List[str],
        terms: List[str],
    ) -> List[Dict[str, Any]]:
        entity_id_set = set(entity_ids)
        term_set = {term.lower() for term in terms}

        def score(row: Dict[str, Any]) -> int:
            matched_ids = set(row.get("matched_entity_ids", []))
            matched_terms = " ".join(row.get("matched_terms", [])).lower()
            s = 0
            s += 10 * len(matched_ids & entity_id_set)
            s += 3 * sum(1 for term in term_set if term in matched_terms)
            s += 2 * len(row.get("symptoms", []))
            s += len(row.get("causes", []))
            s += len(row.get("mitigations", []))
            s += 2 * len(row.get("leads_to", []))
            if str(row.get("severity", "")).lower() in {
                "critical",
                "high",
                "severe",
            }:
                s += 2
            return s

        for row in rows:
            row["retrieval_score"] = score(row)

        return sorted(rows, key=lambda r: r.get("retrieval_score", 0), reverse=True)

    # ------------------------------------------------------------------
    # Chunk fetcher (unchanged)
    # ------------------------------------------------------------------

    def fetch_chunks(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        if not chunk_ids:
            return []

        cypher = """
        MATCH (c:Chunk)
        WHERE c.chunk_id IN $chunk_ids
        OPTIONAL MATCH (d:Document)-[:HAS_CHUNK]->(c)
        RETURN
            c.chunk_id   AS chunk_id,
            c.text       AS text,
            c.section    AS section,
            c.page       AS page,
            c.doc_id     AS doc_id,
            d.title      AS document_title,
            d.publisher  AS publisher,
            d.year       AS year,
            d.view_url   AS view_url
        ORDER BY c.doc_id, c.page
        """
        return self._run(cypher, {"chunk_ids": chunk_ids})

    # ------------------------------------------------------------------
    # v2 STAR QUERIES — now with LEADS_TO + DEGRADES + RESTORES
    # ------------------------------------------------------------------

    # Shared Cypher fragment: the enriched star around a FailureMode node
    # called `f`, collecting everything the pipeline needs.
    _STAR_RETURN = """
        collect(DISTINCT CASE WHEN sym IS NOT NULL THEN {
            symptom_id:  sym.id,
            symptom:     sym.name,
            confidence:  sr.confidence,
            claim_id:    sr.claim_id,
            chunks:      sr.source_chunk_ids
        } END) AS symptoms,

        collect(DISTINCT CASE WHEN c IS NOT NULL THEN {
            cause_id:    c.id,
            cause:       c.name,
            confidence:  cr.confidence,
            claim_id:    cr.claim_id,
            chunks:      cr.source_chunk_ids
        } END) AS causes,

        collect(DISTINCT CASE WHEN m IS NOT NULL THEN {
            mitigation_id:   m.id,
            mitigation:      m.name,
            mitigation_type: m.type,
            confidence:      mr.confidence,
            claim_id:        mr.claim_id,
            chunks:          mr.source_chunk_ids
        } END) AS mitigations,

        collect(DISTINCT CASE WHEN p IS NOT NULL THEN {
            affected_id:   p.id,
            affected_name: p.name,
            confidence:    ar.confidence,
            claim_id:      ar.claim_id,
            chunks:        ar.source_chunk_ids
        } END) AS affected_components,

        collect(DISTINCT CASE WHEN lt_fm IS NOT NULL THEN {
            failure_id:   lt_fm.id,
            failure_mode: lt_fm.name,
            severity:     lt_fm.severity,
            confidence:   lt.confidence,
            claim_id:     lt.claim_id,
            chunks:       lt.source_chunk_ids
        } END) AS leads_to,

        collect(DISTINCT CASE WHEN deg_p IS NOT NULL THEN {
            parameter_id: deg_p.id,
            parameter:    deg_p.name,
            confidence:   deg.confidence,
            claim_id:     deg.claim_id,
            chunks:       deg.source_chunk_ids
        } END) AS degrades,

        collect(DISTINCT CASE WHEN res_m IS NOT NULL THEN {
            parameter_id: res_p.id,
            parameter:    res_p.name,
            mitigation:   res_m.name,
            confidence:   res.confidence,
            claim_id:     res.claim_id,
            chunks:       res.source_chunk_ids
        } END) AS restores
    """

    # Shared Cypher fragment: the OPTIONAL MATCHes that feed _STAR_RETURN.
    # Expects the FailureMode to be bound as `f`.
    _STAR_MATCHES = """
        OPTIONAL MATCH (f)-[sr:MANIFESTS_AS]->(sym:Symptom)
        OPTIONAL MATCH (c)-[cr]->(f)
            WHERE type(cr) IN ['CAUSES', 'INFLUENCES', 'LEADS_TO']
              AND ('Cause' IN labels(c) OR 'OperatingFactor' IN labels(c)
                   OR 'FailureMode' IN labels(c))
        OPTIONAL MATCH (m:Mitigation)-[mr:MITIGATES]->(f)
        OPTIONAL MATCH (f)-[ar:AFFECTS]->(p)
        OPTIONAL MATCH (f)-[lt:LEADS_TO]->(lt_fm:FailureMode)
        OPTIONAL MATCH (f)-[deg:DEGRADES]->(deg_p:Parameter)
        OPTIONAL MATCH (res_m:Mitigation)-[res:RESTORES]->(res_p:Parameter)
            WHERE (f)-[:DEGRADES]->(res_p)
    """

    def retrieve_by_symptom(self, symptom_id: str) -> Dict[str, Any]:
        cypher = f"""
        MATCH (f:FailureMode)-[sr_anchor:MANIFESTS_AS]->(s:Symptom {{id: $symptom_id}})
        WITH f, s, sr_anchor
        {self._STAR_MATCHES}
        RETURN
            s.id   AS symptom_id,
            s.name AS symptom,
            f.id   AS failure_id,
            f.name AS failure_mode,
            f.severity AS severity,
            f.category AS category,
            [s.id]   AS matched_entity_ids,
            [s.name] AS matched_terms,
            {self._STAR_RETURN},
            collect(DISTINCT {{
                relationship: 'MANIFESTS_AS',
                confidence:   sr_anchor.confidence,
                claim_id:     sr_anchor.claim_id,
                chunks:       sr_anchor.source_chunk_ids
            }}) AS symptom_evidence
        """

        rows = self._run(cypher, {"symptom_id": symptom_id})
        self._postprocess_rows(rows)
        chunk_ids = self._chunk_ids_from_rows(rows)

        return {
            "retrieval_type": "symptom_to_failure_modes",
            "symptom_id": symptom_id,
            "results": rows,
            "chunk_ids": chunk_ids,
            "chunks": self.fetch_chunks(chunk_ids),
        }

    def retrieve_by_failure(self, failure_id: str) -> Dict[str, Any]:
        cypher = f"""
        MATCH (f:FailureMode {{id: $failure_id}})
        {self._STAR_MATCHES}
        RETURN
            f.id   AS failure_id,
            f.name AS failure_mode,
            f.severity AS severity,
            f.category AS category,
            [f.id]   AS matched_entity_ids,
            [f.name] AS matched_terms,
            {self._STAR_RETURN}
        """

        rows = self._run(cypher, {"failure_id": failure_id})
        self._postprocess_rows(rows)
        chunk_ids = self._chunk_ids_from_rows(rows)

        return {
            "retrieval_type": "failure_mode_diagnostic_profile",
            "failure_id": failure_id,
            "results": rows,
            "chunk_ids": chunk_ids,
            "chunks": self.fetch_chunks(chunk_ids),
        }

    # ------------------------------------------------------------------
    # NEW: Retrieve by Cause / Parameter / Part / Module / OperatingFactor
    #
    # Strategy: find all FailureModes connected to the given entity
    # (within 1–2 hops) and return enriched stars for each.
    # ------------------------------------------------------------------

    def retrieve_by_connected_entity(self, entity_id: str) -> Dict[str, Any]:
        """
        Generic retrieval for any non-FM, non-SY node (Cause, Parameter,
        Part, Module, OperatingFactor, Method, Mitigation).

        Finds FailureModes within 2 hops and returns their enriched stars,
        so the output is structurally identical to retrieve_by_failure.
        """
        cypher = f"""
        MATCH (anchor {{id: $entity_id}})
        MATCH (anchor)-[*1..2]-(f:FailureMode)
        WITH DISTINCT f, anchor
        {self._STAR_MATCHES}
        RETURN
            f.id   AS failure_id,
            f.name AS failure_mode,
            f.severity AS severity,
            f.category AS category,
            [anchor.id]   AS matched_entity_ids,
            [anchor.name] AS matched_terms,
            {self._STAR_RETURN}
        """

        rows = self._run(cypher, {"entity_id": entity_id})
        rows = self._dedupe_rows_by_failure(rows)
        self._postprocess_rows(rows)
        chunk_ids = self._chunk_ids_from_rows(rows)

        return {
            "retrieval_type": "connected_entity_to_failure_modes",
            "entity_id": entity_id,
            "results": rows,
            "chunk_ids": chunk_ids,
            "chunks": self.fetch_chunks(chunk_ids),
        }

    # ------------------------------------------------------------------
    # NEW: CHAIN / PATH TRAVERSAL
    #
    # Walks a variable-length path between two graph entities (any type)
    # and returns:
    #   - A reasoning_chain on each row: ordered list of
    #     {id, name, label, edge_type, edge_direction, claim_id, chunks}
    #   - The normal enriched-star results for every FailureMode on the
    #     path (so context_builder sees the same row schema).
    # ------------------------------------------------------------------

    def retrieve_path(
        self,
        start_id: str,
        end_id: str,
        max_hops: int = 5,
    ) -> Dict[str, Any]:
        """
        Find shortest path(s) between two entities and return enriched
        results for every FailureMode along each path.

        The reasoning_chain field on each result row gives the ordered
        traversal with edge-level provenance.
        """

        # Step 1: find shortest paths (up to max_hops relationships).
        path_cypher = """
        MATCH (start {id: $start_id}), (end {id: $end_id})
        MATCH path = shortestPath((start)-[*1..%d]-(end))
        WITH path,
             nodes(path) AS ns,
             relationships(path) AS rels
        RETURN
            [n IN ns | {
                id:    n.id,
                name:  n.name,
                label: labels(n)[0]
            }] AS path_nodes,
            [r IN rels | {
                type:       type(r),
                claim_id:   r.claim_id,
                confidence: r.confidence,
                chunks:     r.source_chunk_ids,
                start_id:   startNode(r).id,
                end_id:     endNode(r).id
            }] AS path_edges
        LIMIT 3
        """ % max_hops

        paths = self._run(
            path_cypher, {"start_id": start_id, "end_id": end_id}
        )

        if not paths:
            # Fall back to independent star retrieval if no path exists.
            return self._fallback_two_stars(start_id, end_id)

        # Step 2: collect FailureMode ids along all paths.
        fm_ids: set[str] = set()
        all_chain_chunk_ids: list[str] = []
        chains: list[list[dict]] = []

        for p in paths:
            chain: list[dict] = []
            for i, node in enumerate(p["path_nodes"]):
                step: dict = dict(node)
                if i < len(p["path_edges"]):
                    edge = p["path_edges"][i]
                    step["edge_type"] = edge["type"]
                    step["edge_direction"] = (
                        "outgoing"
                        if edge["start_id"] == node["id"]
                        else "incoming"
                    )
                    step["edge_claim_id"] = edge.get("claim_id")
                    step["edge_confidence"] = edge.get("confidence")
                    step["edge_chunks"] = edge.get("chunks") or []
                    all_chain_chunk_ids.extend(step["edge_chunks"])
                chain.append(step)

                if node.get("label") == "FailureMode":
                    fm_ids.add(node["id"])
            chains.append(chain)

        # Step 3: retrieve enriched stars for each FailureMode on the path.
        rows: list[dict] = []
        for fm_id in fm_ids:
            result = self.retrieve_by_failure(fm_id)
            for row in result.get("results", []):
                row["reasoning_chain"] = []  # attach chains below
                rows.append(row)

        rows = self._dedupe_rows_by_failure(rows)

        # Attach the best chain to the first row (for the LLM to narrate).
        if rows and chains:
            rows[0]["reasoning_chain"] = chains[0]

        self._postprocess_rows(rows)
        chunk_ids = self._chunk_ids_from_rows(rows)

        # Merge in chain-level chunk ids (edge provenance from the path).
        # Order-preserving merge, not alphabetical sort, for the same
        # reason as _flatten_chunk_ids above.
        extra_chain_chunks = self._flatten_chunk_ids(all_chain_chunk_ids)
        seen = set(chunk_ids)
        for cid in extra_chain_chunks:
            if cid not in seen:
                chunk_ids.append(cid)
                seen.add(cid)

        return {
            "retrieval_type": "path_traversal",
            "start_id": start_id,
            "end_id": end_id,
            "path_count": len(paths),
            "results": rows,
            "chunk_ids": chunk_ids,
            "chunks": self.fetch_chunks(chunk_ids),
        }

    def _fallback_two_stars(
        self, id_a: str, id_b: str
    ) -> Dict[str, Any]:
        """When no path connects two entities, retrieve both independently."""
        rows: list[dict] = []
        for eid in [id_a, id_b]:
            try:
                result = self.retrieve(eid)
                rows.extend(result.get("results", []))
            except ValueError:
                continue

        rows = self._dedupe_rows_by_failure(rows)
        self._postprocess_rows(rows)
        chunk_ids = self._chunk_ids_from_rows(rows)

        return {
            "retrieval_type": "independent_stars_no_path",
            "results": rows,
            "chunk_ids": chunk_ids,
            "chunks": self.fetch_chunks(chunk_ids),
        }

    # ------------------------------------------------------------------
    # TERM-BASED RETRIEVAL (enhanced from v2 with LEADS_TO/DEGRADES)
    # ------------------------------------------------------------------

    def retrieve_related_to_terms(
        self, terms: List[str], limit: int = 8
    ) -> Dict[str, Any]:
        clean_terms = [
            term.strip().lower()
            for term in terms
            if term and len(term.strip()) >= 3
        ]
        if not clean_terms:
            return {
                "retrieval_type": "term_related_graph_context",
                "results": [],
                "chunk_ids": [],
                "chunks": [],
            }

        cypher = f"""
        MATCH (n)
        WHERE n.name IS NOT NULL
          AND any(term IN $terms
                  WHERE toLower(n.name) CONTAINS term
                     OR term CONTAINS toLower(n.name))
        WITH DISTINCT n
        OPTIONAL MATCH path1 = (f1:FailureMode)-[]-(n)
        OPTIONAL MATCH path2 = (f2:FailureMode)-[]-()-[]-(n)
        WITH n, collect(DISTINCT f1) + collect(DISTINCT f2) AS candidates
        UNWIND candidates AS f
        WITH DISTINCT n, f
        WHERE f IS NOT NULL
        {self._STAR_MATCHES}
        RETURN
            f.id   AS failure_id,
            f.name AS failure_mode,
            f.severity AS severity,
            f.category AS category,
            collect(DISTINCT n.id)   AS matched_entity_ids,
            collect(DISTINCT n.name) AS matched_terms,
            {self._STAR_RETURN}
        LIMIT $limit
        """

        rows = self._run(cypher, {"terms": clean_terms, "limit": limit})
        self._postprocess_rows(rows)
        chunk_ids = self._chunk_ids_from_rows(rows)

        return {
            "retrieval_type": "term_related_graph_context",
            "terms": clean_terms,
            "results": rows,
            "chunk_ids": chunk_ids,
            "chunks": self.fetch_chunks(chunk_ids),
        }

    # ------------------------------------------------------------------
    # QUERY-PLAN RETRIEVAL (enhanced: detects two anchors -> path)
    # ------------------------------------------------------------------

    def retrieve_by_query_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        entity_ids = plan.get("entity_ids", [])
        terms = plan.get("expanded_terms", []) or plan.get("keywords", [])

        # ── Path retrieval when two distinct entities are identified ──
        if len(entity_ids) >= 2:
            # Try a path between the first two anchors.
            path_result = self.retrieve_path(entity_ids[0], entity_ids[1])
            if path_result.get("results"):
                # Augment with any remaining entity stars.
                extra_rows: list[dict] = []
                for eid in entity_ids[2:]:
                    try:
                        r = self.retrieve(eid)
                        extra_rows.extend(r.get("results", []))
                    except ValueError:
                        continue
                if extra_rows:
                    all_rows = path_result["results"] + extra_rows
                    all_rows = self._dedupe_rows_by_failure(all_rows)
                    self._postprocess_rows(all_rows)
                    path_result["results"] = all_rows
                    path_result["chunk_ids"] = self._chunk_ids_from_rows(
                        all_rows
                    )
                    path_result["chunks"] = self.fetch_chunks(
                        path_result["chunk_ids"]
                    )
                return path_result

        # ── Single-entity or term-based (same as v2) ──
        rows: List[Dict[str, Any]] = []

        for entity_id in entity_ids:
            try:
                result = self.retrieve(entity_id)
                rows.extend(result.get("results", []))
            except ValueError:
                continue

        rows.extend(
            self.retrieve_related_to_terms(terms).get("results", [])
        )

        rows = self._dedupe_rows_by_failure(rows)
        self._postprocess_rows(rows)
        rows = self._rank_rows(rows, entity_ids, terms)

        # ── Precision cap (recall-heavy path only) ──
        # Keep only the top-ranked failure modes, then cap the chunks that
        # flow from them. This fixes over-fetch on precision-sensitive
        # queries (e.g. "list all X") and cuts latency, without touching
        # the precise path_traversal / star routes.
        rows = rows[: self.MAX_RECALL_ROWS]
        chunk_ids = self._chunk_ids_from_rows(rows)[: self.MAX_RECALL_CHUNKS]

        return {
            "retrieval_type": "query_plan_recall_heavy_graph_context",
            "query_plan": plan,
            "results": rows,
            "chunk_ids": chunk_ids,
            "chunks": self.fetch_chunks(chunk_ids),
        }

    # ------------------------------------------------------------------
    # ENTITY SEARCH (unchanged)
    # ------------------------------------------------------------------

    def search_entities(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (n)
        WHERE n.name IS NOT NULL
          AND toLower(n.name) CONTAINS toLower($query)
        RETURN
            n.id AS id,
            n.name AS name,
            labels(n)[0] AS label
        LIMIT $limit
        """
        return self._run(cypher, {"query": query, "limit": limit})

    # ------------------------------------------------------------------
    # MAIN DISPATCH (v3: handles all node-type prefixes)
    # ------------------------------------------------------------------

    def retrieve(self, entity_or_plan: Any) -> Dict[str, Any]:
        """
        Backward-compatible entrypoint.

        Accepts:
        - 'SY_...'  -> symptom star
        - 'FM_...'  -> failure-mode star (enriched with LEADS_TO / DEGRADES)
        - 'C_...'   -> cause  -> connected failure modes
        - 'PA_...'  -> parameter -> connected failure modes
        - 'P_...'   -> part   -> connected failure modes
        - 'M_...'   -> module -> connected failure modes
        - 'MI_...'  -> mitigation -> connected failure modes
        - 'OF_...'  -> operating factor -> connected failure modes
        - 'ME_...'  -> method -> connected failure modes
        - 'E_...'   -> engine -> connected failure modes
        - 'PLAN::<base64-json>' -> query-plan retrieval
        - dict plan -> query-plan retrieval
        """
        if isinstance(entity_or_plan, dict):
            return self.retrieve_by_query_plan(entity_or_plan)

        if not entity_or_plan:
            return {
                "retrieval_type": "empty_query",
                "results": [],
                "chunk_ids": [],
                "chunks": [],
            }

        if isinstance(entity_or_plan, str) and entity_or_plan.startswith(
            self.PLAN_PREFIX
        ):
            return self.retrieve_by_query_plan(
                self._decode_plan(entity_or_plan)
            )

        entity_id = str(entity_or_plan)

        if entity_id.startswith("SY_"):
            return self.retrieve_by_symptom(entity_id)

        if entity_id.startswith("FM_"):
            return self.retrieve_by_failure(entity_id)

        # v3: all other typed prefixes go through connected-entity retrieval.
        known_prefixes = ("C_", "PA_", "P_", "M_", "MI_", "OF_", "ME_", "E_")
        if any(entity_id.startswith(pfx) for pfx in known_prefixes):
            return self.retrieve_by_connected_entity(entity_id)

        raise ValueError(
            f"Unsupported entity_id for graph retrieval: {entity_id}"
        )

    def _decode_plan(self, encoded: str) -> Dict[str, Any]:
        raw = base64.urlsafe_b64decode(
            encoded[len(self.PLAN_PREFIX) :].encode("ascii")
        )
        return json.loads(raw.decode("utf-8"))
