"""Tools for interacting with the XSPM Vulnerabilities Management system."""

# TEMPORARY: Using Optional[T] instead of T | None for FastMCP compatibility
# FastMCP's current OpenAI function schema generation requires Optional[T] syntax.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports it.

import json
import logging
from textwrap import dedent
from typing import Final

from purple_mcp.config import get_settings
from purple_mcp.libs.vulnerabilities import (
    FilterInput,
    VulnerabilitiesClient,
    VulnerabilitiesConfig,
)
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
GET_VULNERABILITY_DESCRIPTION: Final[str] = dedent(
    """
    Get detailed information about a specific vulnerability by ID.

    Retrieves comprehensive vulnerability data including CVE details, affected assets,
    risk scores, EPSS metrics, exploit maturity, and remediation information.

    Args:
        vulnerability_id: The unique identifier of the vulnerability (string).

    Returns:
        Detailed vulnerability information in JSON format containing:
        - id: Unique vulnerability identifier
        - externalId: External system identifier
        - name: Vulnerability title/name
        - severity: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
        - status: NEW, IN_PROGRESS, ON_HOLD, RESOLVED, RISK_ACKED, SUPPRESSED, TO_BE_PATCHED
        - detectedAt: ISO timestamp when vulnerability was detected
        - lastSeenAt: ISO timestamp of most recent occurrence
        - updatedAt: ISO timestamp of last update
        - product: Detection source product name
        - vendor: Detection source vendor name
        - asset: Associated asset information {id, name, type, category, cloudInfo, etc.}
        - scope: Organizational scope {account, site, group}
        - scopeLevel: account/site/group
        - cve: CVE details including:
          - id: CVE identifier (CVE-YYYY-NNNN)
          - description: CVE description
          - nvdBaseScore: NVD base score
          - riskScore: SentinelOne risk score
          - publishedDate: Publication date
          - epssScore: EPSS probability score
          - epssPercentile: EPSS percentile
          - exploitMaturity: Exploit code maturity level
          - exploitedInTheWild: Boolean indicating active exploitation
          - kevAvailable: CISA KEV catalog availability
          - s1BaseValues: CVSS vector components
          - riskIndicators: Additional risk indicators
          - timeline: CVE timeline events
        - software: Affected software {name, version, fixVersion, type, vendor}
        - findingData: Additional context and properties
        - paidScope: Whether under paid scope
        - remediationInsightsAvailable: Remediation insights availability
        - selfLink: Link to the vulnerability details
        - analystVerdict: TRUE_POSITIVE or FALSE_POSITIVE
        - assignee: Assigned user information {id, email, fullName}
        - exclusionPolicyId: Exclusion policy identifier if applicable

    Common Use Cases:
        - Vulnerability assessment and prioritization
        - CVE research and analysis
        - Risk scoring and exposure analysis
        - Patch management workflows
        - Compliance reporting

    Raises:
        RuntimeError: If there's an error retrieving the vulnerability.
        ValueError: If vulnerability_id is invalid or empty.
    """
).strip()

