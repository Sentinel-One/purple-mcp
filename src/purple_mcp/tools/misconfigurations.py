"""Tools for interacting with the XSPM Misconfigurations Management system."""

# TEMPORARY: Using Optional[T] instead of T | None for FastMCP compatibility
# FastMCP's current OpenAI function schema generation requires Optional[T] syntax.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports it.

import json
import logging
from textwrap import dedent
from typing import Final

from purple_mcp.config import get_settings
from purple_mcp.libs.misconfigurations import (
    FilterInput,
    MisconfigurationsClient,
    MisconfigurationsConfig,
    ViewType,
)
from purple_mcp.type_defs import JsonDict

# TEMPORARY: Using Optional[T] instead of T | None throughout this file for FastMCP compatibility.
# FastMCP's current OpenAI function schema generation requires explicit Optional types to properly
# handle optional parameters in the JSON schema format.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports modern union syntax.

logger = logging.getLogger(__name__)

# DoS protection constants
MAX_FILTERS_COUNT: Final = 50
MAX_FILTER_VALUES_COUNT: Final = 100


# Docstring constants
GET_MISCONFIGURATION_DESCRIPTION: Final[str] = dedent(
    """
    Get detailed information about a specific misconfiguration by ID.

    Retrieves comprehensive misconfiguration data including metadata, severity,
    affected assets, compliance information, remediation steps, and MITRE ATT&CK mappings.

    Args:
        misconfiguration_id: The unique identifier of the misconfiguration (string).

    Returns:
        Detailed misconfiguration information in JSON format containing:
        - id: Unique misconfiguration identifier
        - externalId: External system identifier
        - name: Misconfiguration title/name
        - description: Detailed description of the issue
        - severity: CRITICAL, HIGH, MEDIUM, LOW, INFO, UNKNOWN
        - status: NEW, IN_PROGRESS, ON_HOLD, RESOLVED, RISK_ACKED, SUPPRESSED, TO_BE_PATCHED
        - detectedAt: ISO timestamp when misconfiguration was detected
        - eventTime: ISO timestamp of the event
        - environment: Environment where detected (e.g., cloud, kubernetes)
        - product: Detection source product name
        - vendor: Detection source vendor name
        - asset: Associated asset information {id, name, type, category, cloudInfo, etc.}
        - scope: Organizational scope {account, site, group}
        - scopeLevel: account/site/group
        - analystVerdict: TRUE_POSITIVE or FALSE_POSITIVE
        - assignee: Assigned user information {id, email, fullName}
        - compliance: Compliance standards and requirements
        - remediation: Remediation steps and references
        - failedRules: List of failed security rules
        - findingData: Additional context and properties
        - mitreAttacks: MITRE ATT&CK technique mappings
        - cnapp: Cloud-native application protection details
        - evidence: Evidence data (files, IPs, ports, secrets, etc.)

    Common Use Cases:
        - Security posture assessment
        - Compliance auditing and reporting
        - Vulnerability management workflows
        - Cloud security remediation
        - Risk assessment and prioritization

    Raises:
        RuntimeError: If there's an error retrieving the misconfiguration.
        ValueError: If misconfiguration_id is invalid or empty.
    """
).strip()

