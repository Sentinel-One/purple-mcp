"""Configuration for SDL integration using Pydantic Settings.

This module provides configuration management for the SDL (Singularity Data Lake)
integration with explicit code-based configuration, validation, and default values.
"""

import logging
import os
from typing import Final, TypedDict

import pydantic
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self, Unpack

from purple_mcp.libs.sdl.security import validate_tls_bypass_config

logger = logging.getLogger(__name__)

# SDL API path constants
SDL_API_PATH: Final[str] = "/sdl"


class TypedSDLSettings(TypedDict, total=False):
    """TypedDict for SDLSettings."""

    # Core SDL Configuration
    base_url: str
    auth_token: str

    # HTTP Client Configuration
    http_timeout: int
    max_timeout_seconds: int
    http_max_retries: int
    skip_tls_verify: bool

    # Query Configuration
    default_poll_timeout_ms: int
    default_poll_interval_ms: int

    # Query Limits
    max_query_results: int
    query_ttl_seconds: int

    # Environment Configuration
    environment: str


class SDLSettings(BaseSettings):
    """SDL integration configuration with explicit code-based settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # Core SDL Configuration
    base_url: str = Field(
        description=f"Base URL for SDL API. {SDL_API_PATH} will be appended if not present.",
    )

    auth_token: str = Field(
        description="Authentication token for SDL API (Bearer token format)",
    )

    # HTTP Client Configuration
    http_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds",
        ge=1,
        le=300,
    )

    max_timeout_seconds: int = Field(
        default=30,
        description="Maximum timeout for operations in seconds",
        ge=1,
        le=3600,
    )

    http_max_retries: int = Field(
        default=3,
        description="Maximum number of HTTP request retries",
        ge=0,
        le=10,
    )

    skip_tls_verify: bool = Field(
        default=False,
        description="Skip TLS certificate verification (SECURITY RISK - never use in production)",
    )

    # Query Configuration
    default_poll_timeout_ms: int = Field(
        default=30_000,
        description="Default timeout for polling query results in milliseconds",
        ge=1000,
        le=3600_000,
    )

    default_poll_interval_ms: int = Field(
        default=100,
        description="Default polling interval in milliseconds",
        ge=50,
        le=5000,
    )

    # Query Limits
    max_query_results: int = Field(
        default=10_000,
        description="Maximum number of query results to retrieve",
        ge=1,
        le=100_000,
    )

    query_ttl_seconds: int = Field(
        default=300,
        description="Query time-to-live in seconds",
        ge=30,
        le=3600,
    )

    # Environment Configuration
    environment: str = Field(
        default_factory=lambda: os.getenv("PURPLEMCP_ENV", "production"),
        description="Environment name for security validation (e.g., 'development', 'production'). "
        "Defaults to PURPLEMCP_ENV environment variable, or 'production' if not set.",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base URL is properly formatted and uses HTTPS.

        Security requirement: Only HTTPS URLs are accepted to ensure TLS encryption.
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with https://")

        # Enforce HTTPS-only for security
        if v.startswith("http://"):
            raise ValueError(
                "base_url must use HTTPS for secure communication. "
                "HTTP URLs are not permitted per security policy."
            )

        # Remove trailing slashes for consistency
        v = v.rstrip("/")

        # Ensure SDL API path is included
        if not v.endswith(SDL_API_PATH):
            v += SDL_API_PATH

        return v

    @field_validator("auth_token")
    @classmethod
    def validate_auth_token(cls, v: str) -> str:
        """Validate auth token format."""
        v = v.strip()
        if not v.startswith("Bearer "):
            v = f"Bearer {v}"
        return v

    @field_validator("http_timeout", "max_timeout_seconds")
    @classmethod
    def validate_positive_timeout(cls, v: int, info: pydantic.ValidationInfo) -> int:
        """Validate that timeout values are positive."""
        if v <= 0:
            field_name = info.field_name
            raise ValueError(f"{field_name} must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_tls_and_log_config(self) -> Self:
        """Validate TLS configuration and log after initialization."""
        # Validate TLS configuration with environment context
        validate_tls_bypass_config(self.skip_tls_verify, self.environment)

        # Log configuration after initialization
        logger.info("SDL configuration loaded successfully")
        logger.info("SDL Base URL configured", extra={"base_url": self.base_url})
        logger.info("HTTP Timeout configured", extra={"timeout_seconds": self.http_timeout})
        logger.info("Max Retries configured", extra={"max_retries": self.http_max_retries})
        logger.info("TLS Verify configured", extra={"tls_verify": not self.skip_tls_verify})
        logger.info(
            "Default Poll Timeout configured",
            extra={"poll_timeout_ms": self.default_poll_timeout_ms},
        )
        logger.info(
            "Default Poll Interval configured",
            extra={"poll_interval_ms": self.default_poll_interval_ms},
        )

        logger.info("SDL auth token is configured")

        # TLS bypass logging is handled by the shared security validation
        return self


def create_sdl_settings(**kwargs: Unpack[TypedSDLSettings]) -> SDLSettings:
    """Create SDL settings with custom configuration values.

    Args:
        **kwargs: Configuration values to override defaults

    Returns:
        SDLSettings: The SDL configuration settings with custom values

    Raises:
        ValidationError: If provided settings are invalid

    Example:
        custom_settings = create_sdl_settings(
            base_url="https://custom.example.com/sdl",
            auth_token="Bearer custom-token",
            http_timeout=60,
            default_poll_timeout_ms=60000
        )
    """
    try:
        settings = SDLSettings.model_validate(kwargs)

        # Register auth token with logging filter to prevent leakage
        try:
            from purple_mcp.logging_security import register_secret

            register_secret(settings.auth_token)
        except ImportError:
            # Filter module not available - this shouldn't happen in normal operation
            logger.warning(
                "Logging security filter not available for SDL - token may appear in logs"
            )

        return settings
    except Exception:
        logger.critical(
            "Failed to create SDL configuration",
            exc_info=True,
        )
        raise
