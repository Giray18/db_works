"""Live demo entrypoint: ask a real question, watch it go through
registries -> gateway -> runtime -> tools -> observability, then print the answer plus the
trace of everything that happened.

Run:
    python demo.py                                  # default question, default model alias
    python demo.py "your question here"
    DEMO_MODEL_ALIAS=fast python demo.py "..."       # re-route through a different model,
                                                      # via the gateway, with no code change
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "rag_agent", ".env"))

from observability import clear_trace_log, read_traces  # noqa: E402
from registries import DEFAULT_DATA_REGISTRY, DEFAULT_TOOL_REGISTRY  # noqa: E402
from runtime import ask  # noqa: E402

DEFAULT_QUESTION = "Which department has the worst procurement savings this year?"


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    model_alias = os.environ.get("DEMO_MODEL_ALIAS", "default")

    print("=" * 72)
    print("AI FACTORY DEMO - Finance Cockpit Q&A")
    print("=" * 72)

    print("\n[Registries] Data products available:")
    for p in DEFAULT_DATA_REGISTRY.list_products():
        print(f"  - {p['name']:<32} ({p['kind']}, owner={p['owner']})")

    print("\n[Registries] Tools available:")
    for t in DEFAULT_TOOL_REGISTRY.list_entries():
        print(f"  - {t['name']:<20} v{t['version']:<8} owner={t['owner']}")

    print(f"\n[Gateway] Routing this session through alias '{model_alias}'")

    clear_trace_log()
    print(f"\n[Runtime] Question: {question}")
    result = ask(question, model_alias=model_alias)

    print("\n[Runtime] Answer:")
    print(result["answer"])

    print("\n[Observability] Trace of this run:")
    for record in read_traces():
        print(f"  {record}")


if __name__ == "__main__":
    main()
