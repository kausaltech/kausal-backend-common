from __future__ import annotations

_otel_initialized = False


def init_telemetry() -> None:
    from kausal_common.deployment import env_bool

    from .metrics import init_metrics
    from .traces import init_traces

    global _otel_initialized  # noqa: PLW0603

    if _otel_initialized:
        return

    init_traces()
    if not env_bool('OTEL_METRICS_WORKER_PROCESS_ONLY', default=False):
        init_metrics()

    _otel_initialized = True
