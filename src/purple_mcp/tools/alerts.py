"""Tools for interacting with the Unified Alerts Management (UAM) system."""

# TEMPORARY: Using Optional[T] instead of T | None for FastMCP compatibility
# FastMCP's current OpenAI function schema generation requires Optional[T] syntax.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports it.

import json
import logging
from textwrap import dedent
from typing import Final, cast

from purple_mcp.config import get_settings
from purple_mcp.libs.alerts import AlertsClient, AlertsConfig, FilterInput, ViewType
from purple_mcp.type_defs import JsonDict

# TEMPORARY: Using Optional[T] instead of T | None throughout this file for FastMCP compatibility.
# FastMCP's current OpenAI function schema generation requires explicit Optional types to properly
# handle optional parameters in the JSON schema format.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports modern union syntax.

logger = logging.getLogger(__name__)

# DoS protection constants
MAX_FILTERS_COUNT: int = 50
MAX_FILTER_VALUES_COUNT: int = 100


# Docstring constants
GET_ALERT_DESCRIPTION: Final[str] = dedent(
    """
    Get detailed information about a specific alert by ID.

    Retrieves comprehensive alert data including metadata, timing information,
    severity, status, associated assets, and analyst findings.

    Args:
        alert_id: The unique identifier of the alert (string).

    Returns:
        Detailed alert information in JSON format containing:
        - id: Unique alert identifier
        - externalId: External system identifier (if any)
        - severity: CRITICAL, HIGH, MEDIUM, LOW, INFO, UNKNOWN
        - status: NEW, IN_PROGRESS, RESOLVED, FALSE_POSITIVE
        - name: Alert title/name
        - description: Detailed description of the alert
        - detectedAt: ISO timestamp when alert was first detected
        - firstSeenAt: ISO timestamp of first occurrence (if different)
        - lastSeenAt: ISO timestamp of most recent occurrence
        - analystVerdict: Expert analysis result (if available)
        - classification: Alert category/type
        - confidenceLevel: Detection confidence score
        - dataSources: List of data sources that contributed to detection
        - detectionSource: {product, vendor} information
        - asset: Associated asset information {id, name, type}
        - assignee: Assigned user information {userId, email, fullName}
        - noteExists: Boolean indicating if notes are attached
        - result: Investigation outcome
        - storylineId: Associated storyline identifier
        - ticketId: Associated ticket identifier

    Common Use Cases:
        - Incident investigation and triage
        - Alert enrichment with contextual data
        - Status and assignment tracking
        - Evidence collection for security workflows

    Raises:
        RuntimeError: If there's an error retrieving the alert.
        ValueError: If alert_id is invalid or empty.
    """
).strip()

