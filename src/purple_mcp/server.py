"""Purple MCP server implementation.

This module boots and exposes the FastMCP server that powers the Purple
MCP service.  Importing the module instantiates the server, registers the
first-party tools, and makes the ASGI application available so that the
same code path can be reused by the CLI, tests, and deployment wsgi/uvicorn
runners.

Key Components:
    - app (fastmcp.FastMCP): Core MCP server instance with the `purple_ai`
      and `powerquery` tools pre-registered.
    - health_check(): Lightweight `/health` endpoint used by load-balancers
      and readiness probes.
    - http_app (Starlette): ASGI application created from `app`, using the
      Server-Sent Events (SSE) transport.

Usage:
    Typical CLI entry-points simply import the module to start the stdio
    server:

    ```python
    # run_stdio.py
    from purple_mcp.server import app  # noqa: F401 - side-effects start server
    ```

    When running under an HTTP server such as Uvicorn:

    ```bash
    uvicorn purple_mcp.server:http_app --host 0.0.0.0 --port 8000
    ```

Architecture:
    The design purposefully keeps the side-effects contained in the module
    so higher-level wrappers stay minimal.  The tools directory is imported
    eagerly to guarantee they are registered exactly once.  Transport
    selection is delegated to FastMCP (`stdio` by default or `sse` for
    HTTP) giving operators flexibility without code changes.

Dependencies:
    fastmcp: Framework that implements the MCP protocol.
    starlette: Underlying ASGI toolkit used by FastMCP for HTTP exposure.
"""

import contextlib

import fastmcp
from fastmcp.server.http import StarletteWithLifespan
from starlette.requests import Request
from starlette.responses import JSONResponse

from purple_mcp.config import Settings, get_settings
from purple_mcp.observability import initialize_logfire, instrument_starlette_app
from purple_mcp.tools.alerts import (
    GET_ALERT_DESCRIPTION,
    GET_ALERT_HISTORY_DESCRIPTION,
    GET_ALERT_NOTES_DESCRIPTION,
    LIST_ALERTS_DESCRIPTION,
    SEARCH_ALERTS_DESCRIPTION,
    get_alert,
    get_alert_history,
    get_alert_notes,
    list_alerts,
    search_alerts,
)
from purple_mcp.tools.inventory import (
    GET_INVENTORY_ITEM_DESCRIPTION,
    LIST_INVENTORY_ITEMS_DESCRIPTION,
    SEARCH_INVENTORY_ITEMS_DESCRIPTION,
    get_inventory_item,
    list_inventory_items,
    search_inventory_items,
)
from purple_mcp.tools.misconfigurations import (
    GET_MISCONFIGURATION_DESCRIPTION,
    GET_MISCONFIGURATION_HISTORY_DESCRIPTION,
    GET_MISCONFIGURATION_NOTES_DESCRIPTION,
    LIST_MISCONFIGURATIONS_DESCRIPTION,
    SEARCH_MISCONFIGURATIONS_DESCRIPTION,
    get_misconfiguration,
    get_misconfiguration_history,
    get_misconfiguration_notes,
    list_misconfigurations,
    search_misconfigurations,
)
from purple_mcp.tools.purple_ai import PURPLE_AI_DESCRIPTION, purple_ai
from purple_mcp.tools.purple_utils import ISO_TO_UNIX_TIMESTAMP_DESCRIPTION, iso_to_unix_timestamp
from purple_mcp.tools.sdl import (
    GET_TIMESTAMP_RANGE_DESCRIPTION,
    POWERQUERY_DESCRIPTION,
    get_timestamp_range,
    powerquery,
)
from purple_mcp.tools.vulnerabilities import (
    GET_VULNERABILITY_DESCRIPTION,
    GET_VULNERABILITY_HISTORY_DESCRIPTION,
    GET_VULNERABILITY_NOTES_DESCRIPTION,
    LIST_VULNERABILITIES_DESCRIPTION,
    SEARCH_VULNERABILITIES_DESCRIPTION,
    get_vulnerability,
    get_vulnerability_history,
    get_vulnerability_notes,
    list_vulnerabilities,
    search_vulnerabilities,
)

# Initialize Pydantic Logfire observability if configured
initialize_logfire()

app: fastmcp.FastMCP[None] = fastmcp.FastMCP("PurpleAIMCP")

# Register MCP tools
app.tool(description=PURPLE_AI_DESCRIPTION)(purple_ai)
app.tool(description=POWERQUERY_DESCRIPTION)(powerquery)
app.tool(description=GET_TIMESTAMP_RANGE_DESCRIPTION)(get_timestamp_range)
app.tool(description=ISO_TO_UNIX_TIMESTAMP_DESCRIPTION)(iso_to_unix_timestamp)
app.tool(description=GET_ALERT_DESCRIPTION)(get_alert)
app.tool(description=LIST_ALERTS_DESCRIPTION)(list_alerts)
app.tool(description=SEARCH_ALERTS_DESCRIPTION)(search_alerts)
app.tool(description=GET_ALERT_NOTES_DESCRIPTION)(get_alert_notes)
app.tool(description=GET_ALERT_HISTORY_DESCRIPTION)(get_alert_history)
app.tool(description=GET_MISCONFIGURATION_DESCRIPTION)(get_misconfiguration)
app.tool(description=LIST_MISCONFIGURATIONS_DESCRIPTION)(list_misconfigurations)
app.tool(description=SEARCH_MISCONFIGURATIONS_DESCRIPTION)(search_misconfigurations)
app.tool(description=GET_MISCONFIGURATION_NOTES_DESCRIPTION)(get_misconfiguration_notes)
app.tool(description=GET_MISCONFIGURATION_HISTORY_DESCRIPTION)(get_misconfiguration_history)
app.tool(description=GET_VULNERABILITY_DESCRIPTION)(get_vulnerability)
app.tool(description=LIST_VULNERABILITIES_DESCRIPTION)(list_vulnerabilities)
app.tool(description=SEARCH_VULNERABILITIES_DESCRIPTION)(search_vulnerabilities)
app.tool(description=GET_VULNERABILITY_NOTES_DESCRIPTION)(get_vulnerability_notes)
app.tool(description=GET_VULNERABILITY_HISTORY_DESCRIPTION)(get_vulnerability_history)
app.tool(description=GET_INVENTORY_ITEM_DESCRIPTION)(get_inventory_item)
app.tool(description=LIST_INVENTORY_ITEMS_DESCRIPTION)(list_inventory_items)
app.tool(description=SEARCH_INVENTORY_ITEMS_DESCRIPTION)(search_inventory_items)


@app.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


settings = None

# Use get_settings to ensure usage of lru_cache decorator.
with contextlib.suppress(BaseException):
    settings = get_settings()


def get_http_app(app: fastmcp.FastMCP, settings: Settings | None) -> StarletteWithLifespan:
    """Returns a http_app using environment variable settings."""
    return (
        app.http_app(transport=settings.transport_mode, stateless_http=settings.stateless_http)
        if settings and settings.transport_mode in ("streamable-http", "http")
        # stateless_http arg has no effect if using "sse" transport mode when instantiating a http_app, AND there
        # is only a choice of three transport modes, hence if settings is None, it is safe to assume "sse" transport
        # mode even if the settings object is None - this also preserves the original module-level implementation of
        # http_app.
        else app.http_app(transport="sse")
    )


http_app = get_http_app(app, settings)

# Instrument the Starlette app with Logfire if enabled
instrument_starlette_app(http_app)
