"""Embeds a question and retrieves the most relevant gold tables by cosine similarity against
the index built by build_table_index.py - the real semantic-search alternative to
list_gold_tables()'s exhaustive dump used everywhere else in this project.

No LLM call happens here - this is pure local vector math, so it's fast and free to call
repeatedly, and it's testable without ANTHROPIC_API_KEY.
"""

import json
import os

import numpy as np
from sentence_transformers import SentenceTransformer

INDEX_PATH = os.path.join(os.path.dirname(__file__), "table_index.json")

_model = None
_index = None


def _load():
    global _model, _index
    if _index is None:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(f"{INDEX_PATH} not found - run `python build_table_index.py` first.")
        with open(INDEX_PATH, encoding="utf-8") as f:
            _index = json.load(f)
        _model = SentenceTransformer(_index["model"])
    return _model, _index


def search_relevant_tables(question: str, top_k: int = 4) -> list[dict]:
    model, index = _load()
    query_vec = model.encode(question)
    scored = []
    for entry in index["entries"]:
        table_vec = np.array(entry["embedding"])
        similarity = float(
            np.dot(query_vec, table_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(table_vec))
        )
        scored.append((similarity, entry["table_name"]))
    scored.sort(reverse=True)
    return [{"table_name": name, "similarity": round(sim, 4)} for sim, name in scored[:top_k]]


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "Which department has the worst procurement savings this year?"
    print("Q:", q)
    for r in search_relevant_tables(q):
        print(f"  {r['similarity']:.4f}  {r['table_name']}")