LIST_ALERTS_DESCRIPTION: Final[str] = dedent(
    """
    List alerts with pagination and filtering capabilities.

    Retrieves a paginated list of alerts with basic filtering by assignment status.
    For advanced filtering by severity, status, time ranges, etc., use search_alerts instead.

    Args:
        first: Number of alerts to retrieve (1-100, default: 10).
        after: Pagination cursor from previous response (optional).
               Use pageInfo.endCursor from previous response to get next page.
        view_type: Assignment filter with options:
                   - "ALL": Show all alerts (default)
                   - "ASSIGNED_TO_ME": Only alerts assigned to current user
                   - "UNASSIGNED": Only unassigned alerts
                   - "MY_TEAM": Only alerts assigned to user's team
        fields: Optional JSON string containing an array of field names to return.
                If not specified, returns all default fields (including dataSources).
                Use minimal fields like '["id"]' when paging through intermediate results.

                Available fields:
                - Basic: "id", "externalId", "severity", "status", "name", "description"
                - Timing: "detectedAt", "firstSeenAt", "lastSeenAt"
                - Analysis: "analystVerdict", "classification", "confidenceLevel"
                - Context: "noteExists", "result", "storylineId", "ticketId", "dataSources"
                - Nested objects (returns all subfields):
                  - "detectionSource" (product, vendor)
                  - "asset" (id, name, type)
                  - "assignee" (userId, email, fullName)

                IMPORTANT - dataSources field behavior:
                - When fields=None (default): dataSources is INCLUDED automatically
                - When fields is provided: dataSources is ONLY included if explicitly requested
                  Example with dataSources: '["id", "severity", "dataSources"]'
                  Example without: '["id", "severity"]' (dataSources will be omitted)

                Examples:
                - Minimal for paging: '["id"]'
                - Summary view: '["id", "severity", "status", "name", "detectedAt"]'
                - With dataSources: '["id", "severity", "dataSources"]'
                - Full details: omit fields parameter or pass None

    Returns:
        Paginated alert list in JSON format containing:
        - edges: Array of alert objects (with requested fields only)
        - pageInfo: Pagination metadata
          - hasNextPage: Boolean indicating more results available
          - hasPreviousPage: Boolean indicating previous page exists
          - startCursor: Cursor for first item in current page
          - endCursor: Cursor for last item (use for next page)
        - totalCount: Total number of matching alerts (if available)

    Common Use Cases:
        - Dashboard alert feeds and overviews
        - Assignment-based alert distribution
        - Bulk alert processing workflows
        - Alert queue management

    Pagination Example:
        1. Call with first=20 to get first 20 alerts
        2. Use pageInfo.endCursor as 'after' parameter for next 20
        3. Continue until pageInfo.hasNextPage is false

    IMPORTANT Performance Notes:
        - Cursor pagination is SEQUENTIAL ONLY - you cannot skip to arbitrary positions
          (e.g., cannot jump directly to "the 1532nd alert")
        - When paging through many results to reach a specific position, use
          fields=["id"] for intermediate pages to conserve context window
        - Use the totalCount field to understand the full result set size

    Raises:
        RuntimeError: If there's an error listing alerts.
        ValueError: If parameters are invalid.
    """
).strip()

