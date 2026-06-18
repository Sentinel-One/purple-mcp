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
import pytest_asyncio
from fastmcp import Client

from purple_mcp.config import get_settings
from purple_mcp.libs.alerts import (
    AlertsClient,
    AlertsConfig,
    AlertsGraphQLError,
    EqualFilterBooleanInput,
    FilterInput,
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

    # Ensure required credentials are not None for integration tests
    assert settings.graphql_service_token is not None

    return AlertsConfig(
        graphql_url=settings.alerts_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,  # Extended timeout for integration tests
    )


@pytest_asyncio.fixture
async def alerts_client(real_alerts_config: AlertsConfig) -> AlertsClient:
    """Create a live AlertsClient for integration testing."""
    client = AlertsClient(real_alerts_config)
    return client


@pytest_asyncio.fixture
async def valid_alert_id(alerts_client: AlertsClient) -> str:
    """Get a valid alert ID for testing.

    Args:
        alerts_client: AlertsClient instance

    Returns:
        Alert ID for the first listed alert

    Raises:
        RuntimeError, if no valid alerts returned
    """
    connection = await alerts_client.list_alerts(first=1, view_type=ViewType.ALL)
    if connection and connection.edges:
        return str(connection.edges[0].node.id)
    raise RuntimeError("No valid alerts found, please check your auth token.")


@pytest_asyncio.fixture()
async def valid_alert_id_with_notes(alerts_client: AlertsClient) -> str:
    """Get a valid alert ID for testing that also has an alertNote.

    Args:
        alerts_client: AlertsClient instance

    Returns:
        Alert ID for the first listed alert

    Raises:
        RuntimeError, if no valid alerts returned
    """
    filter = FilterInput(
        fieldId="alertNoteExists", booleanEqual=EqualFilterBooleanInput(value=True)
    )
    connection = await alerts_client.search_alerts(
        first=1, view_type=ViewType.ALL, filters=[filter]
    )
    if connection and connection.edges:
        return str(connection.edges[0].node.id)
    raise RuntimeError("No alerts with notes found.")


class TestAlertsDirectClient(IntegrationTestBase):
    """Test AlertsClient with real API."""

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
        assert alerts_connection is not None
        assert hasattr(alerts_connection, "edges")
        assert hasattr(alerts_connection, "page_info")

        assert len(alerts_connection.edges) > 0

        # Verify alert-node structure
        first_alert = alerts_connection.edges[0].node
        assert first_alert.id is not None
        assert first_alert.severity is not None
        assert first_alert.status is not None
        assert first_alert.name is not None
        assert first_alert.detected_at is not None

    @pytest.mark.asyncio
    async def test_search_alerts_with_filters(self, alerts_client: AlertsClient) -> None:
        """Test searching alerts with filters against real API."""
        # arrange
        filters = [FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"])]
        expected_field_values = {"severity": {"HIGH", "CRITICAL"}}

        # act
        alert_results = await alerts_client.search_alerts(
            filters=filters, first=10, view_type=ViewType.ALL
        )

        # assert
        for alert_edge in alert_results.edges:
            alert_dict = alert_edge.node.model_dump()
            for field, acceptable_values in expected_field_values.items():
                assert field in alert_dict
                assert alert_dict[field] in acceptable_values

    @pytest.mark.asyncio
    async def test_get_specific_alert(
        self, alerts_client: AlertsClient, valid_alert_id: str
    ) -> None:
        """Test getting a specific alert by ID."""
        alert_id = valid_alert_id

        # Get the specific alert
        alert = await alerts_client.get_alert(alert_id)

        assert alert is not None
        assert alert.id == alert_id
        assert alert.severity is not None
        assert alert.status is not None

    @pytest.mark.asyncio
    async def test_get_alert_notes(
        self, alerts_client: AlertsClient, valid_alert_id_with_notes: str
    ) -> None:
        """Test getting alert notes."""
        # Get notes for the alert
        notes_response = await alerts_client.get_alert_notes(alert_id=valid_alert_id_with_notes)

        # Verify response structure
        assert hasattr(notes_response, "data")
        assert notes_response.data
        first_note = notes_response.data[0]
        assert first_note.id is not None
        assert first_note.text is not None
        assert first_note.created_at is not None

    @pytest.mark.asyncio
    async def test_error_handling_invalid_alert_id(self, alerts_client: AlertsClient) -> None:
        """Test with obviously invalid (not conforming to UUID) alert ID."""
        invalid_id = "invalid-alert-id-12345"
        with pytest.raises(AlertsGraphQLError, match=r"could not be parsed into a UUID"):
            await alerts_client.get_alert(invalid_id)

    @pytest.mark.asyncio
    async def test_error_handling_missing_alert_id(self, alerts_client: AlertsClient) -> None:
        """Test error handling with plausible-but-actually-not-present alert ID."""
        invalid_id = "0123a4bc-53df-7a54-878f-0abc12345d67"
        with pytest.raises(AlertsGraphQLError, match=r"Required value was null"):
            await alerts_client.get_alert(invalid_id)

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

        # Check if ANY results were returned
        assert results["total_items"] > 0
        # Verify pagination worked correctly
        assert results["page_count"] > 0
        assert results["total_items"] == results["cursors_seen"]


class TestAlertsMCPTools(IntegrationTestBase):
    """Integration tests for alerts tools via MCP."""

    @pytest.mark.asyncio
    async def test_get_alert_tool(self, valid_alert_id: str) -> None:
        """Test get_alert tool with real API."""
        # Use the tool
        result = await alerts.get_alert(valid_alert_id)

        # Verify JSON response
        data = json.loads(result)
        assert data is not None
        assert data["id"] == valid_alert_id
        assert "severity" in data
        assert "status" in data
        # check for camelCasing, need a field we expect to always be present:
        # 'detectedAt' is specified as non-optional by the GQL schema.
        assert "detectedAt" in data

    @pytest.mark.asyncio
    async def test_search_alerts_tool_with_filters(
        self, integration_env_check: dict[str, str]
    ) -> None:
        """Test search_alerts tool with filters."""
        # Try multiple filter combinations to increase chances of finding alerts
        # arrange
        severity_values = ["HIGH", "MEDIUM", "LOW", "CRITICAL"]
        filters = [
            {"fieldId": "severity", "filterType": "string_in", "values": severity_values},
        ]

        # act
        result = await alerts.search_alerts(filters=json.dumps(filters), first=20)
        data = json.loads(result)

        # Verify JSON response structure
        assert data is not None  # Loop always executes since filter_attempts is not empty
        assert isinstance(data, dict)
        assert "edges" in data
        assert "pageInfo" in data

        assert len(data["edges"]) > 0
        # Verify filter was applied correctly (only if filters were used)
        for edge in data["edges"]:
            assert "node" in edge
            node = edge["node"]
            if "severity" in node:
                assert node["severity"] in severity_values
            # check for camelCasing, need a field we expect to always be present:
            # 'detectedAt' is specified as non-optional by the GQL schema.
            assert "detectedAt" in node

    @pytest.mark.asyncio
    async def test_tools_parameter_validation(self, integration_env_check: dict[str, str]) -> None:
        """Test that tools properly validate parameters."""
        # Test invalid first parameter
        with pytest.raises(ValueError, match="first must be between 1 and 100"):
            await alerts.list_alerts(first=0)

        # Test invalid view type
        with pytest.raises(ValueError, match="view_type must be one of"):
            await alerts.list_alerts(view_type="INVALID")


class TestAlertsPerformance(IntegrationTestBase):
    """Performance tests for alerts functionality."""

    @pytest.mark.asyncio
    @pytest.mark.alerts_performance
    async def test_concurrent_requests(self, alerts_client: AlertsClient) -> None:
        """Test concurrent requests performance."""
        client = alerts_client
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
    async def test_large_pagination_performance(self, alerts_client: AlertsClient) -> None:
        """Test performance with large page sizes."""
        client = alerts_client
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
            assert "pageInfo" in data

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
