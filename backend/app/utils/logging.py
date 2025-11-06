"""
Structured logging configuration using structlog.
Provides consistent, parseable logs for observability.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import LoggerFactory

from app.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    Uses structlog with JSON formatting for production.
    """
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add JSON renderer for production, console for development
    if settings.env == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


def redact_pii(data: dict) -> dict:
    """
    Redact PII from logging data.

    Args:
        data: Dictionary potentially containing PII

    Returns:
        Dictionary with PII fields redacted
    """
    pii_fields = [
        "email",
        "phone",
        "address",
        "ssn",
        "date_of_birth",
        "full_name",
        "password",
        "token",
        "api_key"
    ]

    redacted = data.copy()
    for field in pii_fields:
        if field in redacted:
            redacted[field] = "***REDACTED***"

    return redacted


# Default logger instance for convenience
logger = get_logger(__name__)