SEARCH_ALERTS_DESCRIPTION: Final[str] = dedent(
    """
    Search alerts using advanced filters and criteria.

    If a user is asking a "how many" type query, set the "first" field to 1 - "totalCount" is returned for any query.

    Args:
        filters: JSON string containing an array of filter objects (optional).
                Each filter object must have:
                - fieldId: String field name (use flattened camelCase names below)
                - filterType: One of the supported filter types below
                - isNegated: Optional boolean to negate the filter (default: false)

                Common Field Names (flattened camelCase):
                - Core: "id", "severity", "status", "alertName", "detectedAt", "createdAt"
                - Analysis: "analystVerdict", "assigneeUserId", "assigneeFullName", "alertNoteExists"
                - Context: "storylineId", "description"

                Filter Types and Required Keys:

                String Filters (for severity, status, analystVerdict, etc.):
                - "string_equals": Exact match. Requires "value" key.
                  Example: {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}
                - "string_in": Match any of multiple values. Requires "values" key (list).
                  Example: {"fieldId": "status", "filterType": "string_in", "values": ["NEW", "IN_PROGRESS"]}

                Boolean Filters (for alertNoteExists, etc.):
                - "boolean_equals": Exact match. Requires "value" key.
                  Example: {"fieldId": "alertNoteExists", "filterType": "boolean_equals", "value": true}
                - "boolean_in": Match any of multiple values. Requires "values" key (list).
                  Example: {"fieldId": "alertNoteExists", "filterType": "boolean_in", "values": [true, false]}

                Long Filters (for numeric IDs like assigneeUserId):
                - "long_equals": Exact match. Requires "value" key.
                  Example: {"fieldId": "assigneeUserId", "filterType": "long_equals", "value": 123}
                - "long_in": Match any of multiple values. Requires "values" key (list).
                  Example: {"fieldId": "assigneeUserId", "filterType": "long_in", "values": [1, 2, 3]}

                DateTime Filters (for detectedAt, createdAt):
                - "datetime_range": Range match using UNIX timestamps in milliseconds (UTC). Requires "start" and/or "end" keys.
                  Optional: "startInclusive", "endInclusive" (default: true)

                  IMPORTANT: All datetimes in the Alert API are in UTC timezone.
                  You MUST use the iso_to_unix_timestamp tool to convert ISO 8601 datetime strings
                  to UNIX timestamps (milliseconds) before using them in datetime filters.

                  IMPORTANT: Unless the user specifies a field to query a DateTime on, use createdAt.

                  The iso_to_unix_timestamp tool handles timezone conversion automatically.
                  Provide datetimes in the user's preferred timezone (e.g., "2024-10-30T08:00:00-04:00" for Eastern Time)
                  and the tool will convert to UTC milliseconds for the API.

                  Example workflow:
                  1. Call iso_to_unix_timestamp("2024-10-30T08:00:00-04:00") -> returns "1730289600000" (UTC)
                  2. Use result in filter: {"fieldId": "createdAt", "filterType": "datetime_range", "start": 1730289600000}

                  Example: {"fieldId": "createdAt", "filterType": "datetime_range", "start": 1730289600000}

                Fulltext Search (for alertName, id, storylineId):
                - "fulltext": Text search with case-insensitive substring matching. Requires "values" key (list).
                  Example: {"fieldId": "alertName", "filterType": "fulltext", "values": ["malware", "threat"]}

                Limits:
                - Maximum 50 filters per request
                - Maximum 100 values in "values" arrays

        first: Number of alerts to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        view_type: Filter by assignment - ALL, ASSIGNED_TO_ME, UNASSIGNED, MY_TEAM (default: ALL).
        fields: Optional JSON string containing an array of field names to return.
                If not specified, returns all default fields (including dataSources).
                See list_alerts for available fields and dataSources behavior.

                IMPORTANT - dataSources field behavior:
                - When fields=None (default): dataSources is INCLUDED automatically
                - When fields is provided: dataSources is ONLY included if explicitly requested
                  Example: '["id", "severity", "dataSources"]'

    Performance Note:
        When paging through many results, use fields='["id"]' for intermediate pages
        to conserve context window space. Use totalCount to gauge result set size.

    Returns:
        Filtered list of alerts in JSON format.

    Raises:
        RuntimeError: If there's an error searching alerts.
        ValueError: If parameters are invalid.

    Examples:
        CORRECT:
        filters=[
          {"fieldId": "severity", "filterType": "string_in", "values": ["CRITICAL", "HIGH"]},
          {"fieldId": "status", "filterType": "string_equals", "value": "NEW"},
          {"fieldId": "alertNoteExists", "filterType": "boolean_equals", "value": false}
        ]

        WRONG:
        filters=[
          {"fieldId": "severity", "filterType": "EQUALS", "value": "CRITICAL"},  # Use "string_equals"
          {"fieldId": "status.value", "filterType": "string_equals", "value": "NEW"}  # Use "status" not "status.value"
        ]
    """
).strip()

GET_ALERT_NOTES_DESCRIPTION: Final[str] = dedent(
    """
    Get all notes and comments associated with an alert.

    Retrieves all analyst notes, comments, and annotations attached to a specific alert.
    Notes provide context, analysis findings, investigation steps, and collaboration history.

    Args:
        alert_id: The unique identifier of the alert.

    Returns:
        List of notes in JSON format, each containing:
        - id: Unique note identifier
        - text: Note content/message
        - createdAt: ISO timestamp when note was created
        - author: User information {userId, email, fullName}
        - alertId: Associated alert identifier

        Notes are typically ordered by creation time (newest first).

    Common Use Cases:
        - Investigation documentation and collaboration
        - Tracking analyst findings and decisions
        - Audit trail for alert handling
        - Knowledge sharing between team members
        - Compliance and reporting requirements

    Note: Returns empty array if no notes exist. Check alert.noteExists
    field from get_alert to avoid unnecessary calls.

    Raises:
        RuntimeError: If there's an error retrieving alert notes.
        ValueError: If alert_id is invalid or empty.
    """
).strip()

