"""Configuration for inventory client."""

from pydantic import Field, field_validator
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


class InventoryConfig(_ProgrammaticSettings):
    """Configuration for Unified Asset Inventory API client."""

    model_config = SettingsConfigDict(validate_assignment=True)

    base_url: str = Field(
        ...,
        description="Base URL for the inventory API (must use HTTPS).",
    )
    api_endpoint: str = Field(
        ...,
        description="API endpoint path for the inventory service.",
    )
    api_token: str = Field(
        ...,
        description="Bearer token for authentication.",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base_url.

        Requirements:
        1. Must use HTTPS protocol
        2. Strips trailing slashes

        Args:
            v: The base_url value to validate

        Returns:
            Normalized base_url

        Raises:
            ValueError: If base_url doesn't use HTTPS
        """
        if not v:
            raise ValueError("base_url cannot be empty")

        # Require HTTPS protocol
        if not v.startswith("https://"):
            raise ValueError("base_url must use HTTPS protocol")

        # Strip trailing slashes
        return v.rstrip("/")

    @field_validator("api_endpoint")
    @classmethod
    def validate_api_endpoint(cls, v: str) -> str:
        """Validate and normalize api_endpoint.

        Requirements:
        1. Must start with a single forward slash
        2. Must not end with trailing slashes

        Args:
            v: The api_endpoint value to validate

        Returns:
            Normalized api_endpoint

        Raises:
            ValueError: If api_endpoint is empty
        """
        if not v:
            raise ValueError("api_endpoint cannot be empty")

        # Strip all leading and trailing slashes, then add exactly one leading slash
        normalized = "/" + v.strip("/")

        return normalized

    @property
    def full_url(self) -> str:
        """Get the full URL for the inventory API."""
        return f"{self.base_url}{self.api_endpoint}"
