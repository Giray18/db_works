"""Optional semantic table-discovery layer for the LangChain runtime - a port of
rag_agent/multi_agent_patterns/build_table_index.py + semantic_search.py (written for the
raw Anthropic SDK agent) into something registries.py can wrap as a LangChain @tool.

Backed by a persistent Chroma collection instead of a hand-rolled JSON file + manual cosine
similarity loop: Chroma owns the embedding call (same all-MiniLM-L6-v2 model as before, via its
SentenceTransformerEmbeddingFunction wrapper), the on-disk index, and the nearest-neighbor
search. `chroma_db/` holds the persisted collection - delete it and re-run build_index() to
rebuild from scratch, same as deleting the old table_index.json used to mean.

Kept as an *optional* discovery path, not a replacement for list_gold_tables:
rag_agent/multi_agent_patterns/README.md found semantic search doesn't change the answer at
15 tables - it only earns its cost once the catalog is too large to hand the LLM in full.
registries.py decides which discovery tool the agent actually gets using CATALOG_SIZE_THRESHOLD,
rather than always shipping both.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag_agent"))

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "rag_agent", ".env"))

import chromadb
from chromadb.utils import embedding_functions

import db
from schema_catalog import CATALOG

MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "gold_tables"
SAMPLE_ROWS = 3

# The filter condition: a top-k match that's still a weak match (e.g. everything under 0.2
# cosine similarity) is more likely to mislead the agent into querying the wrong table than to
# help it, so returning fewer than top_k - or zero - is correct when nothing is a good match.
MIN_SIMILARITY = 0.2

_client = None
_collection = None


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


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)
        # hnsw:space="cosine" makes query() return cosine distance (0 = identical, 2 = opposite),
        # so similarity = 1 - distance matches the same scale MIN_SIMILARITY was tuned against.
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=ef, metadata={"hnsw:space": "cosine"}
        )
    return _collection


def build_index() -> None:
    collection = _get_collection()
    ids, documents, metadatas = [], [], []
    for table in CATALOG.values():
        text = _table_text(table)
        ids.append(table.name)
        documents.append(text)
        metadatas.append({"table_name": table.name, "kind": table.kind})
        print(f"embedded {table.name} ({len(text)} chars)")

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"\nUpserted {len(ids)} table embeddings into Chroma collection '{COLLECTION_NAME}' at {CHROMA_PATH}")


def search_relevant_tables(question: str, top_k: int = 4) -> list[dict]:
    """Embeds `question` and scores it against every table's precomputed embedding by cosine
    similarity, via Chroma's nearest-neighbor search. Returns up to `top_k` matches that clear
    MIN_SIMILARITY - the enhancement over a plain top-k: a table only comes back if it's
    actually relevant, not just the closest of a bad set."""
    collection = _get_collection()
    if collection.count() == 0:
        raise RuntimeError(f"Chroma collection '{COLLECTION_NAME}' is empty - run `python semantic_index.py` first.")

    results = collection.query(query_texts=[question], n_results=top_k)
    matches = []
    print(f"\n[semantic_index] question={question!r} MIN_SIMILARITY={MIN_SIMILARITY}")
    for table_name, distance in zip(results["ids"][0], results["distances"][0]):
        similarity = round(1 - distance, 4)
        kept = similarity >= MIN_SIMILARITY
        print(f"[semantic_index]   {table_name:<32} cosine_similarity={similarity:.4f} {'KEEP' if kept else 'drop (below threshold)'}")
        if kept:
            matches.append({"table_name": table_name, "similarity": similarity})
    return matches


if __name__ == "__main__":
    build_index()
