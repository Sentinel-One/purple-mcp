"""Models for SDL API integration.

SDL API Models that match the response structure from the SDL API source.
These models provide type safety and validation for API interactions.
They ensure proper deserialization of API responses and enable static type checking.
"""

import sys
from datetime import UTC, timezone
from typing import Annotated, Final, TypeAlias, assert_never

import pandas as pd
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, JsonValue, computed_field

from purple_mcp.libs.sdl.enums import PQColumnType, SDLPQFrequency, SDLPQResultType
from purple_mcp.libs.sdl.type_definitions import JsonDict


class SDLErrorObject(BaseModel):
    """Model for error object."""

    message: str
    details: JsonDict | None = None


class SDLTimeRangeResultData(BaseModel):
    """Model for time range result data."""

    start: int
    end: int


class SDLColumn(BaseModel):
    """Model for column in the result set."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    name: str
    type: Annotated[PQColumnType, Field(..., validation_alias=AliasChoices("cellType", "type"))]
    decimal_places: Annotated[int | None, Field(alias="decimalPlaces")] = None

    @property
    def format(self) -> str:
        """Get the format of the column.

        Returns:
            A string representing the format of the column
        """
        # Note: Format is derived from the column type.
        return self.type.lower()


class SDLCell(BaseModel):
    """Model for cell in the result set."""

    value: JsonValue
    url: str | None = None


# This is a list of possible values that we consider missing.
SDL_MISSING_VALUES: Final = ("", "none", "None", "N/A", "n/a", "NA", "null", "NULL")


class SDLTableResultData(BaseModel):
    """Model for table result data."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    match_count: Annotated[float, Field(alias="matchCount")] = 0.0
    values: list[list[JsonValue]]  # Arbitrary objects in each cell
    columns: list[SDLColumn]
    key_columns: Annotated[int | None, Field(alias="keyColumns")] = None
    omitted_events: Annotated[float | None, Field(alias="omittedEvents")] = None
    partial_results_due_to_time_limit: Annotated[
        bool | None,
        Field(
            alias="partialResultsDueToTimeLimit",
        ),
    ] = None
    discarded_array_items: Annotated[int | None, Field(alias="discardedArrayItems")] = None
    warnings: list[str] = Field(default_factory=list)
    truncated_at_limit: bool = Field(
        default=False,
        description="Indicates whether results were truncated due to max_query_results limit",
    )

    @computed_field  # type: ignore[prop-decorator]  # https://github.com/python/mypy/issues/1362
    @property
    def cells(self) -> list[list[SDLCell]]:
        """Compute cells from values if cells is not provided.

        Returns:
            The validated model with cells computed if necessary
        """
        # Note: Cell objects are synthesized from the values array.
        cells = []
        if hasattr(self, "values") and self.values:
            cells = [[SDLCell(value=value) for value in row] for row in self.values]
        return cells

    def to_df(self, tz: timezone = UTC) -> pd.DataFrame:
        """Given a SDLTableResultData object, return a pandas DataFrame.

        Args:
            tz: The timezone to convert to (UTC by default)

        Returns:
            The pandas DataFrame
        """
        columns = [col.name for col in self.columns]
        digit_to_unit = {19: "ns", 16: "us", 13: "ms", 10: "s"}

        df = pd.DataFrame(self.values, columns=columns)
        for column, dtype in zip(self.columns, df.dtypes, strict=True):
            if column.type == PQColumnType.TIMESTAMP:
                is_empty = df[column.name].isin(SDL_MISSING_VALUES) | df[column.name].isna()

                # Replace common missing value representations with None
                df[column.name] = df[column.name].replace(SDL_MISSING_VALUES, None)

                # Try to convert to numeric, coercing errors to NaN
                # Use downcast=None to prevent automatic downcasting that might lose precision
                numeric_col = pd.to_numeric(df[column.name], errors="coerce", downcast=None)

                # Track which values failed numeric conversion (invalid dates)
                # Also track values that are too large (will be inf or very large floats)
                max_safe_int = sys.maxsize
                is_invalid = (numeric_col.isna() & ~is_empty) | (numeric_col > max_safe_int)

                # Check if we have any valid numeric values (not NaN and not too large)
                has_valid = numeric_col.notna() & (numeric_col <= max_safe_int)

                # All values are either empty or invalid
                if not has_valid.any():
                    df[column.name] = ""
                    df.loc[is_invalid, column.name] = "Invalid Date"
                    df[column.name] = df[column.name].astype("string")
                    continue

                # Get the max length of valid (non-NaN, non-overflow) timestamps
                valid_timestamps = numeric_col[has_valid]

                # No valid timestamps
                if len(valid_timestamps) == 0:
                    df[column.name] = ""
                    df[column.name] = df[column.name].astype("string")
                    continue

                ct = valid_timestamps.astype("int64").astype("string").str.len().max()

                # Invalid timestamp length
                if ct not in digit_to_unit:
                    df[column.name] = "Invalid Date"
                    df.loc[is_empty, column.name] = ""
                    df[column.name] = df[column.name].astype("string")
                    continue

                # Check each individual timestamp length and mark invalid ones
                # Only check non-NaN values (NaN values are already marked as invalid or empty)
                valid_mask = numeric_col.notna()
                timestamp_lengths = pd.Series(index=numeric_col.index, dtype="Int64")
                timestamp_lengths[valid_mask] = (
                    numeric_col[valid_mask].astype("int64").astype("string").str.len()
                )
                has_invalid_length = timestamp_lengths.notna() & ~timestamp_lengths.isin(
                    digit_to_unit.keys()
                )
                is_invalid = is_invalid | has_invalid_length

                # Validate timestamp range to avoid overflow errors
                # Max safe timestamp for nanoseconds: ~2262-04-11
                max_safe_ns = sys.maxsize  # Max int64
                max_safe_values = {
                    "ns": max_safe_ns,
                    "us": max_safe_ns // 1000,
                    "ms": max_safe_ns // 1_000_000,
                    "s": max_safe_ns // 1_000_000_000,
                }
                max_safe = max_safe_values[digit_to_unit[ct]]

                # Mark values outside safe range as invalid
                is_invalid = is_invalid | (numeric_col > max_safe)
                numeric_col.loc[numeric_col > max_safe] = None

                # Convert integer timestamp to datetime in UTC
                datetime_col = pd.to_datetime(
                    numeric_col,
                    unit=digit_to_unit[ct],
                    utc=True,
                    errors="coerce",
                )

                # Convert to desired timezone
                datetime_col = datetime_col.dt.tz_convert(tz)

                # Convert datetime to ISO format, handling NaT values
                # Empty values -> '', Invalid values -> 'Invalid Date'
                df[column.name] = datetime_col.apply(
                    lambda x: x.strftime("%Y-%m-%dT%H:%M:%S.%f%z") if pd.notna(x) else None
                )
                df.loc[is_empty, column.name] = ""
                df.loc[is_invalid, column.name] = "Invalid Date"
                df[column.name] = df[column.name].astype("string")

            elif column.type == PQColumnType.NUMBER or column.type == PQColumnType.PERCENTAGE:
                df[column.name] = df[column.name].replace(SDL_MISSING_VALUES, None)

                try:
                    df[column.name] = pd.to_numeric(df[column.name], errors="raise")
                except (ValueError, TypeError):
                    df[column.name] = df[column.name].astype("string")
            elif column.type == PQColumnType.STRING:
                # we want to keep auto-detected booleans as-is
                if dtype != "bool":
                    df[column.name] = df[column.name].astype("string").fillna("")
            else:  # pragma: no cover
                assert_never(column.type)

        return df


