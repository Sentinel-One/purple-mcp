"""Application configuration management using Pydantic Settings.

This module provides centralized configuration management for the MCP server,
loading and validating settings from environment variables. Configuration
validation occurs at application startup, ensuring all required settings are
present before the server begins accepting requests.
"""

import logging
import os
import re
import uuid
from functools import lru_cache
from typing import Annotated, ClassVar, Final, Literal, assert_never
from urllib.parse import urlparse

from pydantic import Field, PositiveFloat, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from purple_mcp import __version__
from purple_mcp.libs.purple_ai.config import validate_scope_id
from purple_mcp.libs.sdl.type_definitions import SDL_QUERY_ORIGIN_PATTERN

logger = logging.getLogger(__name__)

# SDL endpoint path appended to the console base URL when no dedicated SDL URL is configured.
_SDL_ENDPOINT_PATH: Final[str] = "/sdl"

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
PURPLE_AI_SESSION_ID_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_SESSION_ID"
PURPLE_AI_EMAIL_ADDRESS_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_EMAIL_ADDRESS"
PURPLE_AI_USER_AGENT_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_USER_AGENT"
PURPLE_AI_BUILD_DATE_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_BUILD_DATE"
PURPLE_AI_BUILD_HASH_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_BUILD_HASH"
PURPLE_AI_CONSOLE_VERSION_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_CONSOLE_VERSION"
PURPLE_AI_CONSOLE_ID_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_CONSOLE_ID"
PURPLE_AI_CONSOLE_TENANT_ID_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_CONSOLE_TENANT_ID"
PURPLE_AI_CONSOLE_ACCOUNT_ID_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_CONSOLE_ACCOUNT_ID"
PURPLE_AI_CONSOLE_SITE_ID_ENV: Final[str] = f"{ENV_PREFIX}PURPLE_AI_CONSOLE_SITE_ID"
ENVIRONMENT_ENV: Final[str] = f"{ENV_PREFIX}ENV"
LOGFIRE_TOKEN_ENV: Final[str] = f"{ENV_PREFIX}LOGFIRE_TOKEN"
LOGFIRE_SERVICE_NAME_ENV: Final[str] = f"{ENV_PREFIX}LOGFIRE_SERVICE_NAME"
VT_API_KEY_ENV: Final[str] = f"{ENV_PREFIX}VT_API_KEY"
VT_TIMEOUT_ENV: Final[str] = f"{ENV_PREFIX}VT_TIMEOUT"
STATELESS_HTTP_ENV: Final[str] = f"{ENV_PREFIX}STATELESS_HTTP"
TRANSPORT_MODE_ENV: Final[str] = f"{ENV_PREFIX}TRANSPORT_MODE"
SDL_BASE_URL_ENV: Final[str] = f"{ENV_PREFIX}SDL_BASE_URL"
SDL_QUERY_ORIGIN_ENV: Final[str] = f"{ENV_PREFIX}SDL_QUERY_ORIGIN"
SDL_CONSOLE_ACCOUNT_IDS_ENV: Final = f"{ENV_PREFIX}SDL_CONSOLE_ACCOUNT_IDS"
SDL_CONSOLE_SITE_IDS_ENV: Final = f"{ENV_PREFIX}SDL_CONSOLE_SITE_IDS"

# Used solely for integration testing but defined here for consistency:
SDL_INT_TEST_SECOND_ACCOUNT_ID_ENV: Final = f"{ENV_PREFIX}SDL_INT_TEST_SECOND_ACCOUNT_ID"
SDL_INT_TEST_AGENT_UUID_ENV: Final = f"{ENV_PREFIX}SDL_INT_TEST_AGENT_UUID"
SDL_INT_TEST_AGENT_EVENT_TIMESTAMP_ENV: Final = f"{ENV_PREFIX}SDL_INT_TEST_AGENT_EVENT_TIMESTAMP"


