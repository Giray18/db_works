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
| **Registries** | `registries.py` | `ToolRegistry` — versioned, owned catalog of the 3 callable tools. `DataProductRegistry` — wraps the 15-gold-table catalog as a governed data-asset registry. Both are what an agent is *allowed* to use, decided here, not hardcoded per-agent. |
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
