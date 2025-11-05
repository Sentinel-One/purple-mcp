"""SDL Integration Package.

This package provides integration with the SDL (Singularity Data Lake) Query API,
allowing you to execute PowerQueries against the SDL backend and process the results.

Main Components:
    - SDLQueryClient: Low-level HTTP client for SDL API
    - SDLHandler: Abstract base class for query handling
    - SDLPowerQueryHandler: Specialized handler for PowerQueries
    - SDLSettings: Configuration management with Pydantic Settings

Configuration:
    The SDL package uses code-based configuration with Pydantic Settings.
    Create custom configurations using create_sdl_settings():

    from purple_mcp.libs.sdl import create_sdl_settings, SDLPowerQueryHandler

    settings = create_sdl_settings(
        base_url="https://sdl.example.com/sdl",
        auth_token="Bearer your-token",
        http_timeout=60,
        default_poll_timeout_ms=60000
    )

    # Use configuration with handler
    handler = SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings
    )

Basic Usage:
    from purple_mcp.libs.sdl import SDLPowerQueryHandler, create_sdl_settings

    settings = create_sdl_settings(
        base_url="https://your-console.sentinelone.net/sdl",
        auth_token="Bearer your-token"
    )

    handler = SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings
    )
"""

from purple_mcp.libs.sdl.config import SDL_API_PATH, SDLSettings, create_sdl_settings
from purple_mcp.libs.sdl.enums import (
    PQColumnType,
    SDLPQFrequency,
    SDLPQResultType,
    SDLQueryPriority,
    SDLQueryType,
)
from purple_mcp.libs.sdl.models import (
    SDLColumn,
    SDLPQAttributes,
    SDLQueryResult,
    SDLResultData,
    SDLTableResultData,
)
from purple_mcp.libs.sdl.sdl_exceptions import (
    SDLClientError,
    SDLConfigError,
    SDLError,
    SDLHandlerError,
    SDLMalformedResponseError,
)
from purple_mcp.libs.sdl.sdl_powerquery_handler import SDLPowerQueryHandler
from purple_mcp.libs.sdl.sdl_query_client import SDLQueryClient
from purple_mcp.libs.sdl.sdl_query_handler import SDLHandler
from purple_mcp.libs.sdl.security import (
    get_security_context,
    is_development_environment,
    is_production_environment,
    validate_security_configuration,
    validate_tls_bypass_client,
    validate_tls_bypass_config,
)
from purple_mcp.libs.sdl.type_definitions import JsonDict

__all__ = [
    "SDL_API_PATH",
    "JsonDict",
    "PQColumnType",
    "SDLClientError",
    "SDLColumn",
    "SDLConfigError",
    "SDLError",
    "SDLHandler",
    "SDLHandlerError",
    "SDLMalformedResponseError",
    "SDLPQAttributes",
    "SDLPQFrequency",
    "SDLPQResultType",
    "SDLPowerQueryHandler",
    "SDLQueryClient",
    "SDLQueryPriority",
    "SDLQueryResult",
    "SDLQueryType",
    "SDLResultData",
    "SDLSettings",
    "SDLTableResultData",
    "create_sdl_settings",
    "get_security_context",
    "is_development_environment",
    "is_production_environment",
    "validate_security_configuration",
    "validate_tls_bypass_client",
    "validate_tls_bypass_config",
]
