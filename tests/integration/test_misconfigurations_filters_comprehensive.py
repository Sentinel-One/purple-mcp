"""Comprehensive integration tests for misconfigurations filter combinations.

These tests exercise every possible filter type and combination to ensure
no errors occur during filtering operations. Tests are designed to verify
filter functionality rather than data accuracy.

IMPORTANT: These tests accurately reflect the XSPM GraphQL API schema.
- No INT_* filters exist in the misconfigurations API
- DateTime fields use dateTimeRange (DATE_RANGE filter type)
- secretValidity uses BOOLEAN_IN only (not BOOLEAN_EQUAL)
- secretHash/secretId only support FULLTEXT/FULLTEXT_IN (not STRING_EQUAL)
- product/vendor only support STRING_IN/STRING_EQUAL (not FULLTEXT)

Requirements:
- PURPLEMCP_CONSOLE_TOKEN: Valid API token
- PURPLEMCP_CONSOLE_BASE_URL: Console base URL

Tests will be skipped if environment is not configured.
"""

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.misconfigurations import (
    FilterInput,
    MisconfigurationsClient,
    MisconfigurationsConfig,
)


@pytest.fixture
def misconfigurations_config(integration_env_check: dict[str, str]) -> MisconfigurationsConfig:
    """Create misconfigurations configuration from environment variables.

    Returns:
        MisconfigurationsConfig with settings from environment.
    """
    settings = get_settings()

    return MisconfigurationsConfig(
        graphql_url=settings.misconfigurations_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,  # Extended timeout for filter operations
    )


@pytest.fixture
def misconfigurations_client(
    misconfigurations_config: MisconfigurationsConfig,
) -> MisconfigurationsClient:
    """Create a misconfigurations client instance."""
    return MisconfigurationsClient(misconfigurations_config)


