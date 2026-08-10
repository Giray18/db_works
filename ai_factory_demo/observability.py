"""Observability pillar: every model call and every tool call the runtime makes gets a
structured trace record - what was called, with what, how long it took, and what came back -
written to a local JSONL log. In a real AI Factory this is what LangSmith (or an equivalent
tracing backend) would ingest; here it's a plain file so the whole pillar is inspectable with
no extra service running.

Implemented via the same LangChain 1.x middleware extension points gateway.py uses
(@wrap_model_call, @wrap_tool_call), applied to a different concern - proof that multiple
middlewares can independently watch the same calls: gateway enforces policy, this just
records, neither has to know the other exists.
"""

import json
import os
import time
from datetime import datetime, timezone

from langchain.agents.middleware import wrap_model_call, wrap_tool_call

TRACE_LOG_PATH = os.path.join(os.path.dirname(__file__), "traces.jsonl")


def _write(record: dict) -> None:
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with open(TRACE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


@wrap_model_call
def trace_model_calls(request, handler):
    start = time.time()
    response = handler(request)
    elapsed = time.time() - start

    result = response.result if hasattr(response, "result") else response
    last_message = result[-1] if isinstance(result, list) else result
    usage = getattr(last_message, "usage_metadata", None) or {}

    _write(
        {
            "event": "model_call",
            "model": getattr(request.model, "model", str(request.model)),
            "elapsed_s": round(elapsed, 2),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }
    )
    return response


@wrap_tool_call
def trace_tool_calls(request, handler):
    start = time.time()
    response = handler(request)
    elapsed = time.time() - start

    _write(
        {
            "event": "tool_call",
            "tool": request.tool_call.get("name"),
            "input": request.tool_call.get("args"),
            "elapsed_s": round(elapsed, 2),
        }
    )
    return response


def clear_trace_log() -> None:
    open(TRACE_LOG_PATH, "w", encoding="utf-8").close()


def read_traces() -> list[dict]:
    if not os.path.exists(TRACE_LOG_PATH):
        return []
    with open(TRACE_LOG_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
