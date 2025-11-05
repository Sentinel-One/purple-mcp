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

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.alerts import AlertsClient, AlertsConfig, FilterInput, ViewType


@pytest.fixture
def alerts_config(integration_env_check: dict[str, str]) -> AlertsConfig:
    """Create alerts configuration from environment variables.

    Returns:
        AlertsConfig with settings from environment.
    """
    settings = get_settings()

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
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringEqual": {"value": "CRITICAL"},
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
    async def test_string_equals_status(self, alerts_client: AlertsClient) -> None:
        """Test string_equals filter on status field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringEqual": {"value": "NEW"},
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
    async def test_string_equals_analyst_verdict(self, alerts_client: AlertsClient) -> None:
        """Test string_equals filter on analystVerdict field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "analystVerdict",
                    "stringEqual": {"value": "TRUE_POSITIVE"},
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
    async def test_string_in_severity(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter on severity field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
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
    async def test_string_in_status_multiple(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter with multiple status values."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": ["NEW", "IN_PROGRESS", "ON_HOLD"]},
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
    async def test_string_in_all_severities(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter with all severity values."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]},
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
    async def test_string_equals_negated(self, alerts_client: AlertsClient) -> None:
        """Test string_equals filter with isNegated=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "isNegated": True,
                    "stringEqual": {"value": "LOW"},
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
    async def test_string_in_alert_name(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter on alertName field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertName",
                    "stringIn": {"values": ["Threat", "Malware"]},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")


class TestBooleanFilters:
    """Test boolean filter types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_equals_true(self, alerts_client: AlertsClient) -> None:
        """Test boolean_equals filter with value=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": True},
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
    async def test_boolean_equals_false(self, alerts_client: AlertsClient) -> None:
        """Test boolean_equals filter with value=false."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": False},
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
    async def test_boolean_negated(self, alerts_client: AlertsClient) -> None:
        """Test boolean_equals filter with isNegated=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "isNegated": True,
                    "booleanEqual": {"value": True},
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
    async def test_boolean_in_single_value(self, alerts_client: AlertsClient) -> None:
        """Test boolean_in filter with single value."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanIn": {"values": [True]},
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
    async def test_boolean_in_multiple_values(self, alerts_client: AlertsClient) -> None:
        """Test boolean_in filter with multiple values (true and false)."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanIn": {"values": [True, False]},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")


class TestDateTimeFilters:
    """Test datetime range filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_both_bounds(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with both start and end."""
        import time

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
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_start_only(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with only start bound."""
        import time

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
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_end_only(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with only end bound."""
        import time

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
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_exclusive_bounds(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter with exclusive bounds."""
        import time

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
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_created_at(self, alerts_client: AlertsClient) -> None:
        """Test datetime_range filter on createdAt field."""
        import time

        seven_days_ago_ms = int((time.time() - (7 * 24 * 60 * 60)) * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "createdAt",
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
        assert hasattr(result, "edges")


class TestFulltextFilters:
    """Test fulltext search filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_single_term(self, alerts_client: AlertsClient) -> None:
        """Test fulltext filter with single search term."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertName",
                    "match": {"values": ["threat"]},
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
    async def test_fulltext_multiple_terms(self, alerts_client: AlertsClient) -> None:
        """Test fulltext filter with multiple search terms."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "alertName",
                    "match": {"values": ["malware", "threat"]},
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
    async def test_fulltext_id_search(self, alerts_client: AlertsClient) -> None:
        """Test fulltext filter searching alert IDs."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "id",
                    "match": {"values": ["alert"]},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")


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
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assigneeUserId",
                    "longEqual": {"value": 1},
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
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assigneeUserId",
                    "longIn": {"values": [1, 2, 3]},
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
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringEqual": {"value": "CRITICAL"},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringEqual": {"value": "NEW"},
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
    async def test_string_and_boolean_filters(self, alerts_client: AlertsClient) -> None:
        """Test combination of string and boolean filters."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": True},
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
    async def test_string_and_datetime_filters(self, alerts_client: AlertsClient) -> None:
        """Test combination of string and datetime filters."""
        import time

        thirty_days_ago_ms = int((time.time() - (30 * 24 * 60 * 60)) * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": ["NEW", "IN_PROGRESS"]},
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
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": False},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringEqual": {"value": "NEW"},
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
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "isNegated": True,
                    "stringEqual": {"value": "RESOLVED"},
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
        import time

        ninety_days_ago_ms = int((time.time() - (90 * 24 * 60 * 60)) * 1_000)

        filters = [
            # Critical or High severity
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            ),
            # Not resolved
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "isNegated": True,
                    "stringEqual": {"value": "RESOLVED"},
                }
            ),
            # No notes
            FilterInput.model_validate(
                {
                    "fieldId": "alertNoteExists",
                    "booleanEqual": {"value": False},
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


class TestFieldVariations:
    """Test filters on various field types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_severity_variations(self, alerts_client: AlertsClient) -> None:
        """Test filtering by different severity levels."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["MEDIUM", "LOW", "INFO"]},
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
    async def test_filter_status_variations(self, alerts_client: AlertsClient) -> None:
        """Test filtering by different status values."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": ["DISMISSED", "CLOSED"]},
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
    async def test_filter_storyline_id(self, alerts_client: AlertsClient) -> None:
        """Test filtering by storylineId field (flattened field)."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "storylineId",
                    "match": {"values": ["storyline"]},
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
    async def test_filter_assignee_full_name(self, alerts_client: AlertsClient) -> None:
        """Test filtering by assigneeFullName field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assigneeFullName",
                    "stringEqual": {"value": "John Doe"},
                }
            )
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
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "isNegated": True,
                    "stringEqual": {"value": "LOW"},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "isNegated": True,
                    "stringEqual": {"value": "INFO"},
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
    async def test_max_first_parameter(self, alerts_client: AlertsClient) -> None:
        """Test search with maximum 'first' parameter value."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                }
            )
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=100, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_with_many_values(self, alerts_client: AlertsClient) -> None:
        """Test string_in filter with many values."""
        statuses = [
            "NEW",
            "IN_PROGRESS",
            "ON_HOLD",
            "RESOLVED",
            "DISMISSED",
            "CLOSED",
        ]

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": statuses},
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
    async def test_all_filters_negated(self, alerts_client: AlertsClient) -> None:
        """Test search where all filters are negated."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "isNegated": True,
                    "stringEqual": {"value": "LOW"},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "isNegated": True,
                    "stringEqual": {"value": "RESOLVED"},
                }
            ),
        ]

        result = await alerts_client.search_alerts(
            filters=filters, first=5, view_type=ViewType.ALL
        )
        assert result is not None
        assert hasattr(result, "edges")


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