class TestStringFilters:
    """Test all string filter types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_severity(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_status(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_analyst_verdict(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_severity(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter on severity field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {"values": ["CRITICAL", "HIGH"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_status_multiple(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_all_severities(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter with all severity values."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "severity",
                    "stringIn": {
                        "values": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"]
                    },
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equals_negated(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_finding_type(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter on findingType field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "findingType",
                    "stringIn": {"values": ["MISCONFIGURATION", "VULNERABILITY"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_equal_product(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_equal filter on product field.

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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_vendor(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter on vendor field.

        Note: vendor field only supports STRING_IN and STRING_EQUAL, not FULLTEXT.
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "vendor",
                    "stringIn": {"values": ["Microsoft", "Google", "Amazon"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestBooleanFilters:
    """Test boolean filter types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_equals_true(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test boolean_equals filter with value=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "mitigable",
                    "booleanEqual": {"value": True},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_equals_false(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test boolean_equals filter with value=false."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "mitigable",
                    "booleanEqual": {"value": False},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_verified_exploitable_true(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test boolean filter on verifiedExploitable field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "verifiedExploitable",
                    "booleanEqual": {"value": True},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_negated(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test boolean_equals filter with isNegated=true."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "mitigable",
                    "isNegated": True,
                    "booleanEqual": {"value": True},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_single_value(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test boolean_in filter with single value."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "hasClassifiedData",
                    "booleanIn": {"values": [True]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_multiple_values(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test boolean_in filter with multiple values (true and false)."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetPrivileged",
                    "booleanIn": {"values": [True, False]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_boolean_in_secret_validity(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test boolean_in filter on secretValidity field.

        Note: secretValidity only supports BOOLEAN_IN, not BOOLEAN_EQUAL.
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "secretValidity",
                    "booleanIn": {"values": [True]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestDateTimeFilters:
    """Test datetime range filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_both_bounds(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_start_only(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_end_only(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_range_exclusive_bounds(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_datetime_last_seen_at(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestFulltextFilters:
    """Test fulltext search filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_single_term(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext filter with single search term."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "name",
                    "match": {"values": ["security"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_multiple_terms(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext filter with multiple search terms."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "name",
                    "match": {"values": ["s3", "bucket"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_exposure_reason(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext filter on exposureReason field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "exposureReason",
                    "match": {"values": ["public"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_in_asset_name(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext_in filter on asset name for partial matching."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetName",
                    "matchIn": {"values": ["server", "prod", "web"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_in_asset_cloud_resource(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_committed_by(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext filter on commitedBy field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "commitedBy",
                    "match": {"values": ["admin"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestSecretFilters:
    """Test filters specific to secret scanning."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_secret_hash(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext filter on secretHash field.

        Note: secretHash only supports FULLTEXT/FULLTEXT_IN, not STRING_EQUAL.
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "secretHash",
                    "match": {"values": ["abc"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_in_asset_id(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext_in filter on assetId field.

        Note: assetId supports FULLTEXT/FULLTEXT_IN/STRING_EQUAL.
        Using matchIn for multi-value search.
        """
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetId",
                    "matchIn": {"values": ["asset"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_secret_type(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter on secretType field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "secretType",
                    "stringIn": {"values": ["AWS_ACCESS_KEY", "GITHUB_TOKEN"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestAdmissionControlFilters:
    """Test filters specific to Kubernetes admission control."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_request_resource_name(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext filter on requestResourceName field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "requestResourceName",
                    "match": {"values": ["deployment"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fulltext_request_user_name(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test fulltext filter on requestUserName field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "requestUserName",
                    "match": {"values": ["admin"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_request_resource_type(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter on requestResourceType field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "requestResourceType",
                    "stringIn": {"values": ["Pod", "Deployment", "Service"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_request_category(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter on requestCategory field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "requestCategory",
                    "stringIn": {"values": ["Security", "NetworkPolicy"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestFilterCombinations:
    """Test combinations of multiple filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_two_string_filters(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_and_boolean_filters(
        self, misconfigurations_client: MisconfigurationsClient
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
                    "fieldId": "mitigable",
                    "booleanEqual": {"value": True},
                }
            ),
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_and_datetime_filters(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_three_filters_mixed_types(
        self, misconfigurations_client: MisconfigurationsClient
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
                    "fieldId": "mitigable",
                    "booleanEqual": {"value": True},
                }
            ),
            FilterInput.model_validate(
                {
                    "fieldId": "environment",
                    "stringEqual": {"value": "Production"},
                }
            ),
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filters_with_negation(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complex_filter_combination(
        self, misconfigurations_client: MisconfigurationsClient
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
            # Mitigable
            FilterInput.model_validate(
                {
                    "fieldId": "mitigable",
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestFieldVariations:
    """Test filters on various field types."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_environment(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test filtering by environment field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "environment",
                    "stringIn": {"values": ["Production", "Staging"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_enforcement_action(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test filtering by enforcementAction field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "enforcementAction",
                    "stringIn": {"values": ["DETECT", "DETECT_AND_PROTECT"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_asset_type(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test filtering by asset type."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "assetType",
                    "stringIn": {"values": ["SERVER", "CONTAINER", "VM"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_asset_criticality(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_assignee_full_name(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_iac_framework(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test filtering by IaC framework field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "iacFramework",
                    "stringIn": {"values": ["Terraform", "CloudFormation", "Ansible"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_compliance_standards(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test filtering by complianceStandards field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "complianceStandards",
                    "match": {"values": ["PCI", "HIPAA"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_organization(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test filtering by organization field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "organization",
                    "stringEqual": {"value": "Engineering"},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_data_classification_categories(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test filtering by dataClassificationCategories field."""
        filters = [
            FilterInput.model_validate(
                {
                    "fieldId": "dataClassificationCategories",
                    "stringIn": {"values": ["PII", "PHI", "Financial"]},
                }
            )
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_empty_filter_list(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test search with empty filter list."""
        result = await misconfigurations_client.search_misconfigurations(filters=[], first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_no_filters(self, misconfigurations_client: MisconfigurationsClient) -> None:
        """Test search with None filters."""
        result = await misconfigurations_client.search_misconfigurations(filters=None, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_filters_same_field(
        self, misconfigurations_client: MisconfigurationsClient
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
                    "stringEqual": {"value": "INFO"},
                }
            ),
        ]

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_max_first_parameter(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(
            filters=filters, first=100
        )
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_in_with_many_values(
        self, misconfigurations_client: MisconfigurationsClient
    ) -> None:
        """Test string_in filter with many values."""
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_all_filters_negated(
        self, misconfigurations_client: MisconfigurationsClient
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

        result = await misconfigurations_client.search_misconfigurations(filters=filters, first=5)
        assert result is not None
        assert hasattr(result, "edges")


class TestPaginationWithFilters:
    """Test pagination combined with filters."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pagination_with_single_filter(
        self, misconfigurations_client: MisconfigurationsClient
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
        first_page = await misconfigurations_client.search_misconfigurations(
            filters=filters, first=2
        )
        assert first_page is not None
        assert hasattr(first_page, "page_info")

        # If there's a next page, fetch it
        if first_page.page_info.has_next_page and first_page.page_info.end_cursor:
            second_page = await misconfigurations_client.search_misconfigurations(
                filters=filters, first=2, after=first_page.page_info.end_cursor
            )
            assert second_page is not None
            assert hasattr(second_page, "edges")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pagination_with_multiple_filters(
        self, misconfigurations_client: MisconfigurationsClient
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
        first_page = await misconfigurations_client.search_misconfigurations(
            filters=filters, first=3
        )
        assert first_page is not None
        assert hasattr(first_page, "page_info")

        # If there's a next page, fetch it with same filters
        if first_page.page_info.has_next_page and first_page.page_info.end_cursor:
            second_page = await misconfigurations_client.search_misconfigurations(
                filters=filters, first=3, after=first_page.page_info.end_cursor
            )
            assert second_page is not None
            assert hasattr(second_page, "edges")
