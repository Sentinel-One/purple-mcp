"""Observability module for optional Pydantic Logfire instrumentation.

This module provides conditional initialization of Pydantic Logfire based on
environment configuration. If PURPLEMCP_LOGFIRE_TOKEN is set, the module will:
- Configure Logfire with the provided token
- Instrument HTTPX client for HTTP request tracing
- Instrument Starlette/FastMCP server for request/response tracing
- Integrate standard library logging with Logfire

If the token is not set, all functions become no-ops and the application
runs without any observability overhead.
"""

from __future__ import annotations

import logging

from starlette.applications import Starlette

logger = logging.getLogger(__name__)

# Track whether logfire has been initialized
_logfire_initialized = False


def initialize_logfire() -> bool:
    """Initialize Pydantic Logfire if configured via environment variables.

    This function checks if PURPLEMCP_LOGFIRE_TOKEN is set in the configuration.
    If present, it configures Logfire with that token and sets up instrumentation
    for HTTPX and standard library logging.

    Returns:
        bool: True if logfire was successfully initialized, False otherwise
    """
    global _logfire_initialized

    if _logfire_initialized:
        logger.debug("Logfire already initialized, skipping")
        return True

    try:
        from purple_mcp.config import get_settings

        settings = get_settings()

        if not settings.logfire_token:
            logger.info("Logfire token not configured, observability disabled")
            return False

        # Import logfire only if we need it
        import logfire

        # Configure logfire with the token
        logfire.configure(token=settings.logfire_token)

        # Instrument HTTPX for HTTP client tracing
        logfire.instrument_httpx()

        # Integrate standard library logging with Logfire by adding handler directly
        # to the root logger. This allows the CLI's _setup_logging() to still control
        # the log level via subsequent basicConfig(level=...) calls.
        root_logger = logging.getLogger()
        root_logger.addHandler(logfire.LogfireLoggingHandler())

        _logfire_initialized = True
        logger.info("Logfire initialized successfully")
        return True

    except ImportError:
        logger.warning("Logfire package not installed, observability disabled")
        return False
    except Exception:
        logger.exception("Failed to initialize Logfire")
        return False


def instrument_starlette_app(app: Starlette) -> None:
    """Instrument a Starlette application with Logfire if enabled.

    This should be called after the Starlette/FastMCP app is created but before
    it starts serving requests.

    To exclude specific URLs from tracing (e.g., health check endpoints), set the
    OTEL_PYTHON_STARLETTE_EXCLUDED_URLS environment variable to a comma-delimited
    list of regex patterns. For example:
        export OTEL_PYTHON_STARLETTE_EXCLUDED_URLS="health,metrics"

    Args:
        app: The Starlette application instance to instrument
    """
    if not _logfire_initialized:
        logger.debug("Logfire not initialized, skipping Starlette instrumentation")
        return

    try:
        import logfire

        logfire.instrument_starlette(app)
        logger.info("Starlette instrumentation enabled")
    except Exception:
        logger.exception("Failed to instrument Starlette with Logfire")
