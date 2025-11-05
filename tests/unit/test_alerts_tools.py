"""Tests for alerts tools."""

import json
from typing import cast
from unittest.mock import Mock, patch

import pytest
from pydantic import JsonValue

from purple_mcp.libs.alerts import (
    AlertConnection,
    AlertHistoryConnection,
    AlertNoteConnection,
    AlertsClientError,
    FilterInput,
    ViewType,
)
from purple_mcp.tools import alerts
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.alerts.helpers import AlertsTestData, JSONAssertions, MockAlertsClientBuilder
from tests.unit.libs.alerts.helpers.base import AlertsTestBase


class TestAlertsToolsHelpers:
    """Test helper functions for alerts tools."""

    @patch("purple_mcp.tools.alerts.get_settings")
    def test_get_alerts_client_success(self, mock_get_settings: Mock) -> None:
        """Test successful creation of AlertsClient."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.alerts_graphql_url = "https://example.test/graphql"
        mock_settings.graphql_service_token = "test-token"
        mock_get_settings.return_value = mock_settings

        client = alerts._get_alerts_client()

        assert client.config.graphql_url == "https://example.test/graphql"
        assert client.config.auth_token == "test-token"

    @patch("purple_mcp.tools.alerts.get_settings")
    def test_get_alerts_client_settings_error(self, mock_get_settings: Mock) -> None:
        """Test that settings error is properly handled."""
        mock_get_settings.side_effect = Exception("Settings not configured")

        with pytest.raises(RuntimeError) as exc_info:
            alerts._get_alerts_client()

        JSONAssertions.assert_error_message(exc_info, "Settings not initialized")
        JSONAssertions.assert_error_message(exc_info, "Settings not configured")


class TestGetAlert(AlertsTestBase):
    """Test get_alert tool."""

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_success(self, mock_get_client: Mock) -> None:
        """Test successful alert retrieval."""
        mock_alert = AlertsTestData.create_test_alert()

        result = await self.assert_tool_success(
            alerts.get_alert,
            mock_get_client,
            mock_alert,
            "get_alert",
            expected_client_args=None,
            tool_args={"alert_id": "alert-123"},
        )

        # Verify JSON response
        data = JSONAssertions.assert_alert_response(result, "alert-123")
        assert data["severity"] == "HIGH"
        assert data["name"] == "Test Alert"

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, mock_get_client: Mock) -> None:
        """Test alert not found returns null."""
        result = await self.assert_tool_success(
            alerts.get_alert,
            mock_get_client,
            None,  # Return None for not found
            "get_alert",
            tool_args={"alert_id": "nonexistent-alert"},
        )

        JSONAssertions.assert_null_response(result)

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_client_error(self, mock_get_client: Mock) -> None:
        """Test client error handling."""
        await self.assert_tool_error(
            alerts.get_alert,
            mock_get_client,
            AlertsClientError("Network error"),
            "get_alert",
            "Failed to retrieve alert alert-123",
            {"alert_id": "alert-123"},
            {"alert_id": "alert-123"},
        )


class TestListAlerts(AlertsTestBase):
    """Test list_alerts tool."""

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_list_alerts_success(self, mock_get_client: Mock) -> None:
        """Test successful alerts listing."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)

        result = await self.assert_tool_success(
            alerts.list_alerts,
            mock_get_client,
            mock_connection,
            "list_alerts",
            expected_client_args={
                "first": 10,
                "after": None,
                "view_type": ViewType.ALL,
                "fields": None,
            },
            tool_args={"first": 10, "view_type": "ALL"},
        )

        JSONAssertions.assert_connection_response(result, expected_edges=0)

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_list_alerts_with_pagination(self, mock_get_client: Mock) -> None:
        """Test alerts listing with pagination."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)

        result = await self.assert_tool_success(
            alerts.list_alerts,
            mock_get_client,
            mock_connection,
            "list_alerts",
            expected_client_args={
                "first": 25,
                "after": "cursor-123",
                "view_type": ViewType.ASSIGNED_TO_ME,
                "fields": None,
            },
            tool_args={"first": 25, "after": "cursor-123", "view_type": "ASSIGNED_TO_ME"},
        )

        JSONAssertions.assert_connection_response(result)

    @pytest.mark.parametrize(
        "first_value,expected_error",
        [
            (0, "first must be between 1 and 100"),
            (101, "first must be between 1 and 100"),
            (-1, "first must be between 1 and 100"),
        ],
    )
    @pytest.mark.asyncio
    async def test_list_alerts_invalid_first_parameter(
        self, first_value: int, expected_error: str
    ) -> None:
        """Test validation of first parameter."""
        await self.assert_tool_validation_error(
            alerts.list_alerts, {"first": first_value}, expected_error
        )

    @pytest.mark.asyncio
    async def test_list_alerts_invalid_view_type(self) -> None:
        """Test validation of view_type parameter."""
        await self.assert_tool_validation_error(
            alerts.list_alerts,
            {"view_type": "INVALID_TYPE"},
            "view_type must be one of:",
        )


class TestSearchAlerts(AlertsTestBase):
    """Test search_alerts function."""

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_search_alerts_without_filters(self, mock_get_client: Mock) -> None:
        """Test search without filters."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)

        result = await self.assert_tool_success(
            alerts.search_alerts,
            mock_get_client,
            mock_connection,
            "search_alerts",
            expected_client_args={
                "filters": None,
                "first": 10,
                "after": None,
                "view_type": ViewType.ALL,
                "fields": None,
            },
        )

        JSONAssertions.assert_connection_response(result)

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_search_alerts_with_filters(self, mock_get_client: Mock) -> None:
        """Test search with filters."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)
        mock_client = MockAlertsClientBuilder.create_mock("search_alerts", mock_connection)
        mock_get_client.return_value = mock_client

        filters: list[JsonDict] = [
            {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}
        ]

        result = await alerts.search_alerts(filters=json.dumps(filters), first=5)

        # Verify FilterInput objects were created
        call_args = mock_client.search_alerts.call_args
        assert call_args[1]["first"] == 5
        assert len(call_args[1]["filters"]) == 1
        assert isinstance(call_args[1]["filters"][0], FilterInput)
        assert call_args[1]["filters"][0].field_id == "severity"

        JSONAssertions.assert_connection_response(result)

    @pytest.mark.parametrize(
        "invalid_filters,expected_error",
        [
            (
                [{"field": "severity"}],
                "Each filter must have 'fieldId' and 'filterType' keys",
            ),
            (
                [{"fieldId": "severity", "filterType": "INVALID_TYPE", "value": "HIGH"}],
                "Invalid filter format",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_alerts_invalid_filters(
        self, invalid_filters: list[dict[str, str]], expected_error: str
    ) -> None:
        """Test validation of filter format."""
        await self.assert_tool_validation_error(
            alerts.search_alerts,
            cast(JsonDict, {"filters": json.dumps(invalid_filters)}),
            expected_error,
        )

    @pytest.mark.asyncio
    async def test_search_alerts_dos_protection_too_many_filters(self) -> None:
        """Test DoS protection against too many filters."""
        # Create 51 filters (over the limit of 50)
        filters = []
        for i in range(51):
            filters.append(
                {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
            )

        await self.assert_tool_validation_error(
            alerts.search_alerts,
            cast(JsonDict, {"filters": json.dumps(filters)}),
            "Too many filters: 51. Maximum allowed: 50",
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_search_alerts_dos_protection_max_filters_allowed(
        self, mock_get_client: Mock
    ) -> None:
        """Test that exactly 50 filters (at the limit) are allowed."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)
        mock_client = MockAlertsClientBuilder.create_mock("search_alerts", mock_connection)
        mock_get_client.return_value = mock_client

        # Create exactly 50 filters (at the limit)
        filters: list[dict[str, JsonValue]] = []
        for i in range(50):
            filters.append(
                {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
            )

        result = await alerts.search_alerts(filters=json.dumps(filters), first=20)
        JSONAssertions.assert_connection_response(result)

    @pytest.mark.parametrize(
        "filter_dict,expected_error",
        [
            # New format - string_in with too many values
            (
                {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH"] * 101},
                "Filter 0 has too many values: 101. Maximum allowed: 100",
            ),
            # Legacy format - IN with too many values in 'value' field
            (
                {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH"] * 101},
                "Filter 0 has too many values: 101. Maximum allowed: 100",
            ),
            # Legacy format - IN with too many values in 'values' field
            (
                {"fieldId": "status", "filterType": "string_in", "values": ["OPEN"] * 101},
                "Filter 0 has too many values: 101. Maximum allowed: 100",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_alerts_dos_protection_too_many_values(
        self, filter_dict: JsonDict, expected_error: str
    ) -> None:
        """Test DoS protection against filters with too many values."""
        await self.assert_tool_validation_error(
            alerts.search_alerts,
            cast(JsonDict, {"filters": json.dumps([filter_dict])}),
            expected_error,
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_search_alerts_dos_protection_max_values_allowed(
        self, mock_get_client: Mock
    ) -> None:
        """Test that filters with exactly 100 values (at the limit) are allowed."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)
        mock_client = MockAlertsClientBuilder.create_mock("search_alerts", mock_connection)
        mock_get_client.return_value = mock_client

        # Test with string_in filter having exactly 100 values
        filter_dict = {
            "fieldId": "severity",
            "filterType": "string_in",
            "values": ["HIGH"] * 100,
        }

        result = await alerts.search_alerts(filters=json.dumps([filter_dict]))
        JSONAssertions.assert_connection_response(result)

    @pytest.mark.asyncio
    async def test_search_alerts_string_in_filter(self) -> None:
        """Test string_in filter works correctly."""
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            mock_client = MockAlertsClientBuilder.create_mock(
                "search_alerts",
                return_value=MockAlertsClientBuilder.create_empty_connection(AlertConnection),
            )
            mock_get_client.return_value = mock_client

            # Test string_in filter
            filters = [
                {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH", "CRITICAL"]}
            ]
            await alerts.search_alerts(filters=json.dumps(filters))

            # Verify the filter was converted correctly
            call_args = mock_client.search_alerts.call_args
            filter_input = call_args[1]["filters"][0]
            assert filter_input.string_in is not None
            assert filter_input.string_in.values == ["HIGH", "CRITICAL"]

    @pytest.mark.asyncio
    async def test_search_alerts_int_in_filter(self) -> None:
        """Test int_in filter works correctly."""
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            mock_client = MockAlertsClientBuilder.create_mock(
                "search_alerts",
                return_value=MockAlertsClientBuilder.create_empty_connection(AlertConnection),
            )
            mock_get_client.return_value = mock_client

            # Test int_in filter
            filters = [{"fieldId": "priority", "filterType": "int_in", "values": [1, 2, 3]}]
            await alerts.search_alerts(filters=json.dumps(filters))

            # Verify the filter was converted to int_in filter
            call_args = mock_client.search_alerts.call_args
            filter_input = call_args[1]["filters"][0]
            assert filter_input.int_in is not None
            assert filter_input.int_in.values == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_search_alerts_boolean_equals_filter(self) -> None:
        """Test boolean_equals filter works correctly."""
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            mock_client = MockAlertsClientBuilder.create_mock(
                "search_alerts",
                return_value=MockAlertsClientBuilder.create_empty_connection(AlertConnection),
            )
            mock_get_client.return_value = mock_client

            # Test boolean_equals filter
            filters = [{"fieldId": "isResolved", "filterType": "boolean_equals", "value": True}]
            await alerts.search_alerts(filters=json.dumps(filters))

            # Verify the filter was converted correctly
            call_args = mock_client.search_alerts.call_args
            filter_input = call_args[1]["filters"][0]
            assert filter_input.boolean_equal is not None
            assert filter_input.boolean_equal.value is True

    @pytest.mark.asyncio
    async def test_search_alerts_datetime_range_filter(self) -> None:
        """Test datetime_range filter works correctly."""
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            mock_client = MockAlertsClientBuilder.create_mock(
                "search_alerts",
                return_value=MockAlertsClientBuilder.create_empty_connection(AlertConnection),
            )
            mock_get_client.return_value = mock_client

            # Test with epoch timestamp (nanoseconds)
            timestamp_ns = 1640995200000  # 2022-01-01 00:00:00 UTC in ms
            filters = [
                {
                    "fieldId": "createdAt",
                    "filterType": "datetime_range",
                    "start": timestamp_ns,
                    "startInclusive": False,
                }
            ]
            await alerts.search_alerts(filters=json.dumps(filters))

            # Verify the filter was converted to datetime_range filter
            call_args = mock_client.search_alerts.call_args
            filter_input = call_args[1]["filters"][0]
            assert filter_input.date_time_range is not None
            assert filter_input.date_time_range.start == timestamp_ns
            assert filter_input.date_time_range.start_inclusive is False

    @pytest.mark.asyncio
    async def test_search_alerts_int_range_filter(self) -> None:
        """Test int_range filter works correctly."""
        with patch("purple_mcp.tools.alerts._get_alerts_client") as mock_get_client:
            mock_client = MockAlertsClientBuilder.create_mock(
                "search_alerts",
                return_value=MockAlertsClientBuilder.create_empty_connection(AlertConnection),
            )
            mock_get_client.return_value = mock_client

            # Test with int_range filter
            filters = [
                {
                    "fieldId": "priority",
                    "filterType": "int_range",
                    "start": 50,
                    "startInclusive": False,
                }
            ]
            await alerts.search_alerts(filters=json.dumps(filters))

            # Verify the filter was converted to int_range filter
            call_args = mock_client.search_alerts.call_args
            filter_input = call_args[1]["filters"][0]
            assert filter_input.int_range is not None
            assert filter_input.int_range.start == 50
            assert filter_input.int_range.start_inclusive is False

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_search_alerts_with_after_parameter(self, mock_get_client: Mock) -> None:
        """Test search_alerts with after pagination parameter."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)
        mock_client = MockAlertsClientBuilder.create_mock("search_alerts", mock_connection)
        mock_get_client.return_value = mock_client

        await alerts.search_alerts(first=5, after="cursor-123")

        # Verify the after parameter was passed to the client
        call_args = mock_client.search_alerts.call_args
        assert call_args[1]["first"] == 5
        assert call_args[1]["after"] == "cursor-123"
        assert call_args[1]["filters"] is None
        assert call_args[1]["view_type"] == ViewType.ALL


class TestGetAlertNotes(AlertsTestBase):
    """Test get_alert_notes tool."""

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_notes_success(self, mock_get_client: Mock) -> None:
        """Test successful notes retrieval."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertNoteConnection)

        result = await self.assert_tool_success(
            alerts.get_alert_notes,
            mock_get_client,
            mock_connection,
            "get_alert_notes",
            expected_client_args={"alert_id": "alert-123"},
            tool_args={"alert_id": "alert-123"},
        )

        JSONAssertions.assert_connection_response(result)


class TestCursorValidation(AlertsTestBase):
    """Test cursor validation across all functions."""

    @pytest.mark.asyncio
    async def test_list_alerts_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected."""
        await self.assert_tool_validation_error(
            alerts.list_alerts,
            {"first": 10, "after": ""},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_list_alerts_invalid_cursor_whitespace_only(self) -> None:
        """Test that whitespace-only cursors are rejected."""
        await self.assert_tool_validation_error(
            alerts.list_alerts,
            {"first": 10, "after": "   \t\n  "},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_get_alert_history_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected for alert history."""
        await self.assert_tool_validation_error(
            alerts.get_alert_history,
            {"alert_id": "test-123", "first": 10, "after": ""},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_get_alert_history_empty_alert_id(self) -> None:
        """Test that empty alert IDs are rejected."""
        await self.assert_tool_validation_error(
            alerts.get_alert_history,
            {"alert_id": "", "first": 10},
            "Alert ID cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_get_alert_history_whitespace_alert_id(self) -> None:
        """Test that whitespace-only alert IDs are rejected."""
        await self.assert_tool_validation_error(
            alerts.get_alert_history,
            {"alert_id": "   \t\n  ", "first": 10},
            "Alert ID cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_search_alerts_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected in search_alerts."""
        await self.assert_tool_validation_error(
            alerts.search_alerts,
            {"first": 10, "after": ""},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_search_alerts_invalid_cursor_whitespace_only(self) -> None:
        """Test that whitespace-only cursors are rejected in search_alerts."""
        await self.assert_tool_validation_error(
            alerts.search_alerts,
            {"first": 10, "after": "   \t\n  "},
            "Cursor cannot be empty",
        )

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_history_alert_id_trimmed(self, mock_get_client: Mock) -> None:
        """Test that alert IDs are properly trimmed."""
        from purple_mcp.libs.alerts import AlertHistoryConnection

        mock_client = MockAlertsClientBuilder.create_mock(
            "get_alert_history",
            return_value=MockAlertsClientBuilder.create_empty_connection(AlertHistoryConnection),
        )
        mock_get_client.return_value = mock_client

        await alerts.get_alert_history(alert_id="  test-123  ", first=10)

        # Verify the alert_id was trimmed
        call_args = mock_client.get_alert_history.call_args
        assert call_args[1]["alert_id"] == "test-123"


class TestGetAlertHistory(AlertsTestBase):
    """Test get_alert_history function."""

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_history_success(self, mock_get_client: Mock) -> None:
        """Test successful history retrieval."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertHistoryConnection)

        result = await self.assert_tool_success(
            alerts.get_alert_history,
            mock_get_client,
            mock_connection,
            "get_alert_history",
            expected_client_args={"alert_id": "alert-123", "first": 10, "after": None},
            tool_args={"alert_id": "alert-123"},
        )

        JSONAssertions.assert_connection_response(result)


class TestFilterParsing:
    """Direct unit tests for filter parsing helper functions."""

    def test_parse_filters_parameter_malformed_json(self) -> None:
        """Test _parse_filters_parameter with malformed JSON."""
        with pytest.raises(ValueError) as exc_info:
            alerts._parse_filters_parameter('{"invalid": json}')

        assert "Invalid JSON in filters parameter" in str(exc_info.value)

    def test_parse_filters_parameter_not_a_list(self) -> None:
        """Test _parse_filters_parameter with valid JSON that is not a list."""
        with pytest.raises(ValueError) as exc_info:
            alerts._parse_filters_parameter('{"fieldId": "severity"}')

        assert "Filters must be an array of filter objects" in str(exc_info.value)

    def test_parse_filters_parameter_string_not_list(self) -> None:
        """Test _parse_filters_parameter with a string instead of list."""
        with pytest.raises(ValueError) as exc_info:
            alerts._parse_filters_parameter('"not a list"')

        assert "Filters must be an array of filter objects" in str(exc_info.value)

    def test_parse_filters_parameter_none(self) -> None:
        """Test _parse_filters_parameter with None input."""
        result = alerts._parse_filters_parameter(None)
        assert result is None

    def test_parse_filters_parameter_valid_list(self) -> None:
        """Test _parse_filters_parameter with valid JSON list."""
        result = alerts._parse_filters_parameter(
            '[{"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}]'
        )
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["fieldId"] == "severity"

    def test_convert_filters_missing_fieldid(self) -> None:
        """Test _convert_filters_to_input with missing fieldId."""
        filters: list[JsonDict] = [{"filterType": "string_equals", "value": "HIGH"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "Each filter must have 'fieldId' and 'filterType' keys" in str(exc_info.value)

    def test_convert_filters_missing_filtertype(self) -> None:
        """Test _convert_filters_to_input with missing filterType."""
        filters: list[JsonDict] = [{"fieldId": "severity", "value": "HIGH"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "Each filter must have 'fieldId' and 'filterType' keys" in str(exc_info.value)

    def test_convert_filters_string_equals_missing_value(self) -> None:
        """Test string_equals filter missing required value key."""
        filters: list[JsonDict] = [{"fieldId": "severity", "filterType": "string_equals"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "string_equals filter requires 'value' key" in str(exc_info.value)

    def test_convert_filters_string_in_missing_values(self) -> None:
        """Test string_in filter missing required values key."""
        filters: list[JsonDict] = [{"fieldId": "severity", "filterType": "string_in"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "string_in filter requires 'values' key" in str(exc_info.value)

    def test_convert_filters_boolean_equals_missing_value(self) -> None:
        """Test boolean_equals filter missing required value key."""
        filters: list[JsonDict] = [{"fieldId": "isResolved", "filterType": "boolean_equals"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "boolean_equals filter requires 'value' key" in str(exc_info.value)

    def test_convert_filters_boolean_equals_wrong_type(self) -> None:
        """Test boolean_equals filter with incorrect value type (string instead of boolean)."""
        filters: list[JsonDict] = [
            {"fieldId": "isResolved", "filterType": "boolean_equals", "value": "true"}
        ]
        # This should still work as it's cast to bool, but let's test the actual value
        filter_inputs = alerts._convert_filters_to_input(filters)
        assert len(filter_inputs) == 1
        assert filter_inputs[0].boolean_equal is not None
        # String "true" is cast to Python's bool (truthy)
        assert filter_inputs[0].boolean_equal.value is True

    def test_convert_filters_int_equals_missing_value(self) -> None:
        """Test int_equals filter missing required value key."""
        filters: list[JsonDict] = [{"fieldId": "assigneeUserId", "filterType": "int_equals"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "int_equals filter requires 'value' key" in str(exc_info.value)

    def test_convert_filters_int_in_missing_values(self) -> None:
        """Test int_in filter missing required values key."""
        filters: list[JsonDict] = [{"fieldId": "assigneeUserId", "filterType": "int_in"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "int_in filter requires 'values' key" in str(exc_info.value)

    def test_convert_filters_fulltext_missing_values(self) -> None:
        """Test fulltext filter missing required values key."""
        filters: list[JsonDict] = [{"fieldId": "alertName", "filterType": "fulltext"}]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "fulltext filter requires 'values' key" in str(exc_info.value)

    def test_convert_filters_unsupported_filtertype(self) -> None:
        """Test filter with unsupported filterType."""
        filters: list[JsonDict] = [
            {"fieldId": "severity", "filterType": "string_contains", "value": "test"}
        ]
        with pytest.raises(ValueError) as exc_info:
            alerts._convert_filters_to_input(filters)

        assert "Unsupported string filter type: string_contains" in str(exc_info.value)

    def test_convert_filters_is_negated_string_equals(self) -> None:
        """Test is_negated flag with string_equals filter."""
        filters: list[JsonDict] = [
            {
                "fieldId": "severity",
                "filterType": "string_equals",
                "value": "HIGH",
                "isNegated": True,
            }
        ]
        filter_inputs = alerts._convert_filters_to_input(filters)

        assert len(filter_inputs) == 1
        assert filter_inputs[0].string_equal is not None
        # is_negated is on the FilterInput, not on the individual filter type
        assert filter_inputs[0].is_negated is True

    def test_convert_filters_is_negated_string_in(self) -> None:
        """Test is_negated flag with string_in filter."""
        filters: list[JsonDict] = [
            {
                "fieldId": "severity",
                "filterType": "string_in",
                "values": ["HIGH", "CRITICAL"],
                "isNegated": True,
            }
        ]
        filter_inputs = alerts._convert_filters_to_input(filters)

        assert len(filter_inputs) == 1
        assert filter_inputs[0].string_in is not None
        # is_negated is on the FilterInput, not on the individual filter type
        assert filter_inputs[0].is_negated is True

    def test_convert_filters_is_negated_boolean_equals(self) -> None:
        """Test is_negated flag with boolean_equals filter."""
        filters: list[JsonDict] = [
            {
                "fieldId": "isResolved",
                "filterType": "boolean_equals",
                "value": True,
                "isNegated": True,
            }
        ]
        filter_inputs = alerts._convert_filters_to_input(filters)

        assert len(filter_inputs) == 1
        assert filter_inputs[0].boolean_equal is not None
        # is_negated is on the FilterInput, not on the individual filter type
        assert filter_inputs[0].is_negated is True

    def test_convert_filters_is_negated_datetime_range(self) -> None:
        """Test is_negated flag with datetime_range filter."""
        filters: list[JsonDict] = [
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": 1000000,
                "end": 2000000,
                "isNegated": True,
            }
        ]
        filter_inputs = alerts._convert_filters_to_input(filters)

        assert len(filter_inputs) == 1
        assert filter_inputs[0].date_time_range is not None
        # is_negated is on the FilterInput, not on the individual filter type
        assert filter_inputs[0].is_negated is True

    def test_convert_filters_is_negated_int_equals(self) -> None:
        """Test is_negated flag with int_equals filter."""
        filters: list[JsonDict] = [
            {
                "fieldId": "assigneeUserId",
                "filterType": "int_equals",
                "value": 123,
                "isNegated": True,
            }
        ]
        filter_inputs = alerts._convert_filters_to_input(filters)

        assert len(filter_inputs) == 1
        assert filter_inputs[0].int_equal is not None
        # is_negated is on the FilterInput, not on the individual filter type
        assert filter_inputs[0].is_negated is True

    def test_convert_filters_is_negated_int_in(self) -> None:
        """Test is_negated flag with int_in filter."""
        filters: list[JsonDict] = [
            {
                "fieldId": "assigneeUserId",
                "filterType": "int_in",
                "values": [1, 2, 3],
                "isNegated": True,
            }
        ]
        filter_inputs = alerts._convert_filters_to_input(filters)

        assert len(filter_inputs) == 1
        assert filter_inputs[0].int_in is not None
        # is_negated is on the FilterInput, not on the individual filter type
        assert filter_inputs[0].is_negated is True

    def test_convert_filters_is_negated_fulltext(self) -> None:
        """Test is_negated flag with fulltext filter."""
        filters: list[JsonDict] = [
            {
                "fieldId": "alertName",
                "filterType": "fulltext",
                "values": ["test"],
                "isNegated": True,
            }
        ]
        filter_inputs = alerts._convert_filters_to_input(filters)

        assert len(filter_inputs) == 1
        # Fulltext uses 'match' field in FilterInput model
        assert filter_inputs[0].match is not None
        # is_negated is on the FilterInput, not on the individual filter type
        assert filter_inputs[0].is_negated is True

    def test_validate_filter_limits_too_many_filters(self) -> None:
        """Test _validate_filter_limits with too many filters."""
        filters: list[JsonDict] = [
            {"fieldId": f"field{i}", "filterType": "string_equals", "value": "test"}
            for i in range(51)
        ]

        with pytest.raises(ValueError) as exc_info:
            alerts._validate_filter_limits(filters)

        assert "Too many filters: 51. Maximum allowed: 50" in str(exc_info.value)

    def test_validate_filter_limits_too_many_values_in_string_in(self) -> None:
        """Test _validate_filter_limits with too many values in string_in filter."""
        filters: list[JsonDict] = [
            {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH"] * 101}
        ]

        with pytest.raises(ValueError) as exc_info:
            alerts._validate_filter_limits(filters)

        assert "Filter 0 has too many values: 101" in str(exc_info.value)

    def test_validate_filter_limits_at_max_filters(self) -> None:
        """Test _validate_filter_limits with exactly 50 filters (at limit)."""
        filters: list[JsonDict] = [
            {"fieldId": f"field{i}", "filterType": "string_equals", "value": "test"}
            for i in range(50)
        ]
        # Should not raise an exception
        alerts._validate_filter_limits(filters)

    def test_validate_filter_limits_at_max_values(self) -> None:
        """Test _validate_filter_limits with exactly 100 values (at limit)."""
        filters: list[JsonDict] = [
            {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH"] * 100}
        ]
        # Should not raise an exception
        alerts._validate_filter_limits(filters)

    def test_datetime_range_rejects_nanoseconds_start(self) -> None:
        """Test that datetime_range filter rejects nanosecond timestamps in start field."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": 1640995200000000000,  # 19 digits - nanoseconds
            "end": 1672531199000,  # 13 digits - milliseconds (valid)
        }

        with pytest.raises(ValueError) as exc_info:
            alerts._parse_new_filter_format(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_rejects_nanoseconds_end(self) -> None:
        """Test that datetime_range filter rejects nanosecond timestamps in end field."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": 1640995200000,  # 13 digits - milliseconds (valid)
            "end": 1672531199000000000,  # 19 digits - nanoseconds
        }

        with pytest.raises(ValueError) as exc_info:
            alerts._parse_new_filter_format(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_rejects_negative_nanoseconds_start(self) -> None:
        """Test that datetime_range filter rejects negative nanosecond timestamps in start field."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": -1640995200000000000,  # 19 digits - negative nanoseconds (pre-1970)
            "end": 1672531199000,  # 13 digits - milliseconds (valid)
        }

        with pytest.raises(ValueError) as exc_info:
            alerts._parse_new_filter_format(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_rejects_negative_nanoseconds_end(self) -> None:
        """Test that datetime_range filter rejects negative nanosecond timestamps in end field."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": 1640995200000,  # 13 digits - milliseconds (valid)
            "end": -1672531199000000000,  # 19 digits - negative nanoseconds
        }

        with pytest.raises(ValueError) as exc_info:
            alerts._parse_new_filter_format(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_accepts_negative_milliseconds(self) -> None:
        """Test that datetime_range filter accepts valid negative millisecond timestamps (pre-1970)."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": -86400000,  # 1969-12-31 (negative but valid milliseconds)
            "end": 0,  # 1970-01-01 00:00:00
        }

        # Should not raise an exception - negative milliseconds for pre-1970 dates are valid
        filter_input = alerts._parse_new_filter_format(filter_dict)
        assert filter_input is not None

    def test_datetime_range_accepts_milliseconds(self) -> None:
        """Test that datetime_range filter accepts valid millisecond timestamps."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": 1640995200000,  # 13 digits - milliseconds
            "end": 1672531199000,  # 13 digits - milliseconds
        }

        # Should not raise an exception
        filter_input = alerts._parse_new_filter_format(filter_dict)
        assert filter_input is not None

    def test_datetime_range_converts_string_milliseconds(self) -> None:
        """Test that datetime_range filter converts string milliseconds (from iso_to_unix_timestamp)."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": "1640995200000",  # String milliseconds (from iso_to_unix_timestamp tool)
            "end": "1672531199000",
        }

        # Should convert strings to integers and not raise an exception
        filter_input = alerts._parse_new_filter_format(filter_dict)
        assert filter_input is not None

    def test_datetime_range_rejects_invalid_string(self) -> None:
        """Test that datetime_range filter rejects non-numeric strings."""
        filter_dict: JsonDict = {
            "fieldId": "createdAt",
            "filterType": "datetime_range",
            "start": "not-a-number",
            "end": 1672531199000,
        }

        with pytest.raises(ValueError) as exc_info:
            alerts._parse_new_filter_format(filter_dict)

        assert "must be an integer" in str(exc_info.value)