GET_ALERT_HISTORY_DESCRIPTION: Final[str] = dedent(
    """
    Get the complete audit history and timeline for an alert.

    Retrieves a chronological record of all actions, status changes, and events
    related to a specific alert. Provides full audit trail for compliance and investigation.

    Args:
        alert_id: The unique identifier of the alert.
        first: Number of history events to retrieve (1-100, default: 10).
        after: Pagination cursor from previous response (optional).

    Returns:
        Paginated chronological list in JSON format containing:
        - edges: Array of history events with:
          - createdAt: ISO timestamp when the event was created
          - eventText: Human-readable description of the event
          - eventType: Type of event (STATUS_CHANGED, ASSIGNMENT_CHANGED, NOTE_ADDED, etc.)
          - reportUrl: Optional URL to mitigation action report (if applicable)
          - historyItemCreator: Creator/author of the event (may be null for system events):
            - userId: User identifier
            - userType: Type of user (MDR, CONSOLE_USER, etc.)
        - pageInfo: Pagination metadata (same structure as list_alerts)

    Common Event Types:
        - status_change: Alert status modified (NEW → IN_PROGRESS, etc.)
        - assignment: Alert assigned/unassigned to user or team
        - severity_change: Severity level modified
        - note_added: Analyst note or comment added
        - verdict_change: Analyst verdict updated
        - escalation: Alert escalated to higher priority
        - integration_action: External system actions (ticket creation, etc.)

    Common Use Cases:
        - Compliance auditing and reporting
        - Investigation timeline reconstruction
        - Performance metrics and SLA tracking
        - Change management and accountability
        - Forensic analysis of alert handling

    Raises:
        RuntimeError: If there's an error retrieving alert history.
        ValueError: If parameters are invalid.
    """
).strip()


def _validate_filter_limits(filters: list[JsonDict]) -> None:
    """Validate filter count and value array limits for DoS protection."""
    if len(filters) > MAX_FILTERS_COUNT:
        raise ValueError(f"Too many filters: {len(filters)}. Maximum allowed: {MAX_FILTERS_COUNT}")

    for i, filter_dict in enumerate(filters):
        if (
            "values" in filter_dict
            and isinstance(filter_dict["values"], list)
            and len(filter_dict["values"]) > MAX_FILTER_VALUES_COUNT
        ):
            raise ValueError(
                f"Filter {i} has too many values: {len(filter_dict['values'])}. "
                f"Maximum allowed: {MAX_FILTER_VALUES_COUNT}"
            )


def _validate_cursor(cursor: str | None) -> None:
    """Validate pagination cursor format."""
    if cursor is None:
        return
    if not isinstance(cursor, str):
        raise ValueError("Cursor must be a string")
    if len(cursor.strip()) == 0:
        raise ValueError("Cursor cannot be empty")


def _get_alerts_client() -> AlertsClient:
    """Get a configured AlertsClient instance.

    Returns:
        Configured AlertsClient instance.

    Raises:
        RuntimeError: If settings are not properly configured.
    """
    try:
        settings = get_settings()
    except Exception as e:
        raise RuntimeError(
            f"Settings not initialized. Please check your environment configuration. Error: {e}"
        ) from e

    config = AlertsConfig(
        graphql_url=settings.alerts_graphql_url,
        auth_token=settings.graphql_service_token,
    )

    return AlertsClient(config)


# MCP Tool Functions
# TEMPORARY: These functions use Optional[T] instead of T | None for FastMCP compatibility.
# FastMCP's current OpenAI function calling support requires this syntax for proper JSON schema
# generation of optional parameters.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports modern union syntax.


async def get_alert(alert_id: str) -> str:
    """Get detailed information about a specific alert by ID.

    Args:
        alert_id: The unique identifier of the alert.

    Returns:
        Detailed alert information in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving the alert.
    """
    try:
        client = _get_alerts_client()
        alert = await client.get_alert(alert_id)

        if alert is None:
            return json.dumps(None, indent=2)

        return alert.model_dump_json(exclude_none=True, indent=2)

    except Exception as exc:
        logger.exception("Error retrieving alert")
        raise RuntimeError(f"Failed to retrieve alert {alert_id}") from exc


