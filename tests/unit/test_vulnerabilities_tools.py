"""Tests for vulnerabilities tools."""

import json
from typing import cast
from unittest.mock import Mock, patch

import pytest
from pydantic import JsonValue

import purple_mcp.tools.vulnerabilities as vulnerabilities
from purple_mcp.libs.vulnerabilities import (
    FilterInput,
    VulnerabilitiesClientError,
    VulnerabilityConnection,
    VulnerabilityHistoryItemConnection,
    VulnerabilityNoteConnection,
)
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.vulnerabilities.helpers import (
    JSONAssertions,
    MockVulnerabilitiesClientBuilder,
    VulnerabilitiesTestData,
)
from tests.unit.libs.vulnerabilities.helpers.base import VulnerabilitiesTestBase


class TestVulnerabilitiesToolsHelpers:
    """Test helper functions for vulnerabilities tools."""

    @patch("purple_mcp.tools.vulnerabilities.get_settings")
    def test_get_vulnerabilities_client_success(self, mock_get_settings: Mock) -> None:
        """Test successful creation of VulnerabilitiesClient."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.vulnerabilities_graphql_url = "https://example.test/graphql"
        mock_settings.graphql_service_token = "test-token"
        mock_get_settings.return_value = mock_settings

        client = vulnerabilities._get_vulnerabilities_client()

        assert client.config.graphql_url == "https://example.test/graphql"
        assert client.config.auth_token == "test-token"

    @patch("purple_mcp.tools.vulnerabilities.get_settings")
    def test_get_vulnerabilities_client_settings_error(self, mock_get_settings: Mock) -> None:
        """Test that settings error is properly handled."""
        mock_get_settings.side_effect = Exception("Settings not configured")

        with pytest.raises(RuntimeError) as exc_info:
            vulnerabilities._get_vulnerabilities_client()

        JSONAssertions.assert_error_message(exc_info, "Settings not initialized")
        JSONAssertions.assert_error_message(exc_info, "Settings not configured")


class TestGetVulnerability(VulnerabilitiesTestBase):
    """Test get_vulnerability tool."""

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_get_vulnerability_success(self, mock_get_client: Mock) -> None:
        """Test successful vulnerability retrieval."""
        mock_vulnerability = VulnerabilitiesTestData.create_test_vulnerability()

        result = await self.assert_tool_success(
            vulnerabilities.get_vulnerability,
            mock_get_client,
            mock_vulnerability,
            "get_vulnerability",
            expected_client_args=None,
            tool_args={"vulnerability_id": "vuln-123"},
        )

        # Verify JSON response - tests actual Pydantic serialization
        data = JSONAssertions.assert_vulnerability_response(result, "vuln-123")
        assert data["severity"] == "CRITICAL"
        assert data["name"] == "Test Vulnerability"

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_get_vulnerability_not_found(self, mock_get_client: Mock) -> None:
        """Test vulnerability not found returns null."""
        result = await self.assert_tool_success(
            vulnerabilities.get_vulnerability,
            mock_get_client,
            None,
            "get_vulnerability",
            tool_args={"vulnerability_id": "nonexistent"},
        )

        JSONAssertions.assert_null_response(result)

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_get_vulnerability_client_error(self, mock_get_client: Mock) -> None:
        """Test client error handling."""
        await self.assert_tool_error(
            vulnerabilities.get_vulnerability,
            mock_get_client,
            VulnerabilitiesClientError("Network error"),
            "get_vulnerability",
            "Failed to retrieve vulnerability vuln-123",
            {"vulnerability_id": "vuln-123"},
            {"vulnerability_id": "vuln-123"},
        )


class TestListVulnerabilities(VulnerabilitiesTestBase):
    """Test list_vulnerabilities tool."""

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_list_vulnerabilities_success(self, mock_get_client: Mock) -> None:
        """Test successful vulnerabilities listing."""
        mock_connection = MockVulnerabilitiesClientBuilder.create_empty_connection(
            VulnerabilityConnection
        )

        result = await self.assert_tool_success(
            vulnerabilities.list_vulnerabilities,
            mock_get_client,
            mock_connection,
            "list_vulnerabilities",
            expected_client_args=None,
            tool_args={"first": 10},
        )

        JSONAssertions.assert_connection_response(result, expected_edges=0)

    @pytest.mark.parametrize(
        "first_value,expected_error",
        [
            (0, "first must be between 1 and 100"),
            (101, "first must be between 1 and 100"),
            (-1, "first must be between 1 and 100"),
        ],
    )
    @pytest.mark.asyncio
    async def test_list_vulnerabilities_invalid_first_parameter(
        self, first_value: int, expected_error: str
    ) -> None:
        """Test validation of first parameter."""
        await self.assert_tool_validation_error(
            vulnerabilities.list_vulnerabilities, {"first": first_value}, expected_error
        )


class TestSearchVulnerabilities(VulnerabilitiesTestBase):
    """Test search_vulnerabilities function."""

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_search_vulnerabilities_without_filters(self, mock_get_client: Mock) -> None:
        """Test search without filters."""
        mock_connection = MockVulnerabilitiesClientBuilder.create_empty_connection(
            VulnerabilityConnection
        )

        result = await self.assert_tool_success(
            vulnerabilities.search_vulnerabilities,
            mock_get_client,
            mock_connection,
            "search_vulnerabilities",
            expected_client_args=None,
            tool_args={"filters": None, "first": 10},
        )

        JSONAssertions.assert_connection_response(result)

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_search_vulnerabilities_with_filters(self, mock_get_client: Mock) -> None:
        """Test search with filters."""
        mock_connection = MockVulnerabilitiesClientBuilder.create_empty_connection(
            VulnerabilityConnection
        )
        mock_client = MockVulnerabilitiesClientBuilder.create_mock(
            "search_vulnerabilities", mock_connection
        )
        mock_get_client.return_value = mock_client

        filters: list[JsonDict] = [
            {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}
        ]

        result = await vulnerabilities.search_vulnerabilities(filters=json.dumps(filters), first=5)

        # Verify FilterInput objects were created
        call_args = mock_client.search_vulnerabilities.call_args
        assert call_args[1]["first"] == 5
        assert len(call_args[1]["filters"]) == 1
        assert isinstance(call_args[1]["filters"][0], FilterInput)
        assert call_args[1]["filters"][0].field_id == "severity"

        JSONAssertions.assert_connection_response(result)

    @pytest.mark.asyncio
    async def test_search_vulnerabilities_dos_protection_too_many_filters(self) -> None:
        """Test DoS protection against too many filters."""
        # Create 51 filters (over the limit of 50)
        filters = []
        for i in range(51):
            filters.append(
                {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
            )

        await self.assert_tool_validation_error(
            vulnerabilities.search_vulnerabilities,
            cast(JsonDict, {"filters": json.dumps(filters)}),
            "Too many filters: 51. Maximum allowed: 50",
        )

    @pytest.mark.asyncio
    async def test_search_vulnerabilities_dos_protection_too_many_values(self) -> None:
        """Test DoS protection against filters with too many values."""
        filter_dict = {
            "fieldId": "severity",
            "filterType": "string_in",
            "values": ["CRITICAL"] * 101,
        }

        await self.assert_tool_validation_error(
            vulnerabilities.search_vulnerabilities,
            cast(JsonDict, {"filters": json.dumps([filter_dict])}),
            "Filter 0 has too many values: 101. Maximum allowed: 100",
        )

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_search_vulnerabilities_dos_protection_max_filters_allowed(
        self, mock_get_client: Mock
    ) -> None:
        """Test that exactly 50 filters (at the limit) are allowed."""
        mock_connection = MockVulnerabilitiesClientBuilder.create_empty_connection(
            VulnerabilityConnection
        )
        mock_client = MockVulnerabilitiesClientBuilder.create_mock(
            "search_vulnerabilities", mock_connection
        )
        mock_get_client.return_value = mock_client

        # Create exactly 50 filters (at the limit)
        filters: list[dict[str, JsonValue]] = []
        for i in range(50):
            filters.append(
                {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
            )

        result = await vulnerabilities.search_vulnerabilities(
            filters=json.dumps(filters), first=20
        )
        JSONAssertions.assert_connection_response(result)

    @pytest.mark.parametrize(
        "filter_dict,expected_error",
        [
            (
                {"fieldId": "severity", "filterType": "string_in", "values": ["CRITICAL"] * 101},
                "Filter 0 has too many values: 101. Maximum allowed: 100",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_vulnerabilities_dos_protection_values_in_filter(
        self, filter_dict: JsonDict, expected_error: str
    ) -> None:
        """Test DoS protection against filters with too many values in different formats."""
        await self.assert_tool_validation_error(
            vulnerabilities.search_vulnerabilities,
            cast(JsonDict, {"filters": json.dumps([filter_dict])}),
            expected_error,
        )

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_search_vulnerabilities_dos_protection_max_values_allowed(
        self, mock_get_client: Mock
    ) -> None:
        """Test that filters with exactly 100 values (at the limit) are allowed."""
        mock_connection = MockVulnerabilitiesClientBuilder.create_empty_connection(
            VulnerabilityConnection
        )
        mock_client = MockVulnerabilitiesClientBuilder.create_mock(
            "search_vulnerabilities", mock_connection
        )
        mock_get_client.return_value = mock_client

        # Test with string_in filter having exactly 100 values
        filter_dict = {
            "fieldId": "severity",
            "filterType": "string_in",
            "values": ["CRITICAL"] * 100,
        }

        result = await vulnerabilities.search_vulnerabilities(filters=json.dumps([filter_dict]))
        JSONAssertions.assert_connection_response(result)

    @pytest.mark.parametrize(
        "filter_dict,expected_operator_field,expected_value",
        [
            # String filters
            (
                {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
                "stringEqual",
                {"value": "CRITICAL"},
            ),
            (
                {"fieldId": "status", "filterType": "string_in", "values": ["NEW", "IN_PROGRESS"]},
                "stringIn",
                {"values": ["NEW", "IN_PROGRESS"]},
            ),
            # Integer filters
            (
                {"fieldId": "count", "filterType": "int_equals", "value": 42},
                "intEqual",
                {"value": 42},
            ),
            (
                {"fieldId": "count", "filterType": "int_in", "values": [1, 2, 3]},
                "intIn",
                {"values": [1, 2, 3]},
            ),
            (
                {
                    "fieldId": "count",
                    "filterType": "int_range",
                    "start": 10,
                    "end": 100,
                    "startInclusive": True,
                    "endInclusive": False,
                },
                "intRange",
                {"start": 10, "end": 100, "startInclusive": True, "endInclusive": False},
            ),
            # Boolean filters
            (
                {
                    "fieldId": "cve.exploitedInTheWild",
                    "filterType": "boolean_equals",
                    "value": True,
                },
                "booleanEqual",
                {"value": True},
            ),
            # DateTime filters (milliseconds since epoch)
            (
                {
                    "fieldId": "detectedAt",
                    "filterType": "datetime_range",
                    "start": 1640995200000,  # 2022-01-01T00:00:00Z
                    "end": 1672531199000,  # 2022-12-31T23:59:59Z
                },
                "dateTimeRange",
                {
                    "start": 1640995200000,
                    "end": 1672531199000,
                    "startInclusive": True,
                    "endInclusive": True,
                },
            ),
            # Fulltext search
            (
                {"fieldId": "name", "filterType": "fulltext", "values": ["log4j", "apache"]},
                "match",
                {"values": ["log4j", "apache"]},
            ),
        ],
    )
    def test_filter_conversion_creates_nested_structure(
        self, filter_dict: JsonDict, expected_operator_field: str, expected_value: JsonDict
    ) -> None:
        """Test that filter conversion creates proper nested GraphQL structure.

        This test verifies that the simplified filter format is correctly translated
        to the nested GraphQL structure, ensuring filters actually work server-side.
        """
        filter_input = vulnerabilities._convert_filter_to_input(filter_dict)

        # Verify the FilterInput object has the correct field_id
        assert filter_input.field_id == filter_dict["fieldId"]

        # Serialize to dict to verify nested structure
        serialized = filter_input.model_dump(by_alias=True, exclude_none=True)

        # Verify the operator field is present in serialized payload
        assert expected_operator_field in serialized, (
            f"Expected operator field '{expected_operator_field}' not found in serialized payload. "
            f"Got: {serialized}"
        )

        # Verify the operator value matches expected
        assert serialized[expected_operator_field] == expected_value, (
            f"Operator value mismatch for '{expected_operator_field}'. "
            f"Expected: {expected_value}, Got: {serialized[expected_operator_field]}"
        )

    @pytest.mark.parametrize(
        "filter_dict,expected_error",
        [
            (
                {"fieldId": "severity", "filterType": "string_equals"},
                "Filter type 'string_equals' requires 'value' key",
            ),
            (
                {"fieldId": "status", "filterType": "string_in"},
                "Filter type 'string_in' requires 'values' key",
            ),
            (
                {"fieldId": "count", "filterType": "int_range"},
                "Filter type 'int_range' requires at least 'start' or 'end' key",
            ),
            (
                {"fieldId": "severity", "filterType": "invalid_type", "value": "CRITICAL"},
                "Unsupported filterType: 'invalid_type'",
            ),
        ],
    )
    def test_filter_conversion_validation_errors(
        self, filter_dict: JsonDict, expected_error: str
    ) -> None:
        """Test that filter conversion properly validates input and raises helpful errors."""
        with pytest.raises(ValueError) as exc_info:
            vulnerabilities._convert_filter_to_input(filter_dict)

        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "filter_dict,expected_operator_field,expected_value",
        [
            # Regression test: int_range with start=0 should be allowed
            (
                {"fieldId": "riskScore", "filterType": "int_range", "start": 0},
                "intRange",
                {"start": 0, "startInclusive": True, "endInclusive": True},
            ),
            # Regression test: int_range with end=0 should be allowed
            (
                {"fieldId": "count", "filterType": "int_range", "end": 0},
                "intRange",
                {"end": 0, "startInclusive": True, "endInclusive": True},
            ),
            # Regression test: datetime_range with start=0 should be allowed
            (
                {"fieldId": "detectedAt", "filterType": "datetime_range", "start": 0},
                "dateTimeRange",
                {"start": 0, "startInclusive": True, "endInclusive": True},
            ),
            # Regression test: datetime_range with end=0 should be allowed
            (
                {"fieldId": "detectedAt", "filterType": "datetime_range", "end": 0},
                "dateTimeRange",
                {"end": 0, "startInclusive": True, "endInclusive": True},
            ),
        ],
    )
    def test_filter_conversion_zero_bounds_allowed(
        self, filter_dict: JsonDict, expected_operator_field: str, expected_value: JsonDict
    ) -> None:
        """Test that zero is allowed as a valid bound in int_range and datetime_range filters.

        Regression test for bug where 0 was treated as missing due to falsy check.
        """
        filter_input = vulnerabilities._convert_filter_to_input(filter_dict)

        # Verify the FilterInput object has the correct field_id
        assert filter_input.field_id == filter_dict["fieldId"]

        # Serialize to dict to verify nested structure
        serialized = filter_input.model_dump(by_alias=True, exclude_none=True)

        # Verify the operator field is present in serialized payload
        assert expected_operator_field in serialized, (
            f"Expected operator field '{expected_operator_field}' not found in serialized payload. "
            f"Got: {serialized}"
        )

        # Verify the operator value matches expected (including zero bounds)
        assert serialized[expected_operator_field] == expected_value, (
            f"Operator value mismatch for '{expected_operator_field}'. "
            f"Expected: {expected_value}, Got: {serialized[expected_operator_field]}"
        )


class TestGetVulnerabilityNotes(VulnerabilitiesTestBase):
    """Test get_vulnerability_notes tool."""

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_get_vulnerability_notes_success(self, mock_get_client: Mock) -> None:
        """Test successful notes retrieval."""
        mock_connection = MockVulnerabilitiesClientBuilder.create_empty_connection(
            VulnerabilityNoteConnection
        )

        result = await self.assert_tool_success(
            vulnerabilities.get_vulnerability_notes,
            mock_get_client,
            mock_connection,
            "get_vulnerability_notes",
            expected_client_args=None,
            tool_args={"vulnerability_id": "vuln-123"},
        )

        JSONAssertions.assert_connection_response(result)

    @pytest.mark.asyncio
    async def test_get_vulnerability_notes_empty_id(self) -> None:
        """Test that empty vulnerability IDs are rejected."""
        await self.assert_tool_validation_error(
            vulnerabilities.get_vulnerability_notes,
            {"vulnerability_id": ""},
            "vulnerability_id cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_get_vulnerability_notes_whitespace_id(self) -> None:
        """Test that whitespace-only vulnerability IDs are rejected."""
        await self.assert_tool_validation_error(
            vulnerabilities.get_vulnerability_notes,
            {"vulnerability_id": "   \t\n  "},
            "vulnerability_id cannot be empty",
        )


class TestGetVulnerabilityHistory(VulnerabilitiesTestBase):
    """Test get_vulnerability_history function."""

    @patch("purple_mcp.tools.vulnerabilities._get_vulnerabilities_client")
    @pytest.mark.asyncio
    async def test_get_vulnerability_history_success(self, mock_get_client: Mock) -> None:
        """Test successful history retrieval."""
        mock_connection = MockVulnerabilitiesClientBuilder.create_empty_connection(
            VulnerabilityHistoryItemConnection
        )

        result = await self.assert_tool_success(
            vulnerabilities.get_vulnerability_history,
            mock_get_client,
            mock_connection,
            "get_vulnerability_history",
            expected_client_args=None,
            tool_args={"vulnerability_id": "vuln-123"},
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
    async def test_get_vulnerability_history_invalid_first_parameter(
        self, first_value: int, expected_error: str
    ) -> None:
        """Test validation of first parameter."""
        await self.assert_tool_validation_error(
            vulnerabilities.get_vulnerability_history,
            {"vulnerability_id": "vuln-123", "first": first_value},
            expected_error,
        )

    @pytest.mark.asyncio
    async def test_get_vulnerability_history_empty_vulnerability_id(self) -> None:
        """Test that empty vulnerability IDs are rejected."""
        await self.assert_tool_validation_error(
            vulnerabilities.get_vulnerability_history,
            {"vulnerability_id": "", "first": 10},
            "vulnerability_id cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_get_vulnerability_history_whitespace_vulnerability_id(self) -> None:
        """Test that whitespace-only vulnerability IDs are rejected."""
        await self.assert_tool_validation_error(
            vulnerabilities.get_vulnerability_history,
            {"vulnerability_id": "   \t\n  ", "first": 10},
            "vulnerability_id cannot be empty",
        )


class TestCursorValidation(VulnerabilitiesTestBase):
    """Test cursor validation across all functions."""

    @pytest.mark.asyncio
    async def test_list_vulnerabilities_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected."""
        await self.assert_tool_validation_error(
            vulnerabilities.list_vulnerabilities,
            {"first": 10, "after": ""},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_list_vulnerabilities_invalid_cursor_whitespace_only(self) -> None:
        """Test that whitespace-only cursors are rejected."""
        await self.assert_tool_validation_error(
            vulnerabilities.list_vulnerabilities,
            {"first": 10, "after": "   \t\n  "},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_search_vulnerabilities_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected in search_vulnerabilities."""
        await self.assert_tool_validation_error(
            vulnerabilities.search_vulnerabilities,
            {"first": 10, "after": ""},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_search_vulnerabilities_invalid_cursor_whitespace_only(self) -> None:
        """Test that whitespace-only cursors are rejected in search_vulnerabilities."""
        await self.assert_tool_validation_error(
            vulnerabilities.search_vulnerabilities,
            {"first": 10, "after": "   \t\n  "},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_get_vulnerability_history_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected for vulnerability history."""
        await self.assert_tool_validation_error(
            vulnerabilities.get_vulnerability_history,
            {"vulnerability_id": "test-123", "first": 10, "after": ""},
            "Cursor cannot be empty",
        )

    @pytest.mark.asyncio
    async def test_get_vulnerability_history_invalid_cursor_whitespace_only(self) -> None:
        """Test that whitespace-only cursors are rejected for vulnerability history."""
        await self.assert_tool_validation_error(
            vulnerabilities.get_vulnerability_history,
            {"vulnerability_id": "test-123", "first": 10, "after": "   \t\n  "},
            "Cursor cannot be empty",
        )

    def test_datetime_range_rejects_nanoseconds_start(self) -> None:
        """Test that datetime_range filter rejects nanosecond timestamps in start field."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": 1640995200000000000,  # 19 digits - nanoseconds
            "end": 1672531199000,  # 13 digits - milliseconds (valid)
        }

        with pytest.raises(ValueError) as exc_info:
            vulnerabilities._convert_filter_to_input(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_rejects_nanoseconds_end(self) -> None:
        """Test that datetime_range filter rejects nanosecond timestamps in end field."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": 1640995200000,  # 13 digits - milliseconds (valid)
            "end": 1672531199000000000,  # 19 digits - nanoseconds
        }

        with pytest.raises(ValueError) as exc_info:
            vulnerabilities._convert_filter_to_input(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_accepts_milliseconds(self) -> None:
        """Test that datetime_range filter accepts valid millisecond timestamps."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": 1640995200000,  # 13 digits - milliseconds
            "end": 1672531199000,  # 13 digits - milliseconds
        }

        # Should not raise an exception
        filter_input = vulnerabilities._convert_filter_to_input(filter_dict)
        assert filter_input is not None

    def test_datetime_range_converts_string_milliseconds(self) -> None:
        """Test that datetime_range filter converts string milliseconds (from iso_to_unix_timestamp)."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": "1640995200000",  # String milliseconds (from iso_to_unix_timestamp tool)
            "end": "1672531199000",
        }

        # Should convert strings to integers and not raise an exception
        filter_input = vulnerabilities._convert_filter_to_input(filter_dict)
        assert filter_input is not None

    def test_datetime_range_rejects_invalid_string(self) -> None:
        """Test that datetime_range filter rejects non-numeric strings."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": "not-a-number",
            "end": 1672531199000,
        }

        with pytest.raises(ValueError) as exc_info:
            vulnerabilities._convert_filter_to_input(filter_dict)

        assert "must be an integer" in str(exc_info.value)

    def test_datetime_range_rejects_negative_nanoseconds_start(self) -> None:
        """Test that datetime_range filter rejects negative nanosecond timestamps in start field."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": -1640995200000000000,  # 19 digits - negative nanoseconds (pre-1970)
            "end": 1672531199000,  # 13 digits - milliseconds (valid)
        }

        with pytest.raises(ValueError) as exc_info:
            vulnerabilities._convert_filter_to_input(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_rejects_negative_nanoseconds_end(self) -> None:
        """Test that datetime_range filter rejects negative nanosecond timestamps in end field."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": 1640995200000,  # 13 digits - milliseconds (valid)
            "end": -1672531199000000000,  # 19 digits - negative nanoseconds
        }

        with pytest.raises(ValueError) as exc_info:
            vulnerabilities._convert_filter_to_input(filter_dict)

        assert "nanoseconds" in str(exc_info.value).lower()
        assert "milliseconds" in str(exc_info.value).lower()
        assert "iso_to_unix_timestamp" in str(exc_info.value)

    def test_datetime_range_accepts_negative_milliseconds(self) -> None:
        """Test that datetime_range filter accepts valid negative millisecond timestamps (pre-1970)."""
        filter_dict: JsonDict = {
            "fieldId": "detectedAt",
            "filterType": "datetime_range",
            "start": -86400000,  # 1969-12-31 (negative but valid milliseconds)
            "end": 0,  # 1970-01-01 00:00:00
        }

        # Should not raise an exception - negative milliseconds for pre-1970 dates are valid
        filter_input = vulnerabilities._convert_filter_to_input(filter_dict)
        assert filter_input is not None
