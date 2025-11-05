# API Reference

Complete reference for the Misconfigurations Library API.

> **📖 Read-Only Library**: This library provides read-only access to the XSPM Misconfigurations management system. All methods listed below are for reading and retrieving misconfiguration data. No data modification operations are included in this library.

## MisconfigurationsClient

Main client class for interacting with the XSPM Misconfigurations GraphQL API.

### Constructor
```python
MisconfigurationsClient(config: MisconfigurationsConfig)
```

### Misconfiguration Operations

#### `get_misconfiguration(misconfiguration_id: str) -> MisconfigurationDetail | None`
Retrieve a specific misconfiguration by ID.

**Parameters:**
- `misconfiguration_id` (str): Unique identifier for the misconfiguration

**Returns:** MisconfigurationDetail object or None if not found

**Example:**
```python
misconfiguration = await client.get_misconfiguration("123")
if misconfiguration:
    print(f"Misconfiguration: {misconfiguration.name} - Severity: {misconfiguration.severity}")
```

#### `list_misconfigurations(first: int = 10, after: str | None = None, view_type: str = "ALL", fields: list[str] | None = None) -> MisconfigurationConnection`
List misconfigurations with pagination.

**Parameters:**
- `first` (int): Number of misconfigurations to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination
- `view_type` (str): Filter by view type (default: "ALL")
- `fields` (list[str], optional): List of field names to return. If None, returns all default fields. Use `["id"]` for efficient pagination.

**Returns:** MisconfigurationConnection with paginated results

**Note:** When using custom field selection, only requested fields will be populated in the Misconfiguration model. All non-ID fields are optional to support this feature.

**Example:**
```python
misconfigurations = await client.list_misconfigurations(first=20)
print(f"Found {len(misconfigurations.edges)} misconfigurations")

# Efficient pagination
misconfigurations = await client.list_misconfigurations(first=100, fields=["id"])
```

#### `search_misconfigurations(filters: list[FilterInput] | None = None, first: int = 10, after: str | None = None, view_type: str = "ALL", fields: list[str] | None = None) -> MisconfigurationConnection`
Search misconfigurations with filters.

**Parameters:**
- `filters` (list[FilterInput], optional): Search filters (max 50 filters, max 100 values per filter)
- `first` (int): Number of misconfigurations to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination
- `view_type` (str): Filter by view type (default: "ALL")
- `fields` (list[str], optional): List of field names to return. If None, returns all default fields.

**Returns:** MisconfigurationConnection with filtered results

**Note:** When using custom field selection, only requested fields will be populated in the Misconfiguration model. All non-ID fields are optional to support this feature.

**Example:**
```python
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
results = await client.search_misconfigurations(filters=filters, first=10)
```

### Note Operations

#### `get_misconfiguration_notes(misconfiguration_id: str) -> list[MisconfigurationNote]`
Get notes for a misconfiguration.

**Parameters:**
- `misconfiguration_id` (str): Unique identifier for the misconfiguration

**Returns:** List of MisconfigurationNote objects

**Example:**
```python
notes = await client.get_misconfiguration_notes("123")
for note in notes:
    print(f"{note.created_at}: {note.text}")
```

### History Operations

#### `get_misconfiguration_history(misconfiguration_id: str, first: int = 10, after: str | None = None) -> MisconfigurationHistoryItemConnection`
Get history events for a misconfiguration.

**Parameters:**
- `misconfiguration_id` (str): Unique identifier for the misconfiguration
- `first` (int): Number of history events to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination

**Returns:** MisconfigurationHistoryItemConnection with paginated history

**Example:**
```python
history = await client.get_misconfiguration_history("123", first=20)
for edge in history.edges:
    event = edge.node
    print(f"{event.event_type} at {event.created_at}")
```

## MisconfigurationsConfig

Configuration class for the misconfigurations client.

### Fields
- `graphql_url: str` - GraphQL endpoint URL for XSPM Misconfigurations
- `auth_token: str` - Bearer token for authentication
- `timeout: float = 30.0` - Request timeout in seconds

### Example
```python
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="your-bearer-token",
    timeout=45.0
)
```

## Data Models

### Core Models
- `Misconfiguration` - Main misconfiguration object with all fields
- `MisconfigurationDetail` - Detailed misconfiguration information
- `MisconfigurationConnection` - Paginated connection for misconfigurations
- `MisconfigurationNote` - Note attached to a misconfiguration
- `MisconfigurationHistoryItem` - Historical event for a misconfiguration

