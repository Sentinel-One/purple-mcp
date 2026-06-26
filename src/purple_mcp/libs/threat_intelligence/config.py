"""Configuration for Threat Intelligence client."""

from pydantic import Field, PositiveFloat, PositiveInt, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


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


class ThreatIntelligenceConfig(_ProgrammaticSettings):
    """Configuration for the Threat Intelligence client."""

    model_config = SettingsConfigDict(extra="forbid", frozen=True)

    api_key: str = Field(
        ...,
        description="VirusTotal API key for authentication.",
    )
    timeout: PositiveFloat = Field(
        default=30.0,
        description="Request timeout in seconds.",
    )
    file_relationships_limit: PositiveInt = Field(
        default=100,
        description="Maximum number of file relationships to retrieve (API max is 100).",
    )
    intelligence_search_limit: PositiveInt = Field(
        default=10,
        description="Maximum number of intelligence search results (API max is 300).",
    )
    file_behavior_limit: PositiveInt = Field(
        default=50,
        description="Maximum number of file behavior reports to retrieve (API max is 50).",
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that api_key is not empty after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("api_key cannot be empty")
        return stripped
