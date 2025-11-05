"""Tests for SDL configuration module."""

import pytest
from pydantic import ValidationError

from purple_mcp.libs.sdl.config import create_sdl_settings


class TestCreateSdlSettings:
    """Test cases for create_sdl_settings function."""

    def test_create_sdl_settings_basic(self) -> None:
        """Test basic settings creation with minimal required fields."""
        settings = create_sdl_settings(base_url="https://example.test", auth_token="test-token")

        assert settings.base_url == "https://example.test/sdl"
        assert settings.auth_token == "Bearer test-token"
        assert settings.http_timeout == 30  # default

    def test_create_sdl_settings_url_normalization(self) -> None:
        """Test URL normalization: trailing slash removal and /sdl path appending."""
        test_cases = [
            ("https://example.test/", "https://example.test/sdl"),
            ("https://example.test", "https://example.test/sdl"),
            ("https://example.test/sdl", "https://example.test/sdl"),
            ("https://example.test/sdl/", "https://example.test/sdl"),
        ]

        for input_url, expected_url in test_cases:
            settings = create_sdl_settings(base_url=input_url, auth_token="test-token")
            assert settings.base_url == expected_url

    def test_create_sdl_settings_auth_token_normalization(self) -> None:
        """Test auth token normalization: Bearer prefix auto-addition."""
        test_cases = [
            ("test-token", "Bearer test-token"),
            ("Bearer test-token", "Bearer test-token"),
            ("  test-token  ", "Bearer test-token"),
            ("  Bearer test-token  ", "Bearer test-token"),
        ]

        for input_token, expected_token in test_cases:
            settings = create_sdl_settings(base_url="https://example.test", auth_token=input_token)
            assert settings.auth_token == expected_token

    def test_create_sdl_settings_explicit_configuration(self) -> None:
        """Test explicit configuration via create_sdl_settings kwargs."""
        settings = create_sdl_settings(
            base_url="https://example.test", auth_token="test-token", http_timeout=60
        )

        assert settings.base_url == "https://example.test/sdl"
        assert settings.auth_token == "Bearer test-token"
        assert settings.http_timeout == 60

    def test_create_sdl_settings_invalid_url(self) -> None:
        """Test validation error for invalid base URL."""
        with pytest.raises(ValidationError, match="base_url must start with https"):
            create_sdl_settings(base_url="ftp://example.test", auth_token="test-token")

    def test_create_sdl_settings_http_url_rejected(self) -> None:
        """Test validation error for HTTP URLs - only HTTPS allowed."""
        with pytest.raises(
            ValidationError, match="base_url must use HTTPS for secure communication"
        ):
            create_sdl_settings(base_url="http://example.test", auth_token="test-token")

    def test_create_sdl_settings_https_url_accepted(self) -> None:
        """Test that HTTPS URLs are accepted."""
        settings = create_sdl_settings(base_url="https://example.test", auth_token="test-token")
        assert settings.base_url == "https://example.test/sdl"

    def test_create_sdl_settings_missing_required_fields(self) -> None:
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            create_sdl_settings()

    def test_create_sdl_settings_field_validation(self) -> None:
        """Test field validation for numeric constraints."""
        # Test valid ranges
        settings = create_sdl_settings(
            base_url="https://example.test",
            auth_token="test-token",
            http_timeout=60,
            max_timeout_seconds=120,
            http_max_retries=5,
        )
        assert settings.http_timeout == 60
        assert settings.max_timeout_seconds == 120
        assert settings.http_max_retries == 5

        # Test invalid ranges
        with pytest.raises(ValidationError):
            create_sdl_settings(
                base_url="https://example.test",
                auth_token="test-token",
                http_timeout=0,  # Below minimum
            )

    def test_create_sdl_settings_skip_tls_security_warning(self) -> None:
        """Test that skip_tls_verify triggers security validation."""
        # This should work (False is default and safe)
        settings = create_sdl_settings(
            base_url="https://example.test", auth_token="test-token", skip_tls_verify=False
        )
        assert settings.skip_tls_verify is False

        # This should trigger security validation but not fail in development environment
        settings = create_sdl_settings(
            base_url="https://example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="development",
        )
        assert settings.skip_tls_verify is True
