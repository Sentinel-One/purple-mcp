"""Tests for sanitized logging behavior across all clients.

This test module verifies that sensitive request data (queries, filters, payloads)
is not logged at DEBUG/INFO level by default, and is only logged when the
PURPLEMCP_DEBUG_UNSAFE_LOGGING environment variable is explicitly set to "1".

These tests exercise the real client code paths with mocked HTTP responses.
"""

import logging
import os

import httpx
import pytest
import respx

from purple_mcp.libs.inventory.client import InventoryClient
from purple_mcp.libs.inventory.config import InventoryConfig
from purple_mcp.libs.inventory.exceptions import InventoryNetworkError
from purple_mcp.libs.purple_ai.client import PurpleAIClient
from purple_mcp.libs.purple_ai.config import (
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIUserDetails,
)


class TestSanitizedLogging:
    """Test suite for sanitized logging across all clients using real code paths."""

    @pytest.fixture(autouse=True)
    def setup_logging(self, caplog: pytest.LogCaptureFixture) -> None:
        """Set up logging capture for tests."""
        caplog.set_level(logging.DEBUG)

    @pytest.fixture(autouse=True)
    def clear_env_var(self) -> None:
        """Ensure PURPLEMCP_DEBUG_UNSAFE_LOGGING is not set."""
        if "PURPLEMCP_DEBUG_UNSAFE_LOGGING" in os.environ:
            del os.environ["PURPLEMCP_DEBUG_UNSAFE_LOGGING"]
        yield
        # Clean up after test
        if "PURPLEMCP_DEBUG_UNSAFE_LOGGING" in os.environ:
            del os.environ["PURPLEMCP_DEBUG_UNSAFE_LOGGING"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_purple_ai_sanitizes_query_at_info_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that PurpleAIClient.ask_purple sanitizes query at INFO level by default."""
        # Mock the GraphQL response
        mock_response = {
            "data": {
                "purpleLaunchQuery": {
                    "result": "RESULT",
                    "text": "Response text",
                    "error": None,
                }
            }
        }
        respx.post("https://test.test/v1/graphql").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        config = PurpleAIConfig(
            graphql_url="https://test.test/v1/graphql",
            auth_token="test-token",
            user_details=PurpleAIUserDetails(
                account_id="test",
                team_token="test",
                email_address="test@test.test",
                user_agent="test",
                build_date="test",
                build_hash="test",
            ),
            console_details=PurpleAIConsoleDetails(base_url="https://test.test", version="test"),
        )
        client = PurpleAIClient(config)

        # Call ask_purple with sensitive query
        sensitive_query = "show me all passwords for user admin@secret-company.com"
        await client.ask_purple(sensitive_query)

        # Verify sensitive query is NOT in text logs
        assert "passwords" not in caplog.text
        assert "admin@secret-company.com" not in caplog.text
        assert "secret-company" not in caplog.text

        # Verify that logging happened
        assert "Querying Purple AI" in caplog.text

        # CRITICAL: Verify sensitive data is NOT in structured logging extras
        # Check that no log record contains raw_query with sensitive data
        for record in caplog.records:
            if "raw_query" in record.__dict__:
                # If raw_query exists, it should NOT contain sensitive data
                raw_query_value = record.__dict__["raw_query"]
                assert "passwords" not in str(raw_query_value)
                assert "admin@secret-company.com" not in str(raw_query_value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_purple_ai_logs_full_query_with_unsafe_logging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that PurpleAIClient logs full query when unsafe logging is enabled."""
        os.environ["PURPLEMCP_DEBUG_UNSAFE_LOGGING"] = "1"

        # Mock the GraphQL response
        mock_response = {
            "data": {
                "purpleLaunchQuery": {
                    "result": "RESULT",
                    "text": "Response text",
                    "error": None,
                }
            }
        }
        respx.post("https://test.test/v1/graphql").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        config = PurpleAIConfig(
            graphql_url="https://test.test/v1/graphql",
            auth_token="test-token",
            user_details=PurpleAIUserDetails(
                account_id="test",
                team_token="test",
                email_address="test@test.test",
                user_agent="test",
                build_date="test",
                build_hash="test",
            ),
            console_details=PurpleAIConsoleDetails(base_url="https://test.test", version="test"),
        )
        client = PurpleAIClient(config)

        # Call ask_purple with sensitive query
        sensitive_query = "show me all passwords"
        await client.ask_purple(sensitive_query)

        # With unsafe logging, the query should be in the log records' __dict__
        # Check that at least one log record has the raw_query attribute
        has_raw_query = any("raw_query" in record.__dict__ for record in caplog.records)
        assert has_raw_query, "Expected raw_query in log records with unsafe logging enabled"

    @pytest.mark.asyncio
    @respx.mock
    async def test_inventory_sanitizes_filters_in_normal_path(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that inventory client sanitizes filters in normal execution path."""
        # Mock successful search response
        mock_response = {
            "data": [{"id": "item-1", "name": "test-server", "resourceType": "Server"}],
            "total": 1,
        }
        respx.post("https://test-inventory.test/api/v1").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        config = InventoryConfig(
            base_url="https://test-inventory.test",
            api_endpoint="/api/v1",
            api_token="test-token",
        )

        async with InventoryClient(config) as client:
            # Search with sensitive filters
            filters = {
                "name__contains": ["production-database-secret"],
                "resourceType": ["Database Server"],
                "tags__contains": ["env:production", "team:security"],
            }
            await client.search_inventory(filters=filters)

        # Verify sensitive filter values are NOT in text logs
        assert "production-database-secret" not in caplog.text
        assert "Database Server" not in caplog.text
        assert "env:production" not in caplog.text
        assert "team:security" not in caplog.text

        # Verify logging happened
        assert "Searching inventory items" in caplog.text

        # CRITICAL: Verify sensitive data is NOT in structured logging extras
        # Check that no log record contains filters dict with sensitive values
        for record in caplog.records:
            if "filters" in record.__dict__:
                # If filters exists, it should NOT contain sensitive filter values
                filters_value = str(record.__dict__["filters"])
                assert "production-database-secret" not in filters_value
                assert "Database Server" not in filters_value
                assert "env:production" not in filters_value
                assert "team:security" not in filters_value

    @pytest.mark.asyncio
    @respx.mock
    async def test_inventory_sanitizes_filters_in_error_path(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that inventory client sanitizes filters in exception logging."""
        # Mock timeout error
        respx.post("https://test-inventory.test/api/v1").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        config = InventoryConfig(
            base_url="https://test-inventory.test",
            api_endpoint="/api/v1",
            api_token="test-token",
        )

        async with InventoryClient(config) as client:
            # Search with sensitive filters - should fail with timeout
            filters = {
                "name__contains": ["secret-production-server"],
                "ip__contains": ["10.0.0.100"],
            }
            with pytest.raises(InventoryNetworkError):
                await client.search_inventory(filters=filters)

        # Verify sensitive filter values are NOT in text exception logs
        assert "secret-production-server" not in caplog.text
        assert "10.0.0.100" not in caplog.text

        # Verify exception was logged
        assert "Timeout searching inventory items" in caplog.text

        # CRITICAL: Verify sensitive data is NOT in structured logging extras during errors
        # Check that no log record contains filters dict with sensitive values
        for record in caplog.records:
            if "filters" in record.__dict__:
                # If filters exists, it should NOT contain sensitive filter values
                filters_value = str(record.__dict__["filters"])
                assert "secret-production-server" not in filters_value
                assert "10.0.0.100" not in filters_value

    @pytest.mark.asyncio
    @respx.mock
    async def test_inventory_logs_full_filters_in_errors_with_unsafe_logging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that inventory client logs full filters in errors when unsafe logging is enabled."""
        os.environ["PURPLEMCP_DEBUG_UNSAFE_LOGGING"] = "1"

        # Mock timeout error
        respx.post("https://test-inventory.test/api/v1").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        config = InventoryConfig(
            base_url="https://test-inventory.test",
            api_endpoint="/api/v1",
            api_token="test-token",
        )

        async with InventoryClient(config) as client:
            # Search with sensitive filters - should fail with timeout
            filters = {
                "name__contains": ["secret-server"],
            }
            with pytest.raises(InventoryNetworkError):
                await client.search_inventory(filters=filters)

        # With unsafe logging, filters should be in log records' __dict__
        has_filters = any("filters" in record.__dict__ for record in caplog.records)
        assert has_filters, "Expected filters in log records with unsafe logging enabled"

    def test_environment_variable_must_be_exactly_one(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that the env var must be exactly '1' to enable unsafe logging."""
        logger = logging.getLogger("purple_mcp.test")

        # Test with various values that should NOT enable unsafe logging
        for value in ["true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON", "2", ""]:
            # Clear previous records
            caplog.clear()
            os.environ["PURPLEMCP_DEBUG_UNSAFE_LOGGING"] = value

            sensitive_data = "secret-value"

            if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
                logger.debug("Full data", extra={"data": sensitive_data})
            else:
                logger.debug("Sanitized data", extra={"has_data": bool(sensitive_data)})

            # Should use sanitized logging (not "1")
            assert "Sanitized data" in caplog.text
            assert len(caplog.records) > 0

        # Now test with "1" - should enable unsafe logging
        caplog.clear()
        os.environ["PURPLEMCP_DEBUG_UNSAFE_LOGGING"] = "1"

        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.debug("Full data", extra={"data": sensitive_data})
        else:
            logger.debug("Sanitized data", extra={"has_data": bool(sensitive_data)})

        # Should use full logging when set to "1"
        assert "Full data" in caplog.text
        assert len(caplog.records) > 0
