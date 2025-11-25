"""Unit tests for helper functions in purple_mcp.cli.

These tests focus on the small, pure-logic helpers that were introduced to
reduce the complexity of the public ``main`` function.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from unittest.mock import Mock, call, patch

import pytest

import purple_mcp.cli as cli
from purple_mcp.config import ENV_PREFIX


@pytest.fixture(autouse=True)
def _clear_env() -> Generator[None, None, None]:
    """Ensure environment is clean for each test."""
    original = os.environ.copy()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


class TestSetupLogging:
    """Ensure ``_setup_logging`` configures the root logger as expected."""

    def test_verbose_sets_debug(self) -> None:
        """Test that verbose flag sets logging level to DEBUG."""
        with patch("logging.basicConfig") as basic_config:
            cli._setup_logging(verbose=True)
            basic_config.assert_called_once()
            _args, kwargs = basic_config.call_args
            assert kwargs["level"] == logging.DEBUG

    def test_non_verbose_sets_info(self) -> None:
        """Test that non-verbose flag sets logging level to INFO."""
        with patch("logging.basicConfig") as basic_config:
            cli._setup_logging(verbose=False)
            basic_config.assert_called_once()
            _args, kwargs = basic_config.call_args
            assert kwargs["level"] == logging.INFO


class TestApplyEnvironmentOverrides:
    """Verify environment variable assignments."""

    def test_tokens_and_urls_are_set(self) -> None:
        """Test that environment variables are properly set from parameters."""
        cli._apply_environment_overrides(
            transport_mode="http",
            sdl_api_token="sdl",
            graphql_service_token="graphql",
            console_base_url="https://example.test",
            graphql_endpoint="/custom",
            alerts_graphql_endpoint="/custom/alerts",
            stateless_http=True,
        )

        assert os.environ[f"{ENV_PREFIX}TRANSPORT_MODE"] == "http"
        assert os.environ[f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN"] == "sdl"
        assert os.environ[f"{ENV_PREFIX}CONSOLE_TOKEN"] == "graphql"
        assert os.environ[f"{ENV_PREFIX}CONSOLE_BASE_URL"] == "https://example.test"
        assert os.environ[f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT"] == "/custom"
        assert os.environ[f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT"] == "/custom/alerts"
        assert os.environ[f"{ENV_PREFIX}STATELESS_HTTP"] == "True"

    def test_defaults_are_not_overridden(self) -> None:
        """Default endpoint should *not* be written to the environment."""
        # Ensure the environment variable is not set before testing
        os.environ.pop(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", None)

        cli._apply_environment_overrides(
            transport_mode=None,
            sdl_api_token=None,
            graphql_service_token=None,
            console_base_url=None,
            graphql_endpoint="/web/api/v2.1/graphql",
            alerts_graphql_endpoint="/web/api/v2.1/unifiedalerts/graphql",
            stateless_http=None,
        )

        assert f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT" not in os.environ
        assert f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT" not in os.environ
        assert f"{ENV_PREFIX}STATELESS_HTTP" not in os.environ


class TestCreateSettings:
    """Test _create_settings helper function in isolation."""

    def test_create_settings_error_handling(self) -> None:
        """Test that _create_settings properly handles Settings() exceptions."""
        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.sys.exit") as mock_exit,
            patch("purple_mcp.cli.click.echo") as mock_echo,
        ):
            # Mock Settings to raise an exception
            mock_settings.side_effect = RuntimeError("Test configuration error")

            # Call the function
            cli._create_settings()

            # Assert Settings was called
            mock_settings.assert_called_once()

            # Assert sys.exit was called with status 1
            mock_exit.assert_called_once_with(1)

            # Assert error messages were printed in correct order
            expected_calls = [
                call("✗ Configuration error: Test configuration error", err=True),
                call("\nRequired environment variables or CLI options:", err=True),
                call(
                    f"  --graphql-service-token or {ENV_PREFIX}CONSOLE_TOKEN (used for both Console and SDL)",
                    err=True,
                ),
                call(f"  --console-base-url or {ENV_PREFIX}CONSOLE_BASE_URL", err=True),
                call(
                    "\nNote: Token must have Account or Site level permissions (not Global)",
                    err=True,
                ),
            ]
            mock_echo.assert_has_calls(expected_calls)

    def test_create_settings_success(self) -> None:
        """Test that _create_settings returns Settings instance when successful."""
        with patch("purple_mcp.cli.Settings") as mock_settings:
            # Mock Settings to return a valid instance
            mock_instance = Mock()
            mock_settings.return_value = mock_instance

            # Call the function
            result = cli._create_settings()

            # Assert Settings was called
            mock_settings.assert_called_once()

            # Assert the Settings instance is returned
            assert result is mock_instance
