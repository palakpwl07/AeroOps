# import_graph.py
#
# One-time seed script: loads knowledgebase/aeroops_knowledgegraph.md (a
# JSON export of the full graph -- documents, chunks, 10 entity node
# types, relationships with claim_id/confidence, and MENTIONED_IN edges)
# into a running Neo4j instance. Written to reproduce the exact schema
# graphretriever_v5.py already queries against (confirmed by reading its
# Cypher directly): Chunk.chunk_id, Document.doc_id, HAS_CHUNK edges,
# entity nodes matched by `id`/`name` properties regardless of label, and
# relationship properties (claim_id, confidence, source_chunk_ids, effect)
# stored directly on the edge -- not on separate Claim nodes.
#
# Run inside the app container (has the neo4j driver + network access to
# the neo4j container already):
#   docker exec aeroops-app-1 python import_graph.py

from __future__ import annotations

import json
import os

from neo4j import GraphDatabase

GRAPH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "knowledgebase", "aeroops_knowledgegraph.md")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


def main() -> None:
    with open(GRAPH_PATH, encoding="utf-8") as f:
        data = json.load(f)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    driver.verify_connectivity()

    with driver.session(database=NEO4J_DATABASE) as session:
        # Constraints double as indexes -- entity-matching in
        # graphretriever_v5.py does full-graph `MATCH (n) WHERE n.name ...`
        # scans, so these mainly protect against accidental duplicate
        # re-imports rather than being required for query correctness.
        session.run("CREATE CONSTRAINT document_id IF NOT EXISTS "
                    "FOR (d:Document) REQUIRE d.doc_id IS UNIQUE")
        session.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS "
                    "FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE")
        for label in data["nodes"].keys():
            session.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                        f"FOR (n:{label}) REQUIRE n.id IS UNIQUE")

        # Documents
        session.run(
            "UNWIND $rows AS row "
            "MERGE (d:Document {doc_id: row.doc_id}) "
            "SET d += row",
            rows=data["documents"],
        )
        print(f"Documents: {len(data['documents'])}")

        # Chunks (embedding field dropped -- confirmed unused by any
        # active retrieval path; graphretriever_v5.py's fetch_chunks()
        # only ever reads chunk_id/text/section/page/doc_id)
        chunk_rows = [
            {k: v for k, v in c.items() if k != "embedding"}
            for c in data["chunks"]
        ]
        session.run(
            "UNWIND $rows AS row "
            "MERGE (c:Chunk {chunk_id: row.chunk_id}) "
            "SET c += row",
            rows=chunk_rows,
        )
        session.run(
            "UNWIND $rows AS row "
            "MATCH (d:Document {doc_id: row.doc_id}) "
            "MATCH (c:Chunk {chunk_id: row.chunk_id}) "
            "MERGE (d)-[:HAS_CHUNK]->(c)",
            rows=chunk_rows,
        )
        print(f"Chunks: {len(chunk_rows)}")

        # Entity nodes, one label at a time (label can't be parameterized
        # in Cypher, so this loop is over the small, known label set)
        total_nodes = 0
        for label, items in data["nodes"].items():
            session.run(
                f"UNWIND $rows AS row "
                f"MERGE (n:{label} {{id: row.id}}) "
                f"SET n += row",
                rows=items,
            )
            total_nodes += len(items)
        print(f"Entity nodes: {total_nodes} across {len(data['nodes'])} labels")

        # Relationships -- grouped by type since Cypher can't parameterize
        # a relationship type, but the type set is small and known
        # (16 types). Properties (claim_id, confidence, source_chunk_ids,
        # effect) are set directly on the edge, matching how
        # graphretriever_v5.py reads them (e.g. `sr.claim_id`).
        rels_by_type: dict[str, list] = {}
        for r in data["relationships"]:
            rels_by_type.setdefault(r["type"], []).append(
                {"from": r["from"], "to": r["to"], "properties": r["properties"]}
            )
        total_rels = 0
        for rel_type, rows in rels_by_type.items():
            session.run(
                f"UNWIND $rows AS row "
                f"MATCH (a {{id: row.from}}), (b {{id: row.to}}) "
                f"MERGE (a)-[r:{rel_type}]->(b) "
                f"SET r += row.properties",
                rows=rows,
            )
            total_rels += len(rows)
        print(f"Relationships: {total_rels} across {len(rels_by_type)} types")

        # MENTIONED_IN: entity -> Chunk (structural, no claim_id -- see
        # context_builder.py's REAL_EDGE_TYPES distinction)
        session.run(
            "UNWIND $rows AS row "
            "MATCH (a {id: row.from}) "
            "MATCH (c:Chunk {chunk_id: row.to}) "
            "MERGE (a)-[:MENTIONED_IN]->(c)",
            rows=data["mentioned_in"],
        )
        print(f"MENTIONED_IN edges: {len(data['mentioned_in'])}")

    driver.close()
    print("Import complete.")


if __name__ == "__main__":
    main()
