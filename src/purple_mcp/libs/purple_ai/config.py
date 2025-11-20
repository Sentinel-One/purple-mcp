"""Configuration for Purple AI client."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


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

    account_id: str = Field(..., description="Account ID for the user.")
    team_token: str = Field(..., description="Team token for the user.")
    session_id: str | None = Field(..., description="Session ID for the user.")
    email_address: str | None = Field(..., description="Email address of the user.")
    user_agent: str | None = Field(..., description="User agent for the request.")
    build_date: str | None = Field(..., description="Build date of the client.")
    build_hash: str | None = Field(..., description="Build hash of the client.")


class PurpleAIConsoleDetails(_ProgrammaticSettings):
    """Console details for Purple AI query."""

    base_url: str = Field(..., description="Base URL of the console.")
    version: str = Field(..., description="Version of the console.")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base_url uses HTTPS and normalize it."""
        # Strip whitespace before validation
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("base_url must use HTTPS protocol")
        return v


class PurpleAIConfig(_ProgrammaticSettings):
    """Configuration for the Purple AI client."""

    graphql_url: str = Field(
        "https://console.example.com/web/api/v2.1/graphql",
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
