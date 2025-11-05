# API Reference

Complete reference for the Alerts Library API.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Alerts Management system. All methods listed below are for reading and retrieving alert data. No data modification operations are included in this library.

## AlertsClient

Main client class for interacting with the UAM API.

### Constructor
```python
AlertsClient(config: AlertsConfig)
```

### Alert Operations

#### `get_alert(alert_id: str) -> Alert | None`
Retrieve a specific alert by ID.

**Parameters:**
- `alert_id` (str): Unique identifier for the alert

**Returns:** Alert object or None if not found

#### `list_alerts(first: int = 10, after: str | None = None, view_type: ViewType = ViewType.ALL, fields: list[str] | None = None) -> AlertConnection`
List alerts with pagination.

**Parameters:**
- `first` (int): Number of alerts to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination
- `view_type` (ViewType): Filter by view type (default: ALL)
- `fields` (list[str], optional): List of field names to return. If None, returns all default fields. Use `["id"]` for efficient pagination.

**Returns:** AlertConnection with paginated results

**Note:** When using custom field selection, only requested fields will be populated in the Alert model. All non-ID fields are optional to support this feature.

#### `search_alerts(filters: list[FilterInput] | None = None, first: int = 10, after: str | None = None, view_type: ViewType = ViewType.ALL, fields: list[str] | None = None) -> AlertConnection`
Search alerts with filters.

**Parameters:**
- `filters` (list[FilterInput], optional): Search filters
- `first` (int): Number of alerts to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination
- `view_type` (ViewType): Filter by view type (default: ALL)
- `fields` (list[str], optional): List of field names to return. If None, returns all default fields.

**Returns:** AlertConnection with filtered results

**Note:** When using custom field selection, only requested fields will be populated in the Alert model. All non-ID fields are optional to support this feature.

### Note Operations

#### `get_alert_notes(alert_id: str, first: int = 10, after: str | None = None) -> AlertNoteConnection`
Get notes for an alert.

**Parameters:**
- `alert_id` (str): Unique identifier for the alert
- `first` (int): Number of notes to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination

**Returns:** AlertNoteConnection with paginated notes



### History Operations

#### `get_alert_history(alert_id: str, first: int = 10, after: str | None = None) -> AlertHistoryConnection`
Get history events for an alert.

**Parameters:**
- `alert_id` (str): Unique identifier for the alert
- `first` (int): Number of history events to retrieve (default: 10)
- `after` (str, optional): Cursor for pagination

**Returns:** AlertHistoryConnection with paginated history



## AlertsConfig

Configuration class for the alerts client.

### Fields
- `graphql_url: str` - GraphQL endpoint URL for UAM
- `auth_token: str` - Bearer token for authentication  
- `timeout: float = 30.0` - Request timeout in seconds
- `supports_view_type: bool = True` - Schema compatibility flag for viewType parameter
- `supports_data_sources: bool = True` - Schema compatibility flag for dataSources field

## Data Models

### Core Models
- `Alert` - Main alert object with all fields
- `AlertConnection` - Paginated connection for alerts
- `AlertNote` - Note attached to an alert
- `AlertHistoryEvent` - Historical event for an alert
- `Asset` - Asset information
- `DetectionSource` - Detection source details
- `User` - User/assignee information

### Enums
- `Severity` - LOW, MEDIUM, HIGH, CRITICAL
- `Status` - NEW, IN_PROGRESS, RESOLVED, FALSE_POSITIVE
- `ViewType` - ALL, ASSIGNED_TO_ME, UNASSIGNED, MY_TEAM
- `AnalystVerdict` - MALICIOUS, SUSPICIOUS, BENIGN, INCONCLUSIVE

### Filter Models
- `FilterInput` - Input filter for searches
- `PageInfo` - Pagination information

## Exception Hierarchy

- `AlertsError` - Base exception for all alerts-related errors
- `AlertsConfigError` - Configuration-related errors  
- `AlertsClientError` - HTTP/network errors (includes status codes)
- `AlertsGraphQLError` - GraphQL-specific errors (includes GraphQL error details)
- `AlertsSchemaError` - Schema compatibility errors

### Example Error Handling

```python
from purple_mcp.libs.alerts.exceptions import AlertsClientError, AlertsGraphQLError

try:
    alert = await client.get_alert("invalid-id")
except AlertsClientError as e:
    print(f"Network error: {e} (Status: {e.status_code})")
except AlertsGraphQLError as e:
    print(f"GraphQL error: {e}")
    print(f"Details: {e.graphql_errors}")
```