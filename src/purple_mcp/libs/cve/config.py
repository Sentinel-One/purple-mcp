"""Configuration for CVE client."""

from pydantic import Field, HttpUrl, PositiveFloat, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from rfc3986 import uri_reference


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


class CVEConfig(_ProgrammaticSettings):
    """Configuration for the CVE client."""

    model_config = SettingsConfigDict(extra="forbid", frozen=True)

    base_url: str = Field(
        default="https://cve.circl.lu/api/",
        description="Base URL for CVE API.",
    )
    timeout: PositiveFloat = Field(
        default=30.0,
        description="Request timeout in seconds.",
    )

    @field_validator("base_url")
    @classmethod
    def validate_and_normalize_url(cls, v: str) -> str:
        """Validate base_url is a valid HTTPS URL and normalize it.

        Uses HttpUrl for validation, then rfc3986 for normalization per RFC 3986, then stores as str for simpler I/O.
        """
        # Validate using Pydantic's HttpUrl - raises ValidationError if invalid
        url_obj = HttpUrl(v)

        if url_obj.scheme != "https":
            raise ValueError("base_url must use HTTPS")
        normalized: str = uri_reference(v).normalize().unsplit()
        return normalized
