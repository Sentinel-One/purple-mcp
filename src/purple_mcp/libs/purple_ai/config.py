"""Configuration for Purple AI client."""

from datetime import datetime

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


def validate_scope_id(v: str | None) -> str | None:
    """Reject empty / whitespace-only console scope ID values.

    Scope IDs are typically 19-digit flake IDs but we do not require
    numericness here — console identifier schemes may evolve. The check is
    limited to ruling out obviously-invalid empty strings.

    Args:
        v: The scope ID value to validate, or None.

    Returns:
        The stripped scope ID, or None if the input was None.

    Raises:
        ValueError: If the value is an empty or whitespace-only string.
    """
    if v is None:
        return None
    stripped = v.strip()
    if not stripped:
        raise ValueError("scope ID must be a non-empty string")
    return stripped


class _ProgrammaticSettings(BaseSettings):
    """Base class to disable environment variable loading for settings."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Disable all settings sources except for programmatic initialization."""
        return (init_settings,)


class PurpleAIUserDetails(_ProgrammaticSettings):
    """User details for Purple AI query."""

    session_id: str | None = Field(..., description="Session ID for the user.")
    email_address: str | None = Field(default=None, description="Email address of the user.")
    user_agent: str | None = Field(..., description="User agent for the request.")
    build_date: str | None = Field(default=None, description="Build date of the client.")
    build_hash: str | None = Field(default=None, description="Build hash of the client.")
    user_time: datetime | None = Field(
        default_factory=lambda: datetime.now().astimezone(),
        description="Timezone-aware local timestamp of the request; defaults to now.",
    )


class PurpleAIConsoleDetails(_ProgrammaticSettings):
    """Console details for Purple AI query."""

    base_url: str = Field(..., description="Base URL of the console.")
    console_id: str | None = Field(default=None, description="Console (deployment) ID.")
    tenant_id: str | None = Field(default=None, description="Tenant scope ID.")
    account_id: str | None = Field(default=None, description="Account scope ID.")
    site_id: str | None = Field(default=None, description="Site scope ID.")
    version: str | None = Field(default=None, description="Version of the console.")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base_url uses HTTPS and normalize it."""
        # Strip whitespace before validation
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("base_url must use HTTPS protocol")
        return v

    _validate_scope_ids = field_validator("console_id", "tenant_id", "account_id", "site_id")(
        validate_scope_id
    )


class PurpleAIConfig(_ProgrammaticSettings):
    """Configuration for the Purple AI client."""

    graphql_url: str = Field(
        "https://console.sentinelone.net/web/api/v2.1/graphql",
        description="GraphQL endpoint URL for Purple AI.",
    )
    auth_token: str = Field(
        ...,
        description="Authentication token for GraphQL API requests.",
    )
    timeout: float = Field(
        default=120.0,
        description="Request timeout in seconds.",
    )
    user_details: PurpleAIUserDetails
    console_details: PurpleAIConsoleDetails

    @field_validator("graphql_url")
    @classmethod
    def validate_graphql_url(cls, v: str) -> str:
        """Validate that graphql_url uses HTTPS and normalize it."""
        # Strip whitespace before validation
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("graphql_url must use HTTPS protocol")
        return v

    @field_validator("auth_token")
    @classmethod
    def validate_auth_token(cls, v: str) -> str:
        """Validate that auth_token is not empty after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("auth_token cannot be empty")
        return stripped

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate that timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be greater than 0")
        return v
