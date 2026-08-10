"""Pipeline pattern: a fixed sequence of subagents, each one's output feeding the next.

No central brain decides the order or re-routes anything at runtime - the sequence is
hardcoded here in Python, the same way stages in a data pipeline are wired. Compare to
hub_and_spoke.py, where an LLM decides at runtime which specialist to call and in what order.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from subagents import answer_agent, schema_agent, sql_agent


def ask(question: str) -> str:
    schema_brief = schema_agent(question)
    sql_brief = sql_agent(question, schema_brief)
    return answer_agent(question, sql_brief)


if __name__ == "__main__":
    q = "Which department has the worst procurement savings this year?"
    print("Q:", q)
    print("A:", ask(q))
