"""
AeroOps jury pass — DeepSeek V4 Pro, retrieval-wired to the local graph export.

Runs entirely offline against aeroops_knowledgegraph.md (the full JSON graph
export), no live Neo4j connection required. This avoids the AuraDB Free
auto-pause issue entirely for this pass.

Retrieval mirrors AeroOps' own two-channel context structure (per the
project's debugging notes): a structured GRAPH_FACTS block built from typed
relationships/claims with inline chunk-id provenance, plus a flat
EVIDENCE_CHUNKS block of the underlying passage text.

Usage:
    export TOKENROUTER_API_KEY=...
    python deepseek_jury_retrieval.py \
        --graph aeroops_knowledgegraph.md \
        --questions blind_questions.json \
        --out jury_deepseek_answers.json
"""

import json
import re
import os
import argparse
import time
from openai import OpenAI

STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "in", "on", "and", "or",
    "what", "how", "why", "does", "do", "can", "if", "for", "with", "that",
    "this", "it", "be", "when", "which", "during",
}


def tokenize(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def load_graph(path):
    with open(path) as f:
        graph = json.load(f)
    nodes_by_id = {}
    for label, items in graph["nodes"].items():
        for n in items:
            nodes_by_id[n["id"]] = {**n, "label": label}
    chunks_by_id = {c["chunk_id"]: c for c in graph["chunks"]}
    return nodes_by_id, chunks_by_id, graph["relationships"], graph["mentioned_in"]


def match_entities(question, nodes_by_id, min_overlap=1, top_n=6):
    """Score nodes by token overlap + specificity (fraction of the node's own
    tokens matched), not raw overlap alone — raw overlap ties otherwise get
    broken arbitrarily and can silently drop the entity that matters most.
    """
    q_tokens = tokenize(question) - STOPWORDS
    scored = []
    for nid, n in nodes_by_id.items():
        name_tokens = tokenize(n.get("name", "")) - STOPWORDS
        id_tokens = tokenize(nid.split("_", 1)[-1]) - STOPWORDS
        node_tokens = name_tokens | id_tokens
        overlap = q_tokens & node_tokens
        if len(overlap) >= min_overlap:
            specificity = len(overlap) / max(len(node_tokens), 1)
            scored.append((len(overlap) + specificity, nid))
    scored.sort(reverse=True)
    return [nid for _, nid in scored[:top_n]]


def expand_graph(seed_ids, relationships, hops=1):
    """1 hop by default, not 2. This graph is small and densely connected
    (111 nodes, 112 relationships) — 2-hop expansion was found to pull in
    30-50 of the corpus's 74 total chunks per question during testing,
    which stops being retrieval and starts being 'most of the corpus.'
    1 hop keeps results anchored to what's actually adjacent to the matched
    entities.
    """
    frontier = set(seed_ids)
    all_nodes = set(seed_ids)
    visited_rels = []
    for _ in range(hops):
        next_frontier = set()
        for r in relationships:
            if r["from"] in frontier or r["to"] in frontier:
                visited_rels.append(r)
                next_frontier.add(r["from"])
                next_frontier.add(r["to"])
        all_nodes |= next_frontier
        frontier = next_frontier - all_nodes
        if not frontier:
            break
    seen, uniq_rels = set(), []
    for r in visited_rels:
        key = (r["type"], r["from"], r["to"])
        if key not in seen:
            seen.add(key)
            uniq_rels.append(r)
    return uniq_rels, all_nodes


def get_evidence_chunk_ids(rels, seed_node_ids, mentioned_in):
    """Chunks come from two sources: (1) claim provenance on relationships
    directly touching a seed entity, (2) mentioned_in for the SEED entities
    only — not every node touched during graph expansion. Widening this to
    all expanded nodes was tested and found to pull 25-50 of the corpus's
    74 chunks per question (median 24), which stops being retrieval.
    Restricting to seeds keeps results anchored to what the question is
    actually about.
    """
    chunk_ids = set()
    for r in rels:
        chunk_ids |= set(r.get("properties", {}).get("source_chunk_ids", []))
    for m in mentioned_in:
        if m["from"] in seed_node_ids:
            chunk_ids.add(m["to"])
    return chunk_ids


def build_context(question, nodes_by_id, chunks_by_id, relationships, mentioned_in):
    seeds = match_entities(question, nodes_by_id)
    rels, all_nodes = expand_graph(seeds, relationships)
    chunk_ids = get_evidence_chunk_ids(rels, seeds, mentioned_in)

    graph_facts = []
    for r in rels:
        props = r.get("properties", {})
        if "claim_id" in props:
            from_name = nodes_by_id.get(r["from"], {}).get("name", r["from"])
            to_name = nodes_by_id.get(r["to"], {}).get("name", r["to"])
            graph_facts.append(
                f"[{props.get('claim_id')}] {from_name} --{r['type']}--> "
                f"{to_name} (source: {props.get('source_chunk_ids')})"
            )

    evidence = []
    for cid in sorted(chunk_ids):
        c = chunks_by_id.get(cid)
        if c:
            evidence.append(f"[{cid}] ({c['section']}): {c['text']}")

    return sorted(chunk_ids), graph_facts, evidence


PROMPT_TEMPLATE = """You are answering a question using ONLY the context provided below. Do not use outside knowledge, even if you're confident it's true in general — this corpus may describe a specific system that differs from general practice. If the context doesn't support an answer, say so explicitly.

GRAPH_FACTS:
{graph_facts}

EVIDENCE_CHUNKS:
{evidence_chunks}

QUESTION:
{question}

Respond with a JSON object only, no other text, in this exact shape:
{{
  "answer": "your answer in plain prose",
  "reasoning_chain": [
    {{"step": 1, "fact": "string", "source_chunk_id": "string"}}
  ]
}}

Leave "reasoning_chain" as an empty array if this is a single-hop question
that didn't require connecting multiple facts. If it did require connecting
facts across more than one piece of context, lay out the chain in order,
each step tied to the specific source_chunk_id that supports it.
"""


def call_deepseek(client, question, graph_facts, evidence, model="deepseek-v4-pro"):
    prompt = PROMPT_TEMPLATE.format(
        graph_facts="\n".join(graph_facts) if graph_facts else "(none found)",
        evidence_chunks="\n".join(evidence) if evidence else "(none found)",
        question=question,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    text = resp.choices[0].message.content.strip()
    # strip markdown code fences if the model wraps its JSON
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"answer": text, "reasoning_chain": [], "_parse_error": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default="aeroops_knowledgegraph.md")
    ap.add_argument("--questions", default="blind_questions.json")
    ap.add_argument("--out", default="jury_deepseek_answers.json")
    ap.add_argument("--model", default="deepseek-v4-pro")
    args = ap.parse_args()

    nodes_by_id, chunks_by_id, relationships, mentioned_in = load_graph(args.graph)
    with open(args.questions) as f:
        questions = json.load(f)

    client = OpenAI(
        api_key=os.environ["TOKENROUTER_API_KEY"],
        base_url="https://api.tokenrouter.com/v1",
    )

    results = []
    for i, item in enumerate(questions):
        qid, question = item["id"], item["question"]
        chunk_ids, graph_facts, evidence = build_context(
            question, nodes_by_id, chunks_by_id, relationships, mentioned_in
        )
        try:
            parsed = call_deepseek(client, question, graph_facts, evidence, model=args.model)
        except Exception as e:
            print(f"  FAILED on {qid}: {e}")
            parsed = {"answer": None, "reasoning_chain": [], "_error": str(e)}

        results.append({
            "id": qid,
            "deepseek_answer": parsed.get("answer"),
            "deepseek_retrieved_chunk_ids": chunk_ids,
            "deepseek_reasoning_chain": parsed.get("reasoning_chain", []),
        })
        print(f"[{i+1}/{len(questions)}] {qid} done ({len(chunk_ids)} chunks, {len(graph_facts)} facts)")
        time.sleep(0.5)  # light rate-limit courtesy

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {len(results)} items to {args.out}")


if __name__ == "__main__":
    main()
