"""Tests for the user_agent module."""

import sys
from types import ModuleType
from unittest.mock import patch

from purple_mcp.user_agent import get_user_agent, get_version


class TestGetVersion:
    """Tests for get_version function."""

    def test_get_version_success(self) -> None:
        """Test successful version retrieval from __version__."""
        # Clear the cache first
        get_version.cache_clear()

        with patch("purple_mcp.__version__", "0.1.0"):
            version = get_version()
            assert version == "0.1.0"

        # Clear cache after test
        get_version.cache_clear()

    def test_get_version_import_error(self) -> None:
        """Test when __version__ cannot be imported (returns 'unknown')."""
        # Clear the cache first
        get_version.cache_clear()

        # Create a mock module without __version__ attribute to simulate
        # the attribute being missing, which triggers the fallback
        mock_purple_mcp = ModuleType("purple_mcp")
        # Intentionally don't set __version__ on this mock module

        with patch.dict(sys.modules, {"purple_mcp": mock_purple_mcp}):
            version = get_version()
            assert version == "unknown"

        # Clear cache after test
        get_version.cache_clear()

    def test_get_version_cached(self) -> None:
        """Test that version is cached."""
        # Clear the cache first
        get_version.cache_clear()

        with patch("purple_mcp.__version__", "1.2.3"):
            # First call should read from __version__
            version1 = get_version()
            assert version1 == "1.2.3"

            # Second call should use cache - we can't easily verify the cache
            # without more complex mocking, but we can at least verify it returns
            # the same value
            version2 = get_version()
            assert version2 == "1.2.3"

        # Clear cache after test
        get_version.cache_clear()


class TestGetUserAgent:
    """Tests for get_user_agent function."""

    def test_get_user_agent_with_version(self) -> None:
        """Test user agent string generation with version."""
        # Clear both caches
        get_version.cache_clear()
        get_user_agent.cache_clear()

        with patch("purple_mcp.__version__", "0.1.0"):
            user_agent = get_user_agent()
            assert user_agent == "sentinelone/purple-mcp (version 0.1.0)"

        # Clear caches after test
        get_version.cache_clear()
        get_user_agent.cache_clear()

    def test_get_user_agent_with_prerelease(self) -> None:
        """Test user agent string generation with prerelease version."""
        # Clear both caches
        get_version.cache_clear()
        get_user_agent.cache_clear()

        with patch("purple_mcp.__version__", "1.0.0-alpha.1"):
            user_agent = get_user_agent()
            assert user_agent == "sentinelone/purple-mcp (version 1.0.0-alpha.1)"

        # Clear caches after test
        get_version.cache_clear()
        get_user_agent.cache_clear()

    def test_get_user_agent_cached(self) -> None:
        """Test that user agent string is cached."""
        # Clear both caches
        get_version.cache_clear()
        get_user_agent.cache_clear()

        with patch("purple_mcp.__version__", "2.0.0"):
            # First call
            user_agent1 = get_user_agent()
            assert user_agent1 == "sentinelone/purple-mcp (version 2.0.0)"

            # Second call should use cache
            user_agent2 = get_user_agent()
            assert user_agent2 == "sentinelone/purple-mcp (version 2.0.0)"

        # Clear caches after test
        get_version.cache_clear()
        get_user_agent.cache_clear()