async def list_alerts(
    first: int = 10,
    after: str | None = None,
    view_type: str = "ALL",
    fields: str | None = None,
) -> str:
    """List alerts with pagination and filtering capabilities.

    Args:
        first: Number of alerts to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        view_type: Filter by assignment - ALL, ASSIGNED_TO_ME, UNASSIGNED, MY_TEAM.
        fields: Optional JSON string containing an array of field names to return.

    Returns:
        Paginated list of alerts in JSON format.

    Raises:
        RuntimeError: If there's an error listing alerts.
        ValueError: If parameters are invalid.
    """
    try:
        # Validate parameters
        if first < 1 or first > 100:
            raise ValueError("first must be between 1 and 100")

        _validate_cursor(after)

        try:
            view_type_enum = ViewType(view_type)
        except ValueError:
            valid_types = [vt.value for vt in ViewType]
            raise ValueError(f"view_type must be one of: {valid_types}") from None

        parsed_fields = _parse_fields(fields)

        client = _get_alerts_client()
        alerts = await client.list_alerts(
            first=first, after=after, view_type=view_type_enum, fields=parsed_fields
        )

        return alerts.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for list_alerts",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error listing alerts")
        raise RuntimeError("Failed to list alerts") from exc


def _convert_filters_to_input(filters: list[JsonDict]) -> list[FilterInput]:
    """Convert filter dictionaries to FilterInput objects."""
    filter_inputs: list[FilterInput] = []
    for filter_dict in filters:
        try:
            # Check if this is the correct format
            if "fieldId" in filter_dict and "filterType" in filter_dict:
                filter_input = _parse_new_filter_format(filter_dict)
            else:
                raise ValueError(
                    "Each filter must have 'fieldId' and 'filterType' keys. "
                    "Example: {'fieldId': 'severity', 'filterType': 'string_equals', 'value': 'HIGH'}"
                )
            filter_inputs.append(filter_input)
        except Exception as e:
            raise ValueError(f"Invalid filter format: {e}") from e
    return filter_inputs


def _parse_filters_parameter(filters: str | None) -> list[JsonDict] | None:
    """Parse and validate the filters parameter from JSON string input.

    Args:
        filters: JSON string containing an array of filter objects, or None.

    Returns:
        Parsed list of filter dictionaries, or None if no filters.

    Raises:
        ValueError: If filters format is invalid.
    """
    if filters is None:
        return None

    try:
        parsed = json.loads(filters)
        if not isinstance(parsed, list):
            raise ValueError("Filters must be an array of filter objects")
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in filters parameter: {e}") from e


def _parse_fields(fields: str | None) -> list[str] | None:
    """Parse and validate the fields parameter from JSON string input.

    Args:
        fields: JSON string containing an array of field names, or None.

    Returns:
        Parsed list of field names, or None if no fields specified.

    Raises:
        ValueError: If fields format is invalid.
    """
    if fields is None:
        return None

    try:
        parsed = json.loads(fields)
        if not isinstance(parsed, list):
            raise ValueError("Fields must be an array of field names")
        # Validate that all elements are strings
        for i, item in enumerate(parsed):
            if not isinstance(item, str):
                raise ValueError(
                    f"All field names must be strings, but element at index {i} "
                    f"is {type(item).__name__}: {item!r}"
                )
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in fields parameter: {e}") from e


async def search_alerts(
    filters: str | None = None,
    first: int = 10,
    after: str | None = None,
    view_type: str = "ALL",
    fields: str | None = None,
) -> str:
    """Search alerts using advanced filters and criteria.

    Args:
        filters: JSON string containing an array of filter objects (optional).
                Each filter object must have fieldId and filterType keys.
        first: Number of alerts to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        view_type: Filter by assignment - ALL, ASSIGNED_TO_ME, UNASSIGNED, MY_TEAM.
        fields: Optional JSON string containing an array of field names to return.

    Returns:
        Filtered list of alerts in JSON format.

    Raises:
        RuntimeError: If there's an error searching alerts.
        ValueError: If parameters are invalid.
    """
    try:
        # Validate parameters
        if first < 1 or first > 100:
            raise ValueError("first must be between 1 and 100")

        _validate_cursor(after)

        try:
            view_type_enum = ViewType(view_type)
        except ValueError:
            valid_types = [vt.value for vt in ViewType]
            raise ValueError(f"view_type must be one of: {valid_types}") from None

        # Parse and validate filters parameter
        parsed_filters = _parse_filters_parameter(filters)

        # DoS protection: validate filter count and value array lengths
        filter_inputs = None
        if parsed_filters:
            _validate_filter_limits(parsed_filters)
            filter_inputs = _convert_filters_to_input(parsed_filters)

        parsed_fields = _parse_fields(fields)

        client = _get_alerts_client()
        alerts = await client.search_alerts(
            filters=filter_inputs,
            first=first,
            after=after,
            view_type=view_type_enum,
            fields=parsed_fields,
        )

        return alerts.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for search_alerts",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error searching alerts")
        raise RuntimeError("Failed to search alerts") from exc