LIST_VULNERABILITIES_DESCRIPTION: Final[str] = dedent(
    """
    List vulnerabilities with pagination.

    Retrieves a paginated list of vulnerabilities in the environment.
    For advanced filtering by severity, CVE, asset type, etc., use search_vulnerabilities instead.

    Args:
        first: Number of vulnerabilities to retrieve (1-100, default: 10).
        after: Pagination cursor from previous response (optional).
               Use pageInfo.endCursor from previous response to get next page.
        fields: Optional JSON string containing an array of field names to return.
                If not specified, returns all default fields.
                Use minimal fields like '["id"]' when paging through intermediate results.

                Available fields:
                - Basic: "id", "name", "severity", "status"
                - Timing: "detectedAt", "lastSeenAt"
                - Context: "product", "vendor"
                - Analysis: "analystVerdict"
                - IDs: "exclusionPolicyId"
                - Nested objects (returns subfields):
                  - "cve" (id, nvdBaseScore, riskScore, publishedDate, epssScore,
                          exploitMaturity, exploitedInTheWild)
                  - "software" (name, version, fixVersion, type, vendor)
                  - "asset" (id, externalId, name, type, category, subcategory, privileged,
                            cloudInfo {accountId, accountName, providerName, region},
                            kubernetesInfo {cluster, namespace})
                  - "scope" (account {id, name}, site {id, name}, group {id, name})
                  - "assignee" (id, email, fullName)

                Examples:
                - Minimal for paging: '["id"]'
                - Summary view: '["id", "severity", "status", "name", "detectedAt"]'
                - With CVE details: '["id", "name", "cve", "software"]'
                - Full details: omit fields parameter or pass None

    Returns:
        Paginated vulnerability list in JSON format containing:
        - edges: Array of vulnerability objects
        - pageInfo: Pagination metadata
          - hasNextPage: Boolean indicating more results available
          - hasPreviousPage: Boolean indicating previous page exists
          - startCursor: Cursor for first item in current page
          - endCursor: Cursor for last item (use for next page)
        - totalCount: Total number of matching vulnerabilities

    Common Use Cases:
        - Vulnerability dashboard feeds
        - Security posture overview
        - Bulk vulnerability processing
        - Patch priority queues
        - Compliance reporting

    Pagination Example:
        1. Call with first=20 to get first 20 vulnerabilities
        2. Use pageInfo.endCursor as 'after' parameter for next 20
        3. Continue until pageInfo.hasNextPage is false

    Raises:
        RuntimeError: If there's an error listing vulnerabilities.
        ValueError: If parameters are invalid.
    """
).strip()

