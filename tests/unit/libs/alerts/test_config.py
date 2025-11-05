"""Tests for alerts configuration."""

import os
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from purple_mcp.libs.alerts.config import AlertsConfig


class TestAlertsConfig:
    """Test AlertsConfig class."""

    def test_config_initialization_with_required_fields(self) -> None:
        """Test that config initializes correctly with required fields."""
        config = AlertsConfig(graphql_url="https://example.test/graphql", auth_token="test-token")

        assert config.graphql_url == "https://example.test/graphql"
        assert config.auth_token == "test-token"
        assert config.timeout == 30.0  # Default value
        assert config.supports_view_type is True  # Default value
        assert config.supports_data_sources is True  # Default value

    def test_config_initialization_with_all_fields(self) -> None:
        """Test that config initializes correctly with all fields specified."""
        config = AlertsConfig(
            graphql_url="https://example.test/graphql",
            auth_token="test-token",
            timeout=60.0,
            supports_view_type=False,
            supports_data_sources=False,
        )

        assert config.graphql_url == "https://example.test/graphql"
        assert config.auth_token == "test-token"
        assert config.timeout == 60.0
        assert config.supports_view_type is False
        assert config.supports_data_sources is False

    def test_config_missing_graphql_url(self) -> None:
        """Test that missing graphql_url raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AlertsConfig(auth_token="test-token")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("graphql_url",)

    def test_config_missing_auth_token(self) -> None:
        """Test that missing auth_token raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AlertsConfig(graphql_url="https://example.test/graphql")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("auth_token",)

    def test_config_missing_both_required_fields(self) -> None:
        """Test that missing both required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AlertsConfig()

        errors = exc_info.value.errors()
        assert len(errors) == 2
        error_locs = {error["loc"] for error in errors}
        assert ("graphql_url",) in error_locs
        assert ("auth_token",) in error_locs

    def test_config_ignores_environment_variables(self) -> None:
        """Test that config doesn't load from environment variables."""
        # Set environment variables that would be loaded by regular BaseSettings
        original_env: dict[str, str | None] = {}
        test_env_vars = {
            "GRAPHQL_URL": "https://env.example.test/graphql",
            "AUTH_TOKEN": "env-token",
            "TIMEOUT": "45.0",
            "SUPPORTS_VIEW_TYPE": "false",
            "SUPPORTS_DATA_SOURCES": "false",
        }

        # Save original values and set test values
        for key, value in test_env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            # Even with env vars set, should still require explicit values
            with pytest.raises(ValidationError):
                AlertsConfig()

            # Explicit values should be used, not env vars
            config = AlertsConfig(
                graphql_url="https://explicit.example.test/graphql", auth_token="explicit-token"
            )

            assert config.graphql_url == "https://explicit.example.test/graphql"
            assert config.auth_token == "explicit-token"
            assert config.timeout == 30.0  # Default, not env var
            assert config.supports_view_type is True  # Default, not env var
            assert config.supports_data_sources is True  # Default, not env var

        finally:
            # Restore original environment
            for key in test_env_vars:
                if original_env[key] is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = str(original_env[key])

    def test_config_timeout_validation(self) -> None:
        """Test timeout field accepts numeric values."""
        # Test integer timeout
        config1 = AlertsConfig(
            graphql_url="https://example.test/graphql", auth_token="test-token", timeout=45
        )
        assert config1.timeout == 45.0

        # Test float timeout
        config2 = AlertsConfig(
            graphql_url="https://example.test/graphql", auth_token="test-token", timeout=45.5
        )
        assert config2.timeout == 45.5

    def test_config_boolean_fields(self) -> None:
        """Test boolean fields accept various boolean representations."""
        config = AlertsConfig(
            graphql_url="https://example.test/graphql",
            auth_token="test-token",
            supports_view_type=False,
            supports_data_sources=True,
        )

        assert config.supports_view_type is False
        assert config.supports_data_sources is True

    def test_config_field_descriptions(self) -> None:
        """Test that field descriptions are properly set."""
        schema = AlertsConfig.model_json_schema()
        properties = schema["properties"]

        assert "description" in properties["graphql_url"]
        assert "GraphQL endpoint URL" in properties["graphql_url"]["description"]

        assert "description" in properties["auth_token"]
        assert "Bearer token" in properties["auth_token"]["description"]

        assert "description" in properties["timeout"]
        assert "timeout" in properties["timeout"]["description"]

    def test_config_programmatic_settings_inheritance(self) -> None:
        """Test that AlertsConfig properly inherits from _ProgrammaticSettings."""
        from purple_mcp.libs.alerts.config import _ProgrammaticSettings

        assert issubclass(AlertsConfig, _ProgrammaticSettings)

        # Test that the settings customization method exists
        assert hasattr(AlertsConfig, "settings_customise_sources")

        # The customization should return only init_settings
        mock_init = Mock()
        mock_env = Mock()
        mock_dotenv = Mock()
        mock_file_secret = Mock()
        result = AlertsConfig.settings_customise_sources(
            AlertsConfig, mock_init, mock_env, mock_dotenv, mock_file_secret
        )
        assert len(result) == 1
        assert result[0] is mock_init  # Only init_settings should be returned
