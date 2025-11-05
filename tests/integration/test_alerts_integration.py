"""Refactored integration tests for Alerts functionality using DRY principles.

These tests require real environment variables to be set in .env.test:
- PURPLEMCP_CONSOLE_TOKEN
- PURPLEMCP_CONSOLE_BASE_URL

Tests will be skipped if these are not set or contain example values.
"""

import asyncio
import json
import logging

import pytest
from fastmcp import Client

from purple_mcp.config import get_settings
from purple_mcp.libs.alerts import (
    AlertsClient,
    AlertsClientError,
    AlertsConfig,
    AlertsGraphQLError,
    ViewType,
)
from purple_mcp.server import app
from purple_mcp.tools import alerts
from tests.integration.helpers import (
    FilterTestHelper,
    IntegrationTestBase,
    PaginationTestHelper,
    PerformanceTestHelper,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def real_alerts_config(integration_env_check: dict[str, str]) -> AlertsConfig:
    """Create a real alerts configuration from environment variables."""
    settings = get_settings()

    return AlertsConfig(
        graphql_url=settings.alerts_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,  # Extended timeout for integration tests
    )


class TestAlertsDirectClient(IntegrationTestBase):
    """Test AlertsClient with real API."""

    @pytest.fixture
    async def alerts_client(self, real_alerts_config: AlertsConfig) -> AlertsClient:
        """Create and verify AlertsClient."""
        client = AlertsClient(real_alerts_config)
        await self.assert_api_accessible(client)
        return client

    @pytest.mark.asyncio
    async def test_alerts_client_initialization(self, real_alerts_config: AlertsConfig) -> None:
        """Test that AlertsClient can be initialized with real config."""
        client = AlertsClient(real_alerts_config)
        assert client.config.graphql_url == real_alerts_config.graphql_url
        assert client.config.auth_token == real_alerts_config.auth_token
        assert client.config.timeout == 60.0

    @pytest.mark.asyncio
    async def test_list_alerts_real_api(self, alerts_client: AlertsClient) -> None:
        """Test listing alerts against real API."""
        # Test basic listing with timeout
        alerts_connection = await self.with_timeout(
            alerts_client.list_alerts(first=5, view_type=ViewType.ALL),
            timeout=30,
            error_message="Alert listing timed out",
        )

        # Verify response structure
        self.assert_connection_valid(alerts_connection)

        # If there are alerts, verify their structure
        if alerts_connection.edges:
            first_alert = alerts_connection.edges[0].node
            assert first_alert.id is not None
            assert first_alert.severity is not None
            assert first_alert.status is not None
            assert first_alert.name is not None
            assert first_alert.detected_at is not None

    @pytest.mark.asyncio
    async def test_search_alerts_with_filters(self, alerts_client: AlertsClient) -> None:
        """Test searching alerts with filters against real API."""
        # Use filter helper to create filters
        filters = FilterTestHelper.create_severity_filters(["HIGH", "CRITICAL"])

        # Search with filters
        await alerts_client.search_alerts(filters=filters, first=10, view_type=ViewType.ALL)

        # Verify using helper
        await FilterTestHelper.verify_filter_results(
            alerts_client, filters, "severity", {"HIGH", "CRITICAL"}, sample_size=10
        )

    @pytest.mark.asyncio
    async def test_get_specific_alert(self, alerts_client: AlertsClient) -> None:
        """Test getting a specific alert by ID."""
        # Get a test alert ID
        alert_id = await self.get_test_alert_id(alerts_client)

        if alert_id:
            # Get the specific alert
            alert = await alerts_client.get_alert(alert_id)

            assert alert is not None
            assert alert.id == alert_id
            assert alert.severity is not None
            assert alert.status is not None
        else:
            pytest.skip("No alerts available for testing")

    @pytest.mark.asyncio
    async def test_get_alert_notes(self, alerts_client: AlertsClient) -> None:
        """Test getting alert notes."""
        # Get a test alert ID
        alert_id = await self.get_test_alert_id(alerts_client)

        if alert_id:
            # Get notes for the alert
            notes_response = await alerts_client.get_alert_notes(alert_id=alert_id)

            # Verify response structure
            assert hasattr(notes_response, "data")

            # If there are notes, verify their structure
            if notes_response.data:
                first_note = notes_response.data[0]
                assert first_note.id is not None
                assert first_note.text is not None
                assert first_note.created_at is not None
        else:
            pytest.skip("No alerts available for testing")

            pytest.skip("No alerts available for testing")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_alert_id(self, alerts_client: AlertsClient) -> None:
        """Test error handling with invalid alert ID."""
        # Test with obviously invalid ID
        invalid_id = "invalid-alert-id-12345"

        try:
            result = await alerts_client.get_alert(invalid_id)
            # Some APIs might return None instead of error
            assert result is None
        except (AlertsClientError, AlertsGraphQLError) as e:
            # Error is expected
            assert "not found" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.asyncio
    async def test_pagination_functionality(self, alerts_client: AlertsClient) -> None:
        """Test pagination with real API."""
        pagination_helper = PaginationTestHelper()

        # Test pagination consistency
        results = await pagination_helper.test_pagination_consistency(
            lambda page_size, current_cursor: alerts_client.list_alerts(
                view_type=ViewType.ALL, first=page_size, after=current_cursor
            ),
            page_size=3,
            max_pages=3,
        )

        # Skip if no alerts are available
        if results["total_items"] == 0:
            pytest.skip("No alerts available for pagination testing")

        # Verify pagination worked correctly
        assert results["page_count"] > 0
        assert results["total_items"] == results["cursors_seen"]

        # No duplicate cursors
        assert results["cursors_seen"] == results["total_items"]


class TestAlertsMCPTools(IntegrationTestBase):
    """Integration tests for alerts tools via MCP."""

    @pytest.mark.asyncio
    async def test_get_alert_tool(self, integration_env_check: dict[str, str]) -> None:
        """Test get_alert tool with real API."""
        # Get a test alert ID first
        client = alerts._get_alerts_client()
        alert_id = await self.get_test_alert_id(client)

        if alert_id:
            # Use the tool
            result = await alerts.get_alert(alert_id)

            # Verify JSON response
            data = json.loads(result)
            assert data is not None
            assert data["id"] == alert_id
            assert "severity" in data
            assert "status" in data
        else:
            pytest.skip("No alerts available for testing")

    @pytest.mark.asyncio
    async def test_search_alerts_tool_with_filters(
        self, integration_env_check: dict[str, str]
    ) -> None:
        """Test search_alerts tool with filters."""
        # Try multiple filter combinations to increase chances of finding alerts
        filter_attempts = [
            [{"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}],
            [{"fieldId": "severity", "filterType": "string_equals", "value": "MEDIUM"}],
            [{"fieldId": "severity", "filterType": "string_equals", "value": "LOW"}],
            [{"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}],
            # Try without filters to get any alerts
            [],
        ]

        data = None
        used_filters = None

        for filters in filter_attempts:
            result = await alerts.search_alerts(filters=json.dumps(filters), first=20)
            data = json.loads(result)

            # Verify JSON response structure
            assert isinstance(data, dict)
            assert "edges" in data
            assert "page_info" in data

            if data["edges"]:
                used_filters = filters
                break

        # Skip if no alerts found with any filter combination
        assert data is not None  # Loop always executes since filter_attempts is not empty
        if not data.get("edges"):
            pytest.skip("No alerts available for testing")

        # Verify filter was applied correctly (only if filters were used)
        if used_filters:
            for edge in data["edges"]:
                if "severity" in edge["node"]:
                    assert edge["node"]["severity"] == used_filters[0]["value"]

    @pytest.mark.asyncio
    async def test_tools_parameter_validation(self, integration_env_check: dict[str, str]) -> None:
        """Test that tools properly validate parameters."""
        # Test invalid first parameter
        with pytest.raises(ValueError, match="first must be between 1 and 100"):
            await alerts.list_alerts(first=0)

        # Test invalid view type
        with pytest.raises(ValueError, match="view_type must be one of"):
            await alerts.list_alerts(view_type="INVALID")

        # Test empty note text


class TestAlertsPerformance(IntegrationTestBase):
    """Performance tests for alerts functionality."""

    @pytest.mark.asyncio
    @pytest.mark.alerts_performance
    async def test_concurrent_requests(self, real_alerts_config: AlertsConfig) -> None:
        """Test concurrent requests performance."""
        client = AlertsClient(real_alerts_config)
        perf_helper = PerformanceTestHelper()

        # Define concurrent operations
        async def concurrent_operations() -> None:
            tasks = [
                perf_helper.measure_operation(
                    "list_alerts",
                    lambda *args, **kwargs: client.list_alerts(**kwargs),
                    first=5,
                    view_type=ViewType.ALL,
                ),
                perf_helper.measure_operation(
                    "search_high_severity",
                    lambda *args, **kwargs: client.search_alerts(**kwargs),
                    filters=FilterTestHelper.create_severity_filters(["HIGH"]),
                    first=5,
                ),
                perf_helper.measure_operation(
                    "search_new_status",
                    lambda *args, **kwargs: client.search_alerts(**kwargs),
                    filters=[FilterTestHelper.create_status_filter("NEW")],
                    first=5,
                ),
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        # Run concurrent requests
        await self.with_timeout(
            concurrent_operations(), timeout=60, error_message="Concurrent requests timed out"
        )

        # Get performance summary
        summary = perf_helper.get_summary()

        # Verify all succeeded
        assert summary["success_rate"] == 1.0, f"Some operations failed: {summary}"

        # Verify performance metrics are within acceptable range
        total_ops = summary["total_operations"]
        assert isinstance(total_ops, int) and total_ops > 0, "Should have operations"

        avg_duration = summary["avg_duration"]
        assert isinstance(avg_duration, (int, float)) and avg_duration >= 0, (
            "Average duration should be non-negative"
        )

        min_duration = summary["min_duration"]
        assert isinstance(min_duration, (int, float)) and min_duration >= 0, (
            "Min duration should be non-negative"
        )

        max_duration = summary["max_duration"]
        assert isinstance(max_duration, (int, float)) and max_duration >= min_duration, (
            "Max should be >= min"
        )

        # Log performance metrics
        logger.info(
            "Concurrent request performance: total=%d, avg=%.2fs, min=%.2fs, max=%.2fs",
            summary["total_operations"],
            summary["avg_duration"],
            summary["min_duration"],
            summary["max_duration"],
        )

    @pytest.mark.asyncio
    @pytest.mark.alerts_performance
    async def test_large_pagination_performance(self, real_alerts_config: AlertsConfig) -> None:
        """Test performance with large page sizes."""
        client = AlertsClient(real_alerts_config)
        perf_helper = PerformanceTestHelper()

        page_sizes = [10, 25, 50, 100]

        for page_size in page_sizes:
            _, duration = await perf_helper.measure_operation(
                f"page_size_{page_size}",
                lambda *args, **kwargs: client.list_alerts(**kwargs),
                first=page_size,
                view_type=ViewType.ALL,
            )

            # Verify duration is reasonable for the page size
            assert duration >= 0, f"Duration for page_size {page_size} should be non-negative"
            logger.debug("Page size %d: %.2fs", page_size, duration)

        # Get summary
        summary = perf_helper.get_summary()

        # Verify performance is reasonable
        max_duration = summary["max_duration"]
        success_rate = summary["success_rate"]
        assert isinstance(max_duration, int | float), "max_duration should be numeric"
        assert isinstance(success_rate, int | float), "success_rate should be numeric"
        assert max_duration < 30, "Some operations took too long"
        assert success_rate == 1.0, "Some operations failed"


class TestAlertsMCPServer(IntegrationTestBase):
    """Integration tests for alerts via MCP server."""

    @pytest.mark.asyncio
    async def test_alerts_tools_via_mcp_client(
        self, integration_env_check: dict[str, str]
    ) -> None:
        """Test calling alerts tools through MCP client."""
        async with Client(app) as client:
            # List available tools
            tools = await client.list_tools()
            alerts_tools = [
                t
                for t in tools
                if t.name.startswith("get_alert") or t.name.startswith("list_alerts")
            ]

            assert len(alerts_tools) >= 2, "Expected at least get_alert and list_alerts tools"

            # Test list_alerts tool
            result = await client.call_tool(
                "list_alerts", arguments={"first": 3, "view_type": "ALL"}
            )

            # Verify response
            assert result.content[0].type == "text"
            data = json.loads(result.content[0].text)
            assert "edges" in data
            assert "page_info" in data

    @pytest.mark.asyncio
    async def test_alerts_tools_error_handling_via_mcp(
        self, integration_env_check: dict[str, str]
    ) -> None:
        """Test error handling through MCP."""
        async with Client(app) as client:
            # Test with invalid parameters
            with pytest.raises(Exception) as exc_info:
                await client.call_tool(
                    "list_alerts",
                    arguments={"first": 0},  # Invalid
                )

            assert "first must be between 1 and 100" in str(exc_info.value)
