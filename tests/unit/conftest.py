"""Pytest configuration and shared fixtures for the purple-mcp test suite.

This module provides common fixtures and configuration used across all tests,
particularly for environment variable management and logging setup.
"""

import logging
import os
import uuid
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from purple_mcp.config import ENV_PREFIX


@pytest.fixture(scope="session")
def test_logging() -> Generator[None, None, None]:
    """Configure logging for test sessions."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Override any existing configuration
    )

    # Suppress overly verbose third-party logs during testing
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    yield

    # Clean up logging handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)


@pytest.fixture
def clean_env() -> Generator[dict[str, str | None], None, None]:
    """Provide a clean environment for testing, restoring state afterwards.

    This fixture captures the current environment state, clears relevant
    environment variables, and restores them after the test completes.

    Yields:
        Dict containing the original environment state
    """
    # Environment variables that our config uses
    config_env_vars = [
        f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN",
        f"{ENV_PREFIX}CONSOLE_TOKEN",
        f"{ENV_PREFIX}CONSOLE_BASE_URL",
        f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT",
        f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT",
    ]

    # Capture current state
    original_env = {}
    for var in config_env_vars:
        original_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    yield original_env

    # Restore original state
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


@pytest.fixture
def valid_env_config(clean_env: dict[str, str | None]) -> dict[str, str]:
    """Provide a valid configuration environment for testing.

    Returns:
        Dict containing valid test configuration values
    """
    config = {
        f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN": "test-sdl-token-12345",
        f"{ENV_PREFIX}CONSOLE_TOKEN": "test-console-token-67890",
        f"{ENV_PREFIX}CONSOLE_BASE_URL": "https://test.example.test",
        f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT": "/web/api/v2.1/graphql",
        f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT": "/web/api/v2.1/unifiedalerts/graphql",
    }

    # Set environment variables
    for key, value in config.items():
        os.environ[key] = value

    return config


@pytest.fixture
def minimal_env_config(clean_env: dict[str, str | None]) -> dict[str, str]:
    """Provide minimal required configuration for testing.

    Returns:
        Dict containing only required configuration values
    """
    config = {
        f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN": "minimal-sdl-token",
        f"{ENV_PREFIX}CONSOLE_TOKEN": "minimal-console-token",
    }

    # Set environment variables
    for key, value in config.items():
        os.environ[key] = value

    return config


@pytest.fixture
def mock_env_var() -> Callable[[str, str], AbstractContextManager[None]]:
    """Factory fixture for temporarily setting environment variables.

    Usage:
        def test_something(mock_env_var):
            with mock_env_var("MY_VAR", "my_value"):
                # Test code here
                pass
    """

    def _mock_env_var(key: str, value: str) -> AbstractContextManager[None]:
        return patch.dict(os.environ, {key: value})

    return _mock_env_var


# Pytest configuration
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require external resources)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (no external dependencies)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark tests based on their location or content."""
    for item in items:
        # Mark all tests in test_config.py as unit tests by default
        if "test_config" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark tests that use network or external resources
        if any(keyword in item.name.lower() for keyword in ["network", "api", "external"]):
            item.add_marker(pytest.mark.integration)


# Test session scoped fixtures for expensive setup
@pytest.fixture(scope="session")
def test_data_dir() -> str:
    """Provide path to test data directory."""
    return str(Path(__file__).parent / "data")


# Cleanup fixture to ensure tests don't interfere with each other
@pytest.fixture(autouse=True)
def reset_lru_cache() -> Generator[None, None, None]:
    """Reset LRU caches between tests to ensure clean state."""
    yield

    # Import and clear the get_settings cache
    try:
        from purple_mcp.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        # Module not available in this test context
        pass


@pytest.fixture
def mock_settings() -> Callable[..., MagicMock]:
    """Factory fixture for creating mock Settings objects with sensible defaults.

    Returns a factory function that creates a mock settings object with all
    necessary attributes pre-populated with test-friendly values. Tests can
    override specific fields by passing keyword arguments.

    Usage:
        def test_something(mock_settings):
            settings = mock_settings(sdl_api_token="custom-token")
            # settings.sdl_api_token == "custom-token"
            # settings.sentinelone_console_base_url == "https://console.test" (default)

    Returns:
        Callable that creates mock settings objects with customizable attributes
    """
    from unittest.mock import MagicMock

    def _create_settings(**overrides: str) -> MagicMock:
        """Create a mock settings object with defaults and optional overrides.

        Args:
            **overrides: Attribute values to override from defaults

        Returns:
            Mock object with all Settings attributes
        """
        mock = MagicMock()

        # Default values for all Settings fields
        defaults: dict[str, str] = {
            # Tokens
            "sdl_api_token": "test-sdl-token",
            "graphql_service_token": "test-graphql-token",
            # Base URLs and endpoints
            "sentinelone_console_base_url": "https://console.test",
            "sentinelone_console_graphql_endpoint": "/web/api/v2.1/graphql",
            "sentinelone_alerts_graphql_endpoint": "/web/api/v2.1/unifiedalerts/graphql",
            "sentinelone_misconfigurations_graphql_endpoint": "/web/api/v2.1/xspm/findings/misconfigurations/graphql",
            "sentinelone_vulnerabilities_graphql_endpoint": "/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
            "sentinelone_inventory_restapi_endpoint": "/web/api/v2.1/xdr/assets",
            # Purple AI user details
            "purple_ai_account_id": "test-account",
            "purple_ai_team_token": "test-team-token",
            "purple_ai_email_address": "test@example.test",
            "purple_ai_session_id": uuid.uuid4().hex,
            "purple_ai_user_agent": "test-agent",
            "purple_ai_build_date": "2025-01-01",
            "purple_ai_build_hash": "testhash",
            "purple_ai_console_version": "1.0.0",
            # Environment
            "environment": "development",
            # Computed properties
            "graphql_full_url": "https://console.test/web/api/v2.1/graphql",
            "alerts_graphql_url": "https://console.test/web/api/v2.1/unifiedalerts/graphql",
            "misconfigurations_graphql_url": "https://console.test/web/api/v2.1/xspm/findings/misconfigurations/graphql",
            "vulnerabilities_graphql_url": "https://console.test/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
            "inventory_api_url": "https://console.test/web/api/v2.1/xdr/assets",
        }

        # Apply overrides
        defaults.update(overrides)

        # Set all attributes on the mock
        for key, value in defaults.items():
            setattr(mock, key, value)

        return mock

    return _create_settings


@pytest.fixture
def purple_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up required environment variables for Purple AI tests.

    This fixture sets the PURPLEMCP_CONSOLE_TOKEN environment variable
    that is required by Purple AI API calls. Use this fixture instead
    of manually setting environment variables in individual tests.

    Usage:
        async def test_purple_ai_feature(purple_ai_env):
            # PURPLEMCP_CONSOLE_TOKEN is already set
            result = await ask_purple(config, "query")
    """
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "test_token")
