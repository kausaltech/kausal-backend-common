from __future__ import annotations

_otel_initialized = False



def init_telemetry() -> None:
    from .metrics import init_metrics
    from .traces import init_traces

    global _otel_initialized  # noqa: PLW0603

    if _otel_initialized:
        return

    init_traces()
    init_metrics()

    _otel_initialized = True
