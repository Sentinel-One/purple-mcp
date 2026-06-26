"""Comprehensive integration tests for alerts filter combinations.

These tests exercise every possible filter type and combination to ensure
no errors occur during filtering operations. Tests are designed to verify
filter functionality rather than data accuracy.

IMPORTANT: These tests accurately reflect the UAM GraphQL API schema.
- Supports all FilterType values: STRING_EQUAL, STRING_IN, FULLTEXT, DATE_RANGE,
  BOOLEAN_IN, BOOLEAN_EQUAL, INT_RANGE, INT_EQUAL, INT_IN, LONG_RANGE, LONG_EQUAL, LONG_IN
- Numeric IDs use LONG_* filters (not INT_*)
- DateTime fields use DATE_RANGE filter type
- Text fields support FULLTEXT, STRING_IN, and STRING_EQUAL (FULLTEXT_FIELD_FILTERS pattern)

Requirements:
- PURPLEMCP_CONSOLE_TOKEN: Valid API token
- PURPLEMCP_CONSOLE_BASE_URL: Console base URL

Tests will be skipped if environment is not configured.
"""

import time
from datetime import datetime

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.alerts import Alert, AlertsClient, AlertsConfig, FilterInput, ViewType


@pytest.fixture
def alerts_config(integration_env_check: dict[str, str]) -> AlertsConfig:
    """Create alerts configuration from environment variables.

    Returns:
        AlertsConfig with settings from environment.
    """
    settings = get_settings()

    # Ensure required credentials are not None for integration tests
    assert settings.graphql_service_token is not None

    return AlertsConfig(
        graphql_url=settings.alerts_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,  # Extended timeout for filter operations
    )


@pytest.fixture
def alerts_client(alerts_config: AlertsConfig) -> AlertsClient:
    """Create an alerts client instance."""
    return AlertsClient(alerts_config)


