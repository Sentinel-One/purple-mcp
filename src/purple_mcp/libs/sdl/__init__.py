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

from purple_mcp.libs.sdl.config import SDLSettings, create_sdl_settings
from purple_mcp.libs.sdl.sdl_powerquery_handler import SDLPowerQueryHandler

__all__ = [
    "SDLPowerQueryHandler",
    "SDLSettings",
    "create_sdl_settings",
]