LIST_MISCONFIGURATIONS_DESCRIPTION: Final[str] = dedent(
    """
    List misconfigurations with pagination and view filtering.

    Retrieves a paginated list of misconfigurations with filtering by environment type.
    For advanced filtering by severity, status, compliance, etc., use search_misconfigurations instead.

    Args:
        first: Number of misconfigurations to retrieve (1-100, default: 10).
        after: Pagination cursor from previous response (optional).
               Use pageInfo.endCursor from previous response to get next page.
        view_type: Environment filter with options:
                   - "ALL": Show all misconfigurations (default)
                   - "CLOUD": Cloud environment only
                   - "KUBERNETES": Kubernetes environment only
                   - "IDENTITY": Identity-related misconfigurations
                   - "INFRASTRUCTURE_AS_CODE": IaC misconfigurations
                   - "ADMISSION_CONTROLLER": Admission controller findings
                   - "OFFENSIVE_SECURITY": Offensive security findings
                   - "SECRET_SCANNING": Secret scanning findings
        fields: Optional JSON string containing an array of field names to return.
                If not specified, returns all default fields.
                Use minimal fields like '["id"]' when paging through intermediate results.

                Available fields:
                - Basic: "id", "externalId", "name", "severity", "status"
                - Timing: "detectedAt", "lastSeenAt", "eventTime"
                - Context: "environment", "product", "vendor", "organization"
                - Analysis: "analystVerdict", "mitigable", "exposureReason"
                - Type: "misconfigurationType"
                - IDs: "resourceUid", "exploitId", "exclusionPolicyId"
                - Nested objects (returns subfields):
                  - "asset" (id, externalId, name, type, category, subcategory, privileged,
                            cloudInfo {accountId, accountName, providerName, region},
                            kubernetesInfo {cluster, namespace})
                  - "scope" (account {id, name}, site {id, name}, group {id, name})
                  - "assignee" (id, email, fullName)
                  - "evidence" (fileName, fileType, iacFramework, ipAddress, port, subdomain)
                  - "cnapp" (policy {id, version, group}, verifiedExploitable)
                  - "admissionRequest" (category, resourceName, resourceNamespace, resourceType,
                                       userName, userUid, userGroup)
                  - "remediation" (mitigable, mitigationSteps)
                  - "mitreAttacks" (techniqueId, techniqueName, techniqueUrl, tacticName, tacticUid)
                - Lists: "complianceStandards", "dataClassificationDataTypes", "dataClassificationCategories"
                - Enforcement: "enforcementAction"

                Examples:
                - Minimal for paging: '["id"]'
                - Summary view: '["id", "severity", "status", "name", "detectedAt"]'
                - With asset context: '["id", "name", "asset", "severity"]'
                - Full details: omit fields parameter or pass None

    Returns:
        Paginated misconfiguration list in JSON format containing:
        - edges: Array of misconfiguration objects
        - pageInfo: Pagination metadata
          - hasNextPage: Boolean indicating more results available
          - hasPreviousPage: Boolean indicating previous page exists
          - startCursor: Cursor for first item in current page
          - endCursor: Cursor for last item (use for next page)
        - totalCount: Total number of matching misconfigurations

    Common Use Cases:
        - Security dashboard feeds
        - Environment-specific security reviews
        - Bulk remediation workflows
        - Compliance reporting by scope
        - Cloud security posture management

    Pagination Example:
        1. Call with first=20 to get first 20 misconfigurations
        2. Use pageInfo.endCursor as 'after' parameter for next 20
        3. Continue until pageInfo.hasNextPage is false

    Raises:
        RuntimeError: If there's an error listing misconfigurations.
        ValueError: If parameters are invalid.
    """
).strip()

