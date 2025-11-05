# Usage Guide

Comprehensive usage examples and patterns for the Alerts Library.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Alerts Management system. All examples below demonstrate data retrieval and analysis operations.

## Basic Operations

### Getting Started
```python
import asyncio
from purple_mcp.libs.alerts import AlertsClient, AlertsConfig

async def main():
    config = AlertsConfig(
        graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
        auth_token="your-bearer-token"
    )
    
    client = AlertsClient(config)
    
    # Your alert operations here
    
asyncio.run(main())
```

### Retrieving Alerts

#### Get a Specific Alert
```python
async def get_alert_details(client: AlertsClient, alert_id: str):
    alert = await client.get_alert(alert_id)
    if alert:
        print(f"Alert: {alert.name}")
        print(f"Severity: {alert.severity}")
        print(f"Status: {alert.status}")
        print(f"Detected: {alert.detected_at}")
    else:
        print("Alert not found")
```

#### List Recent Alerts
```python
async def list_recent_alerts(client: AlertsClient):
    alerts = await client.list_alerts(first=10, view_type=ViewType.ALL)
    
    print(f"Found {len(alerts.edges)} alerts")
    for edge in alerts.edges:
        alert = edge.node
        print(f"- {alert.name} ({alert.severity})")
```

### Searching with Filters

#### Basic Filter Search
```python
from purple_mcp.libs.alerts import FilterInput

async def search_high_severity_alerts(client: AlertsClient):
    filters = [
        FilterInput.create_string_equal("severity", "HIGH")
    ]
    
    results = await client.search_alerts(filters=filters, first=5)
    return [edge.node for edge in results.edges]
```

#### Complex Filter Search
```python
async def search_unresolved_critical_alerts(client: AlertsClient):
    filters = [
        FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"]),
        FilterInput.create_string_in("status", ["NEW", "IN_PROGRESS"])
    ]

    results = await client.search_alerts(filters=filters, first=20)
    return results
```

## Dynamic Field Selection

### Overview

The alerts library supports dynamic field selection to reduce token usage and improve performance when paging through large result sets. This feature allows you to specify exactly which fields you want returned in the query response.

### Benefits

- **Reduced Context Window Usage**: Request only the fields you need during pagination
- **Improved Performance**: Smaller responses mean faster processing
- **Flexible Data Retrieval**: Different use cases can request different field sets

### Available Fields

Basic fields:
- `id`, `externalId`, `severity`, `status`, `name`, `description`
- `detectedAt`, `firstSeenAt`, `lastSeenAt`
- `analystVerdict`, `classification`, `confidenceLevel`
- `noteExists`, `result`, `storylineId`, `ticketId`

Nested object fields:
- `detectionSource` - Auto-expands to `detectionSource { product vendor }`
- `asset` - Auto-expands to `asset { id name type }`
- `assignee` - Auto-expands to `assignee { userId email fullName }`

Special scalar field:
- `dataSources` - Returns a list of string identifiers. Available only when the server reports `supports_data_sources=True`.

**Note**: You can use either the simple name (e.g., `"asset"`) which auto-expands to all subfields,
or provide an explicit fragment (e.g., `"asset { id }"`) for precise control.

**Nested Fragments**: Custom fragments support arbitrary nesting depth. You can request deeply nested
fields like `"asset { cloudInfo { accountId region } }"` or complex structures like
`"scope { account { id name } site { id name } }"`. All braces must be balanced and field names must
follow GraphQL identifier rules.

### Usage Examples

#### Default Behavior (All Fields)
```python
async def list_all_fields(client: AlertsClient):
    # Omit fields parameter or pass None to get all fields
    alerts = await client.list_alerts(first=10)
    # Returns all 17+ fields
```

#### Minimal Fields for Pagination
```python
async def page_to_position_1532(client: AlertsClient):
    """Efficiently page through intermediate results using minimal fields."""
    cursor = None
    for page in range(153):
        # Request only ID field for intermediate pages to conserve context window
        alerts = await client.list_alerts(
            first=10,
            after=cursor,
            fields=["id"]
        )
        cursor = alerts.pageInfo.endCursor

        if not alerts.pageInfo.hasNextPage:
            break

    # Now get the actual data with all fields
    final_alerts = await client.list_alerts(first=10, after=cursor)
    return final_alerts
```

#### Summary View for Dashboards
```python
async def get_alert_summary(client: AlertsClient):
    """Get a lightweight summary view of alerts."""
    alerts = await client.list_alerts(
        first=20,
        fields=["id", "severity", "status", "name", "detectedAt"]
    )

    for edge in alerts.edges:
        alert = edge.node
        print(f"{alert.id}: {alert.name} - {alert.severity}")
```