SEARCH_VULNERABILITIES_DESCRIPTION: Final[str] = dedent(
    """
    Search vulnerabilities using advanced filters and criteria.

    Args:
        filters: JSON string containing an array of filter objects (optional).
                Each filter object must have:
                - fieldId: String field name - MUST use flattened camelCase names (see Valid Field Names below)
                - filterType: One of the supported filter types below
                - isNegated: Optional boolean to negate the filter (default: false)

                Valid Field Names (fieldId values):
                IMPORTANT: Use these exact field names, NOT nested paths like "cve.id" or "asset.name"

                Core Fields:
                - "id": Vulnerability ID
                - "name": Vulnerability name
                - "severity": CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
                - "status": NEW, IN_PROGRESS, ON_HOLD, RESOLVED, RISK_ACKED, SUPPRESSED, TO_BE_PATCHED
                - "detectedAt": Detection timestamp
                - "lastSeenAt": Last seen timestamp
                - "product": Product name
                - "vendor": Vendor name
                - "analystVerdict": TRUE_POSITIVE, FALSE_POSITIVE
                - "assigneeFullName": Assigned user full name

                CVE Fields (use "cve" prefix, NOT "cve."):
                - "cveId": CVE identifier (e.g. CVE-2024-1234)
                - "cveNvdBaseScore": NVD base score (SORT ONLY - not filterable)
                - "cveRiskScore": SentinelOne risk score (SORT ONLY - not filterable)
                - "cveEpssScore": EPSS probability score (STRING_IN only - use ranges: "0.0-0.35", "0.35-0.5", "0.5-0.75", "0.75-1.0")
                - "cveExploitMaturity": NOT_AVAILABLE, UNPROVEN, PROOF_OF_CONCEPT, FUNCTIONAL, HIGH
                - "cveExploitedInTheWild": Boolean - actively exploited
                - "cveKevAvailable": Boolean - in CISA KEV catalog
                - "cveReportConfidence": Report confidence level

                Software Fields (use "software" prefix, NOT "software."):
                - "softwareName": Software package name
                - "softwareVersion": Installed version
                - "softwareFixVersion": Available fix version
                - "softwareFixVersionAvailable": Boolean - fix available
                - "softwareType": OPERATING_SYSTEM, APPLICATION, LIBRARY, etc.
                - "softwareVendor": Software vendor name

                Asset Fields (use "asset" prefix, NOT "asset."):
                - "assetId": Asset identifier
                - "assetName": Asset name
                - "assetType": Asset type
                - "assetTypeCategory": Asset type category
                - "assetCategory": Asset category
                - "assetSubcategory": Asset subcategory
                - "assetCriticality": CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
                - "assetPrivileged": Boolean - privileged asset
                - "assetCloudResourceId": Cloud resource ID
                - "assetCloudAccountId": Cloud account ID
                - "assetCloudAccount": Cloud account name
                - "assetCloudRegion": Cloud region
                - "assetKubernetesCluster": Kubernetes cluster name
                - "assetKubernetesClusterId": Kubernetes cluster ID

                Other Fields:
                - "remediationInsightsAvailable": Boolean - remediation insights available
                - "accountId": Account ID (hidden)
                - "siteId": Site ID (hidden)
                - "groupId": Group ID (hidden)

                Filter Types and Required Keys:
                IMPORTANT: The vulnerabilities API does NOT support INT filters. Use STRING or BOOLEAN filters.

                String Filters (for severity, status, product, vendor, etc.):
                - "string_equals": Exact match. Requires "value" key.
                  Example: {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}
                - "string_in": Match any of multiple values. Requires "values" key (list).
                  Example: {"fieldId": "status", "filterType": "string_in", "values": ["NEW", "IN_PROGRESS"]}
                  SPECIAL CASE - cveEpssScore: Use range format like {"fieldId": "cveEpssScore", "filterType": "string_in", "values": ["0.5-0.75", "0.75-1.0"]}
                  Note: product and vendor ONLY support STRING filters, NOT fulltext

                Boolean Filters (for exploited, KEV, fix available, etc.):
                - "boolean_equals": Exact match for single boolean. Requires "value" key.
                  Example: {"fieldId": "cveExploitedInTheWild", "filterType": "boolean_equals", "value": true}
                - "boolean_in": Match any of multiple boolean values. Requires "values" key (list).
                  Example: {"fieldId": "softwareFixVersionAvailable", "filterType": "boolean_in", "values": [true, null]}
                  Note: Can include null to match missing/unset values

                DateTime Filters (for detectedAt, lastSeenAt):
                - "datetime_range": Range match using UNIX timestamps in milliseconds (UTC). Requires "start" and/or "end" keys.
                  Optional: "startInclusive", "endInclusive" (default: true)

                  IMPORTANT: All datetimes in the Vulnerability API are in UTC timezone.
                  You MUST use the iso_to_unix_timestamp tool to convert ISO 8601 datetime strings
                  to UNIX timestamps (milliseconds) before using them in datetime filters.

                  IMPORTANT: Unless the user specifies a field to query a DateTime on, use detectedAt.

                  The iso_to_unix_timestamp tool handles timezone conversion automatically.
                  Provide datetimes in the user's preferred timezone (e.g., "2024-10-30T08:00:00-04:00" for Eastern Time)
                  and the tool will convert to UTC milliseconds for the API.

                  Example workflow:
                  1. Call iso_to_unix_timestamp("2024-10-30T08:00:00-04:00") -> returns "1730289600000" (UTC)
                  2. Use result in filter: {"fieldId": "detectedAt", "filterType": "datetime_range", "start": 1730289600000}

                  Example: {"fieldId": "detectedAt", "filterType": "datetime_range", "start": 1730289600000}

                Fulltext Search (for name, CVE ID, software/asset names):
                - "fulltext": Single-value text search. Requires "values" key (list of search terms).
                  Example: {"fieldId": "name", "filterType": "fulltext", "values": ["log4j"]}
                - "fulltext_in": Multi-value text search with partial matching. Requires "values" key (list).
                  Example: {"fieldId": "assetName", "filterType": "fulltext_in", "values": ["server", "prod", "web"]}

                Limits:
                - Maximum 50 filters per request
                - Maximum 100 values in "values" arrays

        first: Number of vulnerabilities to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        fields: Optional JSON string containing an array of field names to return.
                If not specified, returns all default fields.
                See list_vulnerabilities for available fields and examples.

                Available fields:
                - Basic: "id", "name", "severity", "status"
                - Timing: "detectedAt", "lastSeenAt"
                - Context: "product", "vendor"
                - Analysis: "analystVerdict"
                - IDs: "exclusionPolicyId"
                - Nested objects: "cve", "software", "asset", "scope", "assignee"
                  (See list_vulnerabilities for exact subfields returned)

                Examples:
                - Minimal for paging: '["id"]'
                - Summary: '["id", "severity", "status", "name", "detectedAt"]'
                - With CVE: '["id", "name", "cve", "software"]'

    Performance Note:
        When paging through many results, use fields='["id"]' for intermediate pages
        to conserve context window space. Use totalCount to gauge result set size.

    Returns:
        Filtered list of vulnerabilities in JSON format.

    Raises:
        RuntimeError: If there's an error searching vulnerabilities.
        ValueError: If parameters are invalid.

    Examples:
        CORRECT: filters=[
          {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
          {"fieldId": "cveExploitedInTheWild", "filterType": "boolean_equals", "value": true},
          {"fieldId": "assetType", "filterType": "string_in", "values": ["SERVER", "WORKSTATION"]}
        ]
        WRONG: filters=[
          {"fieldId": "cve.id", "filterType": "string_equals", "value": "CVE-2024-1234"},  # Use "cveId" not "cve.id"
          {"fieldId": "asset.name", "filterType": "fulltext", "values": ["prod"]},  # Use "assetName" not "asset.name"
          {"fieldId": "severity", "filterType": "EQUALS", "value": "CRITICAL"}  # Use "string_equals" not "EQUALS"
        ]
    """
).strip()

