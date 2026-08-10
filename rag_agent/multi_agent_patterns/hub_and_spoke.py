"""Hub-and-spoke pattern: a coordinator LLM call decides which specialist subagent to invoke,
in what order, and whether to re-invoke one - the routing intelligence lives in the hub at
runtime, not in fixed Python control flow. Compare to pipeline.py, where the sequence is
hardcoded and nothing decides anything.

The hub's own `messages` conversation only ever contains the original question and each
spoke's short text report - never the raw tool_use/tool_result traffic that happened inside a
spoke (that's all invisible, buried inside subagents.py's own mini-loops). That's the whole
point of the pattern: the hub reasons over compact reports, not a firehose of raw tool output.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import anthropic

from subagents import answer_agent, schema_agent, sql_agent

MODEL = "claude-sonnet-5"
MAX_ITERATIONS = 6

COORDINATOR_TOOLS = [
    {
        "name": "call_schema_agent",
        "description": (
            "Delegates to the schema specialist: figures out which gold tables are relevant "
            "to the question and returns a schema brief."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "call_sql_agent",
        "description": (
            "Delegates to the SQL specialist: writes and executes one query given the "
            "question and a schema brief, returns a result brief."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}, "schema_brief": {"type": "string"}},
            "required": ["question", "schema_brief"],
        },
    },
    {
        "name": "call_answer_agent",
        "description": (
            "Delegates to the answer specialist: synthesizes the final natural-language "
            "answer from a SQL result brief. Call this last - its output IS the final answer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}, "sql_result_brief": {"type": "string"}},
            "required": ["question", "sql_result_brief"],
        },
    },
]

_DISPATCH = {
    "call_schema_agent": lambda question: schema_agent(question),
    "call_sql_agent": lambda question, schema_brief: sql_agent(question, schema_brief),
    "call_answer_agent": lambda question, sql_result_brief: answer_agent(question, sql_result_brief),
}

COORDINATOR_SYSTEM = (
    "You coordinate 3 specialist subagents to answer a data question: call_schema_agent "
    "(finds relevant tables), call_sql_agent (writes+runs SQL given a schema brief), and "
    "call_answer_agent (writes the final answer given a SQL result brief). Decide the order "
    "yourself, and call a specialist more than once if needed - e.g. re-run call_sql_agent "
    "with a note about what went wrong if its result brief describes an error. Once you call "
    "call_answer_agent, treat its returned text as the final answer and relay it verbatim as "
    "your own final message."
)


def ask(question: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": question}]

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=COORDINATOR_SYSTEM,
            tools=COORDINATOR_TOOLS,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            report_text = _DISPATCH[block.name](**block.input)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": report_text})
        messages.append({"role": "user", "content": results})

    return "(coordinator exhausted its iteration budget without a final answer)"


if __name__ == "__main__":
    q = "Which department has the worst procurement savings this year?"
    print("Q:", q)
    print("A:", ask(q))