### Supporting Models
- `Asset` - Asset information
- `Account` - Account details
- `Group` - Group information
- `Site` - Site details
- `User` - User information
- `Policy` - Policy details
- `PolicyDetail` - Detailed policy information
- `Compliance` - Compliance framework information
- `Evidence` - Evidence supporting the misconfiguration
- `Remediation` - Remediation guidance
- `KbArticle` - Knowledge base article
- `MitreAttack` - MITRE ATT&CK information
- `CloudInfo` - Cloud-specific metadata
- `KubernetesInfo` - Kubernetes-specific metadata
- `Cnapp` - CNAPP-related information
- `AdmissionRequest` - Admission request details

### Enums
- `MisconfigurationSeverity` - LOW, MEDIUM, HIGH, CRITICAL
- `Status` - OPEN, IN_PROGRESS, RESOLVED, DISMISSED
- `AnalystVerdict` - VALID, INVALID, IN_REVIEW
- `AssetCriticality` - LOW, MEDIUM, HIGH, CRITICAL
- `ComplianceStatus` - COMPLIANT, NON_COMPLIANT, NOT_APPLICABLE
- `HistoryEventType` - Various event types (STATUS_CHANGE, NOTE_ADDED, etc.)
- `EnforcementAction` - ALLOW, DENY, AUDIT
- `OsType` - WINDOWS, LINUX, MACOS, etc.
- `AssetScopeLevel` - ACCOUNT, SITE, GROUP, GLOBAL

### Filter Models
- `FilterInput` - Input filter for searches
- `EqualFilterStringInput` - String equality filter
- `EqualFilterIntegerInput` - Integer equality filter
- `EqualFilterLongInput` - Long equality filter
- `EqualFilterBooleanInput` - Boolean equality filter
- `InFilterStringInput` - String IN filter
- `InFilterIntegerInput` - Integer IN filter
- `InFilterLongInput` - Long IN filter
- `InFilterBooleanInput` - Boolean IN filter
- `RangeFilterIntegerInput` - Integer range filter
- `RangeFilterLongInput` - Long range filter
- `FulltextFilterInput` - Full-text search filter
- `AndFilterSelectionInput` - AND logic filter
- `OrFilterSelectionInput` - OR logic filter
- `PageInfo` - Pagination information

## Exception Hierarchy

- `MisconfigurationsError` - Base exception for all misconfigurations-related errors
- `MisconfigurationsConfigError` - Configuration-related errors
- `MisconfigurationsClientError` - HTTP/network errors (includes status codes)
- `MisconfigurationsGraphQLError` - GraphQL-specific errors (includes GraphQL error details)
- `MisconfigurationsSchemaError` - Schema compatibility errors

### Example Error Handling

```python
from purple_mcp.libs.misconfigurations.exceptions import (
    MisconfigurationsClientError,
    MisconfigurationsGraphQLError,
    MisconfigurationsConfigError
)

try:
    misconfiguration = await client.get_misconfiguration("invalid-id")
except MisconfigurationsClientError as e:
    print(f"Network error: {e} (Status: {e.status_code})")
except MisconfigurationsGraphQLError as e:
    print(f"GraphQL error: {e}")
    print(f"Details: {e.graphql_errors}")
except MisconfigurationsConfigError as e:
    print(f"Configuration error: {e}")
```

## Filter DoS Protection

The library includes built-in protection against Denial of Service attacks through filters:

- **Maximum 50 filters per request** - Prevents filter-based DoS
- **Maximum 100 values per filter** - Prevents value-based DoS

These limits are enforced automatically and will raise `ValueError` if exceeded:

```python
# ✅ Acceptable
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}
] * 50  # Exactly at limit

# ❌ Will raise ValueError
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}
] * 51  # Exceeds limit
```

## Pagination

The library uses cursor-based GraphQL pagination:

```python
# First page
page1 = await client.list_misconfigurations(first=20)

# Next page using end cursor
if page1.page_info.has_next_page:
    page2 = await client.list_misconfigurations(
        first=20,
        after=page1.page_info.end_cursor
    )
```

### Pagination Info
The `MisconfigurationConnection` includes:
- `edges: list[MisconfigurationEdge]` - List of misconfiguration edges
- `page_info: PageInfo` - Pagination metadata including:
  - `has_next_page: bool` - Whether more pages exist
  - `end_cursor: str | None` - Cursor for next page
