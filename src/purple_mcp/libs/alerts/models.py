"""Pydantic models for alerts data structures."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    UNKNOWN = "UNKNOWN"


class Status(str, Enum):
    """Alert status values."""

    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class ViewType(str, Enum):
    """View type for alert queries."""

    ALL = "ALL"
    ASSIGNED_TO_ME = "ASSIGNED_TO_ME"
    UNASSIGNED = "UNASSIGNED"
    MY_TEAM = "MY_TEAM"


class AnalystVerdict(str, Enum):
    """Analyst verdict for alerts."""

    FALSE_POSITIVE_BENIGN = "FALSE_POSITIVE_BENIGN"
    FALSE_POSITIVE_BENIGN_BUT_SUSPICIOUS = "FALSE_POSITIVE_BENIGN_BUT_SUSPICIOUS"
    FALSE_POSITIVE_SYSTEM_ERROR = "FALSE_POSITIVE_SYSTEM_ERROR"
    FALSE_POSITIVE_UNDEFINED = "FALSE_POSITIVE_UNDEFINED"
    FALSE_POSITIVE_USER_ERROR = "FALSE_POSITIVE_USER_ERROR"
    TRUE_POSITIVE_ADVANCED_PERSISTENT_THREAT = "TRUE_POSITIVE_ADVANCED_PERSISTENT_THREAT"
    TRUE_POSITIVE_BENIGN = "TRUE_POSITIVE_BENIGN"
    TRUE_POSITIVE_BENIGN_BUT_SUSPICIOUS = "TRUE_POSITIVE_BENIGN_BUT_SUSPICIOUS"
    TRUE_POSITIVE_DATA_EXFILTRATION = "TRUE_POSITIVE_DATA_EXFILTRATION"
    TRUE_POSITIVE_DENIAL_OF_SERVICE = "TRUE_POSITIVE_DENIAL_OF_SERVICE"
    TRUE_POSITIVE_EXPLOITATION_TOOLS = "TRUE_POSITIVE_EXPLOITATION_TOOLS"
    TRUE_POSITIVE_INSIDER_THREAT = "TRUE_POSITIVE_INSIDER_THREAT"
    TRUE_POSITIVE_MALWARE = "TRUE_POSITIVE_MALWARE"
    TRUE_POSITIVE_PHISHING_ATTACK = "TRUE_POSITIVE_PHISHING_ATTACK"
    TRUE_POSITIVE_POLICY_VIOLATION = "TRUE_POSITIVE_POLICY_VIOLATION"
    TRUE_POSITIVE_PUA_ADWARE = "TRUE_POSITIVE_PUA_ADWARE"
    TRUE_POSITIVE_RANSOMWARE = "TRUE_POSITIVE_RANSOMWARE"
    TRUE_POSITIVE_UNAUTHORIZED_ACCESS = "TRUE_POSITIVE_UNAUTHORIZED_ACCESS"
    TRUE_POSITIVE_UNDEFINED = "TRUE_POSITIVE_UNDEFINED"
    UNDEFINED = "UNDEFINED"


# Filter Input Types - matching GraphQL schema


class EqualFilterBooleanInput(BaseModel):
    """Strictly matching a boolean value."""

    value: bool | None = None


class EqualFilterIntegerInput(BaseModel):
    """Strictly matching an integer value."""

    value: int | None = None


class EqualFilterLongInput(BaseModel):
    """Strictly matching a long value."""

    value: int | None = None  # Using int for Long in Python


class EqualFilterStringInput(BaseModel):
    """Strictly matching a string value."""

    value: str | None = None


class InFilterBooleanInput(BaseModel):
    """Filter for multiple boolean values."""

    values: list[bool] = Field(default_factory=list)


class InFilterIntegerInput(BaseModel):
    """Filter for multiple integer values."""

    values: list[int] = Field(default_factory=list)


class InFilterLongInput(BaseModel):
    """Filter for multiple long values."""

    values: list[int] = Field(default_factory=list)  # Using int for Long in Python


class InFilterStringInput(BaseModel):
    """Filter for multiple string values."""

    values: list[str] = Field(default_factory=list)


class RangeFilterIntegerInput(BaseModel):
    """Filter for ranges of integer types."""

    start: int | None = None
    start_inclusive: bool = Field(default=True, alias="startInclusive")
    end: int | None = None
    end_inclusive: bool = Field(default=True, alias="endInclusive")


class RangeFilterLongInput(BaseModel):
    """Filter for ranges of long types."""

    start: int | None = None  # Using int for Long in Python
    start_inclusive: bool = Field(default=True, alias="startInclusive")
    end: int | None = None  # Using int for Long in Python
    end_inclusive: bool = Field(default=True, alias="endInclusive")


class FulltextFilterInput(BaseModel):
    """Filter for full-text search."""

    values: list[str] = Field(default_factory=list)


class DetectionSource(BaseModel):
    """Detection source information."""

    product: str | None = None
    vendor: str | None = None


class Asset(BaseModel):
    """Asset information associated with an alert."""

    id: str
    name: str | None = None
    type: str | None = None


class User(BaseModel):
    """User information for assignees."""

    user_id: str | None = Field(None, alias="userId")
    email: str | None = None
    full_name: str | None = Field(None, alias="fullName")


class Alert(BaseModel):
    """Main alert model with comprehensive field mapping.

    All fields except 'id' are optional to support dynamic field selection.
    When using custom field selection, only requested fields will be populated.
    """

    id: str
    external_id: str | None = Field(None, alias="externalId")
    severity: Severity | None = None
    status: Status | None = None
    name: str | None = None
    description: str | None = None
    detected_at: str | None = Field(None, alias="detectedAt")
    first_seen_at: str | None = Field(None, alias="firstSeenAt")
    last_seen_at: str | None = Field(None, alias="lastSeenAt")
    analyst_verdict: AnalystVerdict | None = Field(None, alias="analystVerdict")
    classification: str | None = None
    confidence_level: str | None = Field(None, alias="confidenceLevel")
    data_sources: list[str] | None = Field(None, alias="dataSources")
    detection_source: DetectionSource | None = Field(None, alias="detectionSource")
    asset: Asset | None = None
    assignee: User | None = None
    note_exists: bool | None = Field(None, alias="noteExists")
    result: str | None = None
    storyline_id: str | None = Field(None, alias="storylineId")
    ticket_id: str | None = Field(None, alias="ticketId")


class PageInfo(BaseModel):
    """Pagination information for connections."""

    has_next_page: bool = Field(alias="hasNextPage")
    has_previous_page: bool = Field(alias="hasPreviousPage")
    start_cursor: str | None = Field(None, alias="startCursor")
    end_cursor: str | None = Field(None, alias="endCursor")


class AlertEdge(BaseModel):
    """Alert edge in a connection."""

    node: Alert
    cursor: str


class AlertConnection(BaseModel):
    """Paginated connection for alerts."""

    edges: list[AlertEdge]
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


class AlertNote(BaseModel):
    """Note associated with an alert."""

    id: str
    text: str
    created_at: str = Field(alias="createdAt")
    author: User | None = None
    alert_id: str = Field(alias="alertId")


class AlertNoteEdge(BaseModel):
    """Alert note edge in a connection."""

    node: AlertNote
    cursor: str


class AlertNoteConnection(BaseModel):
    """Paginated connection for alert notes."""

    edges: list[AlertNoteEdge]
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


class UserHistoryItemCreator(BaseModel):
    """Details of the user who triggered an action which created the history event.

    This represents a user creator from the HistoryItemCreator union type.
    System-generated events may have null creator or other creator types.
    """

    typename: str | None = Field(None, alias="__typename")
    user_id: str | None = Field(None, alias="userId")
    user_type: str | None = Field(None, alias="userType")


class AlertHistoryEvent(BaseModel):
    """Historical event for an alert."""

    created_at: str = Field(alias="createdAt")
    event_text: str = Field(alias="eventText")
    event_type: str = Field(alias="eventType")
    report_url: str | None = Field(None, alias="reportUrl")
    history_item_creator: UserHistoryItemCreator | None = Field(None, alias="historyItemCreator")

    @field_validator("history_item_creator", mode="before")
    @classmethod
    def handle_empty_creator(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Handle empty creator objects from non-matching union types.

        When the GraphQL inline fragment doesn't match (e.g., system events),
        we get an empty dict or just __typename. Return None for cleaner handling.
        """
        if v is None:
            return None
        if isinstance(v, dict):
            # If we only have __typename or the dict is empty, treat as None
            if not v or (len(v) == 1 and "__typename" in v):
                return None
            # If we have __typename but it's not UserHistoryItemCreator, treat as None
            if v.get("__typename") and v.get("__typename") != "UserHistoryItemCreator":
                return None
        return v


