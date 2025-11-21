"""Command-line interface for the Purple MCP server.

This module implements the CLI using Click, providing commands for running
the MCP server in different modes (stdio, SSE, streamable-http) and managing
server configuration through command-line arguments and environment variables.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import sys
from collections.abc import Callable, Mapping
from typing import Literal

import click
import uvicorn

from purple_mcp.config import ENV_PREFIX, Settings
from purple_mcp.observability import instrument_starlette_app

VALID_MODES: tuple[str, ...] = ("stdio", "sse", "streamable-http")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _is_loopback_host(host: str) -> bool:
    """Check if a host string represents a loopback address.

    Args:
        host: The host string to check (e.g., "localhost", "127.0.0.1", "::1")

    Returns:
        True if the host is a loopback address, False otherwise
    """
    # Handle common loopback hostnames
    if host.lower() in ("localhost", "localhost.localdomain"):
        return True

    # Try to parse as IP address
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback
    except ValueError:
        # Not a valid IP address, assume it's not loopback
        return False


def _setup_logging(verbose: bool) -> None:
    """Configure global logging.

    Args:
        verbose: If *True* enable more detailed *DEBUG* level logging, otherwise use
        *INFO* to reduce noise. The log format remains the default provided by
        the Python ``logging`` module so it is easy to override with
        ``logging.basicConfig`` calls made by embedding applications.
    """
    level = logging.DEBUG if verbose else logging.INFO
    # Intentionally rely on the default logging format so it can be customised by
    # the caller. Only set the log *level* here.
    logging.basicConfig(level=level)

    # Install secret filter to prevent token leakage in logs
    from purple_mcp.logging_security import install_filter

    install_filter()


def _apply_environment_overrides(
    sdl_api_token: str | None,
    graphql_service_token: str | None,
    console_base_url: str | None,
    graphql_endpoint: str | None,
    alerts_graphql_endpoint: str | None,
    stateless_http: bool
) -> None:
    """Apply CLI argument values to environment variables.

    Populates os.environ with provided CLI arguments, allowing command-line
    configuration to override environment variable defaults.

    Args:
        sdl_api_token: SDL API authentication token
        graphql_service_token: GraphQL service authentication token
        console_base_url: Base URL for the console
        graphql_endpoint: GraphQL endpoint path
        alerts_graphql_endpoint: Alerts GraphQL endpoint path
    """
    if sdl_api_token:
        os.environ[f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN"] = sdl_api_token
    if graphql_service_token:
        os.environ[f"{ENV_PREFIX}CONSOLE_TOKEN"] = graphql_service_token
    if console_base_url:
        os.environ[f"{ENV_PREFIX}CONSOLE_BASE_URL"] = console_base_url
    if graphql_endpoint and graphql_endpoint != "/web/api/v2.1/graphql":
        os.environ[f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT"] = graphql_endpoint
    if (
        alerts_graphql_endpoint
        and alerts_graphql_endpoint != "/web/api/v2.1/unifiedalerts/graphql"
    ):
        os.environ[f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT"] = alerts_graphql_endpoint
    if stateless_http:
        os.environ[f"{ENV_PREFIX}STATELESS_HTTP"] = str(stateless_http)


def _check_unsupported_config() -> None:
    """Validate configuration and warn about deprecated environment variables.

    Checks for the presence of deprecated SDL_READ_LOGS_TOKEN environment
    variable and displays a warning if found, as this setting is no longer
    supported.
    """
    from purple_mcp.config import SDL_READ_LOGS_TOKEN_ENV

    sdl_token = os.getenv(SDL_READ_LOGS_TOKEN_ENV)

    # Warn if SDL_READ_LOGS_TOKEN is set (it will be ignored)
    if sdl_token:
        click.echo(
            f"⚠️  WARNING: {SDL_READ_LOGS_TOKEN_ENV} is not supported and will be ignored.",
            err=True,
        )
        click.echo(
            f"   Use {ENV_PREFIX}CONSOLE_TOKEN instead and remove {SDL_READ_LOGS_TOKEN_ENV} from your configuration.",
            err=True,
        )
        click.echo("", err=True)


def _create_settings() -> Settings:
    """Return validated :class:`~purple_mcp.config.Settings` instance.

    Exits the program with status *1* if validation fails.
    """
    try:
        return Settings()
    except Exception as exc:  # pragma: no cover - exact validation exceptions vary
        click.echo(f"✗ Configuration error: {exc}", err=True)
        click.echo("\nRequired environment variables or CLI options:", err=True)
        click.echo(
            f"  --graphql-service-token or {ENV_PREFIX}CONSOLE_TOKEN (used for both Console and SDL)",
            err=True,
        )
        click.echo(f"  --console-base-url or {ENV_PREFIX}CONSOLE_BASE_URL", err=True)
        click.echo(
            "\nNote: Token must have Account or Site level permissions (not Global)", err=True
        )
        sys.exit(1)


def _validate_http_binding(host: str, allow_remote_access: bool) -> None:
    """Validate HTTP binding for security.

    Prevents binding to non-loopback interfaces without explicit consent to avoid
    exposing unauthenticated MCP tools to the network.

    Args:
        host: The host address to bind to
        allow_remote_access: Whether remote access has been explicitly allowed

    Raises:
        SystemExit: If binding to non-loopback without --allow-remote-access flag
    """
    if not _is_loopback_host(host) and not allow_remote_access:
        click.echo("", err=True)
        click.echo("✗ SECURITY ERROR: Refusing to bind to non-loopback interface", err=True)
        click.echo("", err=True)
        click.echo(
            f"  Binding to '{host}' would expose unauthenticated MCP tools to the network.",
            err=True,
        )
        click.echo(
            "  This could allow remote invocation of tools and potential data exfiltration.",
            err=True,
        )
        click.echo("", err=True)
        click.echo("  Options:", err=True)
        click.echo("    1. Use --host localhost (recommended for local development)", err=True)
        click.echo(
            "    2. Use --allow-remote-access flag if you understand the security risks",
            err=True,
        )
        click.echo("", err=True)
        sys.exit(1)


def _display_security_warning(host: str) -> None:
    """Display a prominent security warning when binding to non-loopback interfaces.

    Args:
        host: The host address being bound to
    """
    click.echo("", err=True)
    click.echo("=" * 80, err=True)
    click.echo("WARNING: RUNNING IN REMOTE ACCESS MODE", err=True)
    click.echo("=" * 80, err=True)
    click.echo("", err=True)
    click.echo(f"  Binding to: {host}", err=True)
    click.echo("", err=True)
    click.echo("  SECURITY RISKS:", err=True)
    click.echo("    - MCP server exposes unauthenticated HTTP/SSE interface", err=True)
    click.echo("    - All registered tools can be invoked remotely", err=True)
    click.echo("    - Service tokens and credentials may be accessible", err=True)
    click.echo("    - Data exfiltration is possible if process has valid tokens", err=True)
    click.echo("", err=True)
    click.echo("  RECOMMENDED PROTECTIONS:", err=True)
    click.echo("    - Use a firewall to restrict access to trusted IPs", err=True)
    click.echo("    - Run behind a reverse proxy with authentication", err=True)
    click.echo("    - Use network policies to limit exposure", err=True)
    click.echo("    - Monitor for unexpected tool invocations", err=True)
    click.echo("", err=True)
    click.echo("=" * 80, err=True)
    click.echo("", err=True)


# ---------------------------------------------------------------------------
# Server runners
# ---------------------------------------------------------------------------


def _run_stdio(
    verbose: bool, no_banner: bool = False
) -> None:  # pragma: no cover - integration tested elsewhere
    """Run MCP in STDIO mode."""
    click.echo("Starting Purple MCP server in STDIO mode...", err=True)
    try:
        from purple_mcp.server import app

        app.run(transport="stdio", show_banner=not no_banner)
    except Exception as exc:
        click.echo(f"✗ Failed to start server: {exc}", err=True)
        sys.exit(1)


def _run_uvicorn(
    transport: Literal["http", "streamable-http", "sse"],
    *,
    host: str,
    port: int,
    verbose: bool,
    allow_remote_access: bool,
    stateless_http: bool
) -> None:  # pragma: no cover - uvicorn is mocked in unit-tests
    """Run the HTTP/SSE transport using *uvicorn*."""
    # Validate host binding for security
    _validate_http_binding(host, allow_remote_access)

    # Display warning if running on non-loopback
    if not _is_loopback_host(host):
        _display_security_warning(host)

    click.echo(
        f"Starting Purple MCP server in {transport.upper()} mode on {host}:{port}...",
        err=True,
    )

    try:
        from purple_mcp.server import app

        # Create the HTTP app and instrument it if Logfire is enabled
        http_app = app.http_app(transport=transport, stateless_http=stateless_http)
        instrument_starlette_app(http_app)

        uvicorn.run(
            http_app,
            host=host,
            port=port,
            log_level="info" if verbose else "warning",
        )
    except Exception as exc:
        click.echo(f"✗ Failed to start server: {exc}", err=True)
        sys.exit(1)


def _run_mode(
    mode: str,
    *,
    host: str,
    port: int,
    verbose: bool,
    no_banner: bool = False,
    allow_remote_access: bool = False,
    stateless_http: bool = False
) -> None:
    """Dispatch to the appropriate server runner for *mode*."""
    mode_normalised = mode.lower()

    runners: Mapping[str, Callable[[], None]] = {
        "stdio": lambda: _run_stdio(verbose, no_banner),
        "sse": lambda: _run_uvicorn(
            "sse", host=host, port=port, verbose=verbose, allow_remote_access=allow_remote_access, stateless_http=stateless_http
        ),
        "streamable-http": lambda: _run_uvicorn(
            "streamable-http",
            host=host,
            port=port,
            verbose=verbose,
            allow_remote_access=allow_remote_access,
            stateless_http=stateless_http
        ),
    }

    runner = runners[mode_normalised]
    runner()


@click.command()
@click.option(
    "--mode",
    "-m",
    type=click.Choice(VALID_MODES, case_sensitive=False),
    default="stdio",
    help="MCP transport mode to use",
)
@click.option(
    "--host",
    default="localhost",
    help="Host to bind to for SSE/HTTP modes (default: localhost)",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to bind to for SSE/HTTP modes (default: 8000)",
)
@click.option(
    "--sdl-api-token",
    envvar=f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN",
    hidden=True,
    help=f"[DEPRECATED] Use --graphql-service-token instead (env: {ENV_PREFIX}SDL_READ_LOGS_TOKEN)",
)
@click.option(
    "--graphql-service-token",
    envvar=f"{ENV_PREFIX}CONSOLE_TOKEN",
    help=f"Service token for SentinelOne OpsCenter Console API (env: {ENV_PREFIX}CONSOLE_TOKEN)",
)
@click.option(
    "--console-base-url",
    envvar=f"{ENV_PREFIX}CONSOLE_BASE_URL",
    help=f"Base URL for SentinelOne console (env: {ENV_PREFIX}CONSOLE_BASE_URL)",
)
@click.option(
    "--graphql-endpoint",
    default="/web/api/v2.1/graphql",
    envvar=f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT",
    help="GraphQL endpoint for SentinelOne OpsCenter (default: /web/api/v2.1/graphql)",
)
@click.option(
    "--alerts-graphql-endpoint",
    default="/web/api/v2.1/unifiedalerts/graphql",
    envvar=f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT",
    help="GraphQL endpoint for Alerts/UAM (default: /web/api/v2.1/unifiedalerts/graphql)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--banner/--no-banner",
    default=False,
    help="Show/hide server startup banner (default: hidden)",
)
@click.option(
    "--allow-remote-access",
    is_flag=True,
    help="Allow binding to non-loopback interfaces (SECURITY RISK: exposes unauthenticated tools)",
)
@click.option(
    "--stateless-http",
    is_flag=True,
    envvar=f"{ENV_PREFIX}STATELESS_HTTP",
    help="uses true stateless mode (new transport per request)",
)
def main(
    mode: str,
    host: str,
    port: int,
    sdl_api_token: str | None,
    graphql_service_token: str | None,
    console_base_url: str | None,
    graphql_endpoint: str,
    alerts_graphql_endpoint: str,
    verbose: bool,
    banner: bool,
    allow_remote_access: bool,
    stateless_http: bool
) -> None:
    """Purple MCP Server - AI monitoring and analysis tool."""
    _setup_logging(verbose)

    # Check for unsupported configuration and warn user
    _check_unsupported_config()

    _apply_environment_overrides(
        sdl_api_token=sdl_api_token,
        graphql_service_token=graphql_service_token,
        console_base_url=console_base_url,
        graphql_endpoint=graphql_endpoint,
        alerts_graphql_endpoint=alerts_graphql_endpoint,
        stateless_http=stateless_http
    )

    settings = _create_settings()
    click.echo("✓ Configuration validated successfully", err=True)
    if verbose:
        click.echo(f"  GraphQL URL: {settings.graphql_full_url}", err=True)
        click.echo(f"  Mode: {mode}", err=True)

    # Finally run the requested transport
    _run_mode(
        mode,
        host=host,
        port=port,
        verbose=verbose,
        no_banner=not banner,
        allow_remote_access=allow_remote_access,
        stateless_http=stateless_http
    )


if __name__ == "__main__":
    main()
