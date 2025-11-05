"""Integration tests for all alerts fields to ensure API compatibility.

These tests verify that every field in the alerts API can be queried successfully
and returns data in the expected format. This helps catch upstream API changes early.
"""

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.alerts.client import DEFAULT_ALERT_FIELDS, AlertsClient
from purple_mcp.libs.alerts.config import AlertsConfig

pytestmark = pytest.mark.integration


@pytest.fixture
def alerts_config() -> AlertsConfig:
    """Create AlertsConfig for integration tests."""
    settings = get_settings()
    return AlertsConfig(
        graphql_url=settings.alerts_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,
    )


@pytest.fixture
def alerts_client(alerts_config: AlertsConfig) -> AlertsClient:
    """Create AlertsClient for integration tests."""
    return AlertsClient(alerts_config)


class TestAllAlertsFields:
    """Test that every alerts field can be queried successfully."""

    @pytest.mark.asyncio
    async def test_all_default_fields(self, alerts_client: AlertsClient) -> None:
        """Test querying with all default fields at once."""
        # Query with all fields to ensure they all work together
        result = await alerts_client.search_alerts(
            first=1,  # Just get one alert
            fields=DEFAULT_ALERT_FIELDS,
        )

        # Should return successfully without errors
        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_individual_simple_fields(self, alerts_client: AlertsClient) -> None:
        """Test each simple field individually."""
        simple_fields = [
            "id",
            "externalId",
            "severity",
            "status",
            "name",
            "description",
            "detectedAt",
            "firstSeenAt",
            "lastSeenAt",
            "analystVerdict",
            "classification",
            "confidenceLevel",
            "noteExists",
            "result",
            "storylineId",
            "ticketId",
        ]

        for field in simple_fields:
            # Test each field individually
            result = await alerts_client.search_alerts(
                first=1,
                fields=["id", field] if field != "id" else ["id"],
            )

            assert result.edges is not None, f"Field '{field}' failed"
            assert isinstance(result.edges, list), f"Field '{field}' returned non-list"

    @pytest.mark.asyncio
    async def test_nested_asset_fields(self, alerts_client: AlertsClient) -> None:
        """Test all asset nested fields."""
        # Test default asset fragment
        result = await alerts_client.search_alerts(
            first=1,
            fields=["id", "asset { id name type }"],
        )
        assert result.edges is not None

        # Test partial asset fields
        partial_fields = [
            "asset { id }",
            "asset { id name }",
            "asset { id type }",
            "asset { id name type }",
        ]

        for field in partial_fields:
            result = await alerts_client.search_alerts(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Asset field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_assignee_fields(self, alerts_client: AlertsClient) -> None:
        """Test all assignee nested fields."""
        # Test default assignee fragment
        result = await alerts_client.search_alerts(
            first=1,
            fields=["id", "assignee { userId email fullName }"],
        )
        assert result.edges is not None

        # Test partial assignee fields
        partial_fields = [
            "assignee { userId }",
            "assignee { email }",
            "assignee { fullName }",
            "assignee { userId email }",
        ]

        for field in partial_fields:
            result = await alerts_client.search_alerts(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Assignee field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_detection_source_fields(self, alerts_client: AlertsClient) -> None:
        """Test all detectionSource nested fields."""
        # Test default detectionSource fragment
        result = await alerts_client.search_alerts(
            first=1,
            fields=["id", "detectionSource { product vendor }"],
        )
        assert result.edges is not None

        # Test partial detectionSource fields
        partial_fields = [
            "detectionSource { product }",
            "detectionSource { vendor }",
        ]

        for field in partial_fields:
            result = await alerts_client.search_alerts(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"DetectionSource field '{field}' failed"

    @pytest.mark.asyncio
    async def test_minimal_field_selection(self, alerts_client: AlertsClient) -> None:
        """Test that minimal field selection (just id) works."""
        result = await alerts_client.search_alerts(
            first=1,
            fields=["id"],
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_data_sources_field(self, alerts_client: AlertsClient) -> None:
        """Test dataSources field (allowed but not in defaults)."""
        result = await alerts_client.search_alerts(
            first=1,
            fields=["id", "dataSources"],
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_combinations_simple_and_nested(self, alerts_client: AlertsClient) -> None:
        """Test combinations of simple and nested fields together."""
        combinations = [
            ["id", "severity", "status", "asset { id name }"],
            ["id", "name", "detectedAt", "assignee { userId email }"],
            ["id", "analystVerdict", "detectionSource { product }"],
            [
                "id",
                "severity",
                "asset { id }",
                "assignee { userId }",
                "detectionSource { vendor }",
            ],
        ]

        for fields in combinations:
            result = await alerts_client.search_alerts(
                first=1,
                fields=fields,
            )
            assert result.edges is not None, f"Combination {fields} failed"

    @pytest.mark.asyncio
    async def test_all_nested_objects_together(self, alerts_client: AlertsClient) -> None:
        """Test all nested objects in a single query."""
        result = await alerts_client.search_alerts(
            first=1,
            fields=[
                "id",
                "asset { id name type }",
                "assignee { userId email fullName }",
                "detectionSource { product vendor }",
            ],
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_maximal_field_selection(self, alerts_client: AlertsClient) -> None:
        """Test requesting all allowed fields including dataSources."""
        from purple_mcp.libs.alerts.client import ALLOWED_ALERT_FIELDS

        result = await alerts_client.search_alerts(
            first=1,
            fields=ALLOWED_ALERT_FIELDS,
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)
