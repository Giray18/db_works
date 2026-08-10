"""Runs the same question through all 4 architectures side by side:

  1. Single agent, one shared tool-use loop     -> rag_agent/agent.py
  2. Pipeline (fixed-sequence subagents)        -> pipeline.py
  3. Hub-and-spoke (LLM-coordinated spokes)     -> hub_and_spoke.py
  4. Single agent + real semantic table search  -> semantic_search_agent.py

Watch latency and, if you check the Anthropic Console afterwards, token cost: the
multi-agent patterns (2, 3) make more separate LLM calls than the single agent for the same
question, and each one re-establishes its own context - that overhead is the price of
context isolation, not a bug. Variant 4 isolates a different question: does replacing
list_gold_tables()'s exhaustive dump with vector search change which tables get queried, or
just add an embedding step for no real benefit at this table count?

Variant 4 needs table_index.json to exist first: run `python build_table_index.py`.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import agent as single_agent  # noqa: E402
import hub_and_spoke  # noqa: E402
import pipeline  # noqa: E402
import semantic_search_agent  # noqa: E402

QUESTION = "Which department has the worst procurement savings this year?"


def _timed(label: str, fn) -> None:
    start = time.time()
    result = fn()
    elapsed = time.time() - start
    print(f"\n=== {label} ({elapsed:.1f}s) ===")
    print(result)


if __name__ == "__main__":
    print("Q:", QUESTION)
    _timed("1. Single agent (rag_agent/agent.py)", lambda: single_agent.ask(QUESTION)["answer"])
    _timed("2. Pipeline (fixed sequence)", lambda: pipeline.ask(QUESTION))
    _timed("3. Hub-and-spoke (LLM-coordinated)", lambda: hub_and_spoke.ask(QUESTION))
    _timed("4. Single agent + semantic table search", lambda: semantic_search_agent.ask(QUESTION)["answer"])