def _create_string_filters(
    field_id: str, filter_type: str, filter_dict: JsonDict, is_negated: bool
) -> FilterInput:
    """Create string-based filters."""
    if filter_type == "string_equals":
        if "value" not in filter_dict:
            raise ValueError("string_equals filter requires 'value' key")
        return FilterInput.create_string_equal(
            field_id, cast(str, filter_dict["value"]), is_negated
        )
    elif filter_type == "string_in":
        if "values" not in filter_dict:
            raise ValueError("string_in filter requires 'values' key")
        values = cast(list[str], filter_dict["values"])
        if len(values) > MAX_FILTER_VALUES_COUNT:
            raise ValueError(
                f"string_in filter has too many values: {len(values)}. "
                f"Maximum allowed: {MAX_FILTER_VALUES_COUNT}"
            )
        return FilterInput.create_string_in(field_id, values, is_negated)
    else:
        raise ValueError(f"Unsupported string filter type: {filter_type}")


def _create_int_filters(
    field_id: str, filter_type: str, filter_dict: JsonDict, is_negated: bool
) -> FilterInput:
    """Create integer-based filters."""
    if filter_type == "int_equals":
        if "value" not in filter_dict:
            raise ValueError("int_equals filter requires 'value' key")
        return FilterInput.create_int_equal(field_id, cast(int, filter_dict["value"]), is_negated)
    elif filter_type == "int_in":
        if "values" not in filter_dict:
            raise ValueError("int_in filter requires 'values' key")
        values = cast(list[int], filter_dict["values"])
        if len(values) > MAX_FILTER_VALUES_COUNT:
            raise ValueError(
                f"int_in filter has too many values: {len(values)}. "
                f"Maximum allowed: {MAX_FILTER_VALUES_COUNT}"
            )
        return FilterInput.create_int_in(field_id, values, is_negated)
    elif filter_type == "int_range":
        start = cast(int, filter_dict.get("start")) if "start" in filter_dict else None
        end = cast(int, filter_dict.get("end")) if "end" in filter_dict else None
        start_inclusive = cast(bool, filter_dict.get("startInclusive", True))
        end_inclusive = cast(bool, filter_dict.get("endInclusive", True))
        return FilterInput.create_int_range(
            field_id, start, end, start_inclusive, end_inclusive, is_negated
        )
    else:
        raise ValueError(f"Unsupported int filter type: {filter_type}")


def _validate_timestamp_milliseconds(value: str | int, field_name: str) -> int:
    """Convert and validate a timestamp value to milliseconds.

    Args:
        value: Timestamp value (string or int)
        field_name: Name of the field for error messages (e.g., 'start', 'end')

    Returns:
        Validated timestamp in milliseconds

    Raises:
        ValueError: If value cannot be converted or is in nanoseconds
    """
    try:
        timestamp_ms = int(value)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"datetime_range filter '{field_name}' must be an integer (milliseconds), got: {value}"
        ) from e

    # Validate that timestamp is milliseconds (13 digits), not nanoseconds (19 digits)
    # Check absolute value to catch both positive and negative nanosecond timestamps
    if abs(timestamp_ms) > 9999999999999:  # More than 13 digits
        raise ValueError(
            f"datetime_range filter '{field_name}' value appears to be in nanoseconds ({timestamp_ms}). "
            "Please use milliseconds instead. Use the iso_to_unix_timestamp tool to convert "
            "ISO 8601 datetime strings to milliseconds."
        )

    return timestamp_ms


