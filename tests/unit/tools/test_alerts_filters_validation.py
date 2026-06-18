"""Test that conversion from filter-strings to appropriate BaseModel works as expected."""

import json

import pytest

from purple_mcp.libs.alerts import (
    EqualFilterBooleanInput,
    EqualFilterIntegerInput,
    EqualFilterStringInput,
    FilterInput,
    FulltextFilterInput,
    InFilterIntegerInput,
    InFilterStringInput,
    RangeFilterIntegerInput,
    RangeFilterLongInput,
)
from purple_mcp.tools.alerts import MAX_FILTER_VALUES_COUNT, MAX_FILTERS_COUNT, load_filters
from purple_mcp.type_defs import JsonDict


@pytest.mark.parametrize(
    ["filter_dict", "expected"],
    [
        pytest.param(
            {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
            FilterInput(fieldId="severity", stringEqual=EqualFilterStringInput(value="HIGH")),
            id="string-equals",
        ),
        pytest.param(
            {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH", "CRITICAL"]},
            FilterInput(
                fieldId="severity", stringIn=InFilterStringInput(values=["HIGH", "CRITICAL"])
            ),
            id="string-in",
        ),
        pytest.param(
            {"fieldId": "priority", "filterType": "int_in", "values": [1, 2, 3]},
            FilterInput(fieldId="priority", intIn=InFilterIntegerInput(values=[1, 2, 3])),
            id="int-in",
        ),
        pytest.param(
            {"fieldId": "isResolved", "filterType": "boolean_equals", "value": True},
            FilterInput(fieldId="isResolved", booleanEqual=EqualFilterBooleanInput(value=True)),
            id="boolean-equals",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": 1640995200000,
                "startInclusive": False,
            },
            FilterInput(
                fieldId="createdAt",
                dateTimeRange=RangeFilterLongInput(start=1640995200000, startInclusive=False),
            ),
            id="datetime-range",
        ),
        pytest.param(
            {
                "fieldId": "priority",
                "filterType": "int_range",
                "start": 50,
                "startInclusive": False,
            },
            FilterInput(
                fieldId="priority",
                intRange=RangeFilterIntegerInput(start=50, startInclusive=False),
            ),
            id="int-range",
        ),
        # isNegated tests
        pytest.param(
            {
                "fieldId": "severity",
                "filterType": "string_equals",
                "value": "HIGH",
                "isNegated": True,
            },
            FilterInput(
                fieldId="severity",
                stringEqual=EqualFilterStringInput(value="HIGH"),
                isNegated=True,
            ),
            id="string-equals-negated",
        ),
        pytest.param(
            {
                "fieldId": "severity",
                "filterType": "string_in",
                "values": ["HIGH", "CRITICAL"],
                "isNegated": True,
            },
            FilterInput(
                fieldId="severity",
                stringIn=InFilterStringInput(values=["HIGH", "CRITICAL"]),
                isNegated=True,
            ),
            id="string-in-negated",
        ),
        pytest.param(
            {
                "fieldId": "isResolved",
                "filterType": "boolean_equals",
                "value": True,
                "isNegated": True,
            },
            FilterInput(
                fieldId="isResolved",
                booleanEqual=EqualFilterBooleanInput(value=True),
                isNegated=True,
            ),
            id="boolean-equals-negated",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": 1000000,
                "end": 2000000,
                "isNegated": True,
            },
            FilterInput(
                fieldId="createdAt",
                dateTimeRange=RangeFilterLongInput(start=1000000, end=2000000),
                isNegated=True,
            ),
            id="datetime-range-negated",
        ),
        pytest.param(
            {
                "fieldId": "assigneeUserId",
                "filterType": "int_equals",
                "value": 123,
                "isNegated": True,
            },
            FilterInput(
                fieldId="assigneeUserId",
                intEqual=EqualFilterIntegerInput(value=123),
                isNegated=True,
            ),
            id="int-equals-negated",
        ),
        pytest.param(
            {
                "fieldId": "assigneeUserId",
                "filterType": "int_in",
                "values": [1, 2, 3],
                "isNegated": True,
            },
            FilterInput(
                fieldId="assigneeUserId",
                intIn=InFilterIntegerInput(values=[1, 2, 3]),
                isNegated=True,
            ),
            id="int-in-negated",
        ),
        pytest.param(
            {
                "fieldId": "alertName",
                "filterType": "fulltext",
                "values": ["test"],
                "isNegated": True,
            },
            FilterInput(
                fieldId="alertName",
                match=FulltextFilterInput(values=["test"]),
                isNegated=True,
            ),
            id="fulltext-negated",
        ),
        # Boolean type conversion (string "true" becomes bool True)
        pytest.param(
            {"fieldId": "isResolved", "filterType": "boolean_equals", "value": "true"},
            FilterInput(
                fieldId="isResolved",
                booleanEqual=EqualFilterBooleanInput(value=True),
            ),
            id="boolean-equals-string-to-bool",
        ),
        # Datetime edge cases
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": -86400000,  # 1969-12-31 (negative but valid milliseconds)
                "end": 0,  # 1970-01-01 00:00:00
            },
            FilterInput(
                fieldId="createdAt",
                dateTimeRange=RangeFilterLongInput(start=-86400000, end=0),
            ),
            id="datetime-range-negative-milliseconds",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": 1640995200000,  # 13 digits - milliseconds
                "end": 1672531199000,  # 13 digits - milliseconds
            },
            FilterInput(
                fieldId="createdAt",
                dateTimeRange=RangeFilterLongInput(start=1640995200000, end=1672531199000),
            ),
            id="datetime-range-milliseconds",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": "1640995200000",  # String milliseconds (from iso_to_unix_timestamp tool)
                "end": "1672531199000",
            },
            FilterInput(
                fieldId="createdAt",
                dateTimeRange=RangeFilterLongInput(start=1640995200000, end=1672531199000),
            ),
            id="datetime-range-string-milliseconds",
        ),
    ],
)
def test_load_filters_happy_path(filter_dict: JsonDict, expected: FilterInput) -> None:
    """Test that loading a filter from a json-string works as expected."""
    # arrange
    filter_str = json.dumps([filter_dict])

    # act
    filters = load_filters(filter_str)

    # assert
    assert len(filters) == 1
    assert filters[0] == expected


