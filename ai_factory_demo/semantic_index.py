"""Optional semantic table-discovery layer for the LangChain runtime - a port of
rag_agent/multi_agent_patterns/build_table_index.py + semantic_search.py (written for the
raw Anthropic SDK agent) into something registries.py can wrap as a LangChain @tool.

Same index format and embedding model as the original, so `python semantic_index.py` and
`rag_agent/multi_agent_patterns/build_table_index.py` are interchangeable - either can produce
table_index.json, this file just reads it from its own directory.

Kept as an *optional* discovery path, not a replacement for list_gold_tables:
rag_agent/multi_agent_patterns/README.md found semantic search doesn't change the answer at
15 tables - it only earns its cost once the catalog is too large to hand the LLM in full.
registries.py decides which discovery tool the agent actually gets using CATALOG_SIZE_THRESHOLD,
rather than always shipping both.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag_agent"))

import numpy as np
from sentence_transformers import SentenceTransformer

import db
from schema_catalog import CATALOG

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = os.path.join(os.path.dirname(__file__), "table_index.json")
SAMPLE_ROWS = 3

# The filter condition: a top-k match that's still a weak match (e.g. everything under 0.2
# cosine similarity) is more likely to mislead the agent into querying the wrong table than to
# help it, so returning fewer than top_k - or zero - is correct when nothing is a good match.
MIN_SIMILARITY = 0.2

_model = None
_index = None


def _table_text(table) -> str:
    columns_text = ", ".join(
        f"{c.name} ({c.type})" + (f" - {c.description}" if c.description else "") for c in table.columns
    )
    try:
        _, rows = db.run_query(f"SELECT * FROM {table.name} LIMIT {SAMPLE_ROWS}")
        sample_text = "\n".join(str(r) for r in rows)
    except Exception as e:  # noqa: BLE001 - a table without readable sample data shouldn't block indexing
        sample_text = f"(sample rows unavailable: {e})"
    return (
        f"Table: {table.name} ({table.kind})\n"
        f"Grain: {table.grain}\n"
        f"Description: {table.business_description}\n"
        f"Columns: {columns_text}\n"
        f"Sample rows:\n{sample_text}"
    )


def build_index() -> None:
    model = SentenceTransformer(MODEL_NAME)
    entries = []
    for table in CATALOG.values():
        text = _table_text(table)
        embedding = model.encode(text).tolist()
        entries.append({"table_name": table.name, "text": text, "embedding": embedding})
        print(f"embedded {table.name} ({len(text)} chars)")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump({"model": MODEL_NAME, "entries": entries}, f)
    print(f"\nWrote {len(entries)} table embeddings to {INDEX_PATH}")


def _load():
    global _model, _index
    if _index is None:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(f"{INDEX_PATH} not found - run `python semantic_index.py` first.")
        with open(INDEX_PATH, encoding="utf-8") as f:
            _index = json.load(f)
        _model = SentenceTransformer(_index["model"])
    return _model, _index


def search_relevant_tables(question: str, top_k: int = 4) -> list[dict]:
    """Embeds `question` and scores it against every table's precomputed embedding by cosine
    similarity. Returns up to `top_k` matches that clear MIN_SIMILARITY - the enhancement over
    a plain top-k: a table only comes back if it's actually relevant, not just the closest of
    a bad set."""
    model, index = _load()
    query_vec = model.encode(question)
    scored = []
    for entry in index["entries"]:
        table_vec = np.array(entry["embedding"])
        similarity = float(
            np.dot(query_vec, table_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(table_vec))
        )
        if similarity >= MIN_SIMILARITY:
            scored.append((similarity, entry["table_name"]))
    scored.sort(reverse=True)
    return [{"table_name": name, "similarity": round(sim, 4)} for sim, name in scored[:top_k]]


if __name__ == "__main__":
    build_index()
