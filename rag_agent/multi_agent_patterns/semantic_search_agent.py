"""4th comparison variant: same single-loop shape as ../agent.py, but table discovery uses
real vector semantic search (search_relevant_tables - cosine similarity over embeddings built
from each table's definition + live sample rows) instead of list_gold_tables()'s exhaustive
dump of all 15 tables.

Is this actually a good idea at 15 tables? No - see ../schema_catalog.py's docstring and
README.md in this folder. "Dump all 15 and let the LLM pick" is simpler and just as accurate
at this scale. This variant exists so you can see what semantic search over a schema catalog
looks like in code, for when the catalog is too large to just show the model everything.

Requires table_index.json to exist first: run `python build_table_index.py`.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import anthropic

from semantic_search import search_relevant_tables
from tools import ALLOWED_SCHEMA
from tools import DISPATCH as _BASE_DISPATCH
from tools import TOOL_DEFINITIONS as _BASE_TOOLS

MODEL = "claude-sonnet-5"
MAX_ITERATIONS = 6
MAX_SQL_RETRIES = 1
TOP_K = 4

SEARCH_TOOL_DEFINITION = {
    "name": "search_relevant_tables",
    "description": (
        "Semantically searches the gold schema's table catalog (definitions + live sample "
        "rows, embedded offline) and returns the tables most relevant to the question, ranked "
        "by similarity. Use this INSTEAD of assuming you already know which tables are "
        "relevant - call it first, with the user's question verbatim."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"question": {"type": "string", "description": "The user's original question, verbatim."}},
        "required": ["question"],
    },
}

# Same 3 tools as ../agent.py, except list_gold_tables is replaced by semantic search.
TOOL_DEFINITIONS = [SEARCH_TOOL_DEFINITION] + [t for t in _BASE_TOOLS if t["name"] != "list_gold_tables"]
DISPATCH = {name: fn for name, fn in _BASE_DISPATCH.items() if name != "list_gold_tables"}
DISPATCH["search_relevant_tables"] = lambda question: {"tables": search_relevant_tables(question, top_k=TOP_K)}

SYSTEM_PROMPT = f"""You answer natural-language questions about a city government's finance \
and procurement data warehouse, using the tools available to you.

Rules:
- You only have SELECT access to the gold layer ({ALLOWED_SCHEMA}). You cannot see raw/bronze \
or intermediate/silver data, including full change history - if a question needs that, say so \
plainly instead of guessing.
- Always call search_relevant_tables first, with the user's question verbatim, to find which \
tables are likely relevant - do not assume you already know. Then call get_table_schema for \
every table it returns before writing SQL. Never guess column names.
- If a run_sql call fails, you may fix the query and try again once. If it fails again, \
explain to the user what went wrong instead of retrying further.
- End every answer by naming which table(s) and column(s) the numbers came from.
"""


def ask(question: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": question}]
    sources: list[tuple[str, str | None]] = []
    sql_failures = 0

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            answer = "".join(block.text for block in response.content if block.type == "text")
            return {"answer": answer, "sources": sources}

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = DISPATCH[block.name](**block.input)
            is_error = bool(result.get("is_error"))

            if block.name == "search_relevant_tables":
                sources.append(("search_relevant_tables", json.dumps(result.get("tables", []))))
            elif block.name == "get_table_schema":
                sources.append(("get_table_schema", block.input.get("table_name")))
            elif block.name == "run_sql":
                sources.append(("run_sql", block.input.get("query")))
                if is_error:
                    sql_failures += 1
                if sql_failures > MAX_SQL_RETRIES:
                    result = {
                        "is_error": True,
                        "error": "SQL retry limit reached - explain the failure to the user instead of retrying again.",
                    }
                    is_error = True

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return {
        "answer": "I couldn't reach a final answer within the allotted number of tool-use steps.",
        "sources": sources,
    }


if __name__ == "__main__":
    q = "Which department has the worst procurement savings this year?"
    result = ask(q)
    print("Q:", q)
    print("A:", result["answer"])
    print("Sources:", result["sources"])