GET_VULNERABILITY_NOTES_DESCRIPTION: Final[str] = dedent(
    """
    Get all notes and comments associated with a vulnerability.

    Retrieves all analyst notes, comments, and annotations attached to a specific
    vulnerability. Notes provide context, analysis findings, remediation steps,
    and collaboration history.

    Args:
        vulnerability_id: The unique identifier of the vulnerability.

    Returns:
        List of notes in JSON format, each containing:
        - id: Unique note identifier
        - vulnerabilityId: Associated vulnerability identifier
        - text: Note content/message
        - author: User information {id, email, fullName, deleted}
        - createdAt: ISO timestamp when note was created
        - updatedAt: ISO timestamp when note was last updated (if applicable)

        Notes are typically ordered by creation time (newest first).

    Common Use Cases:
        - Vulnerability analysis documentation
        - Tracking security team findings and decisions
        - Audit trail for vulnerability handling
        - Knowledge sharing between security analysts
        - Compliance and reporting requirements

    Raises:
        RuntimeError: If there's an error retrieving vulnerability notes.
        ValueError: If vulnerability_id is invalid or empty.
    """
).strip()

GET_VULNERABILITY_HISTORY_DESCRIPTION: Final[str] = dedent(
    """
    Get the complete audit history and timeline for a vulnerability.

    Retrieves a chronological record of all actions, status changes, and events
    related to a specific vulnerability. Provides full audit trail for compliance
    and investigation.

    Args:
        vulnerability_id: The unique identifier of the vulnerability.
        first: Number of history events to retrieve (1-100, default: 10).
        after: Pagination cursor from previous response (optional).

    Returns:
        Paginated chronological list in JSON format containing:
        - edges: Array of history events with:
          - eventType: Type of event (CREATION, STATUS, ANALYST_VERDICT, USER_ASSIGNMENT, NOTES, WORKFLOW_ACTION)
          - eventText: Human-readable description of the event
          - createdAt: ISO timestamp when event occurred
        - pageInfo: Pagination metadata (same structure as list_vulnerabilities)

    Common Event Types:
        - CREATION: Vulnerability first detected
        - STATUS: Status changed (NEW → IN_PROGRESS, etc.)
        - ANALYST_VERDICT: Verdict updated (TRUE_POSITIVE/FALSE_POSITIVE)
        - USER_ASSIGNMENT: Assigned/unassigned to user
        - NOTES: Note or comment added
        - WORKFLOW_ACTION: Automated action or workflow step

    Common Use Cases:
        - Compliance auditing and reporting
        - Investigation timeline reconstruction
        - Performance metrics and SLA tracking
        - Change management and accountability
        - Vulnerability lifecycle analysis

    Raises:
        RuntimeError: If there's an error retrieving vulnerability history.
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


def _get_vulnerabilities_client() -> VulnerabilitiesClient:
    """Get a configured VulnerabilitiesClient instance.

    Returns:
        Configured VulnerabilitiesClient instance.

    Raises:
        RuntimeError: If settings are not properly configured.
    """
    try:
        settings = get_settings()
    except Exception as e:
        raise RuntimeError(
            f"Settings not initialized. Please check your environment configuration. Error: {e}"
        ) from e

    config = VulnerabilitiesConfig(
        graphql_url=settings.vulnerabilities_graphql_url,
        auth_token=settings.graphql_service_token,
    )

    return VulnerabilitiesClient(config)


# MCP Tool Functions
# TEMPORARY: These functions use Optional[T] instead of T | None for FastMCP compatibility.
# FastMCP's current OpenAI function calling support requires this syntax for proper JSON schema
# generation of optional parameters.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports modern union syntax.


async def get_vulnerability(vulnerability_id: str) -> str:
    """Get detailed information about a specific vulnerability by ID.

    Args:
        vulnerability_id: The unique identifier of the vulnerability.

    Returns:
        Detailed vulnerability information in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving the vulnerability.
    """
    try:
        client = _get_vulnerabilities_client()
        vulnerability = await client.get_vulnerability(vulnerability_id)

        if vulnerability is None:
            return json.dumps(None, indent=2)

        return vulnerability.model_dump_json(exclude_none=True, indent=2)

    except Exception as exc:
        logger.exception("Error retrieving vulnerability")
        raise RuntimeError(f"Failed to retrieve vulnerability {vulnerability_id}") from exc


async def list_vulnerabilities(
    first: int = 10, after: str | None = None, fields: str | None = None
) -> str:
    """List vulnerabilities with pagination.

    Args:
        first: Number of vulnerabilities to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        fields: Optional JSON string containing an array of field names to return.

    Returns:
        Paginated list of vulnerabilities in JSON format.

    Raises:
        RuntimeError: If there's an error listing vulnerabilities.
        ValueError: If parameters are invalid.
    """
    try:
        # Validate parameters
        if first < 1 or first > 100:
            raise ValueError("first must be between 1 and 100")

        _validate_cursor(after)

        parsed_fields = _parse_fields(fields)

        client = _get_vulnerabilities_client()
        vulnerabilities = await client.list_vulnerabilities(
            first=first, after=after, fields=parsed_fields
        )

        return vulnerabilities.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for list_vulnerabilities",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error listing vulnerabilities")
        raise RuntimeError("Failed to list vulnerabilities") from exc


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


def _convert_filter_to_input(filter_dict: JsonDict) -> FilterInput:  # noqa: C901
    """Convert a single filter dictionary to FilterInput object.

    Translates simplified filter format to nested GraphQL structure.
    Input: {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}
    Output: {"fieldId": "severity", "stringEqual": {"value": "HIGH"}}

    Args:
        filter_dict: Dictionary containing filter specification with:
            - fieldId: Field name
            - filterType: Filter operation type
            - Additional keys based on filterType (value/values/start/end/etc.)
            - isNegated: Optional boolean to negate filter

    Returns:
        FilterInput object with properly nested GraphQL structure.

    Raises:
        ValueError: If filter format is invalid or unsupported.
    """
    if "fieldId" not in filter_dict or "filterType" not in filter_dict:
        raise ValueError(
            "Each filter must have 'fieldId' and 'filterType' keys. "
            "Example: {'fieldId': 'severity', 'filterType': 'string_equals', 'value': 'CRITICAL'}"
        )

    filter_type = filter_dict["filterType"]

    # Map filterType to GraphQL field name and build nested structure
    graphql_dict: JsonDict = {
        "fieldId": filter_dict["fieldId"],
        "isNegated": filter_dict.get("isNegated", False),
    }

    # String filters
    if filter_type == "string_equals":
        if "value" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'value' key")
        graphql_dict["stringEqual"] = {"value": filter_dict["value"]}
    elif filter_type == "string_in":
        if "values" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'values' key")
        graphql_dict["stringIn"] = {"values": filter_dict["values"]}

    # Integer filters
    elif filter_type == "int_equals":
        if "value" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'value' key")
        graphql_dict["intEqual"] = {"value": filter_dict["value"]}
    elif filter_type == "int_in":
        if "values" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'values' key")
        graphql_dict["intIn"] = {"values": filter_dict["values"]}
    elif filter_type == "int_range":
        range_dict: JsonDict = {}
        if "start" in filter_dict:
            range_dict["start"] = filter_dict["start"]
        if "end" in filter_dict:
            range_dict["end"] = filter_dict["end"]
        if "startInclusive" in filter_dict:
            range_dict["startInclusive"] = filter_dict["startInclusive"]
        if "endInclusive" in filter_dict:
            range_dict["endInclusive"] = filter_dict["endInclusive"]
        if "start" not in range_dict and "end" not in range_dict:
            raise ValueError(f"Filter type '{filter_type}' requires at least 'start' or 'end' key")
        graphql_dict["intRange"] = range_dict

    # Long filters
    elif filter_type == "long_equals":
        if "value" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'value' key")
        graphql_dict["longEqual"] = {"value": filter_dict["value"]}
    elif filter_type == "long_in":
        if "values" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'values' key")
        graphql_dict["longIn"] = {"values": filter_dict["values"]}
    elif filter_type == "long_range":
        range_dict = {}
        if "start" in filter_dict:
            range_dict["start"] = filter_dict["start"]
        if "end" in filter_dict:
            range_dict["end"] = filter_dict["end"]
        if "startInclusive" in filter_dict:
            range_dict["startInclusive"] = filter_dict["startInclusive"]
        if "endInclusive" in filter_dict:
            range_dict["endInclusive"] = filter_dict["endInclusive"]
        if "start" not in range_dict and "end" not in range_dict:
            raise ValueError(f"Filter type '{filter_type}' requires at least 'start' or 'end' key")
        graphql_dict["longRange"] = range_dict

    # Boolean filters
    elif filter_type == "boolean_equals":
        if "value" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'value' key")
        graphql_dict["booleanEqual"] = {"value": filter_dict["value"]}
    elif filter_type == "boolean_in":
        if "values" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'values' key")
        graphql_dict["booleanIn"] = {"values": filter_dict["values"]}

    # DateTime filters
    elif filter_type == "datetime_range":
        from typing import cast

        range_dict = {}

        # Convert and validate start timestamp
        if "start" in filter_dict:
            start_raw = cast(str | int, filter_dict["start"])
            try:
                start_value = int(start_raw)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"datetime_range filter 'start' must be an integer (milliseconds), got: {start_raw}"
                ) from e

            # Validate that timestamp is milliseconds (13 digits), not nanoseconds (19 digits)
            # Check absolute value to catch both positive and negative nanosecond timestamps
            if abs(start_value) > 9999999999999:  # More than 13 digits
                raise ValueError(
                    f"datetime_range filter 'start' value appears to be in nanoseconds ({start_value}). "
                    "Please use milliseconds instead. Use the iso_to_unix_timestamp tool to convert "
                    "ISO 8601 datetime strings to milliseconds."
                )
            range_dict["start"] = start_value

        # Convert and validate end timestamp
        if "end" in filter_dict:
            end_raw = cast(str | int, filter_dict["end"])
            try:
                end_value = int(end_raw)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"datetime_range filter 'end' must be an integer (milliseconds), got: {end_raw}"
                ) from e

            # Validate that timestamp is milliseconds (13 digits), not nanoseconds (19 digits)
            # Check absolute value to catch both positive and negative nanosecond timestamps
            if abs(end_value) > 9999999999999:  # More than 13 digits
                raise ValueError(
                    f"datetime_range filter 'end' value appears to be in nanoseconds ({end_value}). "
                    "Please use milliseconds instead. Use the iso_to_unix_timestamp tool to convert "
                    "ISO 8601 datetime strings to milliseconds."
                )
            range_dict["end"] = end_value
        if "startInclusive" in filter_dict:
            range_dict["startInclusive"] = filter_dict["startInclusive"]
        if "endInclusive" in filter_dict:
            range_dict["endInclusive"] = filter_dict["endInclusive"]
        if "start" not in range_dict and "end" not in range_dict:
            raise ValueError(f"Filter type '{filter_type}' requires at least 'start' or 'end' key")
        graphql_dict["dateTimeRange"] = range_dict

    # Fulltext search
    elif filter_type == "fulltext":
        if "values" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'values' key")
        graphql_dict["match"] = {"values": filter_dict["values"]}
    elif filter_type == "fulltext_in":
        if "values" not in filter_dict:
            raise ValueError(f"Filter type '{filter_type}' requires 'values' key")
        graphql_dict["matchIn"] = {"values": filter_dict["values"]}

    else:
        raise ValueError(
            f"Unsupported filterType: '{filter_type}'. "
            "Supported types: string_equals, string_in, int_equals, int_in, int_range, "
            "long_equals, long_in, long_range, boolean_equals, boolean_in, datetime_range, "
            "fulltext, fulltext_in"
        )

    # Build FilterInput using model_validate with properly nested structure
    return FilterInput.model_validate(graphql_dict)


def _convert_filters_to_input(filters: list[JsonDict]) -> list[FilterInput]:
    """Convert filter dictionaries to FilterInput objects."""
    filter_inputs: list[FilterInput] = []
    for filter_dict in filters:
        try:
            filter_input = _convert_filter_to_input(filter_dict)
            filter_inputs.append(filter_input)
        except Exception as e:
            raise ValueError(f"Invalid filter format: {e}") from e
    return filter_inputs


async def search_vulnerabilities(
    filters: str | None = None,
    first: int = 10,
    after: str | None = None,
    fields: str | None = None,
) -> str:
    """Search vulnerabilities using advanced filters and criteria.

    Args:
        filters: JSON string containing an array of filter objects (optional).
                Each filter object must have fieldId and filterType keys.
        first: Number of vulnerabilities to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        fields: Optional JSON string containing an array of field names to return.

    Returns:
        Filtered list of vulnerabilities in JSON format.

    Raises:
        RuntimeError: If there's an error searching vulnerabilities.
        ValueError: If parameters are invalid.
    """
    try:
        # Validate parameters
        if first < 1 or first > 100:
            raise ValueError("first must be between 1 and 100")

        _validate_cursor(after)

        # Parse and validate filters
        parsed_filters = _parse_filters_parameter(filters)

        filter_inputs: list[FilterInput] | None = None
        if parsed_filters:
            _validate_filter_limits(parsed_filters)
            filter_inputs = _convert_filters_to_input(parsed_filters)

        parsed_fields = _parse_fields(fields)

        client = _get_vulnerabilities_client()
        vulnerabilities = await client.search_vulnerabilities(
            filters=filter_inputs, first=first, after=after, fields=parsed_fields
        )

        return vulnerabilities.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for search_vulnerabilities",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error searching vulnerabilities")
        raise RuntimeError("Failed to search vulnerabilities") from exc


async def get_vulnerability_notes(vulnerability_id: str) -> str:
    """Get all notes associated with a vulnerability.

    Args:
        vulnerability_id: The unique identifier of the vulnerability.

    Returns:
        List of notes in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving vulnerability notes.
        ValueError: If vulnerability_id is invalid or empty.
    """
    try:
        if not vulnerability_id or not vulnerability_id.strip():
            raise ValueError("vulnerability_id cannot be empty")

        client = _get_vulnerabilities_client()
        notes = await client.get_vulnerability_notes(vulnerability_id)

        return notes.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for get_vulnerability_notes",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error retrieving vulnerability notes")
        raise RuntimeError(
            f"Failed to retrieve notes for vulnerability {vulnerability_id}"
        ) from exc


async def get_vulnerability_history(
    vulnerability_id: str, first: int = 10, after: str | None = None
) -> str:
    """Get the audit history for a vulnerability.

    Args:
        vulnerability_id: The unique identifier of the vulnerability.
        first: Number of history events to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).

    Returns:
        Paginated list of history events in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving vulnerability history.
        ValueError: If parameters are invalid.
    """
    try:
        if not vulnerability_id or not vulnerability_id.strip():
            raise ValueError("vulnerability_id cannot be empty")

        if first < 1 or first > 100:
            raise ValueError("first must be between 1 and 100")

        _validate_cursor(after)

        client = _get_vulnerabilities_client()
        history = await client.get_vulnerability_history(
            vulnerability_id, first=first, after=after
        )

        return history.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for get_vulnerability_history",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error retrieving vulnerability history")
        raise RuntimeError(
            f"Failed to retrieve history for vulnerability {vulnerability_id}"
        ) from exc
