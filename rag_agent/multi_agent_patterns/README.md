# Multi-agent patterns — training/comparison folder

This folder does not change or depend on anything having been broken in `../agent.py` or
`../app.py` — it's a separate exploration of two multi-agent architectures for the same
problem (answer a data question over the gold schema), reusing `../tools.py`, `../db.py`, and
`../schema_catalog.py` as-is. Nothing here is wired into the Streamlit app.

## The four architectures, compared

**1. Single agent, one shared loop** (`../agent.py`, for reference) — one Claude conversation
that calls `list_gold_tables`/`get_table_schema`/`run_sql` directly as tools. Every tool call
and its full raw result sits in the one growing `messages` list Claude sees from start to
finish.

```
User -> [Claude + tools: list_gold_tables, get_table_schema, run_sql] -> Answer
         (one conversation, one shared context, sees every raw tool result)
```

**2. Pipeline** (`pipeline.py`) — a fixed sequence of three subagents. Python code decides the
order; nothing is dynamic.

```
question -> schema_agent -> schema_brief -> sql_agent -> sql_result_brief -> answer_agent -> answer
            (LLM call #1)                   (LLM call #2)                    (LLM call #3)
```

**3. Hub-and-spoke** (`hub_and_spoke.py`) — a coordinator LLM decides at runtime which
specialist to call, in what order, and whether to re-invoke one (e.g. re-run the SQL spoke
after a failure). The specialists (`subagents.py`) are the same three functions pipeline.py
uses, just invoked dynamically instead of hardcoded in sequence.

```
                    +--> call_schema_agent --> schema_agent (LLM call)
question -> [Coordinator LLM] --> call_sql_agent --> sql_agent (LLM call)
                    +--> call_answer_agent --> answer_agent (LLM call)
            (decides order/retries itself, one call per decision)
```

**4. Single agent + real semantic table search** (`semantic_search_agent.py`) — the answer to
"are we doing semantic search to pick which table to query?" (we weren't, everywhere else in
this project). Same loop shape as `../agent.py`, but `list_gold_tables()`'s exhaustive dump of
all 15 tables is replaced with `search_relevant_tables()`: a local `sentence-transformers`
model embeds the question and compares it by cosine similarity against pre-computed embeddings
of each table (built from its `schema_catalog.py` definition **plus a few live sample rows**,
so the vectors capture actual data content, not just column names).

```
question -> [Claude] -> search_relevant_tables(question)
                            -> embed(question) -> cosine similarity vs. 15 pre-computed
                               table embeddings -> top-k table names
                         -> get_table_schema (for the retrieved tables) -> run_sql -> Answer
```

Build the index once (and again whenever `schema_catalog.py` or the underlying data changes):

```bash
python build_table_index.py    # embeds all 15 tables + sample rows -> table_index.json
python semantic_search.py "which department has the worst savings"   # sanity-check retrieval alone, no LLM call
python semantic_search_agent.py
```

**Is this actually worth it at 15 tables? No** — that's the point of including it. `compare.py`
lets you watch variant 1 and variant 4 answer the same question and see that vector search
doesn't change the outcome here; it just adds an embedding step and a model download. Semantic
search over a table catalog earns its cost when the catalog is too large to hand the LLM in
full (hundreds/thousands of tables) - the exhaustive-dump approach the rest of this project
uses is the *simpler* choice at 15 tables, not a shortcut that's missing something.

## The property that actually matters here: context isolation

The real difference between "calling a Python function" and "calling a subagent" is that a
subagent gets its **own fresh conversation** — its own `messages` list, its own system prompt,
its own narrow toolset — and only a short text report crosses back to whoever called it.
`subagents.py`'s `sql_agent()`, for example, never sees the raw JSON `get_table_schema()`
returned to `schema_agent()` — it only sees `schema_agent()`'s prose summary of it. Compare
that to `../agent.py`, where the single loop's `messages` list accumulates every tool call and
every raw row of every query result, all in one context Claude re-reads on every turn.

This is a real tradeoff, not a strict upgrade:
- **Isolation helps** when a subtask's raw working detail (e.g. `list_gold_tables`'s full
  15-table dump) would just be noise to the next stage — the report format lets you filter
  down to what actually matters.
- **Isolation hurts** when something subtle gets lost in translation — `sql_agent()` only knows
  what `schema_agent()`'s prose said, not the verbatim column types and FK detail a single
  shared context would still have. If a question needs a precise column detail that didn't
  make it into the brief, this is where it breaks.
- **Isolation costs more** — pipeline and hub-and-spoke both make 3+ separate LLM calls per
  question (each re-paying system-prompt tokens), versus the single agent's one conversation
  making several tool calls within it. Run `compare.py` and check the Anthropic Console for a
  real before/after on latency and token cost.

## Running

```bash
pip install -r requirements.txt   # sentence-transformers + numpy, only needed for variant 4
python build_table_index.py       # one-time: builds table_index.json for variant 4
python pipeline.py                # fixed sequence, one hardcoded question
python hub_and_spoke.py           # LLM-coordinated, same hardcoded question
python semantic_search_agent.py   # single agent + vector table search
python compare.py                 # runs the same question through all 4 and times each
```

All four need `ANTHROPIC_API_KEY` and the Databricks connection vars already set up in
`../.env` (see `../README.md`). Variant 4 additionally needs `table_index.json` built first,
and downloads a small (~90MB) embedding model the first time it runs.