#### Custom Field Selection with Filters
```python
async def search_with_custom_fields(client: AlertsClient):
    """Search alerts with custom field selection."""
    filters = [
        FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"])
    ]

    # Request only fields needed for analysis
    results = await client.search_alerts(
        filters=filters,
        first=50,
        fields=[
            "id",
            "severity",
            "status",
            "name",
            "asset",  # Auto-expands to "asset { id name type }"
            "detectedAt"
        ]
    )
    return results
```

### Performance Comparison

**Without field selection** (default):
- Returns ~17 fields + nested objects per alert
- 10 alerts = ~5-10KB response

**With minimal field selection** (`fields=["id"]`):
- Returns only 1 field per alert
- 10 alerts = ~500 bytes response
- **~90% reduction in response size**

### Best Practices

1. **Use minimal fields for pagination**: When paging through many results, use `fields=["id"]` for intermediate pages
2. **Request full details when needed**: Omit the fields parameter or pass `None` when you need complete alert data
3. **Tailor fields to use case**: Dashboard views need different fields than detailed investigation
4. **Use simple names for nested objects**: Specify `"asset"` to auto-expand to all asset subfields
5. **Use explicit fragments for precise control**: Use custom fragments like `"asset { id }"` for specific fields or `"asset { cloudInfo { accountId } }"` for deeply nested structures
6. **Empty list handling**: Passing `fields=[]` is automatically coerced to `fields=["id"]` to ensure valid GraphQL queries
7. **Conditional fields**: The `"dataSources"` fragment is only available when the backend advertises support (see `AlertsConfig.supports_data_sources`). Requesting it on older schemas will raise a validation error.

## Reading Alert Notes

### Getting Alert Notes
```python
async def get_alert_notes(client: AlertsClient, alert_id: str):
    notes = await client.get_alert_notes(alert_id, first=10)
    
    print(f"Alert has {len(notes.edges)} notes:")
    for edge in notes.edges:
        note = edge.node
        print(f"- {note.created_at}: {note.text}")
        print(f"  By: {note.created_by}")
```

### Viewing Existing Notes
```python
async def view_all_alert_notes(client: AlertsClient, alert_id: str):
    # Get all notes with pagination
    all_notes = []
    cursor = None
    
    while True:
        notes = await client.get_alert_notes(alert_id, first=50, after=cursor)
        all_notes.extend([edge.node for edge in notes.edges])
        
        if not notes.page_info.has_next_page:
            break
        cursor = notes.page_info.end_cursor
    
    print(f"Alert has {len(all_notes)} total notes")
    return all_notes
```

## Working with Alert History

### Viewing Alert History
```python
async def view_alert_history(client: AlertsClient, alert_id: str):
    history = await client.get_alert_history(alert_id, first=20)

    print(f"Alert history ({len(history.edges)} events):")
    for edge in history.edges:
        event = edge.node
        print(f"- {event.created_at}: {event.event_type}")
        print(f"  {event.event_text}")
        if event.history_item_creator:
            print(f"  By: {event.history_item_creator.user_id} ({event.history_item_creator.user_type})")
        else:
            print(f"  By: System")
        if event.report_url:
            print(f"  Report: {event.report_url}")
```

### Tracking Status Changes
```python
async def track_alert_progression(client: AlertsClient, alert_id: str):
    history = await client.get_alert_history(alert_id, first=50)

    status_changes = []
    for edge in history.edges:
        event = edge.node
        if "STATUS" in event.event_type:
            status_changes.append({
                'timestamp': event.created_at,
                'event_type': event.event_type,
                'description': event.event_text,
                'user': event.history_item_creator.user_id if event.history_item_creator else 'System'
            })

    print(f"Found {len(status_changes)} status changes")
    return status_changes
```

## Pagination Patterns

### Basic Pagination
```python
async def paginate_through_alerts(client: AlertsClient):
    all_alerts = []
    cursor = None
    
    while True:
        connection = await client.list_alerts(first=50, after=cursor)
        all_alerts.extend([edge.node for edge in connection.edges])
        
        print(f"Fetched {len(connection.edges)} alerts (total: {len(all_alerts)})")
        
        if not connection.page_info.has_next_page:
            break
        cursor = connection.page_info.end_cursor
    
    return all_alerts
```

### Filtered Pagination
```python
async def paginate_high_severity_alerts(client: AlertsClient):
    filters = [
        FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"])
    ]
    
    all_high_severity = []
    cursor = None
    
    while True:
        results = await client.search_alerts(
            filters=filters,
            first=50,
            after=cursor
        )
        
        all_high_severity.extend([edge.node for edge in results.edges])
        
        if not results.page_info.has_next_page:
            break
        cursor = results.page_info.end_cursor
    
    return all_high_severity
```

## Advanced Patterns

### Bulk Analysis