class AlertHistoryEdge(BaseModel):
    """Alert history edge in a connection."""

    node: AlertHistoryEvent
    cursor: str


class AlertHistoryConnection(BaseModel):
    """Paginated connection for alert history."""

    edges: list[AlertHistoryEdge]
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


class FilterInput(BaseModel):
    """Filter for a field. Only one filter can be defined in the input argument."""

    field_id: str = Field(alias="fieldId")
    is_negated: bool = Field(default=False, alias="isNegated")

    # Boolean filters
    boolean_equal: EqualFilterBooleanInput | None = Field(default=None, alias="booleanEqual")
    boolean_in: InFilterBooleanInput | None = Field(default=None, alias="booleanIn")

    # DateTime filters
    date_time_range: RangeFilterLongInput | None = Field(default=None, alias="dateTimeRange")

    # Integer filters
    int_equal: EqualFilterIntegerInput | None = Field(default=None, alias="intEqual")
    int_in: InFilterIntegerInput | None = Field(default=None, alias="intIn")
    int_range: RangeFilterIntegerInput | None = Field(default=None, alias="intRange")

    # Long filters
    long_equal: EqualFilterLongInput | None = Field(default=None, alias="longEqual")
    long_in: InFilterLongInput | None = Field(default=None, alias="longIn")
    long_range: RangeFilterLongInput | None = Field(default=None, alias="longRange")

    # String filters
    string_equal: EqualFilterStringInput | None = Field(default=None, alias="stringEqual")
    string_in: InFilterStringInput | None = Field(default=None, alias="stringIn")

    # Fulltext search
    match: FulltextFilterInput | None = None

    @classmethod
    def create_string_equal(
        cls, field_id: str, value: str | None, is_negated: bool = False
    ) -> "FilterInput":
        """Create a string equality filter."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            stringEqual=EqualFilterStringInput(value=value),
        )

    @classmethod
    def create_string_in(
        cls, field_id: str, values: list[str], is_negated: bool = False
    ) -> "FilterInput":
        """Create a string IN filter."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            stringIn=InFilterStringInput(values=values),
        )

    @classmethod
    def create_int_equal(
        cls, field_id: str, value: int | None, is_negated: bool = False
    ) -> "FilterInput":
        """Create an integer equality filter."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            intEqual=EqualFilterIntegerInput(value=value),
        )

    @classmethod
    def create_int_in(
        cls, field_id: str, values: list[int], is_negated: bool = False
    ) -> "FilterInput":
        """Create an integer IN filter."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            intIn=InFilterIntegerInput(values=values),
        )

    @classmethod
    def create_int_range(
        cls,
        field_id: str,
        start: int | None = None,
        end: int | None = None,
        start_inclusive: bool = True,
        end_inclusive: bool = True,
        is_negated: bool = False,
    ) -> "FilterInput":
        """Create an integer range filter."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            intRange=RangeFilterIntegerInput(
                start=start,
                startInclusive=start_inclusive,
                end=end,
                endInclusive=end_inclusive,
            ),
        )

    @classmethod
    def create_boolean_equal(
        cls, field_id: str, value: bool | None, is_negated: bool = False
    ) -> "FilterInput":
        """Create a boolean equality filter."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            booleanEqual=EqualFilterBooleanInput(value=value),
        )

    @classmethod
    def create_datetime_range(
        cls,
        field_id: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
        start_inclusive: bool = True,
        end_inclusive: bool = True,
        is_negated: bool = False,
    ) -> "FilterInput":
        """Create a datetime range filter (timestamps in milliseconds)."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            dateTimeRange=RangeFilterLongInput(
                start=start_ms,
                startInclusive=start_inclusive,
                end=end_ms,
                endInclusive=end_inclusive,
            ),
        )

    @classmethod
    def create_fulltext_search(
        cls, field_id: str, values: list[str], is_negated: bool = False
    ) -> "FilterInput":
        """Create a fulltext search filter."""
        return cls(
            fieldId=field_id,
            isNegated=is_negated,
            match=FulltextFilterInput(values=values),
        )


class AndFilterSelectionInput(BaseModel):
    """List of filters with implicit AND between them."""

    and_filters: list[FilterInput] = Field(default_factory=list, alias="and")


class OrFilterSelectionInput(BaseModel):
    """List of AndFilterSelection's with implicit OR between them."""

    or_filters: list[AndFilterSelectionInput] = Field(default_factory=list, alias="or")


