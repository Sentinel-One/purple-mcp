"""Comprehensive integration tests for vulnerabilities filter combinations.

These tests exercise every possible filter type and combination to ensure
no errors occur during filtering operations. Tests are designed to verify
filter functionality rather than data accuracy.

IMPORTANT: These tests accurately reflect the XSPM GraphQL API schema.
- cveEpssScore: Uses STRING_IN only (bucketed ranges), not numeric filters
- cveNvdBaseScore/cveRiskScore: NOT filterable (sort-only fields)
- No INT_* filters exist in the vulnerabilities API
- DateTime fields use dateTimeRange (DATE_RANGE filter type)

Requirements:
- PURPLEMCP_CONSOLE_TOKEN: Valid API token
- PURPLEMCP_CONSOLE_BASE_URL: Console base URL

Tests will be skipped if environment is not configured.
"""

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.vulnerabilities import (
    FilterInput,
    VulnerabilitiesClient,
    VulnerabilitiesConfig,
)


@pytest.fixture
def vulnerabilities_config(integration_env_check: dict[str, str]) -> VulnerabilitiesConfig:
    """Create vulnerabilities configuration from environment variables.

    Returns:
        VulnerabilitiesConfig with settings from environment.
    """
    settings = get_settings()

    return VulnerabilitiesConfig(
        graphql_url=settings.vulnerabilities_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,  # Extended timeout for filter operations
    )


@pytest.fixture
def vulnerabilities_client(
    vulnerabilities_config: VulnerabilitiesConfig,
) -> VulnerabilitiesClient:
    """Create a vulnerabilities client instance."""
    return VulnerabilitiesClient(vulnerabilities_config)