```python
async def analyze_high_severity_alerts(client: AlertsClient):
    """Example of analyzing multiple alerts in bulk."""
    filters = [
        FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"]),
        FilterInput.create_boolean_equal("isResolved", False)
    ]
    
    cursor = None
    analyzed_alerts = []
    
    while True:
        results = await client.search_alerts(
            filters=filters,
            first=50,
            after=cursor
        )
        
        # Analyze each alert
        for edge in results.edges:
            alert = edge.node
            
            # Collect analysis data
            analysis = {
                "id": alert.id,
                "name": alert.name,
                "severity": alert.severity,
                "detected_at": alert.detected_at,
                "has_notes": alert.note_exists,
            }
            analyzed_alerts.append(analysis)
            print(f"Analyzed alert {alert.id}")
        
        if not results.page_info.has_next_page:
            break
        cursor = results.page_info.end_cursor
    
    print(f"Analyzed {len(analyzed_alerts)} high severity alerts")
    return analyzed_alerts
```

### Time-Based Analysis
```python
from datetime import datetime, timedelta

async def analyze_recent_alert_trends(client: AlertsClient):
    """Analyze alert trends over the last 7 days."""
    
    # Get timestamps for last 7 days
    now = datetime.now()
    days_ago_7 = now - timedelta(days=7)
    
    timestamp_7d = int(days_ago_7.timestamp() * 1000)
    timestamp_now = int(now.timestamp() * 1000)
    
    # Get all alerts from last 7 days
    filters = [
        FilterInput.create_datetime_range(
            "createdAt",
            start_ms=timestamp_7d,
            end_ms=timestamp_now
        )
    ]
    
    # Collect all alerts
    all_recent_alerts = []
    cursor = None
    
    while True:
        results = await client.search_alerts(
            filters=filters,
            first=100,
            after=cursor
        )
        
        all_recent_alerts.extend([edge.node for edge in results.edges])
        
        if not results.page_info.has_next_page:
            break
        cursor = results.page_info.end_cursor
    
    # Analyze trends
    severity_counts = {}
    for alert in all_recent_alerts:
        severity = alert.severity
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    print(f"Alert trends (last 7 days):")
    print(f"Total alerts: {len(all_recent_alerts)}")
    for severity, count in severity_counts.items():
        print(f"- {severity}: {count}")
    
    return {
        'total': len(all_recent_alerts),
        'by_severity': severity_counts,
        'alerts': all_recent_alerts
    }
```



## Error Handling Patterns

### Comprehensive Error Handling
```python
from purple_mcp.libs.alerts.exceptions import (
    AlertsClientError, 
    AlertsGraphQLError, 
    AlertsConfigError,
    AlertsSchemaError
)

async def robust_alert_retrieval(client: AlertsClient, alert_id: str):
    try:
        alert = await client.get_alert(alert_id)
        return alert
        
    except AlertsClientError as e:
        print(f"Network/HTTP error: {e}")
        print(f"Status code: {e.status_code}")
        return None
        
    except AlertsGraphQLError as e:
        print(f"GraphQL error: {e}")
        print(f"GraphQL details: {e.graphql_errors}")
        return None
        
    except AlertsSchemaError as e:
        print(f"Schema compatibility error: {e}")
        # Could retry with different schema settings
        return None
        
    except AlertsConfigError as e:
        print(f"Configuration error: {e}")
        return None
```

### Retry with Exponential Backoff
```python
import asyncio
from typing import Optional

async def resilient_alert_fetch(
    client: AlertsClient, 
    alert_id: str, 
    max_retries: int = 3
) -> Optional[Alert]:
    """Fetch alert with retry logic and exponential backoff."""
    
    for attempt in range(max_retries):
        try:
            alert = await client.get_alert(alert_id)
            return alert
            
        except AlertsClientError as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return None
            
            # Exponential backoff
            delay = 2 ** attempt
            print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            await asyncio.sleep(delay)
            
        except AlertsGraphQLError:
            # Don't retry GraphQL errors
            return None
    
    return None
```

## Testing Patterns

### Mock Testing Setup
```python
from unittest.mock import AsyncMock, patch

async def test_alert_operations():
    """Example of how to test alerts operations."""
    
    config = AlertsConfig(
        graphql_url="https://test.example.com/graphql",
        auth_token="test-token"
    )
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        # Mock successful response
        mock_post.return_value.json.return_value = {
            "data": {
                "alert": {
                    "id": "123",
                    "name": "Test Alert",
                    "severity": "HIGH"
                }
            }
        }
        
        client = AlertsClient(config)
        alert = await client.get_alert("123")
        
        assert alert is not None
        assert alert.id == "123"
        assert alert.name == "Test Alert"
        assert alert.severity == "HIGH"
```