class AlertSearchInput(BaseModel):
    """Input parameters for alert search."""

    filters: list[FilterInput] | None = None
    first: int = Field(default=10, ge=1, le=100)
    after: str | None = None
    view_type: ViewType = Field(default=ViewType.ALL, alias="viewType")

    @field_validator("after")
    @classmethod
    def validate_cursor(cls, v: str | None) -> str | None:
        """Validate pagination cursor format."""
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Cursor must be a string")
        if len(v.strip()) == 0:
            raise ValueError("Cursor cannot be empty")
        # Basic format validation - cursors should be non-empty strings
        # The actual cursor validation is done by the GraphQL server
        return v


class AlertListInput(BaseModel):
    """Input parameters for listing alerts."""

    first: int = Field(default=10, ge=1, le=100)
    after: str | None = None
    view_type: ViewType = Field(default=ViewType.ALL, alias="viewType")

    @field_validator("after")
    @classmethod
    def validate_cursor(cls, v: str | None) -> str | None:
        """Validate pagination cursor format."""
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Cursor must be a string")
        if len(v.strip()) == 0:
            raise ValueError("Cursor cannot be empty")
        # Basic format validation - cursors should be non-empty strings
        # The actual cursor validation is done by the GraphQL server
        return v


class AlertHistoryInput(BaseModel):
    """Input parameters for retrieving alert history."""

    alert_id: str = Field(min_length=1)
    first: int = Field(default=10, ge=1, le=100)
    after: str | None = None

    @field_validator("after")
    @classmethod
    def validate_cursor(cls, v: str | None) -> str | None:
        """Validate pagination cursor format."""
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Cursor must be a string")
        if len(v.strip()) == 0:
            raise ValueError("Cursor cannot be empty")
        # Basic format validation - cursors should be non-empty strings
        # The actual cursor validation is done by the GraphQL server
        return v

    @field_validator("alert_id")
    @classmethod
    def validate_alert_id(cls, v: str) -> str:
        """Validate alert ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Alert ID cannot be empty")
        return v.strip()


# Response wrapper models for different operations
class GetAlertResponse(BaseModel):
    """Response model for get_alert operation."""

    alert: Alert | None


class ListAlertsResponse(BaseModel):
    """Response model for list_alerts operation."""

    alerts: AlertConnection


class SearchAlertsResponse(BaseModel):
    """Response model for search_alerts operation."""

    alerts: AlertConnection


class GetAlertNotesResponse(BaseModel):
    """Response model for get_alert_notes operation."""

    data: list[AlertNote] = Field(default_factory=list)


class GetAlertHistoryResponse(BaseModel):
    """Response model for get_alert_history operation."""

    alert_history: AlertHistoryConnection = Field(alias="alertHistory")


# Schema compatibility models
class SchemaInfo(BaseModel):
    """Information about schema capabilities."""

    supports_view_type: bool
    supports_data_sources: bool
    supports_confidence_level: bool
    supports_classification: bool
