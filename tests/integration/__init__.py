"""Integration tests for Purple MCP server.

This package contains integration tests that require real environment variables
and external service connections. Tests will be automatically skipped if the
required environment variables are not set in .env.test file.

Required environment variables:
- PURPLEMCP_CONSOLE_TOKEN: Authentication token for Console API (used for both SDL and Console access)
- PURPLEMCP_CONSOLE_BASE_URL: Base URL for SentinelOne/Scalyr console

Tests are marked with @pytest.mark.integration and @pytest.mark.slow.
"""