@pytest.mark.parametrize(
    ["filter_dict", "expected_error_fragment"],
    [
        pytest.param(
            {"filterType": "string_equals", "value": "HIGH"},
            "Each filter must have 'fieldId' and 'filterType' keys",
            id="missing-fieldid",
        ),
        pytest.param(
            {"fieldId": "severity", "value": "HIGH"},
            "Each filter must have 'fieldId' and 'filterType' keys",
            id="missing-filtertype",
        ),
        pytest.param(
            {"fieldId": "severity", "filterType": "string_equals"},
            "string_equals filter requires 'value' key",
            id="string-equals-missing-value",
        ),
        pytest.param(
            {"fieldId": "severity", "filterType": "string_in"},
            "string_in filter requires 'values' key",
            id="string-in-missing-values",
        ),
        pytest.param(
            {"fieldId": "isResolved", "filterType": "boolean_equals"},
            "boolean_equals filter requires 'value' key",
            id="boolean-equals-missing-value",
        ),
        pytest.param(
            {"fieldId": "assigneeUserId", "filterType": "int_equals"},
            "int_equals filter requires 'value' key",
            id="int-equals-missing-value",
        ),
        pytest.param(
            {"fieldId": "assigneeUserId", "filterType": "int_in"},
            "int_in filter requires 'values' key",
            id="int-in-missing-values",
        ),
        pytest.param(
            {"fieldId": "alertName", "filterType": "fulltext"},
            "fulltext filter requires 'values' key",
            id="fulltext-missing-values",
        ),
        pytest.param(
            {"fieldId": "severity", "filterType": "string_contains", "value": "test"},
            "Unsupported string filter type: string_contains",
            id="unsupported-filtertype",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": 1640995200000000000,  # 19 digits - nanoseconds
                "end": 1672531199000,  # 13 digits - milliseconds (valid)
            },
            "nanoseconds",
            id="datetime-range-nanoseconds-start",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": 1640995200000,  # 13 digits - milliseconds (valid)
                "end": 1672531199000000000,  # 19 digits - nanoseconds
            },
            "nanoseconds",
            id="datetime-range-nanoseconds-end",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": -1640995200000000000,  # 19 digits - negative nanoseconds (pre-1970)
                "end": 1672531199000,  # 13 digits - milliseconds (valid)
            },
            "nanoseconds",
            id="datetime-range-negative-nanoseconds-start",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": 1640995200000,  # 13 digits - milliseconds (valid)
                "end": -1672531199000000000,  # 19 digits - negative nanoseconds
            },
            "nanoseconds",
            id="datetime-range-negative-nanoseconds-end",
        ),
        pytest.param(
            {
                "fieldId": "createdAt",
                "filterType": "datetime_range",
                "start": "not-a-number",
                "end": 1672531199000,
            },
            "must be an integer",
            id="datetime-range-invalid-string",
        ),
    ],
)
def test_load_filters_failure_cases(filter_dict: JsonDict, expected_error_fragment: str) -> None:
    """Test that loading a filter from an invalid json-string fails as expected."""
    # arrange
    filter_str = json.dumps([filter_dict])

    # act
    with pytest.raises(ValueError, match=expected_error_fragment):
        load_filters(filter_str)


