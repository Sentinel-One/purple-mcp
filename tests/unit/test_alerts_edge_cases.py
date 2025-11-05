"""Tests for alerts edge cases and security scenarios."""

import json
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import pytest

from purple_mcp.libs.alerts import (
    AlertConnection,
    AlertsClientError,
    AlertsConfig,
    AlertsGraphQLError,
)
from purple_mcp.tools import alerts
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.alerts.helpers import JSONAssertions, MockAlertsClientBuilder
from tests.unit.libs.alerts.helpers.base import AlertsTestBase


class TestNetworkResilience(AlertsTestBase):
    """Test network resilience and timeout handling."""

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, mock_get_client: Mock) -> None:
        """Test that network timeouts are properly handled."""
        # Setup mock to raise timeout error
        mock_client = MockAlertsClientBuilder.create_mock(
            "get_alert", side_effect=AlertsClientError("Request timed out after 30.0 seconds")
        )
        mock_get_client.return_value = mock_client

        # Execute and expect chained error
        with pytest.raises(RuntimeError) as exc_info:
            await alerts.get_alert(alert_id="test-123")

        # Validate both wrapper message and underlying cause
        JSONAssertions.assert_error_message(
            exc_info,
            "Failed to retrieve alert test-123",
            expected_cause_message="Request timed out",
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_network_connection_error(self, mock_get_client: Mock) -> None:
        """Test handling of network connection errors."""
        # Setup mock to raise connection error
        mock_client = MockAlertsClientBuilder.create_mock(
            "list_alerts", side_effect=AlertsClientError("Connection refused")
        )
        mock_get_client.return_value = mock_client

        # Execute and expect chained error
        with pytest.raises(RuntimeError) as exc_info:
            await alerts.list_alerts(first=10)

        # Validate both wrapper message and underlying cause
        JSONAssertions.assert_error_message(
            exc_info, "Failed to list alerts", expected_cause_message="Connection refused"
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_graphql_malformed_response(self, mock_get_client: Mock) -> None:
        """Test handling of malformed GraphQL responses."""
        # Setup mock to raise GraphQL error
        mock_client = MockAlertsClientBuilder.create_mock(
            "search_alerts",
            side_effect=AlertsGraphQLError("Malformed response: missing data field"),
        )
        mock_get_client.return_value = mock_client

        # Execute and expect chained error
        with pytest.raises(RuntimeError) as exc_info:
            await alerts.search_alerts(filters=json.dumps([]))

        # Validate both wrapper message and underlying cause
        JSONAssertions.assert_error_message(
            exc_info, "Failed to search alerts", expected_cause_message="Malformed response"
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_concurrent_request_errors(self, mock_get_client: Mock) -> None:
        """Test handling of errors in concurrent requests."""
        # Create a mock that fails on the third call
        call_count = 0

        async def side_effect(*args: str, **kwargs: str | int | bool) -> AlertConnection:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise AlertsClientError("Too many concurrent requests")
            return MockAlertsClientBuilder.create_empty_connection(AlertConnection)

        mock_client = AsyncMock()
        mock_client.list_alerts.side_effect = side_effect
        mock_get_client.return_value = mock_client

        # First two calls should succeed
        await alerts.list_alerts(first=5)
        await alerts.list_alerts(first=5)

        # Third call should fail
        with pytest.raises(RuntimeError) as exc_info:
            await alerts.list_alerts(first=5)

        # Validate both wrapper message and underlying cause
        JSONAssertions.assert_error_message(
            exc_info,
            "Failed to list alerts",
            expected_cause_message="Too many concurrent requests",
        )


class TestSecurityScenarios(AlertsTestBase):
    """Test security-related scenarios."""

    @pytest.mark.parametrize(
        ("error_message", "expected_cause_fragment"),
        [
            pytest.param(
                "Unauthorized: Invalid or expired token",
                "Unauthorized",
                id="unauthorized-401",
            ),
            pytest.param(
                "Forbidden: Insufficient permissions",
                "Forbidden",
                id="forbidden-403",
            ),
        ],
    )
    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_http_authentication_errors(
        self, mock_get_client: Mock, error_message: str, expected_cause_fragment: str
    ) -> None:
        """Test handling of HTTP authentication/authorization errors."""
        mock_client = MockAlertsClientBuilder.create_mock(
            "get_alert", side_effect=AlertsClientError(error_message)
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError) as exc_info:
            await alerts.get_alert(alert_id="test-123")

        JSONAssertions.assert_error_message(
            exc_info,
            "Failed to retrieve alert test-123",
            expected_cause_message=expected_cause_fragment,
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_get_client: Mock) -> None:
        """Test handling of rate limiting responses."""
        mock_client = MockAlertsClientBuilder.create_mock(
            "search_alerts",
            side_effect=AlertsClientError("Rate limit exceeded. Please retry after 60 seconds."),
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError) as exc_info:
            await alerts.search_alerts(filters=json.dumps([]), first=100)

        JSONAssertions.assert_error_message(
            exc_info, "Failed to search alerts", expected_cause_message="Rate limit exceeded"
        )

    @pytest.mark.asyncio
    async def test_token_expiration_during_pagination(self) -> None:
        """Test token expiration during pagination."""
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            # Mock successful first page
            mock_client = AsyncMock()
            first_page = MockAlertsClientBuilder.create_alert_connection([])
            first_page.page_info.has_next_page = True
            first_page.page_info.end_cursor = "cursor-1"
            mock_client.list_alerts.return_value = first_page
            mock_get_client.return_value = mock_client

            # First call succeeds
            result1 = await alerts.list_alerts(first=10)
            assert json.loads(result1)["page_info"]["has_next_page"] is True

            # Simulate token expiration for next page
            mock_client.list_alerts.side_effect = AlertsClientError("Token expired")

            # Second call with cursor should fail
            with pytest.raises(RuntimeError) as exc_info:
                await alerts.list_alerts(first=10, after="cursor-1")

            # Validate both wrapper message and underlying cause
            JSONAssertions.assert_error_message(
                exc_info, "Failed to list alerts", expected_cause_message="Token expired"
            )


class TestDataValidationEdgeCases(AlertsTestBase):
    """Test edge cases in data validation."""

    @pytest.mark.parametrize(
        "filter_config,expected_error",
        [
            # Missing required fields
            (
                [{"fieldId": "severity"}],
                "Each filter must have 'fieldId' and 'filterType' keys",
            ),
            # Invalid filter type
            (
                [{"fieldId": "severity", "filterType": "LIKE", "value": "HIGH"}],
                "Unsupported filter type: LIKE",
            ),
            # None values
            (
                [{"fieldId": None, "filterType": "string_equals", "value": "HIGH"}],
                "Invalid filter format",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_filter_validation_edge_cases(
        self, filter_config: list[dict[str, str]], expected_error: str
    ) -> None:
        """Test edge cases in filter validation that fail before network calls."""
        # These should fail at validation level before settings are accessed
        with pytest.raises(ValueError) as exc_info:
            await alerts.search_alerts(filters=json.dumps(cast(list[JsonDict], filter_config)))
        JSONAssertions.assert_error_message(exc_info, expected_error)

    @pytest.mark.parametrize(
        "filter_config,expected_error",
        [
            # Empty field name - passes validation but fails at server
            (
                [{"fieldId": "", "filterType": "string_equals", "value": "HIGH"}],
                "Failed to search alerts",
            ),
            # Invalid field name - passes validation but fails at server
            (
                [{"fieldId": "invalid_field", "filterType": "string_equals", "value": "HIGH"}],
                "Failed to search alerts",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_filter_server_level_errors(
        self,
        minimal_env_config: dict[str, str],
        filter_config: list[dict[str, str]],
        expected_error: str,
    ) -> None:
        """Test filter validation that passes local validation but fails at server level."""
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            # Mock client that raises an error
            mock_client = Mock()
            mock_client.search_alerts = AsyncMock(side_effect=Exception("Server validation error"))
            mock_get_client.return_value = mock_client

            with pytest.raises(RuntimeError) as exc_info:
                await alerts.search_alerts(filters=json.dumps(cast(list[JsonDict], filter_config)))
            JSONAssertions.assert_error_message(exc_info, expected_error)

    @pytest.mark.asyncio
    async def test_very_large_filter_list(self, minimal_env_config: dict[str, str]) -> None:
        """Test handling of very large filter lists."""
        # Create 50 filters
        large_filters = [
            {"fieldId": "severity", "filterType": "string_equals", "value": f"VALUE_{i}"}
            for i in range(50)
        ]

        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            from purple_mcp.libs.alerts import AlertConnection

            mock_client = MockAlertsClientBuilder.create_mock(
                "search_alerts",
                return_value=MockAlertsClientBuilder.create_empty_connection(AlertConnection),
            )
            mock_get_client.return_value = mock_client

            # Should handle large filter list
            result = await alerts.search_alerts(
                filters=json.dumps(cast(list[JsonDict], large_filters))
            )
            JSONAssertions.assert_connection_response(result)

            # Verify all filters were passed
            call_args = mock_client.search_alerts.call_args
            assert len(call_args[1]["filters"]) == 50


class TestConfigurationEdgeCases:
    """Test edge cases in configuration handling."""

    def test_config_with_extreme_timeout(self) -> None:
        """Test configuration with extreme timeout values."""
        # Very short timeout
        config1 = AlertsConfig(
            graphql_url="https://example.test/graphql",
            auth_token="token",
            timeout=0.001,  # 1ms
        )
        assert config1.timeout == 0.001

        # Very long timeout
        config2 = AlertsConfig(
            graphql_url="https://example.test/graphql",
            auth_token="token",
            timeout=3600.0,  # 1 hour
        )
        assert config2.timeout == 3600.0

    def test_config_with_special_characters_in_url(self) -> None:
        """Test configuration with special characters in URL."""
        special_urls = [
            "https://example.test/graphql?key=value&other=123",
            "https://user:pass@example.test/graphql",
            "https://example.test:8080/path/to/graphql",
            "https://example.test/graphql#fragment",
        ]

        for url in special_urls:
            config = AlertsConfig(
                graphql_url=url,
                auth_token="token",
            )
            assert config.graphql_url == url

    def test_config_with_special_tokens(self) -> None:
        """Test configuration with various token formats."""
        special_tokens = [
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  # JWT-like
            "token-with-dashes-and-numbers-123",
            "very" * 100,  # Very long token
            "token with spaces",  # Should work but unusual
            "token\nwith\nnewlines",  # Should work but unusual
        ]

        for token in special_tokens:
            config = AlertsConfig(
                graphql_url="https://example.test/graphql",
                auth_token=token,
            )
            assert config.auth_token == token
