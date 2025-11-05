"""Unit tests for SDL models DataFrame conversion.

These tests verify that SDLTableResultData.to_df() correctly handles
type conversions, preserves boolean dtypes, and handles edge cases.
"""

from datetime import timezone

import pandas as pd

from purple_mcp.libs.sdl.enums import PQColumnType
from purple_mcp.libs.sdl.models import SDLColumn, SDLTableResultData


class TestSDLTableResultDataToDf:
    """Test suite for SDLTableResultData.to_df() method."""

    def test_boolean_column_preserves_dtype(self) -> None:
        """Test that boolean columns with PQColumnType.STRING preserve boolean dtype.

        This is a regression test for the bug where booleans were incorrectly
        converted to strings due to dtype comparison with string literals.
        """
        # Create a table with boolean data and STRING column type
        columns = [
            SDLColumn(name="is_active", type=PQColumnType.STRING),
            SDLColumn(name="name", type=PQColumnType.STRING),
        ]
        values = [
            [True, "Alice"],
            [False, "Bob"],
            [True, "Charlie"],
        ]

        result_data = SDLTableResultData(match_count=3, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        # Verify boolean column preserves boolean dtype
        assert pd.api.types.is_bool_dtype(df["is_active"])
        assert df["is_active"].tolist() == [True, False, True]

        # Verify string column is converted to string dtype
        assert pd.api.types.is_string_dtype(df["name"])
        assert df["name"].tolist() == ["Alice", "Bob", "Charlie"]

    def test_timestamp_column_with_none_values(self) -> None:
        """Test that timestamp columns with None values don't crash.

        This verifies that pd.to_datetime with errors='coerce' handles None values
        and that digit detection ignores None to properly format valid timestamps.
        The regression would return raw epoch floats instead of ISO strings.
        """
        columns = [
            SDLColumn(name="event_time", type=PQColumnType.TIMESTAMP),
            SDLColumn(name="event_name", type=PQColumnType.STRING),
        ]

        # Use timestamps in seconds (10 digits) - the valid timestamps determine the unit
        values = [
            [1609459200, "event1"],  # 2021-01-01
            [None, "event2"],
            [1640995200, "event3"],  # 2022-01-01
        ]

        result_data = SDLTableResultData(match_count=3, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        # Verify conversion succeeded and shape is correct
        assert df.shape == (3, 2)

        # Critical: Must be converted to string type, not left as numeric
        # The bug would leave this as float64 with values like 1609459200.0
        assert pd.api.types.is_string_dtype(df["event_time"]), (
            "Timestamp column must be string type, not numeric. "
            "If numeric, the None value broke digit detection."
        )

        # Verify valid timestamps are formatted as ISO strings
        assert df["event_time"][0].startswith("2021-01-01T00:00:00")
        assert df["event_time"][2].startswith("2022-01-01T00:00:00")

        # Verify None becomes NA in string column
        assert pd.isna(df["event_time"][1])

    def test_timestamp_precision_seconds(self) -> None:
        """Test timestamp conversion with second precision (10 digits)."""
        columns = [SDLColumn(name="timestamp", type=PQColumnType.TIMESTAMP)]

        # 10-digit timestamp (seconds): 2021-01-01 00:00:00 UTC
        values = [[1609459200]]

        result_data = SDLTableResultData(match_count=1, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        # Verify conversion succeeded and result is string
        assert pd.api.types.is_string_dtype(df["timestamp"])
        timestamp_str = df["timestamp"][0]

        # Should be ISO format with UTC timezone
        assert timestamp_str.startswith("2021-01-01T00:00:00")
        assert timestamp_str.endswith("+0000")

    def test_timestamp_precision_milliseconds(self) -> None:
        """Test timestamp conversion with millisecond precision (13 digits)."""
        columns = [SDLColumn(name="timestamp", type=PQColumnType.TIMESTAMP)]

        # 13-digit timestamp (milliseconds): 2021-01-01 00:00:00.123 UTC
        values = [[1609459200123]]

        result_data = SDLTableResultData(match_count=1, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        assert pd.api.types.is_string_dtype(df["timestamp"])
        timestamp_str = df["timestamp"][0]

        # Should include milliseconds
        assert timestamp_str.startswith("2021-01-01T00:00:00")
        assert ".123" in timestamp_str
        assert timestamp_str.endswith("+0000")

    def test_timestamp_precision_microseconds(self) -> None:
        """Test timestamp conversion with microsecond precision (16 digits)."""
        columns = [SDLColumn(name="timestamp", type=PQColumnType.TIMESTAMP)]

        # 16-digit timestamp (microseconds): 2021-01-01 00:00:00.123456 UTC
        values = [[1609459200123456]]

        result_data = SDLTableResultData(match_count=1, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        assert pd.api.types.is_string_dtype(df["timestamp"])
        timestamp_str = df["timestamp"][0]

        # Should include microseconds
        assert timestamp_str.startswith("2021-01-01T00:00:00")
        assert ".123456" in timestamp_str
        assert timestamp_str.endswith("+0000")

    def test_timestamp_precision_nanoseconds(self) -> None:
        """Test timestamp conversion with nanosecond precision (19 digits)."""
        columns = [SDLColumn(name="timestamp", type=PQColumnType.TIMESTAMP)]

        # 19-digit timestamp (nanoseconds): 2021-01-01 00:00:00.123456789 UTC
        values = [[1609459200123456789]]

        result_data = SDLTableResultData(match_count=1, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        assert pd.api.types.is_string_dtype(df["timestamp"])
        timestamp_str = df["timestamp"][0]

        # Should include nanoseconds (though might be truncated to 6 decimal places)
        assert timestamp_str.startswith("2021-01-01T00:00:00")
        assert timestamp_str.endswith("+0000")

    def test_mixed_string_number_columns(self) -> None:
        """Test that mixed string/number columns convert correctly."""
        columns = [
            SDLColumn(name="id", type=PQColumnType.NUMBER),
            SDLColumn(name="name", type=PQColumnType.STRING),
            SDLColumn(name="score", type=PQColumnType.NUMBER),
            SDLColumn(name="percentage", type=PQColumnType.PERCENTAGE),
        ]

        values = [
            [1, "Alice", 95.5, 0.955],
            [2, "Bob", 87.3, 0.873],
        ]

        result_data = SDLTableResultData(match_count=2, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        # Verify numeric columns
        assert pd.api.types.is_numeric_dtype(df["id"])
        assert pd.api.types.is_numeric_dtype(df["score"])
        assert pd.api.types.is_numeric_dtype(df["percentage"])

        # Verify string column
        assert pd.api.types.is_string_dtype(df["name"])

        # Verify values
        assert df["id"].tolist() == [1, 2]
        assert df["name"].tolist() == ["Alice", "Bob"]

    def test_number_column_with_invalid_values(self) -> None:
        """Test that NUMBER columns with invalid values use errors='coerce'."""
        columns = [
            SDLColumn(name="value", type=PQColumnType.NUMBER),
        ]

        values = [
            [42],
            ["invalid"],
            [None],
            [99],
        ]

        result_data = SDLTableResultData(match_count=4, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        # Verify numeric dtype
        assert pd.api.types.is_numeric_dtype(df["value"])

        # Verify valid values
        assert df["value"][0] == 42
        assert df["value"][3] == 99

        # Verify invalid values are coerced to NaN
        assert pd.isna(df["value"][1])
        assert pd.isna(df["value"][2])

    def test_percentage_column_conversion(self) -> None:
        """Test that PERCENTAGE columns are converted to numeric."""
        columns = [
            SDLColumn(name="completion", type=PQColumnType.PERCENTAGE),
        ]

        values = [
            [0.75],
            [0.9],
            [1.0],
        ]

        result_data = SDLTableResultData(match_count=3, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        assert pd.api.types.is_numeric_dtype(df["completion"])
        assert df["completion"].tolist() == [0.75, 0.9, 1.0]

    def test_empty_dataframe(self) -> None:
        """Test conversion of empty result set."""
        columns = [
            SDLColumn(name="id", type=PQColumnType.NUMBER),
            SDLColumn(name="name", type=PQColumnType.STRING),
        ]

        result_data = SDLTableResultData(match_count=0, values=[], columns=columns)
        df = result_data.to_df()

        # Verify shape
        assert df.shape == (0, 2)
        assert list(df.columns) == ["id", "name"]

    def test_custom_timezone_conversion(self) -> None:
        """Test timestamp conversion with custom timezone.

        Note: The method signature uses datetime.timezone, so we pass timezone.utc
        as a workaround for testing non-UTC timezones.
        """
        columns = [SDLColumn(name="timestamp", type=PQColumnType.TIMESTAMP)]

        # 10-digit timestamp (seconds): 2021-01-01 00:00:00 UTC
        values = [[1609459200]]

        result_data = SDLTableResultData(match_count=1, values=values, columns=columns)  # type: ignore[arg-type]

        # Test with UTC timezone (method only accepts datetime.timezone)
        df = result_data.to_df(tz=timezone.utc)

        assert pd.api.types.is_string_dtype(df["timestamp"])
        timestamp_str = df["timestamp"][0]

        # Should be in UTC timezone
        assert timestamp_str.startswith("2021-01-01T00:00:00")
        assert "+0000" in timestamp_str

    def test_all_column_types_together(self) -> None:
        """Integration test with all column types in one DataFrame."""
        columns = [
            SDLColumn(name="timestamp", type=PQColumnType.TIMESTAMP),
            SDLColumn(name="count", type=PQColumnType.NUMBER),
            SDLColumn(name="name", type=PQColumnType.STRING),
            SDLColumn(name="is_active", type=PQColumnType.STRING),
            SDLColumn(name="percentage", type=PQColumnType.PERCENTAGE),
        ]

        values = [
            [1609459200, 100, "test1", True, 0.95],  # timestamp in seconds
            [1640995200, 200, "test2", False, 0.87],
        ]

        result_data = SDLTableResultData(match_count=2, values=values, columns=columns)  # type: ignore[arg-type]
        df = result_data.to_df()

        # Verify all types
        assert pd.api.types.is_string_dtype(df["timestamp"])
        assert pd.api.types.is_numeric_dtype(df["count"])
        assert pd.api.types.is_string_dtype(df["name"])
        assert pd.api.types.is_bool_dtype(df["is_active"])
        assert pd.api.types.is_numeric_dtype(df["percentage"])

        # Verify shape
        assert df.shape == (2, 5)
