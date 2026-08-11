# AI Factory tooling demo — gateway, runtime, registries, observability (LangChain)

A working demonstration of the four "AI Factory" tooling pillars, built on LangChain 1.x, using
the finance-cockpit Q&A agent from `../rag_agent/` as the real running example instead of a
toy. Nothing here duplicates that agent's logic — `registries.py` wraps `../rag_agent/tools.py`
and `../rag_agent/schema_catalog.py` directly.

## Why this dataset, not a generic example

A business audience is more convinced by "here's our real finance/procurement data, here's a
real question, here's the real answer, and here's the platform tooling that made it governed
and observable" than by a synthetic hello-world. This demo answers the same kind of question
`../rag_agent/agent.py` does, but executed through LangChain's agent runtime instead of a
hand-rolled Anthropic tool-use loop, with each platform pillar visibly separated in the code.

## The four pillars, and where they live

| Pillar | File | What it actually does |
|---|---|---|
| **Registries** | `registries.py` | `ToolRegistry` — versioned, owned catalog of the 3 callable tools (one of which, table discovery, is itself picked by a condition — see below). `DataProductRegistry` — wraps the 15-gold-table catalog as a governed data-asset registry. Both are what an agent is *allowed* to use, decided here, not hardcoded per-agent. |
| **Gateway** | `gateway.py` | `MODEL_ALIASES` maps a logical name (`"default"`, `"fast"`, `"accurate"`) to a real model id. All model calls route through this middleware, which also enforces a per-session request budget (`MAX_REQUESTS_PER_SESSION`). Swap the alias mapping and every agent using this gateway changes model without a code change. |
| **Runtime** | `runtime.py` | LangChain 1.x's `create_agent()` — compiles the tool-calling loop into a LangGraph state machine. This is the actual execution engine; gateway and observability attach to it as middleware, registries supply its tools. |
| **Observability** | `observability.py` | `@wrap_model_call` / `@wrap_tool_call` middleware logging every model and tool call (model used, tokens, latency, tool name/input) to `traces.jsonl`. In a production AI Factory this is what would feed LangSmith or an equivalent; here it's a plain file so it's inspectable with nothing else running. |

Middleware is the load-bearing idea connecting all of this: `gateway.py` and
`observability.py` both hook the exact same LangChain 1.x extension points
(`wrap_model_call`/`wrap_tool_call`) for two unrelated concerns — policy vs. logging — without
either knowing the other exists. That's the platform argument in one sentence: cross-cutting
concerns (auth, cost control, tracing, compliance) attach to the runtime independently of
agent-specific logic.

## What's genuinely functional vs. illustrative

Everything above actually runs — this isn't a mockup. What's deliberately kept simple for a
one-day build, and worth saying so plainly if asked in the meeting:

- **Gateway's policy** is one request-count budget. Real gateway products (or LangChain's own
  `ModelCallLimitMiddleware`, `ModelFallbackMiddleware` in `langchain.agents.middleware`) add
  per-tenant quotas, cost-based budgets, and automatic provider fallback — same extension
  point, more policy.
- **Observability** writes to a local JSONL file, not a real tracing backend. The middleware
  hooks are the same ones a LangSmith integration would use — swapping the destination is a
  `_write()` change, not an architecture change.
- **Registries** are in-process Python objects, not a networked service other teams' agents
  could query. The interface (`list_entries()`, `get()`, `list_products()`) is what a real
  registry service would expose over an API.

## Semantic table discovery (registries deciding between two tools)

`rag_agent/multi_agent_patterns/semantic_search_agent.py` already showed what real semantic
table search looks like — embed the question, compare it against pre-computed table embeddings,
return the closest matches instead of `list_gold_tables()`'s exhaustive dump. That version is
written directly against the `anthropic` SDK and stores its embeddings in a hand-rolled JSON
file with a manual cosine-similarity loop. `semantic_index.py` ports the same idea to a
LangChain `@tool` (`search_relevant_tables` in `registries.py`), backed by a persistent
**Chroma** collection (`chroma_db/`) instead — Chroma owns the embedding calls (same
`all-MiniLM-L6-v2` model), the on-disk index, and the nearest-neighbor search, so there's no
hand-rolled similarity math here.

The registry doesn't ship both discovery tools at once — it picks one, via
`_pick_discovery_tool()`:

- **`CATALOG_SIZE_THRESHOLD = 25`** — below this many gold tables, `list_gold_tables` is
  cheaper and just as accurate (this is `multi_agent_patterns/README.md`'s own finding, at the
  current 15-table size); at or above it, semantic search keeps the discovery step's context
  bounded instead of growing with every table added to the schema.
- **`MIN_SIMILARITY = 0.2`** in `semantic_index.py` — a second filter *inside* the semantic
  search itself: a top-k match that's still a weak match gets dropped rather than handed to the
  agent as if it were relevant. Returning fewer than `top_k` results, or zero, is correct when
  nothing actually matches.
- **`DEMO_DISCOVERY`** env var overrides the size decision for a live walkthrough — `semantic`
  or `exhaustive` force one or the other regardless of catalog size; unset (`auto`) uses the
  threshold.

At the repo's real 15-table catalog, `auto` always resolves to `list_gold_tables` — the point
being demonstrated is the *condition*, not that semantic search is secretly better here.

```bash
python semantic_index.py                          # builds/updates the chroma_db/ collection (needed once for the semantic path)
DEMO_DISCOVERY=semantic python demo.py "..."       # force the semantic-search discovery tool
DEMO_DISCOVERY=exhaustive python demo.py "..."     # force the full-catalog dump
```

## Running it

```bash
pip install -r requirements.txt
python demo.py
python demo.py "Which suppliers win the most bids?"
DEMO_MODEL_ALIAS=fast python demo.py "..."   # re-route through claude-haiku-4-5, no code change
```

Uses the same `ANTHROPIC_API_KEY` and Databricks connection already configured in
`../rag_agent/.env` — nothing new to set up if `rag_agent/` is already working.

Each run prints, in order: the registries (what's available), the gateway routing decision,
the question and answer, and the full observability trace of every model/tool call that
happened — the whole story end to end for a live walkthrough.
