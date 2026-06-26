"""Tests for alerts edge cases and security scenarios."""

import json
from typing import cast
from unittest.mock import AsyncMock, create_autospec

import pytest

from purple_mcp.libs.alerts import (
    AlertConnection,
    AlertsClient,
    AlertsClientError,
    AlertsConfig,
    AlertsGraphQLError,
)
from purple_mcp.tools import alerts
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.alerts.helpers import MockAlertsClientBuilder


class TestNetworkResilience:
    """Test network resilience and timeout handling."""

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that network timeouts are properly handled."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert = AsyncMock(
            side_effect=AlertsClientError("Request timed out after 30.0 seconds")
        )
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)
        expected_cause_message = "Request timed out"

        # act & assert
        with pytest.raises(RuntimeError, match="Failed to retrieve alert test-123") as exc_info:
            await alerts.get_alert(alert_id="test-123")
        assert expected_cause_message in str(exc_info.value.__cause__)

    @pytest.mark.asyncio
    async def test_network_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of network connection errors."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.list_alerts = AsyncMock(side_effect=AlertsClientError("Connection refused"))
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)
        expected_cause_message = "Connection refused"

        # act & assert
        with pytest.raises(RuntimeError, match="Failed to list alerts") as exc_info:
            await alerts.list_alerts(first=10)
        assert expected_cause_message in str(exc_info.value.__cause__)

    @pytest.mark.asyncio
    async def test_graphql_malformed_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of malformed GraphQL responses."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.search_alerts = AsyncMock(
            side_effect=AlertsGraphQLError("Malformed response: missing data field")
        )
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)
        expected_cause_message = "Malformed response"

        # act & assert
        with pytest.raises(RuntimeError, match="Failed to search alerts") as exc_info:
            await alerts.search_alerts(filters=json.dumps([]))
        assert expected_cause_message in str(exc_info.value.__cause__)

    @pytest.mark.asyncio
    async def test_concurrent_request_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of errors in concurrent requests."""
        # arrange - Create a mock that fails on the third call
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        call_count = 0

        async def side_effect(*args: str, **kwargs: str | int | bool) -> AlertConnection:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise AlertsClientError("Too many concurrent requests")
            return MockAlertsClientBuilder.create_empty_connection(AlertConnection)

        mock_client.list_alerts = AsyncMock(side_effect=side_effect)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)
        expected_cause_message = "Too many concurrent requests"

        # act - First two calls should succeed
        await alerts.list_alerts(first=5)
        await alerts.list_alerts(first=5)

        # Third call should fail
        with pytest.raises(RuntimeError, match="Failed to list alerts") as exc_info:
            await alerts.list_alerts(first=5)
        assert expected_cause_message in str(exc_info.value.__cause__)


class TestSecurityScenarios:
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
    @pytest.mark.asyncio
    async def test_http_authentication_errors(
        self, monkeypatch: pytest.MonkeyPatch, error_message: str, expected_cause_fragment: str
    ) -> None:
        """Test handling of HTTP authentication/authorization errors."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert = AsyncMock(side_effect=AlertsClientError(error_message))
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act & assert
        with pytest.raises(RuntimeError, match="Failed to retrieve alert test-123") as exc_info:
            await alerts.get_alert(alert_id="test-123")
        assert expected_cause_fragment in str(exc_info.value.__cause__)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of rate limiting responses."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.search_alerts = AsyncMock(
            side_effect=AlertsClientError("Rate limit exceeded. Please retry after 60 seconds.")
        )
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)
        expected_cause_message = "Rate limit exceeded"

        # act & assert
        with pytest.raises(RuntimeError, match="Failed to search alerts") as exc_info:
            await alerts.search_alerts(filters=json.dumps([]), first=100)
        assert expected_cause_message in str(exc_info.value.__cause__)

    @pytest.mark.asyncio
    async def test_token_expiration_during_pagination(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test token expiration during pagination."""
        # arrange - Mock successful first page
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        first_page = MockAlertsClientBuilder.create_empty_connection(AlertConnection)
        first_page.page_info.has_next_page = True
        first_page.page_info.end_cursor = "cursor-1"
        mock_client.list_alerts = AsyncMock(return_value=first_page)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act - First call succeeds
        result1 = await alerts.list_alerts(first=10)
        assert json.loads(result1)["pageInfo"]["hasNextPage"] is True

        # arrange - Simulate token expiration for next page
        mock_client.list_alerts.side_effect = AlertsClientError("Token expired")
        expected_cause_message = "Token expired"

        # act & assert - Second call with cursor should fail
        with pytest.raises(RuntimeError, match="Failed to list alerts") as exc_info:
            await alerts.list_alerts(first=10, after="cursor-1")
        assert expected_cause_message in str(exc_info.value.__cause__)


class TestDataValidationEdgeCases:
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
        with pytest.raises(ValueError, match=expected_error):
            await alerts.search_alerts(filters=json.dumps(cast(list[JsonDict], filter_config)))

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
        monkeypatch: pytest.MonkeyPatch,
        filter_config: list[dict[str, str]],
        expected_error: str,
    ) -> None:
        """Test filter validation that passes local validation but fails at server level."""
        # arrange - Mock client that raises an error
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.search_alerts = AsyncMock(side_effect=Exception("Server validation error"))
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act & assert
        with pytest.raises(RuntimeError, match=expected_error):
            await alerts.search_alerts(filters=json.dumps(cast(list[JsonDict], filter_config)))


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
