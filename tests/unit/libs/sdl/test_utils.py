"""Tests for SDL utils functions."""

from datetime import datetime, timedelta, timezone

import pytest

from purple_mcp.libs.sdl.utils import parse_time_param
from purple_mcp.tools.sdl import _iso_to_nanoseconds, get_timestamp_range


class TestParseTimeParam:
    """Test cases for the parse_time_param function."""

    def test_parse_time_param_with_timezone_aware_datetime(self) -> None:
        """Test that timezone-aware datetime objects are accepted."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = parse_time_param(dt)

        # Should return a string representation of milliseconds
        assert isinstance(result, str)

        # Verify the conversion is correct
        expected_ms = str(int(dt.timestamp() * 1_000))
        assert result == expected_ms

    def test_parse_time_param_with_timezone_naive_datetime_raises_error(self) -> None:
        """Test that timezone-naive datetime objects raise ValueError."""
        dt = datetime(2024, 1, 15, 10, 30, 0)  # No timezone info

        with pytest.raises(ValueError, match="Timezone-naive time_param is not allowed"):
            parse_time_param(dt)

    def test_parse_time_param_with_timedelta(self) -> None:
        """Test that timedelta objects are accepted."""
        delta = timedelta(hours=1)
        result = parse_time_param(delta)

        # Should return a string representation of milliseconds
        assert isinstance(result, str)

        # Verify it's a valid integer string
        assert int(result) > 0

    def test_parse_time_param_with_different_timezones(self) -> None:
        """Test that different timezone-aware datetimes work correctly."""
        from datetime import (
            timedelta as td,
            timezone as tz,
        )

        # UTC datetime
        dt_utc = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result_utc = parse_time_param(dt_utc)

        # UTC+5 datetime (same absolute time as 05:30 UTC)
        dt_plus5 = datetime(2024, 1, 15, 10, 30, 0, tzinfo=tz(td(hours=5)))
        result_plus5 = parse_time_param(dt_plus5)

        # Both should be valid strings
        assert isinstance(result_utc, str)
        assert isinstance(result_plus5, str)

        # They should be different because they represent different absolute times
        assert result_utc != result_plus5

    def test_parse_time_param_timedelta_returns_past_time(self) -> None:
        """Test that timedelta subtracts from current time."""
        delta = timedelta(hours=2)
        result = parse_time_param(delta)

        # Get current time for comparison
        now = datetime.now(timezone.utc)
        now_ms = int(now.timestamp() * 1_000)
        result_ms = int(result)

        # Result should be less than now (in the past)
        assert result_ms < now_ms

        # Difference should be approximately 2 hours (with small tolerance)
        diff_hours = (now_ms - result_ms) / (1_000 * 60 * 60)
        assert 1.99 < diff_hours < 2.01


class TestIsoToNanoseconds:
    """Test cases for the iso_to_nanoseconds function."""

    def test_iso_to_nanoseconds_utc(self) -> None:
        """Test conversion of UTC datetime."""
        result = _iso_to_nanoseconds("2024-01-15T10:30:00Z")
        assert isinstance(result, int)
        assert result > 0
        # Verify the conversion is correct
        expected_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        assert result == expected_ns

    def test_iso_to_nanoseconds_with_offset(self) -> None:
        """Test conversion with timezone offset."""
        result = _iso_to_nanoseconds("2024-01-15T10:30:00+05:00")
        assert isinstance(result, int)
        assert result > 0
        # This should be different from UTC time due to offset
        utc_result = _iso_to_nanoseconds("2024-01-15T10:30:00Z")
        assert result != utc_result

    def test_iso_to_nanoseconds_negative_offset(self) -> None:
        """Test conversion with negative timezone offset."""
        result = _iso_to_nanoseconds("2024-01-15T10:30:00-05:00")
        assert isinstance(result, int)
        assert result > 0

    def test_iso_to_nanoseconds_microseconds(self) -> None:
        """Test conversion with microseconds precision."""
        result = _iso_to_nanoseconds("2024-01-15T10:30:00.123456Z")
        assert isinstance(result, int)
        assert result > 0
        # Verify microseconds are preserved in nanoseconds
        expected_dt = datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        assert result == expected_ns

    def test_iso_to_nanoseconds_invalid_format(self) -> None:
        """Test error handling for invalid datetime format."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 datetime"):
            _iso_to_nanoseconds("invalid-datetime")

    def test_iso_to_nanoseconds_space_separator_allowed(self) -> None:
        """Test that space separator is accepted by dateutil parser."""
        result = _iso_to_nanoseconds("2024-01-15 10:30:00Z")
        assert isinstance(result, int)
        assert result > 0
        # Should be same as T separator
        t_result = _iso_to_nanoseconds("2024-01-15T10:30:00Z")
        assert result == t_result

    def test_iso_to_nanoseconds_no_timezone_raises_error(self) -> None:
        """Test that missing timezone raises ValueError."""
        with pytest.raises(ValueError, match="explicit timezone information"):
            _iso_to_nanoseconds("2024-01-15T10:30:00")

    def test_iso_to_nanoseconds_empty_string(self) -> None:
        """Test error handling for empty string."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 datetime"):
            _iso_to_nanoseconds("")

    def test_iso_to_nanoseconds_invalid_input(self) -> None:
        """Test error handling for invalid input."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 datetime"):
            _iso_to_nanoseconds("invalid")

    def test_iso_to_nanoseconds_different_formats(self) -> None:
        """Test various valid ISO 8601 formats."""
        test_cases = [
            "2024-01-15T10:30:00Z",
            "2024-01-15T10:30:00+00:00",
            "2024-01-15T10:30:00.000Z",
            "2024-01-15T10:30:00.123Z",
            "2024-01-15T10:30:00+02:30",
            "2024-01-15T10:30:00-08:00",
        ]

        for iso_string in test_cases:
            result = _iso_to_nanoseconds(iso_string)
            assert isinstance(result, int)
            assert result > 0

    def test_iso_to_nanoseconds_consistency(self) -> None:
        """Test that the same datetime string always produces the same result."""
        iso_string = "2024-01-15T10:30:00Z"
        result1 = _iso_to_nanoseconds(iso_string)
        result2 = _iso_to_nanoseconds(iso_string)
        assert result1 == result2

    def test_iso_to_nanoseconds_epoch(self) -> None:
        """Test conversion of Unix epoch time."""
        result = _iso_to_nanoseconds("1970-01-01T00:00:00Z")
        assert result == 0

    def test_iso_to_nanoseconds_precision(self) -> None:
        """Test nanosecond precision is maintained."""
        # Test with known datetime
        iso_string = "2024-01-01T00:00:01Z"
        result = _iso_to_nanoseconds(iso_string)
        # Should be exactly 1 second in nanoseconds after epoch
        expected_dt = datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
        expected_ns = int(expected_dt.timestamp() * 1_000_000_000)
        assert result == expected_ns

    def test_iso_to_nanoseconds_timezone_requirement(self) -> None:
        """Test that timezone is required for all timestamps."""
        # Naive datetime (no timezone) should raise an error
        with pytest.raises(ValueError, match="explicit timezone information"):
            _iso_to_nanoseconds("2024-01-15T10:30:00")

        # Timezone-aware datetime is required and recommended
        utc_result = _iso_to_nanoseconds("2024-01-15T10:30:00Z")
        offset_result = _iso_to_nanoseconds("2024-01-15T10:30:00+00:00")

        # UTC and +00:00 should give same result
        assert utc_result == offset_result

        # The key point: always specify timezone for predictable, portable results
        timezone_aware_examples = [
            "2024-01-15T10:30:00Z",  # UTC (recommended)
            "2024-01-15T10:30:00+00:00",  # UTC explicit
            "2024-01-15T10:30:00+05:00",  # UTC+5
            "2024-01-15T10:30:00-08:00",  # UTC-8
        ]

        for example in timezone_aware_examples:
            result = _iso_to_nanoseconds(example)
            assert isinstance(result, int)
            assert result > 0


