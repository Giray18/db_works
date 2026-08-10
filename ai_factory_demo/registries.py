"""Registries pillar: catalogs of governed, reusable building blocks the runtime is allowed to
use - which tools an agent can call, and which data products it can query. Centralizing these
means adding, removing, or versioning a capability is a registry change, not an agent-by-agent
code change.

Wraps rag_agent's already-tested logic rather than duplicating it: the raw functions in
rag_agent/tools.py and the metadata in rag_agent/schema_catalog.py become this registry's
entries, exposed as LangChain @tool-decorated callables for runtime.py to hand to create_agent.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag_agent"))

from langchain_core.tools import tool

import tools as _rag_tools
from schema_catalog import CATALOG
from semantic_index import search_relevant_tables as _search_relevant_tables

# Discovery-tool selection condition: below this many tables, dumping the full catalog is
# cheaper and just as accurate as a vector-search hop (see
# rag_agent/multi_agent_patterns/README.md's compare.py finding at the current 15-table size).
# At or above it, semantic search keeps the discovery step's context bounded instead of growing
# with every table added to the gold schema.
CATALOG_SIZE_THRESHOLD = 25

# Overrides the size-based decision for demo purposes, mirroring demo.py's DEMO_MODEL_ALIAS
# pattern: DEMO_DISCOVERY=semantic python demo.py "..." forces semantic search even below the
# threshold, DEMO_DISCOVERY=exhaustive forces list_gold_tables. Unset (or "auto") uses the
# catalog-size condition above.
DISCOVERY_MODE = os.environ.get("DEMO_DISCOVERY", "auto")


@tool
def list_gold_tables() -> dict:
    """Lists all gold-layer tables available to query, each with its grain and a one-line business description."""
    return _rag_tools.list_gold_tables()


@tool
def search_relevant_tables(question: str) -> dict:
    """Semantic alternative to list_gold_tables: embeds the question and returns only the gold
    tables whose schema-plus-sample-data embedding is actually similar to it, instead of the
    full catalog. Call this first, with the user's question verbatim, when it's the discovery
    tool available to you."""
    return {"tables": _search_relevant_tables(question)}


@tool
def get_table_schema(table_name: str) -> dict:
    """Returns the full column list, primary key, and foreign keys for one gold table."""
    return _rag_tools.get_table_schema(table_name)


@tool
def run_sql(query: str) -> dict:
    """Executes a single read-only SELECT statement against the gold schema and returns the resulting rows."""
    return _rag_tools.run_sql(query)


class ToolRegistry:
    """An explicit tool registry: name -> (callable, version, owner) instead of a bare list, so
    tools can be looked up, versioned, and audited independently of any one agent."""

    def __init__(self) -> None:
        self._entries: dict[str, dict] = {}

    def register(self, langchain_tool, *, version: str = "1.0.0", owner: str = "finance-cockpit-team"):
        self._entries[langchain_tool.name] = {"tool": langchain_tool, "version": version, "owner": owner}
        return langchain_tool

    def get(self, name: str):
        return self._entries[name]["tool"]

    def list_entries(self) -> list[dict]:
        return [
            {"name": name, "version": e["version"], "owner": e["owner"], "description": e["tool"].description}
            for name, e in self._entries.items()
        ]

    def as_tool_list(self) -> list:
        return [e["tool"] for e in self._entries.values()]


def _pick_discovery_tool():
    """The enhancement condition: which table-discovery tool the agent actually gets.
    'auto' decides by catalog size; DEMO_DISCOVERY overrides it for a live walkthrough."""
    if DISCOVERY_MODE == "semantic":
        return search_relevant_tables, "1.0.0"
    if DISCOVERY_MODE == "exhaustive":
        return list_gold_tables, "1.0.0"
    if len(CATALOG) >= CATALOG_SIZE_THRESHOLD:
        return search_relevant_tables, "1.0.0"
    return list_gold_tables, "1.0.0"


DEFAULT_TOOL_REGISTRY = ToolRegistry()
_discovery_tool, _discovery_version = _pick_discovery_tool()
DEFAULT_TOOL_REGISTRY.register(_discovery_tool, version=_discovery_version)
DEFAULT_TOOL_REGISTRY.register(get_table_schema, version="1.0.0")
DEFAULT_TOOL_REGISTRY.register(run_sql, version="1.1.0")  # e.g. bumped when the row cap last changed


class DataProductRegistry:
    """Wraps rag_agent/schema_catalog.py's CATALOG as a governed data-product catalog: which
    data assets exist, who owns them, and their schema - what the tool registry's tools are
    actually allowed to touch. In a real AI Factory this is the piece that stops an agent from
    querying a data product nobody approved it to see."""

    def __init__(self, catalog: dict = CATALOG) -> None:
        self._catalog = catalog

    def list_products(self) -> list[dict]:
        return [
            {"name": t.name, "kind": t.kind, "owner": "finance-cockpit-team", "grain": t.grain}
            for t in self._catalog.values()
        ]

    def get_product(self, name: str):
        return self._catalog.get(name)


DEFAULT_DATA_REGISTRY = DataProductRegistry()
