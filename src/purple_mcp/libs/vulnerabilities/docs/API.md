# API Reference

Complete reference for the Vulnerabilities Library API.

> **📖 Read-Only Library**: This library provides read-only access to the XSPM Vulnerabilities management system. All methods listed below are for reading and retrieving vulnerability data. No data modification operations are included in this library.

## VulnerabilitiesClient

Main client class for interacting with the XSPM Vulnerabilities GraphQL API.

### Constructor
```python
VulnerabilitiesClient(config: VulnerabilitiesConfig)
```

### Vulnerability Operations

#### `get_vulnerability(vulnerability_id: str) -> VulnerabilityDetail | None`
Retrieve a specific vulnerability by ID.

**Parameters:**
- `vulnerability_id` (str): Unique identifier for the vulnerability

**Returns:** VulnerabilityDetail object or None if not found

**Example:**
```python
vulnerability = await client.get_vulnerability("123")
if vulnerability:
    print(f"Vulnerability: {vulnerability.name} - Severity: {vulnerability.severity}")
```

#### `list_vulnerabilities(first: int = 10, after: str | None = None, fields: list[str] | None = None) -> VulnerabilityConnection`
List vulnerabilities with pagination.

**Parameters:**
- `first` (int): Number of vulnerabilities to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination
- `fields` (list[str], optional): List of field names to return. If None, returns all default fields. Use `["id"]` for efficient pagination.

**Returns:** VulnerabilityConnection with paginated results

**Note:** When using custom field selection, only requested fields will be populated in the Vulnerability model. All non-ID fields are optional to support this feature.

**Example:**
```python
vulnerabilities = await client.list_vulnerabilities(first=20)
print(f"Found {len(vulnerabilities.edges)} vulnerabilities")

# Efficient pagination
vulnerabilities = await client.list_vulnerabilities(first=100, fields=["id"])
```

#### `search_vulnerabilities(filters: list[FilterInput] | None = None, first: int = 10, after: str | None = None, fields: list[str] | None = None) -> VulnerabilityConnection`
Search vulnerabilities with filters.

**Parameters:**
- `filters` (list[FilterInput], optional): Search filters (max 50 filters, max 100 values per filter)
- `first` (int): Number of vulnerabilities to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination
- `fields` (list[str], optional): List of field names to return. If None, returns all default fields.

**Returns:** VulnerabilityConnection with filtered results

**Note:** When using custom field selection, only requested fields will be populated in the Vulnerability model. All non-ID fields are optional to support this feature.

**Example:**
```python
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
results = await client.search_vulnerabilities(filters=filters, first=10)
```

### Note Operations

#### `get_vulnerability_notes(vulnerability_id: str) -> list[VulnerabilityNote]`
Get notes for a vulnerability.

**Parameters:**
- `vulnerability_id` (str): Unique identifier for the vulnerability

**Returns:** List of VulnerabilityNote objects

**Example:**
```python
notes = await client.get_vulnerability_notes("123")
for note in notes:
    print(f"{note.created_at}: {note.text}")
```

### History Operations

#### `get_vulnerability_history(vulnerability_id: str, first: int = 10, after: str | None = None) -> VulnerabilityHistoryItemConnection`
Get history events for a vulnerability.

**Parameters:**
- `vulnerability_id` (str): Unique identifier for the vulnerability
- `first` (int): Number of history events to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination

**Returns:** VulnerabilityHistoryItemConnection with paginated history

**Example:**
```python
history = await client.get_vulnerability_history("123", first=20)
for edge in history.edges:
    event = edge.node
    print(f"{event.event_type} at {event.created_at}")
```

## VulnerabilitiesConfig

Configuration class for the vulnerabilities client.

### Fields
- `graphql_url: str` - GraphQL endpoint URL for XSPM Vulnerabilities
- `auth_token: str` - Bearer token for authentication
- `timeout: float = 30.0` - Request timeout in seconds

### Example
```python
config = VulnerabilitiesConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token="your-bearer-token",
    timeout=45.0
)
```

## Data Models

### Core Models
- `Vulnerability` - Main vulnerability object with all fields
- `VulnerabilityDetail` - Detailed vulnerability information including CVE details
- `VulnerabilityConnection` - Paginated connection for vulnerabilities
- `VulnerabilityNote` - Note attached to a vulnerability
- `VulnerabilityHistoryItem` - Historical event for a vulnerability

### CVE Models
- `Cve` - CVE (Common Vulnerabilities and Exposures) information
- `CveDetail` - Detailed CVE information including CVSS scores
- `CveTimelineItem` - CVE timeline events

### Supporting Models
- `Asset` - Asset information
- `Account` - Account details
- `Group` - Group information
- `Site` - Site details
- `User` - User information
- `Software` - Software package information
- `CloudInfo` - Cloud-specific metadata
- `KubernetesInfo` - Kubernetes-specific metadata

### Risk Assessment Models
- `RiskIndicators` - Risk assessment indicators
- `S1BaseValues` - SentinelOne base risk values
- `ExploitMaturity` - Exploit maturity level
- `RemediationLevel` - Remediation availability level
- `ReportConfidence` - Report confidence level

### Enums
- `VulnerabilitySeverity` - LOW, MEDIUM, HIGH, CRITICAL
- `Status` - OPEN, IN_PROGRESS, RESOLVED, DISMISSED
- `AnalystVerdict` - VALID, INVALID, IN_REVIEW
- `AssetCriticality` - LOW, MEDIUM, HIGH, CRITICAL
- `HistoryEventType` - Various event types (STATUS_CHANGE, NOTE_ADDED, etc.)
- `OsType` - WINDOWS, LINUX, MACOS, etc.
- `SoftwareType` - APPLICATION, SYSTEM, LIBRARY, etc.
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

- `VulnerabilitiesError` - Base exception for all vulnerabilities-related errors
- `VulnerabilitiesConfigError` - Configuration-related errors
- `VulnerabilitiesClientError` - HTTP/network errors (includes status codes)
- `VulnerabilitiesGraphQLError` - GraphQL-specific errors (includes GraphQL error details)
- `VulnerabilitiesSchemaError` - Schema compatibility errors

### Example Error Handling

```python
from purple_mcp.libs.vulnerabilities.exceptions import (
    VulnerabilitiesClientError,
    VulnerabilitiesGraphQLError,
    VulnerabilitiesConfigError
)

try:
    vulnerability = await client.get_vulnerability("invalid-id")
except VulnerabilitiesClientError as e:
    print(f"Network error: {e} (Status: {e.status_code})")
except VulnerabilitiesGraphQLError as e:
    print(f"GraphQL error: {e}")
    print(f"Details: {e.graphql_errors}")
except VulnerabilitiesConfigError as e:
    print(f"Configuration error: {e}")
```

## Filter DoS Protection

The library includes built-in protection against Denial of Service attacks through filters:

- **Maximum 50 filters per request** - Prevents filter-based DoS
- **Maximum 100 values per filter** - Prevents value-based DoS

These limits are enforced automatically and will raise `ValueError` if exceeded.

## Pagination

The library uses cursor-based GraphQL pagination:

```python
# First page
page1 = await client.list_vulnerabilities(first=20)

# Next page using end cursor
if page1.page_info.has_next_page:
    page2 = await client.list_vulnerabilities(
        first=20,
        after=page1.page_info.end_cursor
    )
```

### Pagination Info
The `VulnerabilityConnection` includes:
- `edges: list[VulnerabilityEdge]` - List of vulnerability edges
- `page_info: PageInfo` - Pagination metadata including:
  - `has_next_page: bool` - Whether more pages exist
  - `end_cursor: str | None` - Cursor for next page
