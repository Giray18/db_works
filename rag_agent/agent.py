"""Claude tool-use loop: takes a natural-language question, answers it grounded in the
gold schema catalog + live SQL results.

A manual loop rather than the SDK's beta Tool Runner, so the retry-on-SQL-error policy and
the "which tables were touched" citation tracking are both explicit and easy to reason about.
"""

import os

import anthropic

from tools import DISPATCH, TOOL_DEFINITIONS, ALLOWED_SCHEMA

MODEL = "claude-sonnet-5"
MAX_ITERATIONS = 6
MAX_SQL_RETRIES = 1

SYSTEM_PROMPT = f"""You answer natural-language questions about a city government's finance \
and procurement data warehouse, using the 3 tools available to you.

Rules:
- You only have SELECT access to the gold layer ({ALLOWED_SCHEMA}). You cannot see raw/bronze \
or intermediate/silver data, including full change history (e.g. cancelled or superseded \
contract versions) - if a question needs that, say so plainly instead of guessing.
- Always call list_gold_tables first if you haven't already this conversation, then \
get_table_schema for every table you plan to reference in SQL. Never guess column names.
- Some KPI/fact tables carry pre-computed percentage columns (e.g. savings_pct, \
realization_pct) that are only valid to read directly AT THEIR NATIVE GRAIN (one row per \
procedure/project). If aggregating across multiple rows (by department, year, etc.), \
recompute the ratio from the underlying SUM()s instead of averaging the percentage column - \
the table descriptions tell you which columns this applies to.
- If a run_sql call fails, you may fix the query and try again once. If it fails again, \
explain to the user what went wrong instead of retrying further.
- End every answer by naming which table(s) and column(s) the numbers came from.
"""


class SqlRetryExhausted(Exception):
    pass


def ask(question: str) -> dict:
    """Runs the tool-use loop for one question. Returns {"answer": str, "sources": list[tuple]}."""
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

            if block.name == "run_sql":
                sources.append(("run_sql", block.input.get("query")))
                if is_error:
                    sql_failures += 1
            elif block.name == "get_table_schema":
                sources.append(("get_table_schema", block.input.get("table_name")))

            if block.name == "run_sql" and sql_failures > MAX_SQL_RETRIES:
                result = {
                    "is_error": True,
                    "error": "SQL retry limit reached - explain the failure to the user instead of retrying again.",
                }

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": _stringify(result),
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return {
        "answer": "I couldn't reach a final answer within the allotted number of tool-use steps.",
        "sources": sources,
    }


def _stringify(result: dict) -> str:
    import json

    return json.dumps(result, default=str)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    q = "Which department has the worst procurement savings this year?"
    result = ask(q)
    print("Q:", q)
    print("A:", result["answer"])
    print("Sources:", result["sources"])