@pytest.mark.parametrize(
    ["filter_str", "expected_error_fragment"],
    [
        pytest.param(
            '{"invalid": json}',
            "Invalid JSON in filters parameter",
            id="malformed-json",
        ),
        pytest.param(
            '{"fieldId": "severity"}',
            "Filters must be an array of filter objects",
            id="not-a-list",
        ),
        pytest.param(
            '"not a list"',
            "Filters must be an array of filter objects",
            id="string-not-list",
        ),
    ],
)
def test_load_filters_json_parsing_errors(filter_str: str, expected_error_fragment: str) -> None:
    """Test that JSON parsing errors are handled correctly."""
    with pytest.raises(ValueError, match=expected_error_fragment):
        load_filters(filter_str)


def test_load_filters_with_none_input() -> None:
    """Test that None input returns empty list."""
    result = load_filters(None)
    assert result == []


@pytest.mark.asyncio
async def test_too_many_filters() -> None:
    """Test that too many filters are rejected."""
    filters: list[JsonDict] = [
        {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
        for i in range(MAX_FILTERS_COUNT + 1)
    ]
    filters_str = json.dumps(filters)

    with pytest.raises(ValueError, match=r"Too many filters: 51. Maximum allowed: 50"):
        load_filters(filters_str)


@pytest.mark.asyncio
async def test_exactly_max_filters_allowed() -> None:
    """Test that exactly 50 filters (at the limit) are allowed."""
    filters: list[JsonDict] = [
        {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
        for i in range(MAX_FILTERS_COUNT)
    ]
    filters_str = json.dumps(filters)

    filters_round_trip = load_filters(filters_str)

    assert len(filters_round_trip) == MAX_FILTERS_COUNT


@pytest.mark.parametrize(
    ("filter_dict", "expected_error"),
    [
        pytest.param(
            {
                "fieldId": "severity",
                "filterType": "string_in",
                "values": ["HIGH"] * (MAX_FILTER_VALUES_COUNT + 1),
            },
            "Filter 0 has too many values: 101. Maximum allowed: 100",
            id="string-in-too-many-values",
        ),
        pytest.param(
            {
                "fieldId": "priority",
                "filterType": "int_in",
                "values": list(range(MAX_FILTER_VALUES_COUNT + 1)),
            },
            "Filter 0 has too many values: 101. Maximum allowed: 100",
            id="int-in-too-many-values",
        ),
        pytest.param(
            {
                "fieldId": "description",
                "filterType": "fulltext",
                "values": ["term"] * (MAX_FILTER_VALUES_COUNT + 1),
            },
            "Filter 0 has too many values: 101. Maximum allowed: 100",
            id="fulltext-too-many-values",
        ),
        pytest.param(
            {
                "fieldId": "status",
                "filterType": "string_in",
                "values": ["OPEN"] * (MAX_FILTER_VALUES_COUNT + 1),
                "isNegated": True,
            },
            "Filter 0 has too many values: 101. Maximum allowed: 100",
            id="negated-string-in-too-many-values",
        ),
    ],
)
@pytest.mark.asyncio
async def test_filter_with_too_many_values(filter_dict: JsonDict, expected_error: str) -> None:
    """Test that filters with too many values are rejected."""
    filter_str = json.dumps([filter_dict])
    with pytest.raises(ValueError, match=expected_error):
        load_filters(filter_str)


@pytest.mark.parametrize(
    "filter_dict",
    [
        pytest.param(
            {
                "fieldId": "severity",
                "filterType": "string_in",
                "values": ["HIGH"] * MAX_FILTER_VALUES_COUNT,
            },
            id="string-in-max-values",
        ),
        pytest.param(
            {
                "fieldId": "priority",
                "filterType": "int_in",
                "values": list(range(MAX_FILTER_VALUES_COUNT)),
            },
            id="int-in-max-values",
        ),
        pytest.param(
            {
                "fieldId": "description",
                "filterType": "fulltext",
                "values": ["term"] * MAX_FILTER_VALUES_COUNT,
            },
            id="fulltext-max-values",
        ),
        pytest.param(
            {
                "fieldId": "status",
                "filterType": "string_in",
                "values": ["OPEN"] * MAX_FILTER_VALUES_COUNT,
                "isNegated": True,
            },
            id="negated-string-in-max-values",
        ),
    ],
)
def test_filter_with_exactly_max_values_allowed(filter_dict: JsonDict) -> None:
    """Test that filters with exactly MAX_FILTER_VALUES_COUNT values (at the limit) are allowed."""
    filter_str = json.dumps([filter_dict])
    filters = load_filters(filter_str)
    assert len(filters) == 1


def test_mixed_valid_and_invalid_filters() -> None:
    """Test scenario with some valid filters and one invalid filter."""
    filters: list[JsonDict] = [
        # Valid filters
        {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
        {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"},
        # Invalid filter with too many values
        {
            "fieldId": "tags",
            "filterType": "string_in",
            "values": ["tag"] * (MAX_FILTER_VALUES_COUNT + 1),
        },
    ]
    filter_str = json.dumps(filters)

    with pytest.raises(
        ValueError, match=r"Filter 2 has too many values: 101. Maximum allowed: 100"
    ):
        load_filters(filter_str)


def test_non_list_values_not_affected() -> None:
    """Test that non-list values in filters are not affected by validation."""
    filters: list[JsonDict] = [
        {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
        {"fieldId": "priority", "filterType": "int_equals", "value": 5},
        {"fieldId": "isResolved", "filterType": "boolean_equals", "value": False},
    ]
    filter_str = json.dumps(filters)

    result = load_filters(filter_str)
    assert len(result) == 3


def test_complex_valid_scenario() -> None:
    """Test a complex but valid scenario with many filters and values."""
    # Create a complex but valid scenario
    filters: list[JsonDict] = []

    # Add 25 filters with single values
    for i in range(25):
        filters.append(
            {"fieldId": f"field{i}", "filterType": "string_equals", "value": f"value{i}"}
        )

    # Add 5 filters with exactly MAX_FILTER_VALUES_COUNT values each
    for i in range(5):
        filters.append(
            {
                "fieldId": f"multi_field{i}",
                "filterType": "string_in",
                "values": [f"value{j}" for j in range(MAX_FILTER_VALUES_COUNT)],
            }
        )

    filter_str = json.dumps(filters)
    result = load_filters(filter_str)
    assert len(result) == 30  # 25 + 5


def test_empty_filters_list_allowed() -> None:
    """Test that empty filters list is allowed."""
    filter_str = json.dumps([])
    result = load_filters(filter_str)
    assert result == []


class TestDoSProtectionConstants:
    """Test DoS protection constants are correctly defined."""

    def test_constants_are_integers(self) -> None:
        """Test that constants are proper integers."""
        assert isinstance(MAX_FILTERS_COUNT, int)
        assert isinstance(MAX_FILTER_VALUES_COUNT, int)
        assert MAX_FILTERS_COUNT > 0
        assert MAX_FILTER_VALUES_COUNT > 0