def _create_other_filters(
    field_id: str, filter_type: str, filter_dict: JsonDict, is_negated: bool
) -> FilterInput:
    """Create boolean, datetime, and fulltext filters."""
    if filter_type == "boolean_equals":
        if "value" not in filter_dict:
            raise ValueError("boolean_equals filter requires 'value' key")
        return FilterInput.create_boolean_equal(
            field_id, cast(bool, filter_dict["value"]), is_negated
        )
    elif filter_type == "datetime_range":
        start_ms: int | None = None
        end_ms: int | None = None

        # Convert and validate start timestamp
        if "start" in filter_dict:
            start_value = cast(str | int, filter_dict["start"])
            start_ms = _validate_timestamp_milliseconds(start_value, "start")

        # Convert and validate end timestamp
        if "end" in filter_dict:
            end_value = cast(str | int, filter_dict["end"])
            end_ms = _validate_timestamp_milliseconds(end_value, "end")

        start_inclusive = cast(bool, filter_dict.get("startInclusive", True))
        end_inclusive = cast(bool, filter_dict.get("endInclusive", True))
        return FilterInput.create_datetime_range(
            field_id, start_ms, end_ms, start_inclusive, end_inclusive, is_negated
        )
    elif filter_type == "fulltext":
        if "values" not in filter_dict:
            raise ValueError("fulltext filter requires 'values' key")
        values = cast(list[str], filter_dict["values"])
        if len(values) > MAX_FILTER_VALUES_COUNT:
            raise ValueError(
                f"fulltext filter has too many values: {len(values)}. "
                f"Maximum allowed: {MAX_FILTER_VALUES_COUNT}"
            )
        return FilterInput.create_fulltext_search(field_id, values, is_negated)
    else:
        raise ValueError(f"Unsupported filter type: {filter_type}")


def _parse_new_filter_format(filter_dict: JsonDict) -> FilterInput:
    """Parse new filter format with filterType."""
    field_id = cast(str, filter_dict["fieldId"])
    filter_type = cast(str, filter_dict["filterType"])
    is_negated = cast(bool, filter_dict.get("isNegated", False))

    if filter_type.startswith("string_"):
        return _create_string_filters(field_id, filter_type, filter_dict, is_negated)
    elif filter_type.startswith("int_"):
        return _create_int_filters(field_id, filter_type, filter_dict, is_negated)
    else:
        return _create_other_filters(field_id, filter_type, filter_dict, is_negated)


async def get_alert_notes(alert_id: str) -> str:
    """Get all notes and comments associated with an alert.

    Args:
        alert_id: The unique identifier of the alert.

    Returns:
        List of notes in JSON format with author and timestamp information.

    Raises:
        RuntimeError: If there's an error retrieving alert notes.
        ValueError: If parameters are invalid.
    """
    try:
        client = _get_alerts_client()
        notes = await client.get_alert_notes(alert_id=alert_id)

        return notes.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        raise  # Re-raise validation errors as-is
    except Exception as exc:
        logger.exception("Error retrieving notes for alert")
        raise RuntimeError(f"Failed to retrieve notes for alert {alert_id}") from exc


async def get_alert_history(alert_id: str, first: int = 10, after: str | None = None) -> str:
    """Get the complete audit history and timeline for an alert.

    Args:
        alert_id: The unique identifier of the alert.
        first: Number of history events to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).

    Returns:
        Chronological list of events and actions in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving alert history.
        ValueError: If parameters are invalid.
    """
    try:
        # Validate parameters
        if not alert_id or len(alert_id.strip()) == 0:
            raise ValueError("Alert ID cannot be empty")
        if first < 1 or first > 100:
            raise ValueError("first must be between 1 and 100")

        _validate_cursor(after)

        alert_id = alert_id.strip()

        client = _get_alerts_client()
        history = await client.get_alert_history(alert_id=alert_id, first=first, after=after)

        return history.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for get_alert_history",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error retrieving history for alert")
        raise RuntimeError(f"Failed to retrieve history for alert {alert_id}") from exc
