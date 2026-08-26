from __future__ import annotations

from contextvars import ContextVar

request_metrics_var: ContextVar[dict[str, float | int | str]] = ContextVar(
    "request_metrics",
    default={},
)
