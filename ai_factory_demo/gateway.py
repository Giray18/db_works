"""Gateway pillar: a single choke point every model call passes through, so model routing,
per-session request budgets, and provider/model swaps happen in one place instead of scattered
through agent or business code.

Implemented as LangChain 1.x middleware via @wrap_model_call - the SDK's real extension point
for intercepting every model call the runtime makes, not a bespoke wrapper bolted on the side.
LangChain also ships production-grade equivalents of the policy piece here
(ModelCallLimitMiddleware, ModelFallbackMiddleware in langchain.agents.middleware) - this one
is hand-rolled so the routing decision and the policy check are both visible in one place for
the demo.
"""

import os
import time
from dataclasses import dataclass, field

from langchain.agents.middleware import wrap_model_call
from langchain_anthropic import ChatAnthropic

# Logical alias -> real model id. Swapping this mapping changes which model actually answers
# session-wide, without touching runtime.py or any agent/business logic - the whole point of a
# gateway: model choice is a platform decision, not something baked into agent code.
MODEL_ALIASES = {
    "default": "claude-sonnet-5",
    "fast": "claude-haiku-4-5-20251001",
    "accurate": "claude-opus-5",
}

MAX_REQUESTS_PER_SESSION = 20  # a real gateway would also do per-tenant quotas, cost caps, etc.


class RequestBudgetExceeded(Exception):
    pass


class UnknownModelAlias(Exception):
    pass


@dataclass
class _GatewayState:
    request_count: int = 0
    log: list[dict] = field(default_factory=list)


_state = _GatewayState()


def build_gateway_middleware(alias: str = "default"):
    """Returns middleware that routes every model call in this session to `alias`'s real
    model, enforces the request budget, and records a routing decision per call."""
    if alias not in MODEL_ALIASES:
        raise UnknownModelAlias(f"Unknown model alias '{alias}'. Known aliases: {sorted(MODEL_ALIASES)}")
    real_model_id = MODEL_ALIASES[alias]

    @wrap_model_call
    def gateway(request, handler):
        _state.request_count += 1
        if _state.request_count > MAX_REQUESTS_PER_SESSION:
            raise RequestBudgetExceeded(
                f"Gateway policy: session request budget ({MAX_REQUESTS_PER_SESSION}) exceeded."
            )

        start = time.time()
        request.model = ChatAnthropic(model=real_model_id, api_key=os.environ["ANTHROPIC_API_KEY"])
        response = handler(request)
        elapsed = time.time() - start

        _state.log.append(
            {
                "request_number": _state.request_count,
                "alias": alias,
                "routed_to_model": real_model_id,
                "elapsed_s": round(elapsed, 2),
            }
        )
        return response

    return gateway


def get_gateway_log() -> list[dict]:
    return list(_state.log)


def reset_gateway_state() -> None:
    _state.request_count = 0
    _state.log.clear()
