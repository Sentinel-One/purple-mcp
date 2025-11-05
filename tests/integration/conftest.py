"""Integration test configuration and utilities.

This module provides shared fixtures and utilities for integration tests
that require real environment variables and external service connections.
"""

import os
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from purple_mcp.config import ENV_PREFIX

UTC = ZoneInfo("UTC")


def load_test_env() -> None:
    """Load environment variables from .env.test file if it exists."""
    env_test_path = Path(__file__).parent.parent.parent / ".env.test"
    if env_test_path.exists():
        with env_test_path.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value


def is_real_environment() -> tuple[bool, list[str]]:
    """Check if we have real environment variables for integration testing.

    Returns:
        Tuple of (is_real, missing_or_example_vars)
    """
    # Load test environment first
    load_test_env()

    required_vars = {
        f"{ENV_PREFIX}CONSOLE_TOKEN": "Console API token",
        f"{ENV_PREFIX}CONSOLE_BASE_URL": "Console base URL",
    }

    example_values = {
        "https://console.example.test",
        "console.example.test",
        "example.test",
        "test-token",
        "your-token-here",
        "Bearer your-token",
        "",
        "none",
        "null",
    }

    missing_or_example = []

    for var, description in required_vars.items():
        value = os.environ.get(var, "").strip()
        if not value or value.lower() in example_values:
            missing_or_example.append(f"{var} ({description})")

    return len(missing_or_example) == 0, missing_or_example


@pytest.fixture(scope="session")
def integration_env_check() -> Generator[dict[str, str], None, None]:
    """Check integration environment and skip if not properly configured."""
    is_real, missing_vars = is_real_environment()

    if not is_real:
        missing_list = "\n  - ".join(missing_vars)
        pytest.skip(
            f"Integration tests require real environment variables. "
            f"Missing or example values found for:\n  - {missing_list}\n\n"
            f"Please set these in .env.test file with real values."
        )

    # Return environment variables for tests to use
    yield {
        f"{ENV_PREFIX}CONSOLE_TOKEN": os.environ[f"{ENV_PREFIX}CONSOLE_TOKEN"],
        f"{ENV_PREFIX}CONSOLE_BASE_URL": os.environ[f"{ENV_PREFIX}CONSOLE_BASE_URL"],
    }


@pytest.fixture
def integration_settings(integration_env_check: dict[str, str]) -> Generator[None, None, None]:
    """Ensure settings are properly configured for integration tests."""
    # Clear any cached settings from unit tests
    try:
        from purple_mcp.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass

    yield

    # Clean up after test
    try:
        from purple_mcp.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def integration_timeout() -> int:
    """Provide extended timeout for integration tests."""
    return 60  # 60 seconds for real API calls


@pytest.fixture
def test_time_range() -> tuple[datetime, datetime]:
    """Provide a reasonable time range for testing queries."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=1)  # Last hour
    return start_time, end_time


@pytest.fixture
def test_time_range_ms(test_time_range: tuple[datetime, datetime]) -> tuple[int, int]:
    """Convert time range to milliseconds for GraphQL filters."""
    start_time, end_time = test_time_range
    start_ms = int(start_time.timestamp() * 1_000)
    end_ms = int(end_time.timestamp() * 1_000)
    return start_ms, end_ms


@pytest.fixture
def recent_time_range_ms() -> tuple[int, int]:
    """Provide a recent time range in milliseconds for GraphQL filters."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(minutes=30)  # Last 30 minutes
    start_ms = int(start_time.timestamp() * 1_000)
    end_ms = int(end_time.timestamp() * 1_000)
    return start_ms, end_ms


@pytest.fixture
def recent_time_range_iso() -> tuple[str, str]:
    """Provide a recent time range in ISO 8601 format for PowerQuery testing.

    Note:
        The defintion of a 'recent' time-range in this fixture must
        include enough data expected by the integration tests.
    """
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=24)
    start_datetime = start_time.isoformat().replace("+00:00", "Z")
    end_datetime = end_time.isoformat().replace("+00:00", "Z")
    return start_datetime, end_datetime


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest for integration tests."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests requiring real environment"
    )
    config.addinivalue_line("markers", "slow: marks tests as slow (may take several seconds)")

    config.addinivalue_line(
        "markers",
        "alerts_integration: marks tests as alerts integration tests requiring real UAM access",
    )
    config.addinivalue_line(
        "markers", "alerts_performance: marks tests as alerts performance tests"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark integration tests."""
    for item in items:
        # Mark all tests in integration directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)