class TestStringFilters:
    """Test all string filter types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_severity(self, alerts_client: AlertsClient) -> None:
        """Test string_equals filter on severity field."""
        severity_value = "CRITICAL"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringEqual": {"value": severity_value},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.severity == severity_value

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_status(self, alerts_client: AlertsClient) -> None:
        """Test string_equals filter on status field."""
        status_value = "NEW"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringEqual": {"value": status_value},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.status == status_value

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_analyst_verdict(self, alerts_client: AlertsClient) -> None:
        """Test string_equals filter on analystVerdict field."""
        verdict_value = "TRUE_POSITIVE"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "analystVerdict",
                    "stringEqual": {"value": verdict_value},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.analyst_verdict == verdict_value

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_severity(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter on severity field."""
        severity_values = ["CRITICAL", "HIGH"]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": severity_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert result.edges
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.severity in severity_values

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_status_multiple(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter with multiple status values."""
        status_values = ["NEW", "IN_PROGRESS", "ON_HOLD"]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": status_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.status in status_values

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_all_severities(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter with all severity values."""
        severity_values = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": severity_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.severity in severity_values

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_negated(self, alerts_client: AlertsClient) -> None:
        """Test string_equals filter with isNegated=true."""
        negated_severity = "LOW"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "isNegated": True,
                    "stringEqual": {"value": negated_severity},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.severity != negated_severity

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_alert_name(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter on alertName field."""
        alert_name_values = ["Threat", "Malware"]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertName",
                    "stringIn": {"values": alert_name_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.name is not None
            assert any(value.lower() in edge.node.name.lower() for value in alert_name_values)


class TestBooleanFilters:
    """Test boolean filter types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.parametrize("note_exists", [True, False])
    async def test_boolean_equals(self, note_exists: bool, alerts_client: AlertsClient) -> None:
        """Test boolean_equals filter with value=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": note_exists},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.note_exists is note_exists

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.parametrize("negated_value", [True, False])
    async def test_boolean_equals_negated(
        self, negated_value: bool, alerts_client: AlertsClient
    ) -> None:
        """Test boolean_equals filter with isNegated=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "isNegated": True,
                    "booleanEqual": {"value": negated_value},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.note_exists is not negated_value

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_single_value(self, alerts_client: AlertsClient) -> None:
        """Test boolean_in filter with single value."""
        note_exists_values = [True]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanIn": {"values": note_exists_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.note_exists

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_multiple_values(self, alerts_client: AlertsClient) -> None:
        """Test boolean_in filter with multiple values (true and false)."""
        note_exists_values = [True, False]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanIn": {"values": note_exists_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.note_exists in note_exists_values


def datetime_str_to_timestamp_ms(datetime_str: str) -> int:
    """Convert from an iso format timestamp to a POSIX timestamp as integer milliseconds."""
    return int(datetime.fromisoformat(datetime_str).timestamp() * 1_000)


class TestDateTimeFilters:
    """Test datetime range filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_both_bounds(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with both start and end."""
        current_time_ms = int(time.time() * 1_000)
        ninety_days_ago_ms = current_time_ms - (90 * 24 * 60 * 60 * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "detectedAt",
                    "dateTimeRange": {
                        "start": ninety_days_ago_ms,
                        "end": current_time_ms,
                        "startInclusive": True,
                        "endInclusive": True,
                    },
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.detected_at is not None
            detected_at_ms = datetime_str_to_timestamp_ms(edge.node.detected_at)
            assert ninety_days_ago_ms <= detected_at_ms <= current_time_ms

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_start_only(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with only start bound."""
        thirty_days_ago_ms = int((time.time() - (30 * 24 * 60 * 60)) * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "detectedAt",
                    "dateTimeRange": {
                        "start": thirty_days_ago_ms,
                        "startInclusive": True,
                    },
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.detected_at is not None
            detected_at_ms = datetime_str_to_timestamp_ms(edge.node.detected_at)
            assert detected_at_ms >= thirty_days_ago_ms

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_end_only(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with only end bound."""
        current_time_ms = int(time.time() * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "detectedAt",
                    "dateTimeRange": {
                        "end": current_time_ms,
                        "endInclusive": True,
                    },
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.detected_at is not None
            detected_at_ms = datetime_str_to_timestamp_ms(edge.node.detected_at)
            assert detected_at_ms <= current_time_ms

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_exclusive_bounds(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with exclusive bounds."""
        current_time_ms = int(time.time() * 1_000)
        sixty_days_ago_ms = current_time_ms - (60 * 24 * 60 * 60 * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "detectedAt",
                    "dateTimeRange": {
                        "start": sixty_days_ago_ms,
                        "end": current_time_ms,
                        "startInclusive": False,
                        "endInclusive": False,
                    },
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.detected_at is not None
            detected_at_ms = datetime_str_to_timestamp_ms(edge.node.detected_at)
            assert sixty_days_ago_ms < detected_at_ms < current_time_ms

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_first_seen_at(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter on firstSeenAt field."""
        seven_days_ago_ms = int((time.time() - (7 * 24 * 60 * 60)) * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "firstSeenAt",
                    "dateTimeRange": {
                        "start": seven_days_ago_ms,
                        "startInclusive": True,
                    },
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.first_seen_at is not None
            first_seen_at_ms = datetime_str_to_timestamp_ms(edge.node.first_seen_at)
            assert first_seen_at_ms >= seven_days_ago_ms


class TestFulltextFilters:
    """Test fulltext search filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_single_term(self, alerts_client: AlertsClient) -> None:
        """Test fulltext filter with single search term."""
        search_terms = ["threat"]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertName",
                    "match": {"values": search_terms},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.name is not None
            assert any(term.lower() in edge.node.name.lower() for term in search_terms)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_multiple_terms(self, alerts_client: AlertsClient) -> None:
        """Test fulltext filter with multiple search terms."""
        search_terms = ["malware", "threat"]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertName",
                    "match": {"values": search_terms},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.name is not None
            assert any(term.lower() in edge.node.name.lower() for term in search_terms)


class TestLongFilters:
    """Test long integer filter types.

    Note: Numeric IDs in UAM use LONG filters, not INT filters.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_long_equals_assignee_user_id(self, alerts_client: AlertsClient) -> None:
        """Test long_equals filter on assigneeUserId field.

        Note: This test may not return results if no alerts are assigned to user ID 1.
        """
        user_id_value = 1
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assigneeUserId",
                    "longEqual": {"value": user_id_value},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_long_in_assignee_user_id(self, alerts_client: AlertsClient) -> None:
        """Test long_in filter on assigneeUserId field with multiple values."""
        user_id_values = [1, 2, 3]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assigneeUserId",
                    "longIn": {"values": user_id_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")


class TestFilterCombinations:
    """Test combinations of multiple filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_two_string_filters(self, alerts_client: AlertsClient) -> None:
        """Test combination of two string filters (AND logic)."""
        severity_value = "CRITICAL"
        status_value = "NEW"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringEqual": {"value": severity_value},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringEqual": {"value": status_value},
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.severity == severity_value
            assert edge.node.status == status_value

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_and_boolean_filters(self, alerts_client: AlertsClient) -> None:
        """Test combination of string and boolean filters."""
        severity_values = ["CRITICAL", "HIGH"]
        note_exists_value = True
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": severity_values},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": note_exists_value},
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.severity in severity_values
            assert edge.node.note_exists == note_exists_value

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_and_datetime_filters(self, alerts_client: AlertsClient) -> None:
        """Test combination of string and datetime filters."""
        import time

        status_values = ["NEW", "IN_PROGRESS"]
        thirty_days_ago_ms = int((time.time() - (30 * 24 * 60 * 60)) * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": status_values},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "detectedAt",
                    "dateTimeRange": {
                        "start": thirty_days_ago_ms,
                        "startInclusive": True,
                    },
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_three_filters_mixed_types(self, alerts_client: AlertsClient) -> None:
        """Test combination of three filters with different types."""
        severity_values = ["CRITICAL", "HIGH"]
        note_exists_value = False
        status_value = "NEW"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": severity_values},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": note_exists_value},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringEqual": {"value": status_value},
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filters_with_negation(self, alerts_client: AlertsClient) -> None:
        """Test combination of positive and negated filters."""
        severity_values = ["CRITICAL", "HIGH"]
        negated_status = "RESOLVED"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": severity_values},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "isNegated": True,
                    "stringEqual": {"value": negated_status},
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complex_filter_combination(self, alerts_client: AlertsClient) -> None:
        """Test complex filter combination with multiple types and negation."""
        severity_values = ["CRITICAL", "HIGH"]
        negated_status = "RESOLVED"
        note_exists_value = False
        ninety_days_ago_ms = int((time.time() - (90 * 24 * 60 * 60)) * 1_000)

        filters = [
            # Critical or High severity
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": severity_values},
                }
            ),
            # Not resolved
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "isNegated": True,
                    "stringEqual": {"value": negated_status},
                }
            ),
            # No notes
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": note_exists_value},
                }
            ),
            # Detected in last 90 days
            FilterInput.model_validate(
                {
                    "fieldId": "detectedAt",
                    "dateTimeRange": {
                        "start": ninety_days_ago_ms,
                        "startInclusive": True,
                    },
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_empty_filter_list(self, alerts_client: AlertsClient) -> None:
        """Test search with empty filter list."""
        result = await alerts_client.search_alerts(filters=[], first=5, view_type=ViewType.ALL)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_no_filters(self, alerts_client: AlertsClient) -> None:
        """Test search with None filters."""
        result = await alerts_client.search_alerts(filters=None, first=5, view_type=ViewType.ALL)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_filters_same_field(self, alerts_client: AlertsClient) -> None:
        """Test multiple filters on the same field (severity with different values)."""
        # Note: UAM allows multiple filters on same field
        negated_severity_1 = "LOW"
        negated_severity_2 = "INFO"
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "isNegated": True,
                    "stringEqual": {"value": negated_severity_1},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "isNegated": True,
                    "stringEqual": {"value": negated_severity_2},
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        for edge in result.edges:
            assert isinstance(edge.node, Alert)
            assert edge.node.severity not in (negated_severity_1, negated_severity_2)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_max_first_parameter(self, alerts_client: AlertsClient) -> None:
        """Test search with maximum 'first' parameter value."""
        n_requested = 100
        severity_values = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": severity_values},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=n_requested, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")
        assert len(result.edges) == n_requested


class TestPaginationWithFilters:
    """Test pagination combined with filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pagination_with_single_filter(self, alerts_client: AlertsClient) -> None:
        """Test pagination works correctly with filters applied."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            )
        ]

        # Get first page
        first_page = await alerts_client.search_alerts(
            filters=filters, first=2, view_type=ViewType.ALL
        )
        assert first_page is not None
        assert hasattr(first_page, "page_info")

        # If there's a next page, fetch it
        if first_page.page_info.has_next_page and first_page.page_info.end_cursor:
            second_page = await alerts_client.search_alerts(
                filters=filters,
                first=2,
                after=first_page.page_info.end_cursor,
                view_type=ViewType.ALL,
            )
            assert second_page is not None
            assert hasattr(second_page, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pagination_with_multiple_filters(self, alerts_client: AlertsClient) -> None:
        """Test pagination with multiple filters applied."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringEqual": {"value": "HIGH"},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": ["NEW", "IN_PROGRESS"]},
                }
            ),
        ]

        # Get first page
        first_page = await alerts_client.search_alerts(
            filters=filters, first=3, view_type=ViewType.ALL
        )
        assert first_page is not None
        assert hasattr(first_page, "page_info")

        # If there's a next page, fetch it with same filters
        if first_page.page_info.has_next_page and first_page.page_info.end_cursor:
            second_page = await alerts_client.search_alerts(
                filters=filters,
                first=3,
                after=first_page.page_info.end_cursor,
                view_type=ViewType.ALL,
            )
            assert second_page is not None
            assert hasattr(second_page, "edges")