class TestParameterValidation:
    """Test parameter validation for ISO datetime strings."""

    def test_iso_datetime_conversion_validates_input(self) -> None:
        """Test that iso_to_nanoseconds validates datetime strings properly."""
        # Test valid inputs work
        valid_inputs = [
            "2024-01-15T10:30:00Z",
            "2024-01-15T10:30:00+05:00",
            "2024-01-15T10:30:00.123Z",
        ]

        for iso_string in valid_inputs:
            result = _iso_to_nanoseconds(iso_string)
            assert isinstance(result, int)
            assert result > 0

        # Test invalid inputs raise ValueError
        invalid_inputs = [
            "not-a-datetime",
            "",
            "2024-13-50T25:70:99Z",  # Invalid date/time values
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError, match="Invalid ISO 8601 datetime"):
                _iso_to_nanoseconds(invalid_input)


class TestGetTimestampRange:
    """Test cases for the get_timestamp_range function."""

    def test_get_timestamp_range_subtract_hours(self) -> None:
        """Test subtracting hours from a timestamp."""
        base_time = "2024-01-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, hours=2)

        # Should return both current and offset time
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2024-01-15T10:00:00Z"

    def test_get_timestamp_range_subtract_days(self) -> None:
        """Test subtracting days from a timestamp."""
        base_time = "2024-01-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, days=1)

        # Should return both current and offset time
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2024-01-14T12:00:00Z"

    def test_get_timestamp_range_subtract_weeks(self) -> None:
        """Test subtracting weeks from a timestamp."""
        base_time = "2024-01-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, weeks=1)

        # Should return both current and offset time
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2024-01-08T12:00:00Z"

    def test_get_timestamp_range_subtract_months(self) -> None:
        """Test subtracting months from a timestamp."""
        base_time = "2024-03-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, months=1)

        # Should return both current and offset time
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2024-02-15T12:00:00Z"

    def test_get_timestamp_range_subtract_years(self) -> None:
        """Test subtracting years from a timestamp."""
        base_time = "2024-01-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, years=1)

        # Should return both current and offset time
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2023-01-15T12:00:00Z"

    def test_get_timestamp_range_add_operation(self) -> None:
        """Test adding time delta instead of subtracting."""
        base_time = "2024-01-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, hours=2, direction="future")

        # Should return both current and offset time
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2024-01-15T14:00:00Z"

    def test_get_timestamp_range_multiple_units(self) -> None:
        """Test combining multiple time units."""
        base_time = "2024-01-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, days=1, hours=2, minutes=30)

        # Should return both current and offset time
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2024-01-14T09:30:00Z"

    def test_get_timestamp_range_no_reference_time(self) -> None:
        """Test using current time as base when no reference_time provided."""
        result = get_timestamp_range(hours=1)

        # Should return dictionary with both timestamps
        assert isinstance(result, dict)
        assert "current_time" in result
        assert "offset_time" in result

        # Both should be valid ISO 8601 timestamps
        assert result["current_time"].endswith("Z")
        assert result["offset_time"].endswith("Z")

        # Should be parseable
        current_ns = _iso_to_nanoseconds(result["current_time"])
        offset_ns = _iso_to_nanoseconds(result["offset_time"])
        assert isinstance(current_ns, int)
        assert isinstance(offset_ns, int)

        # Offset should be approximately 1 hour before current
        hour_diff_ns = current_ns - offset_ns
        expected_hour_ns = 60 * 60 * 1_000_000_000

        # Allow 1 second tolerance
        assert abs(hour_diff_ns - expected_hour_ns) < 1_000_000_000

    def test_get_timestamp_range_preserve_timezone(self) -> None:
        """Test that timezone information is preserved."""
        base_time = "2024-01-15T12:00:00+05:00"
        result = get_timestamp_range(reference_time=base_time, hours=1)

        # Current time should be the reference time
        assert result["current_time"] == base_time
        # Offset should be in UTC format
        assert result["offset_time"].endswith("Z")

    def test_get_timestamp_range_zero_delta(self) -> None:
        """Test with zero delta (should return same timestamp)."""
        base_time = "2024-01-15T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time)

        # Should return both times as the same
        assert result["current_time"] == base_time
        assert result["offset_time"] == base_time

    def test_get_timestamp_range_complex_scenarios(self) -> None:
        """Test complex time calculations for common PowerQuery scenarios."""
        base_time = "2024-01-15T12:00:00Z"

        # Last 24 hours
        last_24h = get_timestamp_range(reference_time=base_time, hours=24)
        assert last_24h["current_time"] == base_time
        assert last_24h["offset_time"] == "2024-01-14T12:00:00Z"

        # Last week
        last_week = get_timestamp_range(reference_time=base_time, weeks=1)
        assert last_week["current_time"] == base_time
        assert last_week["offset_time"] == "2024-01-08T12:00:00Z"

        # Last month
        last_month = get_timestamp_range(reference_time=base_time, months=1)
        assert last_month["current_time"] == base_time
        assert last_month["offset_time"] == "2023-12-15T12:00:00Z"

        # Last 6 hours
        last_6h = get_timestamp_range(reference_time=base_time, hours=6)
        assert last_6h["current_time"] == base_time
        assert last_6h["offset_time"] == "2024-01-15T06:00:00Z"

    def test_get_timestamp_range_edge_cases(self) -> None:
        """Test edge cases like leap years, month boundaries."""
        # Test leap year
        base_time = "2024-03-01T12:00:00Z"  # 2024 is a leap year
        result = get_timestamp_range(reference_time=base_time, months=1)
        assert result["current_time"] == base_time
        assert result["offset_time"] == "2024-02-01T12:00:00Z"

        # Test month boundary
        base_time = "2024-01-31T12:00:00Z"
        result = get_timestamp_range(reference_time=base_time, months=1, direction="future")
        # Should handle month-end properly (might be Feb 29 in leap year)
        assert result["current_time"] == base_time
        assert "2024-02-" in result["offset_time"]

    def test_get_timestamp_range_invalid_direction(self) -> None:
        """Test that invalid direction parameter raises error."""
        with pytest.raises(ValueError):
            get_timestamp_range(
                reference_time="2024-01-15T12:00:00Z",
                hours=1,
                direction="invalid",  # type: ignore[arg-type]
            )