SEARCH_MISCONFIGURATIONS_DESCRIPTION: Final[str] = dedent(
    """
    Search misconfigurations using advanced filters and criteria.

    Args:
        filters: JSON string containing an array of filter objects (optional).
                Each filter object must have:
                - fieldId: String field name - MUST use flattened camelCase names (see Valid Field Names below)
                - filterType: One of the supported filter types below
                - isNegated: Optional boolean to negate the filter (default: false)

                Valid Field Names (fieldId values):
                IMPORTANT: Use these exact field names, NOT nested paths like "asset.name" or "evidence.secret"

                Core Fields:
                - "id": Misconfiguration ID
                - "name": Misconfiguration name
                - "severity": CRITICAL, HIGH, MEDIUM, LOW, INFO, UNKNOWN
                - "status": NEW, IN_PROGRESS, ON_HOLD, RESOLVED, RISK_ACKED, SUPPRESSED, TO_BE_PATCHED
                - "detectedAt": Detection timestamp
                - "lastSeenAt": Last seen timestamp
                - "environment": Environment type
                - "product": Product name
                - "vendor": Vendor name
                - "analystVerdict": TRUE_POSITIVE, FALSE_POSITIVE
                - "assigneeFullName": Assigned user full name
                - "exposureReason": Reason for exposure
                - "mitigable": Boolean - can be mitigated

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

                Policy Fields (use appropriate prefixes):
                - "policyId": Policy identifier
                - "policyVersion": Policy version
                - "policyGroup": Policy group name
                - "organization": Organization name
                - "enforcementAction": Enforcement action type
                - "iacFramework": Infrastructure as Code framework

                Compliance & Classification:
                - "complianceStandards": Compliance standards
                - "hasClassifiedData": Boolean - contains classified data
                - "dataClassificationCategories": Data classification categories
                - "dataClassificationDataTypes": Data classification types

                Secret Fields (use "secret" prefix, NOT "evidence.secret."):
                - "secretId": Secret identifier
                - "secretHash": Secret hash
                - "secretType": Type of secret
                - "secretValidity": Secret validity status

                Request Fields (for admission controller, use "request" prefix):
                - "requestResourceName": Resource name
                - "requestResourceType": Resource type
                - "requestResourceNamespace": Resource namespace
                - "requestUserName": User name
                - "requestUserUid": User UID
                - "requestUserGroup": User group
                - "requestCategory": Request category

                Other Fields:
                - "commitedBy": Committed by (IaC findings)
                - "verifiedExploitable": Boolean - verified as exploitable
                - "accountId": Account ID (hidden)
                - "siteId": Site ID (hidden)
                - "groupId": Group ID (hidden)

                Filter Types and Required Keys:
                IMPORTANT: The misconfigurations API does NOT support INT filters. Use STRING or BOOLEAN filters.

                String Filters (for severity, status, product, vendor, etc.):
                - "string_equals": Exact match. Requires "value" key.
                  Example: {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}
                - "string_in": Match any of multiple values. Requires "values" key (list).
                  Example: {"fieldId": "status", "filterType": "string_in", "values": ["NEW", "IN_PROGRESS"]}
                  Note: product and vendor ONLY support STRING filters, NOT fulltext

                Boolean Filters (for mitigable, verifiedExploitable, hasClassifiedData, etc.):
                - "boolean_equals": Exact match for single boolean. Requires "value" key.
                  Example: {"fieldId": "mitigable", "filterType": "boolean_equals", "value": true}
                - "boolean_in": Match any of multiple boolean values. Requires "values" key (list).
                  Example: {"fieldId": "hasClassifiedData", "filterType": "boolean_in", "values": [true, null]}
                  Note: Can include null to match missing/unset values
                  SPECIAL CASE - secretValidity: ONLY supports boolean_in (NOT boolean_equals)

                DateTime Filters (for detectedAt, lastSeenAt):
                - "datetime_range": Range match using UNIX timestamps in milliseconds (UTC). Requires "start" and/or "end" keys.
                  Optional: "startInclusive", "endInclusive" (default: true)

                  IMPORTANT: All datetimes in the Misconfiguration API are in UTC timezone.
                  You MUST use the iso_to_unix_timestamp tool to convert ISO 8601 datetime strings
                  to UNIX timestamps (milliseconds) before using them in datetime filters.

                  IMPORTANT: Unless the user specifies a field to query a DateTime on, use lastSeenAt.

                  The iso_to_unix_timestamp tool handles timezone conversion automatically.
                  Provide datetimes in the user's preferred timezone (e.g., "2024-10-30T08:00:00-04:00" for Eastern Time)
                  and the tool will convert to UTC milliseconds for the API.

                  Example workflow:
                  1. Call iso_to_unix_timestamp("2024-10-30T08:00:00-04:00") -> returns "1730289600000" (UTC)
                  2. Use result in filter: {"fieldId": "detectedAt", "filterType": "datetime_range", "start": 1730289600000}

                  Example: {"fieldId": "detectedAt", "filterType": "datetime_range", "start": 1730289600000}

                Fulltext Search (for name, exposureReason, asset/resource names, compliance, etc.):
                - "fulltext": Single-value text search. Requires "values" key (list of search terms).
                  Example: {"fieldId": "name", "filterType": "fulltext", "values": ["s3"]}
                - "fulltext_in": Multi-value text search with partial matching. Requires "values" key (list).
                  Example: {"fieldId": "assetName", "filterType": "fulltext_in", "values": ["server", "prod", "web"]}
                  SPECIAL CASES - secretHash/secretId: ONLY support fulltext/fulltext_in (NOT string_equals)

                Limits:
                - Maximum 50 filters per request
                - Maximum 100 values in "values" arrays

        first: Number of misconfigurations to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        view_type: Filter by environment - ALL, CLOUD, KUBERNETES, etc.
        fields: Optional JSON string containing an array of field names to return.
                If not specified, returns all default fields.
                See list_misconfigurations for available fields and examples.

                Available fields:
                - Basic: "id", "externalId", "name", "severity", "status"
                - Timing: "detectedAt", "lastSeenAt", "eventTime"
                - Context: "environment", "product", "vendor", "organization"
                - Analysis: "analystVerdict", "mitigable", "exposureReason"
                - Type: "misconfigurationType"
                - IDs: "resourceUid", "exploitId", "exclusionPolicyId"
                - Nested objects: "asset", "scope", "assignee", "evidence", "cnapp",
                                "admissionRequest", "remediation", "mitreAttacks"
                  (See list_misconfigurations for exact subfields returned)
                - Lists: "complianceStandards", "dataClassificationDataTypes",
                        "dataClassificationCategories"

                Examples:
                - Minimal for paging: '["id"]'
                - Summary: '["id", "severity", "status", "name", "detectedAt"]'
                - With asset: '["id", "name", "asset", "severity"]'

    Performance Note:
        When paging through many results, use fields='["id"]' for intermediate pages
        to conserve context window space. Use totalCount to gauge result set size.

    Returns:
        Filtered list of misconfigurations in JSON format.

    Raises:
        RuntimeError: If there's an error searching misconfigurations.
        ValueError: If parameters are invalid.

    Examples:
        CORRECT: filters=[
          {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
          {"fieldId": "status", "filterType": "string_in", "values": ["NEW", "IN_PROGRESS"]},
          {"fieldId": "assetCloudRegion", "filterType": "string_in", "values": ["us-east-1", "us-west-2"]}
        ]
        WRONG: filters=[
          {"fieldId": "asset.name", "filterType": "fulltext", "values": ["prod"]},  # Use "assetName" not "asset.name"
          {"fieldId": "evidence.secret.hash", "filterType": "string_equals", "value": "abc123"},  # Use "secretHash" not "evidence.secret.hash"
          {"fieldId": "severity", "filterType": "EQUALS", "value": "CRITICAL"}  # Use "string_equals" not "EQUALS"
        ]
    """
).strip()