class TestStringFilters:
    """Test all string filter types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_severity(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_equals filter on severity field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringEqual": {"value": "CRITICAL"},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_status(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_equals filter on status field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringEqual": {"value": "NEW"},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_analyst_verdict(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_equals filter on analystVerdict field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "analystVerdict",
                    "stringEqual": {"value": "TRUE_POSITIVE"},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_severity(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test string_in filter on severity field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_status_multiple(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_in filter with multiple status values."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": ["NEW", "IN_PROGRESS", "ON_HOLD"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_all_severities(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_in filter with all severity values."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_negated(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestIntegerFilters:
    """Test integer-related fields.

    NOTE: There are NO integer filter types in the vulnerabilities API.
    Fields like cveEpssScore use STRING_IN with bucketed ranges.
    Fields like cveNvdBaseScore are sort-only (not filterable).
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_epss_score(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_in filter on cveEpssScore.

        EPSS scores use STRING_IN with range format "x-y" based on boundaries: 0.0, 0.35, 0.5, 0.75, 1.0
        Valid ranges:
        - "0.0-0.35": Less than 35%
        - "0.35-0.5": Between 35% and 50%
        - "0.5-0.75": Between 50% and 75%
        - "0.75-1.0": Greater than 75%
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveEpssScore",
                    "stringIn": {"values": ["0.5-0.75", "0.75-1.0"]},  # High EPSS scores
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestBooleanFilters:
    """Test boolean filter types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_equals_true(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test boolean_equals filter with value=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveExploitedInTheWild",
                    "booleanEqual": {"value": True},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_equals_false(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test boolean_equals filter with value=false."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveExploitedInTheWild",
                    "booleanEqual": {"value": False},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_kev_available_true(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test boolean filter on kevAvailable field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveKevAvailable",
                    "booleanEqual": {"value": True},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_negated(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test boolean_equals filter with isNegated=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveExploitedInTheWild",
                    "isNegated": True,
                    "booleanEqual": {"value": True},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_single_value(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test boolean_in filter with single value."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveExploitedInTheWild",
                    "booleanIn": {"values": [True]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_multiple_values(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test boolean_in filter with multiple values (true and false)."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveKevAvailable",
                    "booleanIn": {"values": [True, False]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_with_null(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test boolean_in filter including null to match unset values."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "softwareFixVersionAvailable",
                    "booleanIn": {"values": [True, None]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestDateTimeFilters:
    """Test datetime range filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_both_bounds(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test datetime_range filter with both start and end."""
        # Use timestamps for a reasonable date range (last 90 days)
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_start_only(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_end_only(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_exclusive_bounds(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_last_seen_at(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test datetime_range filter on lastSeenAt field."""
        import time

        seven_days_ago_ms = int((time.time() - (7 * 24 * 60 * 60)) * 1_000)

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "lastSeenAt",
                    "dateTimeRange": {
                        "start": seven_days_ago_ms,
                        "startInclusive": True,
                    },
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestFulltextFilters:
    """Test fulltext search filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_single_term(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test fulltext filter with single search term."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "name",
                    "match": {"values": ["CVE"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_multiple_terms(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test fulltext filter with multiple search terms."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "name",
                    "match": {"values": ["apache", "log4j"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_cve_search(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test fulltext filter searching for CVE identifiers."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveId",
                    "match": {"values": ["2024"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_in_single_value(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test fulltext_in filter with single search value."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "softwareName",
                    "matchIn": {"values": ["apache"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_in_multiple_values(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test fulltext_in filter with multiple search values for partial matching."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetName",
                    "matchIn": {"values": ["server", "prod", "web"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_in_asset_cloud_resource(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test fulltext_in filter on cloud resource IDs."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetCloudResourceId",
                    "matchIn": {"values": ["i-", "vol-", "sg-"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestFilterCombinations:
    """Test combinations of multiple filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_two_string_filters(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_and_boolean_filters(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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
                    "fieldId": "cveExploitedInTheWild",
                    "booleanEqual": {"value": True},
                }
            ),
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_and_epss_filters(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test combination of string and EPSS score filters."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringEqual": {"value": "HIGH"},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "cveEpssScore",
                    "stringIn": {"values": ["0.5-0.75", "0.75-1.0"]},
                }
            ),
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_and_datetime_filters(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_three_filters_mixed_types(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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
                    "fieldId": "cveExploitedInTheWild",
                    "booleanEqual": {"value": True},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "cveEpssScore",
                    "stringIn": {"values": ["0.75-1.0"]},  # Greater than 75%
                }
            ),
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filters_with_negation(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complex_filter_combination(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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
            # Exploited in the wild
            FilterInput.model_validate(
                {
                    "fieldId": "cveExploitedInTheWild",
                    "booleanEqual": {"value": True},
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_exploited_kev_combination(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test combination of exploited in wild and KEV available filters."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveExploitedInTheWild",
                    "booleanEqual": {"value": True},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "cveKevAvailable",
                    "booleanEqual": {"value": True},
                }
            ),
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_empty_filter_list(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test search with empty filter list."""
        result = await vulnerabilities_client.search_vulnerabilities(filters=[], first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_no_filters(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test search with None filters."""
        result = await vulnerabilities_client.search_vulnerabilities(filters=None, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_filters_same_field(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test multiple filters on the same field (severity with different values)."""
        # Note: XSPM allows multiple filters on same field
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
                    "stringEqual": {"value": "MEDIUM"},
                }
            ),
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_max_first_parameter(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test search with maximum 'first' parameter value."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=100)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_with_many_values(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_in filter with many values."""
        # Create a list with various status values (within reasonable limits)
        statuses = [
            "NEW",
            "IN_PROGRESS",
            "ON_HOLD",
            "RESOLVED",
            "RISK_ACKED",
            "SUPPRESSED",
            "TO_BE_PATCHED",
        ]

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "status",
                    "stringIn": {"values": statuses},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_with_many_asset_types(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test string_in filter with many asset type values."""
        asset_types = ["SERVER", "WORKSTATION", "CONTAINER", "VM", "NETWORK_DEVICE"]

        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetType",
                    "stringIn": {"values": asset_types},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_all_filters_negated(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestFieldVariations:
    """Test filters on various field types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_cve_epss_score(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by CVE EPSS score.

        Note: EPSS returns float (e.g., 0.63806) but filters via STRING_IN with range format "x-y".
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveEpssScore",
                    "stringIn": {"values": ["0.5-0.75", "0.75-1.0"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_product(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test filtering by product field.

        Note: product field only supports STRING_IN and STRING_EQUAL, not FULLTEXT.
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "product",
                    "stringEqual": {"value": "Cloud Native Security"},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_vendor(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test filtering by vendor field.

        Note: vendor field only supports STRING_IN and STRING_EQUAL, not FULLTEXT.
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "vendor",
                    "stringIn": {"values": ["Microsoft", "Apache", "Google"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_software_name(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by software name (flattened field)."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "softwareName",
                    "match": {"values": ["linux"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_software_version(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by software version."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "softwareVersion",
                    "stringIn": {"values": ["1.0", "2.0", "3.0"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_software_type(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by software type enum."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "softwareType",
                    "stringIn": {"values": ["OPERATING_SYSTEM", "APPLICATION"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_asset_name(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test filtering by asset name (flattened field)."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetName",
                    "match": {"values": ["server"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_asset_type(self, vulnerabilities_client: VulnerabilitiesClient) -> None:
        """Test filtering by asset type."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetType",
                    "stringIn": {"values": ["SERVER", "WORKSTATION", "CONTAINER"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_asset_criticality(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by asset criticality enum."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetCriticality",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_cve_exploit_maturity(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by CVE exploit maturity enum."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "cveExploitMaturity",
                    "stringIn": {"values": ["FUNCTIONAL", "HIGH", "PROOF_OF_CONCEPT"]},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_assignee_full_name(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by assignee full name."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assigneeFullName",
                    "stringEqual": {"value": "John Doe"},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_remediation_insights_available(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
        """Test filtering by remediation insights availability."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "remediationInsightsAvailable",
                    "booleanEqual": {"value": True},
                }
            )
        ]

        result = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestPaginationWithFilters:
    """Test pagination combined with filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pagination_with_single_filter(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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
        first_page = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=2)
        assert first_page is not None
        assert hasattr(first_page, "page_info")

        # If there's a next page, fetch it
        if first_page.page_info.has_next_page and first_page.page_info.end_cursor:
            second_page = await vulnerabilities_client.search_vulnerabilities(
                filters=filters, first=2, after=first_page.page_info.end_cursor
            )
            assert second_page is not None
            assert hasattr(second_page, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pagination_with_multiple_filters(
        self, vulnerabilities_client: VulnerabilitiesClient
    ) -> None:
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
        first_page = await vulnerabilities_client.search_vulnerabilities(filters=filters, first=3)
        assert first_page is not None
        assert hasattr(first_page, "page_info")

        # If there's a next page, fetch it with same filters
        if first_page.page_info.has_next_page and first_page.page_info.end_cursor:
            second_page = await vulnerabilities_client.search_vulnerabilities(
                filters=filters, first=3, after=first_page.page_info.end_cursor
            )
            assert second_page is not None
            assert hasattr(second_page, "edges")
