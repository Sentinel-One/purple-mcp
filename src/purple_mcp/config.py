"""Application configuration management using Pydantic Settings.

This module provides centralized configuration management for the MCP server,
loading and validating settings from environment variables. Configuration
validation occurs at application startup, ensuring all required settings are
present before the server begins accepting requests.
"""

import logging
import uuid
from functools import lru_cache
from typing import ClassVar, Final
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from purple_mcp import __version__

logger = logging.getLogger(__name__)

# Environment variable prefix constants
ENV_PREFIX_NAME: Final[str] = "PURPLEMCP"
ENV_PREFIX_DELIMITER: Final[str] = "_"
ENV_PREFIX: Final[str] = f"{ENV_PREFIX_NAME}{ENV_PREFIX_DELIMITER}"

# Environment variable name constants - dynamically generated from prefix
SDL_READ_LOGS_TOKEN_ENV: Final[str] = f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN"
CONSOLE_TOKEN_ENV: Final[str] = f"{ENV_PREFIX}CONSOLE_TOKEN"
CONSOLE_BASE_URL_ENV: Final[str] = f"{ENV_PREFIX}CONSOLE_BASE_URL"
CONSOLE_GRAPHQL_ENDPOINT_ENV: Final[str] = f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT"
ALERTS_GRAPHQL_ENDPOINT_ENV: Final[str] = f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT"
MISCONFIGURATIONS_GRAPHQL_ENDPOINT_ENV: Final[str] = (
    f"{ENV_PREFIX}MISCONFIGURATIONS_GRAPHQL_ENDPOINT"
)
VULNERABILITIES_GRAPHQL_ENDPOINT_ENV: Final[str] = f"{ENV_PREFIX}VULNERABILITIES_GRAPHQL_ENDPOINT"
INVENTORY_RESTAPI_ENDPOINT_ENV: Final[str] = f"{ENV_PREFIX}INVENTORY_RESTAPI_ENDPOINT"
PURPLE_AI_ACCOUNT_ID_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_ACCOUNT_ID"
PURPLE_AI_TEAM_TOKEN_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_TEAM_TOKEN"
PURPLE_AI_SESSION_ID_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_SESSION_ID"
PURPLE_AI_EMAIL_ADDRESS_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_EMAIL_ADDRESS"
PURPLE_AI_USER_AGENT_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_USER_AGENT"
PURPLE_AI_BUILD_DATE_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_BUILD_DATE"
PURPLE_AI_BUILD_HASH_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_BUILD_HASH"
PURPLE_AI_CONSOLE_VERSION_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_CONSOLE_VERSION"
ENVIRONMENT_ENV: Final[str] = f"{ENV_PREFIX}ENV"
LOGFIRE_TOKEN_ENV: Final[str] = f"{ENV_PREFIX}LOGFIRE_TOKEN"
STATELESS_HTTP_ENV = f"{ENV_PREFIX}STATELESS_HTTP"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # Scalyr/PowerQuery Configuration
    # Note: SDL uses the same token as Console for authentication
    sdl_api_token: str = Field(
        ...,
        description="Authentication token for PowerQuery logs API (uses Console Token)",
        validation_alias=CONSOLE_TOKEN_ENV,
    )

    # Purple AI Configuration
    graphql_service_token: str = Field(
        ...,
        description="Service token for SentinelOne OpsCenter Console API",
        validation_alias=CONSOLE_TOKEN_ENV,
    )

    # Scalyr Console Configuration
    sentinelone_console_base_url: str = Field(
        ...,
        description="Base URL for Scalyr/SentinelOne console",
        validation_alias=CONSOLE_BASE_URL_ENV,
    )

    # Purple AI GraphQL Configuration
    sentinelone_console_graphql_endpoint: str = Field(
        default="/web/api/v2.1/graphql",
        description="GraphQL endpoint for Purple AI",
        validation_alias=CONSOLE_GRAPHQL_ENDPOINT_ENV,
    )

    # Alerts GraphQL Configuration
    sentinelone_alerts_graphql_endpoint: str = Field(
        default="/web/api/v2.1/unifiedalerts/graphql",
        description="GraphQL endpoint for Alerts/UAM",
        validation_alias=ALERTS_GRAPHQL_ENDPOINT_ENV,
    )

    # XSPM Misconfigurations GraphQL Configuration
    sentinelone_misconfigurations_graphql_endpoint: str = Field(
        default="/web/api/v2.1/xspm/findings/misconfigurations/graphql",
        description="GraphQL endpoint for XSPM Misconfigurations",
        validation_alias=MISCONFIGURATIONS_GRAPHQL_ENDPOINT_ENV,
    )

    # XSPM Vulnerabilities GraphQL Configuration
    sentinelone_vulnerabilities_graphql_endpoint: str = Field(
        default="/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
        description="GraphQL endpoint for XSPM Vulnerabilities",
        validation_alias=VULNERABILITIES_GRAPHQL_ENDPOINT_ENV,
    )

    # Unified Asset Inventory REST API Configuration
    sentinelone_inventory_restapi_endpoint: str = Field(
        default="/web/api/v2.1/xdr/assets",
        description="REST API endpoint for Unified Asset Inventory",
        validation_alias=INVENTORY_RESTAPI_ENDPOINT_ENV,
    )

    # Purple AI User Details
    purple_ai_account_id: str = Field(
        default="0",
        description="Account ID for Purple AI user details",
        validation_alias=PURPLE_AI_ACCOUNT_ID_ENV,
    )
    purple_ai_team_token: str = Field(
        default="0",
        description="Team token for Purple AI user details",
        validation_alias=PURPLE_AI_TEAM_TOKEN_ENV,
    )
    purple_ai_session_id: str | None = Field(
        default_factory=lambda: uuid.uuid4().hex,
        description="Session ID for Purple AI user details",
        validation_alias=PURPLE_AI_SESSION_ID_ENV,
    )
    purple_ai_email_address: str | None = Field(
        default=None,
        description="Email address for Purple AI user details",
        validation_alias=PURPLE_AI_EMAIL_ADDRESS_ENV,
    )
    purple_ai_user_agent: str = Field(
        default=f"sentinelone/purple-mcp (version {__version__})",
        description="User agent for Purple AI user details",
        validation_alias=PURPLE_AI_USER_AGENT_ENV,
    )
    purple_ai_build_date: str | None = Field(
        default=None,
        description="Build date for Purple AI user details",
        validation_alias=PURPLE_AI_BUILD_DATE_ENV,
    )
    purple_ai_build_hash: str | None = Field(
        default=None,
        description="Build hash for Purple AI user details",
        validation_alias=PURPLE_AI_BUILD_HASH_ENV,
    )

    # Purple AI Console Details
    purple_ai_console_version: str = Field(
        default="S",
        description="Version for Purple AI console details",
        validation_alias=PURPLE_AI_CONSOLE_VERSION_ENV,
    )

    # Environment Configuration
    environment: str = Field(
        default="development",
        description="Environment name (e.g., 'development', 'production', 'staging')",
        validation_alias=ENVIRONMENT_ENV,
    )

    # Logfire Configuration (optional)
    logfire_token: str | None = Field(
        default=None,
        description="Optional Pydantic Logfire token for observability",
        validation_alias=LOGFIRE_TOKEN_ENV,
    )

    stateless_http: bool | None = Field(
        default=False,
        description="Stateless mode (new transport per request)",
        validation_alias=STATELESS_HTTP_ENV,
    )

    @field_validator("sentinelone_console_base_url")
    @classmethod
    def validate_console_base_url(cls, v: str) -> str:
        """Validate that the console base URL is a clean HTTPS origin with no extras."""
        if not v.startswith("https://"):
            raise ValueError("Console base URL must use HTTPS (https://)")

        # Reject trailing slash or hash
        if v.endswith("/"):
            raise ValueError("Console base URL must not have a trailing slash")
        if v.endswith("#"):
            raise ValueError("Console base URL must not have a trailing hash")

        # Strip https:// prefix to check the origin
        origin = v.removeprefix("https://")

        # Reject any URL components beyond scheme and netloc
        # These characters indicate paths, queries, fragments, or parameters
        if "/" in origin:
            raise ValueError(
                "Console base URL must not contain a path (remove path segments like /sdl)"
            )
        if "?" in origin:
            raise ValueError("Console base URL must not contain query parameters")
        if "#" in origin:
            raise ValueError("Console base URL must not contain a fragment")
        if ";" in origin:
            raise ValueError("Console base URL must not contain path parameters")

        # Verify we have a valid hostname using urlparse
        parsed = urlparse(v)
        if not parsed.hostname:
            raise ValueError("Console base URL must have a valid hostname")

        return v

    @field_validator("sentinelone_console_graphql_endpoint")
    @classmethod
    def validate_console_graphql_endpoint(cls, v: str) -> str:
        """Validate that the graphql endpoint starts with a slash."""
        if not v.startswith("/"):
            raise ValueError("Console graphql endpoint must start with a slash")

        return v

    @field_validator("sentinelone_alerts_graphql_endpoint")
    @classmethod
    def validate_alerts_graphql_endpoint(cls, v: str) -> str:
        """Validate that the alerts graphql endpoint starts with a slash."""
        if not v.startswith("/"):
            raise ValueError("Alerts graphql endpoint must start with a slash")

        return v

    @field_validator("sentinelone_misconfigurations_graphql_endpoint")
    @classmethod
    def validate_misconfigurations_graphql_endpoint(cls, v: str) -> str:
        """Validate that the misconfigurations graphql endpoint starts with a slash."""
        if not v.startswith("/"):
            raise ValueError("Misconfigurations graphql endpoint must start with a slash")

        return v

    @field_validator("sentinelone_vulnerabilities_graphql_endpoint")
    @classmethod
    def validate_vulnerabilities_graphql_endpoint(cls, v: str) -> str:
        """Validate that the vulnerabilities graphql endpoint starts with a slash."""
        if not v.startswith("/"):
            raise ValueError("Vulnerabilities graphql endpoint must start with a slash")

        return v

    @field_validator("sentinelone_inventory_restapi_endpoint")
    @classmethod
    def validate_inventory_restapi_endpoint(cls, v: str) -> str:
        """Validate that the inventory REST API endpoint starts with a slash."""
        if not v.startswith("/"):
            raise ValueError("Inventory REST API endpoint must start with a slash")

        return v

    @property
    def graphql_full_url(self) -> str:
        """Full GraphQL URL combining base URL and endpoint."""
        return f"{self.sentinelone_console_base_url}{self.sentinelone_console_graphql_endpoint}"

    @property
    def alerts_graphql_url(self) -> str:
        """Full GraphQL URL for alerts/UAM endpoint."""
        return f"{self.sentinelone_console_base_url}{self.sentinelone_alerts_graphql_endpoint}"

    @property
    def misconfigurations_graphql_url(self) -> str:
        """Full GraphQL URL for XSPM misconfigurations endpoint."""
        return f"{self.sentinelone_console_base_url}{self.sentinelone_misconfigurations_graphql_endpoint}"

    @property
    def vulnerabilities_graphql_url(self) -> str:
        """Full GraphQL URL for XSPM vulnerabilities endpoint."""
        return f"{self.sentinelone_console_base_url}{self.sentinelone_vulnerabilities_graphql_endpoint}"

    @property
    def inventory_api_url(self) -> str:
        """Full REST API URL for Unified Asset Inventory endpoint."""
        return f"{self.sentinelone_console_base_url}{self.sentinelone_inventory_restapi_endpoint}"

    def model_post_init(self, __context: object, /) -> None:
        """Log configuration after initialization."""
        logger.info("Application configuration loaded successfully")
        logger.info(
            "SentinelOne Console Base URL configured",
            extra={"console_base_url": self.sentinelone_console_base_url},
        )
        logger.info(
            "Purple AI GraphQL URL configured", extra={"graphql_url": self.graphql_full_url}
        )
        logger.info("Alerts GraphQL URL configured", extra={"alerts_url": self.alerts_graphql_url})
        logger.info(
            "Misconfigurations GraphQL URL configured",
            extra={"misconfigurations_url": self.misconfigurations_graphql_url},
        )
        logger.info(
            "Vulnerabilities GraphQL URL configured",
            extra={"vulnerabilities_url": self.vulnerabilities_graphql_url},
        )
        logger.info(
            "Inventory API URL configured", extra={"inventory_url": self.inventory_api_url}
        )

        # Log token presence without exposing values
        logger.info(
            "%sCONSOLE_TOKEN is configured (used for both Console and SDL access)", ENV_PREFIX
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The application settings

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    try:
        settings = Settings()

        # Register sensitive tokens with logging filter to prevent leakage
        try:
            from purple_mcp.logging_security import register_secret

            register_secret(settings.sdl_api_token)
            register_secret(settings.graphql_service_token)
        except ImportError:
            # Filter module not available - this shouldn't happen in normal operation
            logger.warning("Logging security filter not available - tokens may appear in logs")

        return settings
    except Exception:
        logger.critical(
            "Failed to initialize application configuration",
            exc_info=True,
        )
        raise


# Create a global settings instance for easy importing
# Only create if environment is properly configured (avoids import-time errors during testing)
try:
    settings = get_settings()
except Exception:
    # Settings will be None if initialization fails (e.g., during testing)
    settings = None