GET_MISCONFIGURATION_NOTES_DESCRIPTION: Final[str] = dedent(
    """
    Get all notes and comments associated with a misconfiguration.

    Retrieves all analyst notes, comments, and annotations attached to a specific
    misconfiguration. Notes provide context, analysis findings, remediation steps,
    and collaboration history.

    Args:
        misconfiguration_id: The unique identifier of the misconfiguration.

    Returns:
        List of notes in JSON format, each containing:
        - id: Unique note identifier
        - misconfigurationId: Associated misconfiguration identifier
        - text: Note content/message
        - author: User information {id, email, fullName, deleted}
        - createdAt: ISO timestamp when note was created
        - updatedAt: ISO timestamp when note was last updated (if applicable)

        Notes are typically ordered by creation time (newest first).

    Common Use Cases:
        - Remediation documentation and collaboration
        - Tracking analyst findings and decisions
        - Audit trail for security issue handling
        - Knowledge sharing between security teams
        - Compliance and reporting requirements

    Raises:
        RuntimeError: If there's an error retrieving misconfiguration notes.
        ValueError: If misconfiguration_id is invalid or empty.
    """
).strip()

GET_MISCONFIGURATION_HISTORY_DESCRIPTION: Final[str] = dedent(
    """
    Get the complete audit history and timeline for a misconfiguration.

    Retrieves a chronological record of all actions, status changes, and events
    related to a specific misconfiguration. Provides full audit trail for compliance
    and investigation.

    Args:
        misconfiguration_id: The unique identifier of the misconfiguration.
        first: Number of history events to retrieve (1-100, default: 10).
        after: Pagination cursor from previous response (optional).

    Returns:
        Paginated chronological list in JSON format containing:
        - edges: Array of history events with:
          - eventType: Type of event (CREATION, STATUS, ANALYST_VERDICT, USER_ASSIGNMENT, NOTES, WORKFLOW_ACTION)
          - eventText: Human-readable description of the event
          - createdAt: ISO timestamp when event occurred
        - pageInfo: Pagination metadata (same structure as list_misconfigurations)

    Common Event Types:
        - CREATION: Misconfiguration first detected
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
        - Security posture trend analysis

    Raises:
        RuntimeError: If there's an error retrieving misconfiguration history.
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


def _get_misconfigurations_client() -> MisconfigurationsClient:
    """Get a configured MisconfigurationsClient instance.

    Returns:
        Configured MisconfigurationsClient instance.

    Raises:
        RuntimeError: If settings are not properly configured.
    """
    try:
        settings = get_settings()
    except Exception as e:
        raise RuntimeError(
            f"Settings not initialized. Please check your environment configuration. Error: {e}"
        ) from e

    config = MisconfigurationsConfig(
        graphql_url=settings.misconfigurations_graphql_url,
        auth_token=settings.graphql_service_token,
    )

    return MisconfigurationsClient(config)


# MCP Tool Functions
# TEMPORARY: These functions use Optional[T] instead of T | None for FastMCP compatibility.
# FastMCP's current OpenAI function calling support requires this syntax for proper JSON schema
# generation of optional parameters.
# TODO: Migrate to PEP 604 unions (T | None) once FastMCP supports modern union syntax.


async def get_misconfiguration(misconfiguration_id: str) -> str:
    """Get detailed information about a specific misconfiguration by ID.

    Args:
        misconfiguration_id: The unique identifier of the misconfiguration.

    Returns:
        Detailed misconfiguration information in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving the misconfiguration.
    """
    try:
        client = _get_misconfigurations_client()
        misconfiguration = await client.get_misconfiguration(misconfiguration_id)

        if misconfiguration is None:
            return json.dumps(None, indent=2)

        return misconfiguration.model_dump_json(exclude_none=True, indent=2)

    except Exception as exc:
        logger.exception("Error retrieving misconfiguration")
        raise RuntimeError(f"Failed to retrieve misconfiguration {misconfiguration_id}") from exc


async def list_misconfigurations(
    first: int = 10,
    after: str | None = None,
    view_type: str = "ALL",
    fields: str | None = None,
) -> str:
    """List misconfigurations with pagination and view filtering.

    Args:
        first: Number of misconfigurations to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        view_type: Filter by environment - ALL, CLOUD, KUBERNETES, IDENTITY, etc.
        fields: Optional JSON string containing an array of field names to return.

    Returns:
        Paginated list of misconfigurations in JSON format.

    Raises:
        RuntimeError: If there's an error listing misconfigurations.
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

        client = _get_misconfigurations_client()
        misconfigurations = await client.list_misconfigurations(
            first=first, after=after, view_type=view_type_enum, fields=parsed_fields
        )

        return misconfigurations.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for list_misconfigurations",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error listing misconfigurations")
        raise RuntimeError("Failed to list misconfigurations") from exc


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


