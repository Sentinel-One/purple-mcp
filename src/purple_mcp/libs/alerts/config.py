"""Configuration for Alerts client."""

from pydantic import Field
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


class AlertsConfig(_ProgrammaticSettings):
    """Configuration for the Alerts client."""

    graphql_url: str = Field(
        ...,
        description="GraphQL endpoint URL for Unified Alerts Management.",
    )
    auth_token: str = Field(
        ...,
        description="Bearer token for authentication.",
    )
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds.",
    )
    supports_view_type: bool = Field(
        default=True,
        description="Whether the schema supports viewType parameter in queries.",
    )
    supports_data_sources: bool = Field(
        default=True,
        description="Whether the schema supports dataSources field in alert responses.",
    )
