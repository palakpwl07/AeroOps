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
from langsmith import traceable

import tracing_setup  # noqa: F401 -- populates LANGCHAIN_* env vars before use


class GraphRetriever:
    PLAN_PREFIX = "PLAN::"

    # Caps applied ONLY to the recall-heavy query-plan path, to stop it
    # over-fetching failure modes and flooding the LLM context with
    # loosely-related chunks. Path traversal and single-entity stars are
    # unaffected (they are already precise).
    MAX_RECALL_ROWS = 4       # keep top-N ranked failure modes
    # Was 12 -- raised 2026-08-28 alongside the _rank_rows fix. With
    # ranking now correctly favoring relevant rows, a flat sequential
    # walk (rank order, no per-row split) already lands the right
    # chunks first; a per-row redistribution/floor scheme was tried to
    # further tighten this and rejected -- it broke CD01 by trimming a
    # correctly-ranked #1 row's own mitigation chunk to backfill lower
    # rows that CD01 didn't actually need, while CD04 needed exactly
    # that kind of backfill for a real, correctly-ranked row (FM_blade_cracking).
    # No universal per-row policy satisfied both without case-specific
    # tuning, so instead of building a fragile reallocation heuristic,
    # the budget was widened enough (12 -> 16) that a plain sequential
    # walk gives every correctly-ranked top-4 row genuine room. Verified
    # against CD01, AF06, and CD04 together (see graphretriever notes).
    #
    # EXPERIMENT (this session): trimmed 16 -> 10 to test whether a
    # smaller context materially cuts GraphRAG generation latency
    # (generation was measured as the dominant cost, ~5.5s mean, vs
    # ~2.8s retrieval). CD01, AF06, and CD04 are the specific items the
    # 12->16 raise was fixing regressions for -- they're the ones to
    # check first if this trim reintroduces a quality regression.
    MAX_RECALL_CHUNKS = 10    # cap chunks sent to the LLM on this path --
    # second half of a fresh back-to-back A/B (16 just run, 10 now,
    # minutes apart) so both readings share the same OpenRouter conditions.

    # Fixed 2026-08-30: retrieve_path()'s shortestPath used to match ANY
    # relationship type, including MENTIONED_IN/HAS_CHUNK (structural
    # Entity->Chunk edges with no claim_id -- see context_builder.py's
    # REAL_EDGE_TYPES, which this list mirrors). That let two entities
    # with no real edge path between them get connected anyway by
    # hopping through a shared Chunk node, and the generator narrated
    # that stitched path as a causal claim (OS04: "loss of a boost pump
    # can cause fuel-filter clogging, which in turn can lead to a
    # flameout" -- confirmed via the mechanical scorer's
    # edge_authenticity_rate: 0.0 for OS04/OS02, 0.333-0.5 category-wide
    # across cross_document/operational_scenario/aggregation_fanout/
    # disambiguation). The prior fix (edge tagging in context_builder.py
    # + generator Rule 12) only changed how a structural hop is
    # *rendered and prompted against* -- it never stopped the retriever
    # from building one in the first place, so a lenient model could
    # still narrate it as causal despite the label.
    # Restricting the traversal itself to these types means a pair of
    # entities with no real-edge path now genuinely has none within this
    # query -- shortestPath returns no rows, and the existing
    # `if not paths: return self._fallback_two_stars(...)` branch
    # (already correct, from the PR02/PR03 chunk_ids fix) takes over,
    # giving each entity's own real star independently instead of a
    # fabricated connection between them.
    REAL_EDGE_TYPES = (
        "MANIFESTS_AS", "CAUSES", "INFLUENCES", "LEADS_TO", "MITIGATES",
        "AFFECTS", "DEGRADES", "RESTORES", "INDICATES", "DETECTS",
    )

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD","Letsrock@263")
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
                ("indicating_symptoms", "symptom_id"),
                ("detected_by", "detector_id"),
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
            row["indicating_symptoms"] = self._clean_items(
                row.get("indicating_symptoms", []), "symptom"
            )
            row["detected_by"] = self._clean_items(
                row.get("detected_by", []), "detector"
            )

    def _capped_chunk_ids(
        self, rows: List[Dict[str, Any]], intent: Optional[str] = None
    ) -> List[str]:
        """
        Plain sequential walk in rank order, same shape as the original
        `self._chunk_ids_from_rows(rows)[: self.MAX_RECALL_CHUNKS]` --
        kept as its own method (rather than inlined) because two
        alternatives were tried here and rejected, and it's worth
        recording why so this isn't re-attempted blind:

        1. An even per-row split (MAX_RECALL_CHUNKS // len(rows) each).
           Fixed CD04 (FM_blade_cracking, ranked into the top 4 by the
           _rank_rows fix but previously starved of its 2 chunks by
           richer rows above it) but broke CD01: a flat 3-chunk share
           exactly exhausted a 12-chunk budget on the first pass, so
           FM_egt_margin_deterioration's own D1_c10 (water-wash) chunk --
           the *second* item in that row's `mitigations` field, preceded
           by 1 symptom + 4 causes in field-walk order -- got cut even
           though the row was correctly ranked #1.
        2. Reordering each row's own field-walk order by the query's
           classified `intent` (e.g. mitigations-first for
           "mitigation_lookup") to reach a needed field faster within a
           tight per-row share. This fixed CD01 but broke it again a
           different way for compound questions: CD01 needs a *cause*
           fact from one row and a *mitigation* fact from another, and a
           single global intent can only reorder one direction --
           reordering to reach the mitigation in row 1 pushed the cause
           fact in row 2 below its share.

        Neither approach generalizes without per-row, per-fact relevance
        scoring that doesn't exist yet. Given ranking now correctly
        surfaces the relevant rows (the _rank_rows fix), the simpler and
        more robust move was widening MAX_RECALL_CHUNKS (12 -> 16) so a
        plain sequential walk gives every correctly-ranked top-4 row
        genuine room without needing to arbitrate between rows at all.
        Verified together against CD01, AF06, and CD04.
        """
        if not rows:
            return []
        chunk_ids: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for cid in self._chunk_ids_from_rows([row]):
                if len(chunk_ids) >= self.MAX_RECALL_CHUNKS:
                    break
                if cid in seen:
                    continue
                chunk_ids.append(cid)
                seen.add(cid)
        return chunk_ids

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
            + [row.get("indicating_symptoms") for row in rows]
            + [row.get("detected_by") for row in rows]
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

        # Fixed 2026-08-28 -- this scoring formula was over-surfacing
        # "richly documented" but query-irrelevant failure modes
        # (confirmed on CD01 and AF06): FM_compressor_surge outranked the
        # correctly-matched FM_egt_margin_deterioration purely because
        # compressor surge has more symptoms/causes/leads_to edges, and
        # it only entered the candidate pool at all via a 2-hop term-
        # search traversal through a shared hub node (e.g. SY_high_egt,
        # a symptom common to many unrelated failure modes) -- not
        # through any real connection to the query. The old
        # `10 * len(matched_ids & entity_id_set)` term made this worse:
        # it credits a row for merely sharing an id with the plan's
        # entities, which is also true of a row that was *discovered
        # while searching from* that entity via term fanout, not a row
        # that actually *is* that entity.
        #
        # Also, this formula predates the v5 star-query addition of
        # detected_by/indicating_symptoms/affected_components/degrades/
        # restores and was never updated for them (confirmed via
        # `git diff` -- _rank_rows/score do not appear in the commit that
        # added those fields). CD04's gold node, FM_blade_cracking,
        # carries its entire relevant signal in detected_by (both a
        # borescope and an NDT DETECTS edge) and scored as if it had no
        # content at all.
        def score(row: Dict[str, Any]) -> int:
            matched_ids = set(row.get("matched_entity_ids", []))
            matched_terms = " ".join(row.get("matched_terms", [])).lower()
            term_hop = row.get("term_hop")  # None (direct/connected-entity row) | 1 | 2

            s = 0

            # -- Relevance (dominant): how was this row actually found? --
            if row.get("failure_id") in entity_id_set:
                # The row IS one of the plan's resolved entities.
                s += 40
            elif matched_ids & entity_id_set and term_hop is None:
                # Reached via a deliberate connected-entity search
                # anchored on a resolved entity (Cause/Mitigation/
                # Parameter/...), not via incidental term fanout.
                s += 20
            else:
                # Reached only through retrieve_related_to_terms. A
                # 1-hop term match is a real, if weaker, signal; a
                # 2-hop match crossed an intermediate node and is much
                # more likely a structural coincidence (a shared
                # symptom/downstream failure mode) than genuine
                # relevance -- this is exactly what let
                # FM_compressor_surge outrank the actually-matched
                # entity on CD01 and AF06.
                s += 6 if term_hop == 1 else 1

            s += 3 * sum(1 for term in term_set if term in matched_terms)

            # -- Richness (secondary: tie-breaker among comparably-
            # relevant rows, not a way to out-vote relevance). Now
            # covers every star field, not just the four that existed
            # before v5. Divided down so it can no longer dominate the
            # relevance terms above the way it did in the CD01/AF06/CD04
            # cases.
            richness = (
                2 * len(row.get("symptoms", []))
                + len(row.get("causes", []))
                + len(row.get("mitigations", []))
                + 2 * len(row.get("leads_to", []))
                + len(row.get("detected_by", []))
                + len(row.get("indicating_symptoms", []))
                + len(row.get("affected_components", []))
                + len(row.get("degrades", []))
                + len(row.get("restores", []))
            )
            s += richness // 3

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
    #
    # v5 addition: indicating_symptoms (INDICATES) and detected_by
    # (DETECTS). Neither was covered by any star query before this --
    # _STAR_MATCHES only traversed 7 of the graph's 21 relationship
    # types. Confirmed via live schema check: Symptom "Oil filter bypass
    # indication" -[:INDICATES]-> FailureMode "Bearing failure" is a real
    # edge that was structurally unreachable no matter how correctly a
    # question's entity matching anchored on either node, because the
    # star itself never asked about INDICATES at all. Same gap for
    # DETECTS (Mitigation/Method -[:DETECTS]-> FailureMode).
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
        } END) AS restores,

        collect(DISTINCT CASE WHEN ind_sym IS NOT NULL THEN {
            symptom_id:  ind_sym.id,
            symptom:     ind_sym.name,
            confidence:  ind.confidence,
            claim_id:    ind.claim_id,
            chunks:      ind.source_chunk_ids
        } END) AS indicating_symptoms,

        collect(DISTINCT CASE WHEN det IS NOT NULL THEN {
            detector_id:   det.id,
            detector:      det.name,
            detector_type: head(labels(det)),
            confidence:    det_r.confidence,
            claim_id:      det_r.claim_id,
            chunks:        det_r.source_chunk_ids
        } END) AS detected_by
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
        OPTIONAL MATCH (ind_sym:Symptom)-[ind:INDICATES]->(f)
        OPTIONAL MATCH (det)-[det_r:DETECTS]->(f)
            WHERE 'Mitigation' IN labels(det) OR 'Method' IN labels(det)
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
        # Relationship types restricted to REAL_EDGE_TYPES -- see the
        # class-level comment. Without this, shortestPath treats
        # MENTIONED_IN/HAS_CHUNK the same as CAUSES/LEADS_TO/etc, and can
        # connect two entities via a shared Chunk node with no real edge
        # between them at all.
        rel_types = "|".join(self.REAL_EDGE_TYPES)
        path_cypher = """
        MATCH (start {id: $start_id}), (end {id: $end_id})
        MATCH path = shortestPath((start)-[:%s*1..%d]-(end))
        WITH path,""" % (rel_types, max_hops) + """
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
        """

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
                result = self._retrieve_base(eid)
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

        # NOTE on term_hop: originally this query only unioned 1-hop and
        # 2-hop FailureMode candidates with no record of which distance
        # actually found each one. _rank_rows had no way to tell "this
        # failure mode IS what the term named" from "this failure mode
        # sits two steps away through some unrelated intermediate node"
        # -- e.g. FM_egt_margin_deterioration reaching FM_compressor_surge
        # only via the shared hub symptom SY_high_egt. min(hop) now
        # records the closest distance at which ANY term-matched node
        # reached this failure mode, so ranking can discount 2-hop-only
        # matches instead of scoring them the same as 1-hop ones.
        cypher = f"""
        MATCH (n)
        WHERE n.name IS NOT NULL
          AND any(term IN $terms
                  WHERE toLower(n.name) CONTAINS term
                     OR term CONTAINS toLower(n.name))
        WITH DISTINCT n
        OPTIONAL MATCH path1 = (f1:FailureMode)-[]-(n)
        OPTIONAL MATCH path2 = (f2:FailureMode)-[]-()-[]-(n)
        WITH n, collect(DISTINCT f1) AS one_hop, collect(DISTINCT f2) AS two_hop
        UNWIND (one_hop + two_hop) AS f
        WITH DISTINCT n, f, (CASE WHEN f IN one_hop THEN 1 ELSE 2 END) AS hop
        WHERE f IS NOT NULL
        {self._STAR_MATCHES}
        RETURN
            f.id   AS failure_id,
            f.name AS failure_mode,
            f.severity AS severity,
            f.category AS category,
            collect(DISTINCT n.id)   AS matched_entity_ids,
            collect(DISTINCT n.name) AS matched_terms,
            min(hop) AS term_hop,
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
            # BUG FIX: this used to check only `path_result.get("results")`,
            # which is empty whenever the shortest path contains no
            # FailureMode node -- retrieve_path only builds enriched rows
            # by iterating FailureMode ids on the path (see its fm_ids
            # loop). But retrieve_path ALSO independently collects
            # chunk_ids/chunks from the path's own edge provenance
            # (the extra_chain_chunks merge), regardless of whether a
            # FailureMode was involved. A direct edge like
            # MI_performance_restoration -[:RESTORES]-> PA_sfc has real,
            # correctly-sourced evidence (confirmed: PR02's D4_c11) but
            # zero FailureMode nodes on it, so the old check discarded
            # that already-correct evidence and fell through to a much
            # broader, less precise search that landed on an unrelated
            # failure mode entirely. Checking chunk_ids too means a real,
            # sourced path result is trusted even when it has no
            # FailureMode-anchored row to attach it to.
            if path_result.get("results") or path_result.get("chunk_ids"):
                # Augment with any remaining entity stars.
                extra_rows: list[dict] = []
                for eid in entity_ids[2:]:
                    try:
                        r = self._retrieve_base(eid)
                        extra_rows.extend(r.get("results", []))
                    except ValueError:
                        continue

                # Fixed 2026-08-30 (OS06): this branch used to return
                # path_result["results"] in whatever order fm_ids (a
                # Python set, so unordered) + extra_rows happened to
                # produce -- it never called _rank_rows at all. For OS06,
                # entity_ids = [SY_high_egt, SY_egt_exceedance,
                # FM_hot_start]: retrieve_path found a real chain through
                # FM_severe_engine_damage/FM_compressor_surge, and
                # FM_hot_start (a real, directly-matched entity, added
                # here via extra_rows) ended up buried behind them in
                # arbitrary set order with no ranking ever applied --
                # confirmed live: none of these rows carried a
                # "retrieval_score" key at all. The generator built its
                # answer around results[0] (whichever failure mode
                # happened to iterate first), leading with compressor
                # surge instead of the directly-matched hot start.
                # _rank_rows already has the machinery for this (a
                # +40 bonus when a row's own failure_id is one of the
                # plan's entity_ids -- true for FM_hot_start here, false
                # for the incidental path nodes) -- it just was never
                # invoked on this return path. Applying it uniformly
                # here (even when extra_rows is empty, e.g. plain 2-hop
                # chains like MH03) makes row order reflect relevance
                # instead of set-iteration order in every path_traversal
                # case, not just this one.
                #
                # Ranking reorders the list, but retrieve_path attaches
                # the reasoning_chain to whichever row happened to be
                # first when it was built (Step 2 of retrieve_path,
                # before any of this runs) -- if that's no longer
                # results[0] after ranking, graph_rag.py's
                # `results[0].get("reasoning_chain", [])` would silently
                # find nothing.
                #
                # First attempt here was "reattach to whichever row ends
                # up on top" -- wrong, and caught live on OS06: the chain
                # found between the two original anchors (SY_high_egt ->
                # FM_compressor_surge -> FM_severe_engine_damage ->
                # SY_egt_exceedance) has nothing to do with FM_hot_start,
                # but once ranking correctly put FM_hot_start on top, the
                # blind reattach put THAT chain under a "Failure Mode 1:
                # Hot start" header anyway. Rule 4 tells the generator to
                # narrate the reasoning chain as a sequence, so it did --
                # producing "a compressor-surge/stall condition that can
                # occur during a hot start", conflating two distinct,
                # mutually-exclusive failure modes because the chain was
                # mislabeled, not because either fact was wrong on its
                # own.
                # Fix: only reattach the chain to a row whose own
                # failure_id actually appears as a node in that chain.
                # If the top-ranked row was never on the traversed path
                # at all (its relevance came from being a direct entity
                # match, not from the path search), drop the chain
                # rather than present it under the wrong heading --
                # every fact in it is still visible in that OTHER row's
                # own graph_facts section further down.
                all_rows = path_result["results"] + extra_rows
                all_rows = self._dedupe_rows_by_failure(all_rows)
                self._postprocess_rows(all_rows)

                reasoning_chain = next(
                    (r.get("reasoning_chain") for r in all_rows if r.get("reasoning_chain")),
                    None,
                )
                for r in all_rows:
                    r.pop("reasoning_chain", None)

                all_rows = self._rank_rows(all_rows, entity_ids, terms)

                if reasoning_chain and all_rows:
                    chain_node_ids = {step.get("id") for step in reasoning_chain if step.get("id")}
                    if all_rows[0].get("failure_id") in chain_node_ids:
                        all_rows[0]["reasoning_chain"] = reasoning_chain

                path_result["results"] = all_rows

                # Bug caught by re-running the full 45 after this fix,
                # not assumed safe: PR02 regressed to "Information not
                # available." Root cause -- this line used to blindly
                # OVERWRITE path_result["chunk_ids"] with
                # self._chunk_ids_from_rows(all_rows). PR02's anchors are
                # MI_performance_restoration and PA_sfc, connected by a
                # single real RESTORES edge with NO FailureMode on it at
                # all, so all_rows is empty (same reason the "BUG FIX"
                # comment above this block exists for the results check).
                # retrieve_path() had already correctly put D4_c11 into
                # path_result["chunk_ids"] from the edge's own
                # source_chunk_ids -- recomputing from an empty all_rows
                # discarded it outright. Merge instead of overwrite, so a
                # path with real edge-level evidence but no row-level
                # evidence doesn't get its only chunk stripped out here.
                combined_chunk_ids = list(path_result.get("chunk_ids") or [])
                seen_chunk_ids = set(combined_chunk_ids)
                for cid in self._chunk_ids_from_rows(all_rows):
                    if cid not in seen_chunk_ids:
                        combined_chunk_ids.append(cid)
                        seen_chunk_ids.add(cid)
                # Fixed 2026-08-30: this merge has no cap of its own, so
                # path-level chunk_ids (already up to MAX_RECALL_CHUNKS)
                # plus row-derived chunk_ids on top could exceed the
                # retriever's own intended ceiling -- confirmed against
                # live eval data: OS08 hit 25 chunks, DA05 22, DA03 20.
                # Re-cap here rather than leaving it to callers; path
                # chunks stay first (direct-path evidence) so the cap
                # trims from the row-derived tail, not the path itself.
                combined_chunk_ids = combined_chunk_ids[: self.MAX_RECALL_CHUNKS]
                path_result["chunk_ids"] = combined_chunk_ids
                path_result["chunks"] = self.fetch_chunks(combined_chunk_ids)
                return path_result

        # ── Single-entity or term-based (same as v2) ──
        rows: List[Dict[str, Any]] = []

        for entity_id in entity_ids:
            try:
                result = self._retrieve_base(entity_id)
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
        chunk_ids = self._capped_chunk_ids(rows, intent=plan.get("intent"))

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

    # Edge types the FailureMode "star" (_STAR_MATCHES) already reads. Any
    # claim-bearing edge of a type NOT in this list is invisible to every
    # star route, so it is fetched separately by fetch_anchor_relations().
    _STAR_EDGE_TYPES = [
        "MANIFESTS_AS", "CAUSES", "INFLUENCES", "LEADS_TO", "MITIGATES",
        "AFFECTS", "DEGRADES", "RESTORES", "INDICATES", "DETECTS",
    ]

    def fetch_anchor_relations(self, entity_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fixed 2026-09-21 (smoke-test query #7, N-CMAPSS): every retrieval
        route returns FailureMode-anchored "stars", and the star only
        reads the edge types in _STAR_EDGE_TYPES. Five claim-bearing edges
        in the graph use other types (MODELS x2, ENABLES x2, SUPPORTS x1;
        the other unread types -- PART_OF, MEASURED_BY, IS_A -- carry no
        claim_id and are structural). "N-CMAPSS -MODELS-> Hardware
        deterioration" (CL071, chunk D2_c05, the ONLY chunk that mentions
        N-CMAPSS) was therefore never retrieved: the entity matched, the
        hardware-deterioration star came back, and the one chunk that
        answers the question never reached the generator -- which then
        said "no information" on about a third of identical requests
        (temperature 0.1) and otherwise paraphrased an unrelated
        ANN-Flux chunk as if it were about N-CMAPSS.

        Returns the matched entities' own direct, claim-bearing edges of
        the types the star does not read, in either direction.
        """
        ids = [e for e in dict.fromkeys(entity_ids or []) if e]
        if not ids:
            return []
        cypher = """
        MATCH (a) WHERE a.id IN $ids
        MATCH (a)-[r]-(o)
        WHERE r.claim_id IS NOT NULL AND NOT type(r) IN $star_types
        RETURN DISTINCT
            a.id AS anchor_id, a.name AS anchor_name,
            (startNode(r) = a) AS outgoing,
            type(r) AS rel,
            o.id AS other_id, o.name AS other_name,
            r.claim_id AS claim_id,
            r.confidence AS confidence,
            r.source_chunk_ids AS chunks
        """
        rows = self._run(cypher, {"ids": ids, "star_types": self._STAR_EDGE_TYPES})
        out: List[Dict[str, Any]] = []
        seen = set()
        for r in rows:
            if r["outgoing"]:
                src_id, src, tgt_id, tgt = r["anchor_id"], r["anchor_name"], r["other_id"], r["other_name"]
            else:
                src_id, src, tgt_id, tgt = r["other_id"], r["other_name"], r["anchor_id"], r["anchor_name"]
            key = (src_id, r["rel"], tgt_id, r["claim_id"])
            if key in seen:  # both endpoints matched -> same edge seen twice
                continue
            seen.add(key)
            out.append({
                "source_id": src_id, "source": src, "rel": r["rel"],
                "target_id": tgt_id, "target": tgt,
                "claim_id": r["claim_id"], "confidence": r["confidence"],
                "chunks": list(r["chunks"] or []),
            })
        return out

    def _anchor_ids(self, entity_or_plan: Any) -> List[str]:
        if isinstance(entity_or_plan, dict):
            return list(entity_or_plan.get("entity_ids") or [])
        if isinstance(entity_or_plan, str):
            if entity_or_plan.startswith(self.PLAN_PREFIX):
                return list(self._decode_plan(entity_or_plan).get("entity_ids") or [])
            return [entity_or_plan]
        return []

    def _attach_anchor_relations(self, result: Dict[str, Any], entity_ids: List[str]) -> None:
        # Retrieval must never fail because of this add-on: on any error
        # the result is left exactly as the star routes produced it.
        try:
            rels = self.fetch_anchor_relations(entity_ids)
        except Exception as exc:
            result["anchor_relations_error"] = str(exc)
            return
        if not rels:
            return
        result["anchor_relations"] = rels
        existing = list(result.get("chunk_ids") or [])
        have = set(existing)
        new = []
        for rel in rels:
            for cid in rel["chunks"]:
                if cid not in have:
                    new.append(cid)
                    have.add(cid)
        if new:
            # Anchor evidence goes first and is not subject to the recall
            # cap: it is a handful of chunks and is the direct answer
            # material for the matched entity.
            result["chunk_ids"] = new + existing
            result["chunks"] = self.fetch_chunks(result["chunk_ids"])

    @traceable(name="graph_retrieve", run_type="retriever")
    def retrieve(self, entity_or_plan: Any) -> Dict[str, Any]:
        result = self._retrieve_base(entity_or_plan)
        self._attach_anchor_relations(result, self._anchor_ids(entity_or_plan))
        return result

    def _retrieve_base(self, entity_or_plan: Any) -> Dict[str, Any]:
        """
        Backward-compatible entrypoint (star / path / plan routes only;
        retrieve() adds the anchor relations on top).

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