class TestTimestampToolsIntegration:
    """Integration tests for timestamp tools working together."""

    def test_tools_integration_for_powerquery_timerange(self) -> None:
        """Test using timestamp range tool for PowerQuery time ranges."""
        # Get both timestamps in one call
        result = get_timestamp_range(hours=24)

        # Both should be valid ISO 8601 timestamps
        end_ns = _iso_to_nanoseconds(result["current_time"])
        start_ns = _iso_to_nanoseconds(result["offset_time"])

        # Start should be before end
        assert start_ns < end_ns

        # Should be approximately 24 hours apart
        diff_seconds = (end_ns - start_ns) / 1_000_000_000
        expected_seconds = 24 * 60 * 60  # 24 hours
        assert abs(diff_seconds - expected_seconds) < 1  # Allow 1 second tolerance

    @pytest.mark.parametrize(
        "scenario_name,delta_kwargs",
        [
            ("last_hour", {"hours": 1}),
            ("last_day", {"days": 1}),
            ("last_week", {"weeks": 1}),
            ("last_month", {"months": 1}),
            ("last_6_hours", {"hours": 6}),
            ("last_30_days", {"days": 30}),
            ("last_year", {"years": 1}),
            ("last_2_weeks", {"weeks": 2}),
            ("last_3_months", {"months": 3}),
            ("last_12_hours", {"hours": 12}),
            ("last_90_days", {"days": 90}),
        ],
    )
    def test_tools_integration_common_scenarios(
        self, scenario_name: str, delta_kwargs: dict[str, int]
    ) -> None:
        """Test integration with common time range scenarios."""
        result = get_timestamp_range(**delta_kwargs)  # type: ignore[arg-type]

        # Should be valid timestamps
        start_ns = _iso_to_nanoseconds(result["offset_time"])
        end_ns = _iso_to_nanoseconds(result["current_time"])

        # Start should be before end
        assert start_ns < end_ns, f"Failed for scenario: {scenario_name}"

        # Should be reasonable time difference
        diff_seconds = (end_ns - start_ns) / 1_000_000_000
        assert diff_seconds > 0, f"Failed for scenario: {scenario_name}"

    def test_tools_integration_with_no_reference_time(self) -> None:
        """Test using get_timestamp_range without reference time."""
        # This should use current time as base
        result = get_timestamp_range(hours=1)

        # Both should be valid
        start_ns = _iso_to_nanoseconds(result["offset_time"])
        end_ns = _iso_to_nanoseconds(result["current_time"])

        # Start should be before end
        assert start_ns < end_ns

        # Should be approximately 1 hour difference
        diff_seconds = (end_ns - start_ns) / 1_000_000_000
        expected_seconds = 60 * 60  # 1 hour
        assert abs(diff_seconds - expected_seconds) < 1  # Allow 1 second tolerance
        assert 3590 <= diff_seconds <= 3610  # Allow 10 second tolerance
