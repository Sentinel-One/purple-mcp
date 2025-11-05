"""Models for SDL API integration.

SDL API Models that match the response structure from the SDL API source.
These models provide type safety and validation for API interactions.
They ensure proper deserialization of API responses and enable static type checking.

References:
    * SDL API documentation: https://api.example.com/docs/sdl
"""

from datetime import timezone
from typing import Annotated, TypeAlias

import pandas as pd
from pandas.api.types import is_bool_dtype
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, JsonValue
from typing_extensions import assert_never

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

    def to_df(self, tz: timezone = timezone.utc) -> pd.DataFrame:
        """Given a SDLTableResultData object, return a pandas DataFrame.

        Args:
            tz: The timezone to convert to (UTC by default)

        Returns:
            The pandas DataFrame
        """
        columns = [col.name for col in self.columns]
        values = [[cell.value for cell in row] for row in self.cells]
        digit_to_unit = {19: "ns", 16: "us", 13: "ms", 10: "s"}
        df = pd.DataFrame(values, columns=columns)

        for column, dtype in zip(self.columns, df.dtypes, strict=True):
            if column.type == PQColumnType.TIMESTAMP:
                # Detect timestamp unit from non-null values only
                # (None causes pandas to upcast to float64, breaking digit detection)
                non_null_values = df[column.name].dropna()
                if len(non_null_values) > 0:
                    # Convert to int64 to remove ".0" from float representation before digit count
                    ct = non_null_values.astype("int64").astype("string").str.len().max()
                else:
                    ct = None

                if ct in digit_to_unit:
                    # errors="coerce" handles None values, converting them to NaT
                    df[column.name] = pd.to_datetime(
                        df[column.name],
                        unit=digit_to_unit[ct],
                        utc=True,
                        errors="coerce",
                    )

                    df[column.name] = df[column.name].dt.tz_convert(tz)

                    # NaT values will be converted to <NA> string
                    df[column.name] = (
                        df[column.name].dt.strftime("%Y-%m-%dT%H:%M:%S.%f%z").astype("string")
                    )
            elif column.type == PQColumnType.NUMBER or column.type == PQColumnType.PERCENTAGE:
                # Use pd.to_numeric with errors="coerce" for consistent handling
                df[column.name] = pd.to_numeric(df[column.name], errors="coerce")
            elif column.type == PQColumnType.STRING:
                # Use pandas type predicate to preserve boolean dtypes
                if not is_bool_dtype(dtype):
                    df[column.name] = df[column.name].astype("string")
            else:
                # Check the column type, not the dtype
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
