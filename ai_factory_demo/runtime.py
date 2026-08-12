"""Runtime pillar: the component that actually executes an agent - the loop deciding when to
call a model, when to call a tool, and when to stop. Built on LangChain 1.x's create_agent(),
which compiles to a LangGraph state machine; gateway.py and observability.py plug into it as
middleware, and registries.py supplies the tools it's allowed to call.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag_agent"))

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic

from gateway import build_gateway_middleware
from observability import trace_model_calls, trace_tool_calls
from registries import DEFAULT_TOOL_REGISTRY
from tools import ALLOWED_SCHEMA

SYSTEM_PROMPT = f"""You answer natural-language questions about a city government's finance \
and procurement data warehouse, using the tools available to you.

Rules:
- You only have SELECT access to the gold layer ({ALLOWED_SCHEMA}).
- Always start by calling whichever table-discovery tool you have - list_gold_tables (full \
catalog) or search_relevant_tables (pass the user's question verbatim) - to find which tables \
are relevant. Never assume you already know. Then call get_table_schema for every table it \
returns, before writing SQL. Never guess column names.
- End every answer by naming which table(s) and column(s) the numbers came from.
"""


def build_runtime(model_alias: str = "default"):
    """Assembles the runtime: a compiled agent graph wired to the gateway (model routing +
    policy), the tool registry (what it's allowed to call), and observability (full trace).

    The `model=` argument below is the nominal/default model used to compile the graph; the
    gateway middleware overwrites it on every actual call, per `model_alias` - that's the
    gateway doing its job, not a redundant configuration.
    """
    nominal_model = ChatAnthropic(model="claude-sonnet-5", api_key=os.environ["ANTHROPIC_API_KEY"])
    return create_agent(
        model=nominal_model,
        tools=DEFAULT_TOOL_REGISTRY.as_tool_list(),
        system_prompt=SYSTEM_PROMPT,
        middleware=[build_gateway_middleware(model_alias), trace_model_calls, trace_tool_calls],
    )


def ask(question: str, model_alias: str = "default") -> dict:
    agent = build_runtime(model_alias)
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    final_message = result["messages"][-1]
    answer = final_message.content if hasattr(final_message, "content") else str(final_message)
    return {"answer": answer, "messages": result["messages"]}
