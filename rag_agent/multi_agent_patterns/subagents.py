"""Three narrow subagents shared by both multi-agent patterns in this folder.

The property that makes these "subagents" rather than just Python functions: each one gets
its own fresh `messages` list and its own system prompt. Nothing from the caller's
conversation leaks in, and nothing but a compact text report leaks back out - contrast this
with rag_agent/agent.py's single loop, where every tool call and every raw row of SQL output
sits directly in the one shared, ever-growing conversation Claude sees from start to finish.

That isolation is a real tradeoff, not a free upgrade: sql_agent() below only ever sees
schema_agent()'s prose summary, never the verbatim get_table_schema() JSON - so it's possible
for something to get lost in that handoff that a single shared context wouldn't have dropped.
Watch for that if you feed it a question that needs a subtle column detail.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic

from tools import DISPATCH, TOOL_DEFINITIONS

MODEL = "claude-sonnet-5"
_TOOLS_BY_NAME = {t["name"]: t for t in TOOL_DEFINITIONS}


def _run_mini_agent(system_prompt: str, user_message: str, tool_names: list[str], max_iterations: int = 4) -> str:
    """The building block every subagent below is made of: a small, self-contained tool-use
    loop that always ends in plain text, never in raw tool output."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    tools = [_TOOLS_BY_NAME[name] for name in tool_names]
    messages = [{"role": "user", "content": user_message}]

    for _ in range(max_iterations):
        response = client.messages.create(
            model=MODEL, max_tokens=1500, system=system_prompt, tools=tools, messages=messages
        )
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = DISPATCH[block.name](**block.input)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                    "is_error": bool(result.get("is_error")),
                }
            )
        messages.append({"role": "user", "content": results})

    return "(subagent exhausted its iteration budget without a final answer)"


def schema_agent(question: str) -> str:
    """Spoke #1: identifies which gold tables are relevant and reports back a prose summary -
    not the raw tool JSON - since prose is what the next subagent should be handed."""
    system = (
        "You investigate which gold-layer tables are relevant to a user's data question. "
        "Call list_gold_tables, then get_table_schema for every table that looks relevant. "
        "Respond with a short plain-text brief: which tables, their key columns, and any join "
        "path needed between them to answer the question. Do not write SQL."
    )
    return _run_mini_agent(system, question, ["list_gold_tables", "get_table_schema"])


def sql_agent(question: str, schema_brief: str) -> str:
    """Spoke #2: given the question and spoke #1's prose brief (not its raw tool calls), writes
    and executes one query, retrying once on failure."""
    system = (
        "You write and execute exactly one SQL query against the gold schema to answer the "
        "user's question, using run_sql. You may retry once if the query errors. Respond with "
        "a short plain-text summary of the query you ran and the rows it returned - or the "
        "error, if it still failed after one retry."
    )
    user_message = f"Question: {question}\n\nRelevant schema:\n{schema_brief}"
    return _run_mini_agent(system, user_message, ["run_sql"])


def answer_agent(question: str, sql_result_brief: str) -> str:
    """Spoke #3: no tools at all - pure synthesis from what the previous subagents reported."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system = (
        "You write the final answer to the user's question in plain English, using only the "
        "SQL result summary you're given. Cite which table(s)/column(s) the numbers came from. "
        "If the summary describes an error, explain the limitation honestly instead of guessing."
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": f"Question: {question}\n\nSQL result:\n{sql_result_brief}"}],
    )
    return "".join(b.text for b in response.content if b.type == "text")
