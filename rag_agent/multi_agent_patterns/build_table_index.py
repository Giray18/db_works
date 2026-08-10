"""Builds a local semantic index over the 15 gold tables: each table's schema_catalog.py
definition (grain, description, columns) combined with a few live sample rows, embedded with
a local sentence-transformers model. semantic_search.py loads this index at query time to
retrieve the most relevant tables by cosine similarity instead of dumping the full 15-table
list into context every time.

Re-run this whenever schema_catalog.py's table set, descriptions, or the underlying data
changes meaningfully:

    python build_table_index.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sentence_transformers import SentenceTransformer

import db
from schema_catalog import CATALOG

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = os.path.join(os.path.dirname(__file__), "table_index.json")
SAMPLE_ROWS = 3


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


if __name__ == "__main__":
    build_index()