# Currently only TableResultData for PQ/TABLE, can be extended for other formats
SDLResultData: TypeAlias = SDLTableResultData | None


class SDLQueryResult(BaseModel):
    """Model for query result."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    id: str | None = None  # In the case of an error, the id will be None
    steps_completed: Annotated[int, Field(..., alias="stepsCompleted")]
    total_steps: Annotated[int, Field(..., alias="totalSteps")]
    resolved_time_range: Annotated[
        SDLTimeRangeResultData | None,
        Field(alias="resolvedTimeRange"),
    ] = None
    error: SDLErrorObject | None = None
    cpu_usage: Annotated[int, Field(alias="cpuUsage")] = 0  # nanoseconds
    data: SDLResultData = None


class SDLQueryHandlerResponse(BaseModel):
    """Response model for SDL query handler."""

    success: bool
    error_message: str | None = None


class SDLSubmitQueryResponse(SDLQueryResult):
    """Response model for submitting a query."""


class SDLPingResponse(SDLQueryResult):
    """Response model for pinging a query."""


class SDLPQAttributes(BaseModel):
    """Model for powerquery attributes."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    query: str
    result_type: Annotated[SDLPQResultType, Field(alias="resultType")] = SDLPQResultType.TABLE
    frequency: Annotated[SDLPQFrequency, Field(alias="frequency")] = SDLPQFrequency.LOW
