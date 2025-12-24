import logging

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer


def configure_logging(log_level: str = "INFO", log_to_console: bool = False) -> None:
    shared_processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.contextvars.merge_contextvars,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]

    renderer = ConsoleRenderer() if log_to_console else JSONRenderer()
    structlog.configure(
        processors=shared_processors + [renderer],  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