def _validate_https_origin_url(v: str | None, label: str) -> str | None:
    """Validate that a URL is a clean HTTPS origin with no path, query, or fragment.

    Args:
        v: The URL string to validate, or None.
        label: Human-readable label for error messages (e.g. "Console base URL").

    Returns:
        The validated URL string, or None if the input was None.

    Raises:
        ValueError: If the URL is not a valid HTTPS origin.
    """
    if v is None:
        return None

    if not v.startswith("https://"):
        raise ValueError(f"{label} must use HTTPS (https://)")

    # Reject trailing slash or hash
    if v.endswith("/"):
        raise ValueError(f"{label} must not have a trailing slash")
    if v.endswith("#"):
        raise ValueError(f"{label} must not have a trailing hash")

    # Strip https:// prefix to check the origin
    origin = v.removeprefix("https://")

    # Reject any URL components beyond scheme and netloc
    # These characters indicate paths, queries, fragments, or parameters
    if "/" in origin:
        raise ValueError(f"{label} must not contain a path (remove path segments like /sdl)")
    if "?" in origin:
        raise ValueError(f"{label} must not contain query parameters")
    if "#" in origin:
        raise ValueError(f"{label} must not contain a fragment")
    if ";" in origin:
        raise ValueError(f"{label} must not contain path parameters")

    # Verify we have a valid hostname using urlparse
    parsed = urlparse(v)
    if not parsed.hostname:
        raise ValueError(f"{label} must have a valid hostname")

    return v


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # SDL Base URL Configuration (Optional)
    # When set, this URL is used directly as the SDL API base URL.
    # When not set, the console base URL with /sdl appended is used instead.
    sdl_base_url: str | None = Field(
        default=None,
        description=(
            "Optional dedicated base URL for the SDL API. "
            "When set, used directly instead of console base URL + /sdl."
        ),
        validation_alias=SDL_BASE_URL_ENV,
    )

    # SDL/PowerQuery Configuration
    # Note: SDL uses the same token as Console for authentication
    sdl_api_token: str | None = Field(
        default=None,
        description="Authentication token for PowerQuery logs API (uses Console Token)",
        validation_alias=CONSOLE_TOKEN_ENV,
    )

    sdl_query_origin: str | None = Field(
        default="ai_purple_mcp",
        description=(
            "Optional SDL queryOrigin value for PowerQuery provenance. "
            "Use lowercase letters, digits, underscores, or hyphens; values must start "
            "and end with a lowercase letter or digit."
        ),
        validation_alias=SDL_QUERY_ORIGIN_ENV,
    )

    # SDL Account Configuration (Optional)
    # Specify account IDs to scope SDL queries to specific accounts.
    # - When specified: queries are scoped to the provided account(s) (tenant=false)
    # - When not specified: queries all accounts accessible to the token (tenant=true)
    # This works for both Console API tokens and Service User tokens.
    # NOTE: This field accepts either a comma-separated string or a JSON array
    sdl_console_account_ids: (
        list[Annotated[str, Field(min_length=18, max_length=19, strip_whitespace=True)]] | None
    ) = Field(
        default=None,
        description="Account IDs for SDL query scoping (comma-separated string or JSON array)",
        validation_alias=SDL_CONSOLE_ACCOUNT_IDS_ENV,
        json_schema_extra={"env_parse_mode": "parse"},
        min_length=1,
    )

    # SDL Site Configuration (Optional)
    # Specify Site IDs to scope SDL queries to specific sites.
    # - When specified: queries are scoped to the provided site
    # When specifying SDL Site, SDL Account must also be set. Note that only one Account must be specified.
    # This works for both Console API tokens and Service User tokens.
    # NOTE: This field accepts either a comma-separated string or a JSON array
    # NOTE: Note that currently, only the first ID is used.
    sdl_console_site_ids: (
        list[Annotated[str, Field(min_length=18, max_length=19, strip_whitespace=True)]] | None
    ) = Field(
        default=None,
        description="Site IDs for SDL query scoping. When specifying SDL Sites, a SDL Account must also be set. Note that only one Account must be specified. The value for Site IDs is a comma-separated string or JSON array. Note that currently, only the first ID is used.",
        validation_alias=SDL_CONSOLE_SITE_IDS_ENV,
        json_schema_extra={"env_parse_mode": "parse"},
        min_length=1,
    )

    # Purple AI Configuration
    graphql_service_token: str | None = Field(
        default=None,
        description="Service token for SentinelOne OpsCenter Console API",
        validation_alias=CONSOLE_TOKEN_ENV,
    )

    # Console Configuration
    sentinelone_console_base_url: str | None = Field(
        default=None,
        description="Base URL for SentinelOne console",
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
    purple_ai_console_version: str | None = Field(
        default=None,
        description="Version for Purple AI console details",
        validation_alias=PURPLE_AI_CONSOLE_VERSION_ENV,
    )
    purple_ai_console_id: str | None = Field(
        default=None,
        description="Console (deployment) ID for Purple AI console details",
        validation_alias=PURPLE_AI_CONSOLE_ID_ENV,
    )
    purple_ai_console_tenant_id: str | None = Field(
        default=None,
        description="Tenant ID for Purple AI console details",
        validation_alias=PURPLE_AI_CONSOLE_TENANT_ID_ENV,
    )
    purple_ai_console_account_id: str | None = Field(
        default=None,
        description="Account ID for Purple AI console details",
        validation_alias=PURPLE_AI_CONSOLE_ACCOUNT_ID_ENV,
    )
    purple_ai_console_site_id: str | None = Field(
        default=None,
        description="Site ID for Purple AI console details",
        validation_alias=PURPLE_AI_CONSOLE_SITE_ID_ENV,
    )

    # Environment Configuration
    environment: str = Field(
        default="development",
        description="Environment name (e.g., 'development', 'testing', 'release')",
        validation_alias=ENVIRONMENT_ENV,
    )

    # Logfire Configuration (optional)
    logfire_token: str | None = Field(
        default=None,
        description="Optional Pydantic Logfire token for observability",
        validation_alias=LOGFIRE_TOKEN_ENV,
    )

    logfire_service_name: str | None = Field(
        default=None,
        description="Optional Pydantic Logfire service name for observability",
        validation_alias=LOGFIRE_SERVICE_NAME_ENV,
    )

    stateless_http: bool = Field(
        default=False,
        description="Stateless mode (new transport per request)",
        validation_alias=STATELESS_HTTP_ENV,
    )

    transport_mode: Literal["stdio", "http", "streamable-http", "sse"] = Field(
        default="stdio",
        description="MCP transport mode (stdio, http, streamable-http, or sse)",
        validation_alias=TRANSPORT_MODE_ENV,
    )

    # VirusTotal/Threat Intelligence Configuration (optional)
    vt_api_key: str | None = Field(
        default=None,
        description="Optional VirusTotal API key for threat intelligence lookups",
        validation_alias=VT_API_KEY_ENV,
    )

    vt_timeout: PositiveFloat = Field(
        default=60.0,
        description="Optional VirusTotal API timeout in seconds",
        validation_alias=VT_TIMEOUT_ENV,
    )

    @field_validator("sentinelone_console_base_url")
    @classmethod
    def validate_console_base_url(cls, v: str | None) -> str | None:
        """Validate that the console base URL is a clean HTTPS origin with no extras."""
        return _validate_https_origin_url(v, "Console base URL")

    _validate_purple_ai_console_scope_ids = field_validator(
        "purple_ai_console_id",
        "purple_ai_console_tenant_id",
        "purple_ai_console_account_id",
        "purple_ai_console_site_id",
    )(validate_scope_id)

    @field_validator("sdl_base_url")
    @classmethod
    def validate_sdl_base_url(cls, v: str | None) -> str | None:
        """Validate that the SDL base URL is a clean HTTPS origin with no extras."""
        return _validate_https_origin_url(v, "SDL base URL")

    @field_validator("sdl_query_origin", mode="before")
    @classmethod
    def validate_sdl_query_origin(cls, value: object) -> str | None:
        """Validate the SDL query origin, failing open when it is invalid."""
        if value is None:
            return None
        if not isinstance(value, str):
            logger.warning("Ignoring non-string SDL query origin.")
            return None

        query_origin = value.strip()
        if query_origin == "":
            return None
        if re.fullmatch(SDL_QUERY_ORIGIN_PATTERN, query_origin) is None:
            logger.warning(
                "Ignoring invalid SDL query origin.",
                extra={"sdl_query_origin": query_origin},
            )
            return None

        return query_origin

    @field_validator("sdl_console_account_ids", "sdl_console_site_ids", mode="before")
    @classmethod
    def validate_sdl_console_scope_ids_to_list_of_str(
        cls, value: str | list[str] | int | None
    ) -> list[str] | None:
        """Parse comma-separated scope IDs into a list.

        Handles multiple input formats:
        - Comma-separated string: "123,456,789"
        - JSON array: ["123", "456"]
        - Single integer (from JSON parsing): 426418030212073761
        - Single string: "426418030212073761"

        Args:
            value: Either a comma-separated string, list of scope IDs, single integer, or None

        Returns:
            List of scope IDs as strings or None
        """
        match value:
            case None:
                return None
            case int():
                # If it's an integer (from JSON parsing of a numeric string), convert to string list
                return [str(value)]
            case list():
                # If already a list, clean it up and convert all elements to strings
                scope_ids = [str(aid).strip() for aid in value if str(aid).strip()]
                return scope_ids if scope_ids else None
            case str():
                # If a string, split by comma and clean up whitespace
                scope_ids = [aid.strip() for aid in value.split(",") if aid.strip()]
                return scope_ids if scope_ids else None
            case _:
                assert_never(value)

    @field_validator("sdl_console_account_ids", "sdl_console_site_ids", mode="after")
    @classmethod
    def validate_sdl_console_scope_ids_are_numeric(
        cls, values: list[str] | None
    ) -> list[str] | None:
        """Once we have correctly parsed a list of strings, check each is purely numeric and so plausibly an scope-ID."""
        if values is None:
            return None
        for val in values:
            if not val.isnumeric():
                raise ValueError(f"'{val}' is not a numeric string")
        return values

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
        """Full GraphQL URL combining base URL and endpoint.

        Raises:
            ValueError: If base URL is not configured.
        """
        if self.sentinelone_console_base_url is None:
            raise ValueError("Console base URL not configured.")
        return f"{self.sentinelone_console_base_url}{self.sentinelone_console_graphql_endpoint}"

    @property
    def alerts_graphql_url(self) -> str:
        """Full GraphQL URL for alerts/UAM endpoint.

        Raises:
            ValueError: If base URL is not configured.
        """
        if self.sentinelone_console_base_url is None:
            raise ValueError("Console base URL not configured.")
        return f"{self.sentinelone_console_base_url}{self.sentinelone_alerts_graphql_endpoint}"

    @property
    def misconfigurations_graphql_url(self) -> str:
        """Full GraphQL URL for XSPM misconfigurations endpoint.

        Raises:
            ValueError: If base URL is not configured.
        """
        if self.sentinelone_console_base_url is None:
            raise ValueError("Console base URL not configured.")
        return f"{self.sentinelone_console_base_url}{self.sentinelone_misconfigurations_graphql_endpoint}"

    @property
    def vulnerabilities_graphql_url(self) -> str:
        """Full GraphQL URL for XSPM vulnerabilities endpoint.

        Raises:
            ValueError: If base URL is not configured.
        """
        if self.sentinelone_console_base_url is None:
            raise ValueError("Console base URL not configured.")
        return f"{self.sentinelone_console_base_url}{self.sentinelone_vulnerabilities_graphql_endpoint}"

    @property
    def inventory_api_url(self) -> str:
        """Full REST API URL for Unified Asset Inventory endpoint.

        Raises:
            ValueError: If base URL is not configured.
        """
        if self.sentinelone_console_base_url is None:
            raise ValueError("Console base URL not configured.")
        return f"{self.sentinelone_console_base_url}{self.sentinelone_inventory_restapi_endpoint}"

    @property
    def sdl_full_url(self) -> str:
        """Full base URL for the SDL API.

        When `sdl_base_url` is configured, it is returned as-is because the SDL API is served at
        the root of that host.  Otherwise, the console base URL with `/sdl` appended is returned
        (the traditional external console layout).

        Raises:
            ValueError: If neither SDL base URL nor console base URL is configured.
        """
        if self.sdl_base_url is not None:
            return self.sdl_base_url
        if self.sentinelone_console_base_url is not None:
            return f"{self.sentinelone_console_base_url}{_SDL_ENDPOINT_PATH}"
        raise ValueError(
            "SDL base URL not configured. Set either "
            f"{SDL_BASE_URL_ENV} or {CONSOLE_BASE_URL_ENV}."
        )

    def model_post_init(self, __context: object, /) -> None:
        """Log configuration and validate required fields after initialization."""
        # Validate required fields first
        errors = []
        if not self.sdl_api_token or not self.graphql_service_token:
            errors.append(f"{CONSOLE_TOKEN_ENV}")
        if not self.sentinelone_console_base_url:
            errors.append(f"{CONSOLE_BASE_URL_ENV}")

        if errors:
            raise ValueError(
                f"The following environment variables must be set: {', '.join(errors)}"
            )

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

        # Log SDL URL configuration
        logger.info(
            "SDL Base URL configured",
            extra={
                "sdl_base_url": self.sdl_full_url,
                "dedicated": self.sdl_base_url is not None,
            },
        )

        # Log token presence without exposing values
        logger.info(
            "%sCONSOLE_TOKEN is configured (used for both Console and SDL access)", ENV_PREFIX
        )


_DEPRECATED_ENV_VARS: Final[tuple[str, ...]] = (
    f"{ENV_PREFIX}PURPLE_AI_ACCOUNT_ID",
    f"{ENV_PREFIX}PURPLE_AI_TEAM_TOKEN",
)


def _warn_on_deprecated_env_vars() -> None:
    """Emit a WARNING for each deprecated env var still present in the environment."""
    for env_var in _DEPRECATED_ENV_VARS:
        if os.environ.get(env_var) is not None:
            logger.warning("%s is removed. This env var is now ignored.", env_var)


@lru_cache
def _load_base_settings() -> Settings:
    """Load and cache the base settings instance.

    This is a private cached helper that loads settings from environment
    variables exactly once.

    Returns:
        Settings: The base application settings

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    try:
        settings = Settings()

        # Surface deprecated env vars to operators so misconfiguration is
        # visible at startup.
        _warn_on_deprecated_env_vars()

        # Register sensitive tokens with logging filter to prevent leakage
        if settings.sdl_api_token or settings.graphql_service_token:
            try:
                from purple_mcp.logging_security import register_secret

                if settings.sdl_api_token:
                    register_secret(settings.sdl_api_token)
                if settings.graphql_service_token:
                    register_secret(settings.graphql_service_token)
                if settings.vt_api_key:
                    register_secret(settings.vt_api_key)
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


def validate_request_credentials(settings: Settings, require_base_url: bool = True) -> None:
    """Validate that required credentials are available for the current request.

    This helper function centralizes credential validation logic used across
    all MCP tools.

    Args:
        settings: The Settings instance to validate
        require_base_url: Whether to validate that console base URL is set.
            Default is True. Set to False for tools that only need the token
            (e.g., alerts management which uses a different GraphQL endpoint).

    Raises:
        ValueError: If required credentials are missing.

    Example:
        ```python
        settings = get_settings()
        validate_request_credentials(settings)  # Validates both token and URL
        validate_request_credentials(settings, require_base_url=False)  # Token only
        ```
    """
    if settings.graphql_service_token is None:
        raise ValueError("GraphQL service token not configured.")

    if require_base_url and settings.sentinelone_console_base_url is None:
        raise ValueError("Console base URL not configured.")


def get_settings() -> Settings:
    """Get the cached application settings instance.

    Returns:
        Settings: The application settings.

    Raises:
        ValidationError: If required settings are missing or invalid.
    """
    return _load_base_settings()


# Create a global settings instance for easy importing
# Only create if environment is properly configured (avoids import-time errors during testing)
# Note: This calls _load_base_settings indirectly through get_settings, but since
# request overrides are not active at import time, it returns the cached base settings.
try:
    settings = get_settings()
except Exception:
    # Settings will be None if initialization fails (e.g., during testing)
    settings = None