async def search_misconfigurations(
    filters: str | None = None,
    first: int = 10,
    after: str | None = None,
    view_type: str = "ALL",
    fields: str | None = None,
) -> str:
    """Search misconfigurations using advanced filters and criteria.

    Args:
        filters: JSON string containing an array of filter objects (optional).
                Each filter object must have fieldId and filterType keys.
        first: Number of misconfigurations to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).
        view_type: Filter by environment - ALL, CLOUD, KUBERNETES, etc.
        fields: Optional JSON string containing an array of field names to return.

    Returns:
        Filtered list of misconfigurations in JSON format.

    Raises:
        RuntimeError: If there's an error searching misconfigurations.
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

        # Parse and validate filters
        parsed_filters = _parse_filters_parameter(filters)

        filter_inputs: list[FilterInput] | None = None
        if parsed_filters:
            _validate_filter_limits(parsed_filters)
            filter_inputs = _convert_filters_to_input(parsed_filters)

        parsed_fields = _parse_fields(fields)

        client = _get_misconfigurations_client()
        misconfigurations = await client.search_misconfigurations(
            filters=filter_inputs,
            first=first,
            after=after,
            view_type=view_type_enum,
            fields=parsed_fields,
        )

        return misconfigurations.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for search_misconfigurations",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error searching misconfigurations")
        raise RuntimeError("Failed to search misconfigurations") from exc


async def get_misconfiguration_notes(misconfiguration_id: str) -> str:
    """Get all notes associated with a misconfiguration.

    Args:
        misconfiguration_id: The unique identifier of the misconfiguration.

    Returns:
        List of notes in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving misconfiguration notes.
        ValueError: If misconfiguration_id is invalid or empty.
    """
    try:
        if not misconfiguration_id or not misconfiguration_id.strip():
            raise ValueError("misconfiguration_id cannot be empty")

        client = _get_misconfigurations_client()
        notes = await client.get_misconfiguration_notes(misconfiguration_id)

        return notes.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for get_misconfiguration_notes",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error retrieving misconfiguration notes")
        raise RuntimeError(
            f"Failed to retrieve notes for misconfiguration {misconfiguration_id}"
        ) from exc


async def get_misconfiguration_history(
    misconfiguration_id: str, first: int = 10, after: str | None = None
) -> str:
    """Get the audit history for a misconfiguration.

    Args:
        misconfiguration_id: The unique identifier of the misconfiguration.
        first: Number of history events to retrieve (1-100, default: 10).
        after: Cursor for pagination (optional).

    Returns:
        Paginated list of history events in JSON format.

    Raises:
        RuntimeError: If there's an error retrieving misconfiguration history.
        ValueError: If parameters are invalid.
    """
    try:
        if not misconfiguration_id or not misconfiguration_id.strip():
            raise ValueError("misconfiguration_id cannot be empty")

        if first < 1 or first > 100:
            raise ValueError("first must be between 1 and 100")

        _validate_cursor(after)

        client = _get_misconfigurations_client()
        history = await client.get_misconfiguration_history(
            misconfiguration_id, first=first, after=after
        )

        return history.model_dump_json(exclude_none=True, indent=2)

    except ValueError:
        logger.warning(
            "Invalid parameters for get_misconfiguration_history",
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.exception("Error retrieving misconfiguration history")
        raise RuntimeError(
            f"Failed to retrieve history for misconfiguration {misconfiguration_id}"
        ) from exc
