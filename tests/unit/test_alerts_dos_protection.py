"""Tests for DoS protection in alerts tools."""

import json
from unittest.mock import Mock, patch

import pytest
from pydantic import JsonValue

from purple_mcp.libs.alerts import AlertConnection
from purple_mcp.tools import alerts
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.alerts.helpers.base import AlertsTestBase


class TestSearchAlertsDoSProtection(AlertsTestBase):
    """Test DoS protection for search_alerts tool."""

    @pytest.mark.asyncio
    async def test_too_many_filters(self) -> None:
        """Test that too many filters are rejected."""
        # Create 51 filters (over the limit of 50)
        filters: list[dict[str, JsonValue]] = []
        for i in range(51):
            filters.append(
                {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
            )

        tool_args = {"filters": json.dumps(filters)}
        await self.assert_tool_validation_error(
            alerts.search_alerts,
            tool_args,
            "Too many filters: 51. Maximum allowed: 50",
        )

    @pytest.mark.asyncio
    async def test_exactly_max_filters_allowed(self) -> None:
        """Test that exactly 50 filters (at the limit) are allowed."""
        # Create exactly 50 filters (at the limit)
        filters: list[dict[str, JsonValue]] = []
        for i in range(50):
            filters.append(
                {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
            )

        # Mock the client to avoid actual API calls
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            mock_client = self.create_mock_with_connection("search_alerts", AlertConnection)
            mock_get_client.return_value = mock_client

            # Should not raise an error
            result = await alerts.search_alerts(filters=json.dumps(filters))
            assert result is not None

    @pytest.mark.parametrize(
        ("filter_dict", "expected_error"),
        [
            pytest.param(
                {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH"] * 101},
                "Filter 0 has too many values: 101. Maximum allowed: 100",
                id="string-in-too-many-values",
            ),
            pytest.param(
                {"fieldId": "priority", "filterType": "int_in", "values": list(range(101))},
                "Filter 0 has too many values: 101. Maximum allowed: 100",
                id="int-in-too-many-values",
            ),
            pytest.param(
                {"fieldId": "description", "filterType": "fulltext", "values": ["term"] * 101},
                "Filter 0 has too many values: 101. Maximum allowed: 100",
                id="fulltext-too-many-values",
            ),
            pytest.param(
                {
                    "fieldId": "status",
                    "filterType": "string_in",
                    "values": ["OPEN"] * 101,
                    "isNegated": True,
                },
                "Filter 0 has too many values: 101. Maximum allowed: 100",
                id="negated-string-in-too-many-values",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_filter_with_too_many_values(
        self, filter_dict: JsonDict, expected_error: str
    ) -> None:
        """Test that filters with too many values are rejected."""
        await self.assert_tool_validation_error(
            alerts.search_alerts, {"filters": json.dumps([filter_dict])}, expected_error
        )

    @pytest.mark.parametrize(
        "filter_dict",
        [
            pytest.param(
                {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH"] * 100},
                id="string-in-max-values",
            ),
            pytest.param(
                {"fieldId": "priority", "filterType": "int_in", "values": list(range(100))},
                id="int-in-max-values",
            ),
            pytest.param(
                {"fieldId": "description", "filterType": "fulltext", "values": ["term"] * 100},
                id="fulltext-max-values",
            ),
            pytest.param(
                {
                    "fieldId": "status",
                    "filterType": "string_in",
                    "values": ["OPEN"] * 100,
                    "isNegated": True,
                },
                id="negated-string-in-max-values",
            ),
        ],
    )
    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_filter_with_exactly_max_values_allowed(
        self, mock_get_client: Mock, filter_dict: JsonDict
    ) -> None:
        """Test that filters with exactly 100 values (at the limit) are allowed."""
        mock_client = self.create_mock_with_connection("search_alerts", AlertConnection)
        mock_get_client.return_value = mock_client

        # Should not raise an error
        result = await alerts.search_alerts(filters=json.dumps([filter_dict]))
        assert result is not None

    @pytest.mark.asyncio
    async def test_early_validation_catches_oversized_values_array(self) -> None:
        """Test that the early validation in search_alerts catches oversized arrays."""
        # This tests the early validation before filter parsing
        filter_with_oversized_values: JsonDict = {
            "field": "severity",
            "operator": "IN",
            "values": ["HIGH"] * 101,  # This should be caught by early validation
        }

        await self.assert_tool_validation_error(
            alerts.search_alerts,
            {"filters": json.dumps([filter_with_oversized_values])},
            "Filter 0 has too many values: 101. Maximum allowed: 100",
        )

    @pytest.mark.asyncio
    async def test_mixed_valid_and_invalid_filters(self) -> None:
        """Test scenario with some valid filters and one invalid filter."""
        filters: list[dict[str, JsonValue]] = [
            # Valid filters
            {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
            {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"},
            # Invalid filter with too many values
            {"fieldId": "tags", "filterType": "string_in", "values": ["tag"] * 101},
        ]

        await self.assert_tool_validation_error(
            alerts.search_alerts,
            {"filters": json.dumps(filters)},
            "Filter 2 has too many values: 101. Maximum allowed: 100",
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_complex_valid_scenario(self, mock_get_client: Mock) -> None:
        """Test a complex but valid scenario with many filters and values."""
        mock_client = self.create_mock_with_connection("search_alerts", AlertConnection)
        mock_get_client.return_value = mock_client

        # Create a complex but valid scenario
        filters: list[dict[str, JsonValue]] = []

        # Add 25 filters with single values
        for i in range(25):
            filters.append(
                {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
            )

        # Add 5 filters with exactly 100 values each
        for i in range(5):
            filter_dict: dict[str, JsonValue] = {
                "fieldId": f"multi_field{i}",
                "filterType": "string_in",
                "values": [f"value{j}" for j in range(100)],
            }
            filters.append(filter_dict)

        # Should not raise an error (30 filters total, all within limits)
        result = await alerts.search_alerts(filters=json.dumps(filters), first=50)
        assert result is not None

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_non_list_values_not_affected(self, mock_get_client: Mock) -> None:
        """Test that non-list values in filters are not affected by validation."""
        mock_client = self.create_mock_with_connection("search_alerts", AlertConnection)
        mock_get_client.return_value = mock_client

        # Filters with non-list values should work fine
        # Filters with non-list values should work fine
        filters: list[dict[str, JsonValue]] = [
            {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
            {"fieldId": "priority", "filterType": "int_equals", "value": 5},
            {"fieldId": "isResolved", "filterType": "boolean_equals", "value": False},
        ]

        result = await alerts.search_alerts(filters=json.dumps(filters))
        assert result is not None

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_empty_filters_list_allowed(self, mock_get_client: Mock) -> None:
        """Test that empty filters list is allowed."""
        mock_client = self.create_mock_with_connection("search_alerts", AlertConnection)
        mock_get_client.return_value = mock_client

        result = await alerts.search_alerts(filters=json.dumps([]))
        assert result is not None

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_none_filters_allowed(self, mock_get_client: Mock) -> None:
        """Test that None filters is allowed."""
        mock_client = self.create_mock_with_connection("search_alerts", AlertConnection)
        mock_get_client.return_value = mock_client

        result = await alerts.search_alerts(filters=None)
        assert result is not None


class TestDoSProtectionConstants:
    """Test DoS protection constants are correctly defined."""

    def test_constants_exist(self) -> None:
        """Test that DoS protection constants exist and have expected values."""
        assert hasattr(alerts, "MAX_FILTERS_COUNT")
        assert hasattr(alerts, "MAX_FILTER_VALUES_COUNT")
        assert alerts.MAX_FILTERS_COUNT == 50
        assert alerts.MAX_FILTER_VALUES_COUNT == 100

    def test_constants_are_integers(self) -> None:
        """Test that constants are proper integers."""
        assert isinstance(alerts.MAX_FILTERS_COUNT, int)
        assert isinstance(alerts.MAX_FILTER_VALUES_COUNT, int)
        assert alerts.MAX_FILTERS_COUNT > 0
        assert alerts.MAX_FILTER_VALUES_COUNT > 0
