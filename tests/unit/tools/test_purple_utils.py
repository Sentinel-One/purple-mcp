"""Tests for purple_utils tools."""

import pytest

from purple_mcp.tools.purple_utils import iso_to_unix_timestamp


class TestIsoToUnixTimestamp:
    """Test iso_to_unix_timestamp function."""

    @pytest.mark.asyncio
    async def test_utc_datetime_with_z_suffix(self) -> None:
        """Test converting UTC datetime with 'Z' suffix."""
        result = await iso_to_unix_timestamp("2025-10-30T12:00:00Z")
        # Expected: October 30, 2025, 12:00:00 UTC = 1761825600000 ms
        assert result == "1761825600000"

    @pytest.mark.asyncio
    async def test_utc_datetime_with_explicit_offset(self) -> None:
        """Test converting UTC datetime with explicit +00:00 offset."""
        result = await iso_to_unix_timestamp("2025-10-30T12:00:00+00:00")
        # Should be same as Z suffix
        assert result == "1761825600000"

    @pytest.mark.asyncio
    async def test_datetime_with_positive_offset(self) -> None:
        """Test converting datetime with positive timezone offset."""
        # 17:00 +05:00 is same as 12:00 UTC
        result = await iso_to_unix_timestamp("2025-10-30T17:00:00+05:00")
        # 17:00 +05:00 = 12:00 UTC actual time
        assert result == "1761825600000"

    @pytest.mark.asyncio
    async def test_datetime_with_negative_offset(self) -> None:
        """Test converting datetime with negative timezone offset."""
        # 08:00 EDT (-04:00) is same as 12:00 UTC
        result = await iso_to_unix_timestamp("2025-10-30T08:00:00-04:00")
        assert result == "1761825600000"

    @pytest.mark.asyncio
    async def test_datetime_without_timezone_assumes_utc(self) -> None:
        """Test that datetime without timezone is treated as UTC."""
        result = await iso_to_unix_timestamp("2025-10-30T12:00:00")
        # Should be treated as UTC
        assert result == "1761825600000"

    @pytest.mark.asyncio
    async def test_datetime_with_milliseconds(self) -> None:
        """Test converting datetime with millisecond precision."""
        result = await iso_to_unix_timestamp("2025-10-30T12:00:00.500Z")
        # 500 milliseconds added
        assert result == "1761825600500"

    @pytest.mark.asyncio
    async def test_datetime_with_microseconds(self) -> None:
        """Test converting datetime with microsecond precision."""
        result = await iso_to_unix_timestamp("2025-10-30T12:00:00.123456Z")
        # Microseconds are preserved in timestamp (123 milliseconds)
        assert result == "1761825600123"

    @pytest.mark.asyncio
    async def test_epoch_start(self) -> None:
        """Test converting Unix epoch start time."""
        result = await iso_to_unix_timestamp("1970-01-01T00:00:00Z")
        assert result == "0"

    @pytest.mark.asyncio
    async def test_year_2000_datetime(self) -> None:
        """Test converting Y2K datetime."""
        result = await iso_to_unix_timestamp("2000-01-01T00:00:00Z")
        # January 1, 2000, 00:00:00 UTC = 946684800000 ms
        assert result == "946684800000"

    @pytest.mark.asyncio
    async def test_recent_datetime(self) -> None:
        """Test converting a recent datetime (Oct 30, 2024)."""
        result = await iso_to_unix_timestamp("2024-10-30T12:00:00Z")
        # October 30, 2024, 12:00:00 UTC = 1730289600000 ms
        assert result == "1730289600000"

    @pytest.mark.asyncio
    async def test_leap_year_datetime(self) -> None:
        """Test converting datetime on leap day."""
        result = await iso_to_unix_timestamp("2024-02-29T12:00:00Z")
        # February 29, 2024 (leap year)
        assert result == "1709208000000"

    @pytest.mark.asyncio
    async def test_end_of_day_datetime(self) -> None:
        """Test converting end of day datetime."""
        result = await iso_to_unix_timestamp("2025-10-30T23:59:59Z")
        # One second before midnight
        assert result == "1761868799000"

    @pytest.mark.asyncio
    async def test_different_timezone_same_instant(self) -> None:
        """Test that different timezone representations of same instant give same result."""
        # All of these represent the same instant in time
        result_utc = await iso_to_unix_timestamp("2025-10-30T12:00:00Z")
        result_est = await iso_to_unix_timestamp("2025-10-30T08:00:00-04:00")
        result_cet = await iso_to_unix_timestamp("2025-10-30T13:00:00+01:00")

        # All should be equal
        assert result_utc == result_est == result_cet

    @pytest.mark.asyncio
    async def test_invalid_format_raises_value_error(self) -> None:
        """Test that invalid datetime format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await iso_to_unix_timestamp("not-a-datetime")

        assert "Invalid ISO 8601 datetime format" in str(exc_info.value)
        assert "not-a-datetime" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_date_raises_value_error(self) -> None:
        """Test that invalid date (e.g., Feb 30) raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await iso_to_unix_timestamp("2025-02-30T12:00:00Z")

        assert "Invalid ISO 8601 datetime format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_time_raises_value_error(self) -> None:
        """Test that invalid time (e.g., 25:00:00) raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await iso_to_unix_timestamp("2025-10-30T25:00:00Z")

        assert "Invalid ISO 8601 datetime format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_string_raises_value_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await iso_to_unix_timestamp("")

        assert "Invalid ISO 8601 datetime format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_date_only_format(self) -> None:
        """Test converting date-only format (no time component)."""
        result = await iso_to_unix_timestamp("2025-10-30")
        # Should be treated as 2025-10-30 00:00:00 UTC
        assert result == "1761782400000"

    @pytest.mark.asyncio
    async def test_datetime_with_t_separator(self) -> None:
        """Test datetime with standard 'T' separator."""
        result = await iso_to_unix_timestamp("2025-10-30T12:00:00Z")
        assert result == "1761825600000"

    @pytest.mark.asyncio
    async def test_datetime_with_space_separator(self) -> None:
        """Test datetime with space separator instead of 'T'."""
        result = await iso_to_unix_timestamp("2025-10-30 12:00:00Z")
        # Should work with space separator
        assert result == "1761825600000"

    @pytest.mark.asyncio
    async def test_timestamp_is_milliseconds_not_seconds(self) -> None:
        """Test that returned timestamp is in milliseconds, not seconds."""
        result = await iso_to_unix_timestamp("2024-10-30T12:00:00Z")
        timestamp = int(result)

        # Millisecond timestamps are 13 digits for dates after 2001
        # Second timestamps are 10 digits
        assert len(str(timestamp)) == 13, "Timestamp should be in milliseconds (13 digits)"

        # The timestamp should be > 1 trillion milliseconds (after Sep 2001)
        assert timestamp > 1_000_000_000_000

    @pytest.mark.asyncio
    async def test_far_future_datetime(self) -> None:
        """Test converting a far future datetime."""
        result = await iso_to_unix_timestamp("2100-01-01T00:00:00Z")
        # January 1, 2100, 00:00:00 UTC
        assert result == "4102444800000"

    @pytest.mark.asyncio
    async def test_pre_epoch_datetime(self) -> None:
        """Test converting a datetime before Unix epoch (1970)."""
        result = await iso_to_unix_timestamp("1969-12-31T23:59:59Z")
        # Should be negative timestamp: -1000 (1 second before epoch in milliseconds)
        assert result == "-1000"
