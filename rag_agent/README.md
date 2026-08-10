# Finance Cockpit Q&A — agentic natural-language query over the gold schema

A local Streamlit app that answers plain-English questions about the finance/procurement gold
star schema (`workspace.dev_finance_cockpit_gold`, 15 tables) live, by giving Claude 3 tools
and letting it decide what to look up and what SQL to run — rather than relying on a
pre-built Power BI visual for every possible question.

## Why "agentic RAG" without a vector database

Classic RAG earns its complexity when you have too much text to fit in a context window, so
you embed and index it. That's not the situation here — the full schema (15 tables' worth of
columns, types, keys, FK relationships, business notes) is a few thousand tokens, comfortably
smaller than a single embedding call's overhead. Standing up a vector index for that would
solve a problem this project doesn't have, and would add a second copy of the schema that can
silently drift from the real pipeline.

Instead, the agent retrieves grounding information via **tool calls**:
1. **Schema retrieval** — `list_gold_tables()` / `get_table_schema()` return real, current
   metadata from `schema_catalog.py` (hand-maintained, sourced from the `comment=` strings in
   `transformations/*.py` plus real column types from `information_schema.columns`).
2. **Data retrieval** — `run_sql()` executes a live, grounded SQL query against the actual
   gold tables.

The final answer is generated from those two retrieval steps — that's the "generation grounded
in retrieved context" definition of RAG, just with schema-catalog + SQL as the retrieval
mechanism instead of embeddings + similarity search. At 15 tables, that's the right-sized
choice, not a shortcut.

## Architecture

```
Streamlit (app.py)
   -> agent.py: Claude (Sonnet 5) tool-use loop
        -> list_gold_tables() / get_table_schema()   [schema_catalog.py, no network call]
        -> run_sql(query)                            [tools.py validates -> db.py ->
                                                        databricks-sql-connector -> SQL warehouse]
   -> answer + "Sourced from" citation
```

`rag_agent/` is a standalone consumer of the existing pipeline output, structurally parallel to
`pbi/` — it does not add any bundle resource and does not touch `transformations/` or
`resources/*.yml`.

## Safety model — be honest about what's actually enforced

`run_sql` is SELECT-only, scoped to `workspace.dev_finance_cockpit_gold`, with a 500-row cap
and a 30s client-side timeout (see `tools.py`). That's an **application-level** control.

The originally-planned second layer — a Unity Catalog grant restricting the connecting
principal to `SELECT` on the gold schema only, with no access to bronze/silver — is not
meaningful as configured today: this app authenticates as the same account
(`cihan.giray.oner@htecgroup.com`) that owns and administers the whole workspace, so a UC
grant on that identity restricts nothing. A UC-level boundary only does real work if this ever
runs under a **separate service principal** created specifically for it, granted `USE CATALOG`
+ `USE SCHEMA` + `SELECT` on the gold schema and nothing else. That's a reasonable hardening
step before giving anyone else access to this app, but it's not applied by default here — set
it up if/when this stops being a single-user local tool.

## Setup

1. `pip install -r requirements.txt` (already done in the repo's `.venv` — see the repo root).
2. `cp .env.example .env` and fill in `ANTHROPIC_API_KEY` and `DATABRICKS_HTTP_PATH` (get the
   warehouse ID from `databricks warehouses list`, or Databricks UI → SQL Warehouses →
   Connection Details). `DATABRICKS_SERVER_HOSTNAME` and `DATABRICKS_CONFIG_PROFILE` are
   already filled in to match this workspace.
3. Confirm `databricks auth login` has been run for that profile (it has, if `databricks
   bundle deploy` already works in this repo) — `db.py` reuses that OAuth session, no PAT
   needed.

## Running it

```bash
streamlit run app.py
```

Or test the agent loop directly without the UI:

```bash
python agent.py
```

## Maintaining `schema_catalog.py`

This file is hand-maintained, not generated. **Any column or FK change in
`transformations/*.py` must be mirrored here in the same change**, or the agent's tools will
describe a schema that no longer matches the real pipeline. Column types were sourced once
from `information_schema.columns` (Spark infers types at runtime, so they're not visible in
the Python source) — re-check them if a table's column types change.

## Known limitations (v1)

- **Single-shot Q&A** — no conversation memory between questions yet. Each question re-runs
  the tool loop from scratch.
- **No year column on `mv_procurement_savings_kpi` / `fact_procurement_performance`** — a
  "this year" question against procurement savings needs a join through `dim_project` (via
  `project_id`) or a `YEAR()` on `dim_procedure.selection_decision_date`; the schema catalog's
  descriptions flag this so the agent knows to join rather than guess.
- **Cost is unmeasured** — run a handful of real questions and check the Anthropic Console's
  usage dashboard for an actual per-question cost baseline before relying on this heavily.
