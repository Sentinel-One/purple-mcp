# Filter Reference

Comprehensive guide to the alerts library filter system.

## Overview

The alerts library uses a structured filter format with `fieldId` and `filterType` keys. All filters are created using `FilterInput.create_*` methods to ensure type safety and consistency.

## Basic Filter Structure

```python
from purple_mcp.libs.alerts import FilterInput

filter = FilterInput.create_string_equal("severity", "HIGH")
```

## Filter Types

### String Filters

#### String Equality
```python
# Exact match
FilterInput.create_string_equal("severity", "HIGH")

# Negated match (NOT equals)
FilterInput.create_string_equal("severity", "HIGH", is_negated=True)
```

#### String Multiple Values
```python
# IN operation
FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"])

# NOT IN operation  
FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"], is_negated=True)
```

### Integer Filters

#### Integer Equality
```python
# Exact match
FilterInput.create_int_equal("priority", 5)

# Negated match
FilterInput.create_int_equal("priority", 5, is_negated=True)
```

#### Integer Multiple Values
```python
# IN operation
FilterInput.create_int_in("priority", [1, 2, 3])
```

#### Integer Ranges
```python
# Range (inclusive by default)
FilterInput.create_int_range("riskScore", start=50, end=100)

# Greater than (exclusive start)
FilterInput.create_int_range("riskScore", start=50, start_inclusive=False)

# Less than (exclusive end)
FilterInput.create_int_range("riskScore", end=100, end_inclusive=False)

# Open-ended ranges
FilterInput.create_int_range("riskScore", start=50)  # >= 50
FilterInput.create_int_range("riskScore", end=100)   # <= 100
```

### Boolean Filters

```python
# Boolean equality
FilterInput.create_boolean_equal("isResolved", False)

# Negated boolean
FilterInput.create_boolean_equal("isResolved", True, is_negated=True)
```

### DateTime Filters

```python
# DateTime ranges (timestamps in milliseconds since Unix epoch)
start_time = 1640995200000  # 2022-01-01 00:00:00 UTC in ms
end_time = 1672531200000    # 2023-01-01 00:00:00 UTC in ms

# Range filter
FilterInput.create_datetime_range("createdAt", start_ms=start_time, end_ms=end_time)

# After timestamp (exclusive)
FilterInput.create_datetime_range("createdAt", start_ms=start_time, start_inclusive=False)

# Before timestamp (exclusive)
FilterInput.create_datetime_range("createdAt", end_ms=end_time, end_inclusive=False)
```

### Full-Text Search

```python
# Search in text fields
FilterInput.create_fulltext_search("description", ["malware", "suspicious"])

# Negated full-text search
FilterInput.create_fulltext_search("description", ["malware"], is_negated=True)
```

## Complex Filter Examples

### Multiple Filters (AND Logic)
```python
filters = [
    FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"]),
    FilterInput.create_boolean_equal("isResolved", False),
    FilterInput.create_datetime_range("createdAt", start_ms=1640995200000)
]

results = await client.search_alerts(filters=filters, first=20)
```

### Time-Based Filtering
```python
from datetime import datetime, timedelta

# Last 24 hours
yesterday = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
today = int(datetime.now().timestamp() * 1000)

recent_critical_alerts = [
    FilterInput.create_string_equal("severity", "CRITICAL"),
    FilterInput.create_datetime_range("detectedAt", start_ms=yesterday, end_ms=today)
]

results = await client.search_alerts(filters=recent_critical_alerts)
```

### Risk Score Filtering
```python
# High risk alerts (risk score > 80)
high_risk_filters = [
    FilterInput.create_int_range("riskScore", start=80, start_inclusive=False),
    FilterInput.create_boolean_equal("isResolved", False)
]

# Medium risk range (30-70)
medium_risk_filters = [
    FilterInput.create_int_range("riskScore", start=30, end=70)
]
```

### Advanced Text Search
```python
# Search for specific threats
threat_filters = [
    FilterInput.create_fulltext_search("description", ["ransomware", "trojan"]),
    FilterInput.create_string_equal("analystVerdict", "MALICIOUS")
]

# Exclude false positives
excluding_fp = [
    FilterInput.create_string_equal("status", "FALSE_POSITIVE", is_negated=True),
    FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"])
]
```

## Common Filter Patterns

### Unresolved Critical Alerts
```python
unresolved_critical = [
    FilterInput.create_string_equal("severity", "CRITICAL"),
    FilterInput.create_boolean_equal("isResolved", False)
]
```

### Recent Assigned Alerts
```python
from datetime import datetime, timedelta

last_week = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)

recent_assigned = [
    FilterInput.create_datetime_range("assignedAt", start_ms=last_week),
    FilterInput.create_string_equal("assignedTo", "current_user_id")
]
```

### Malware Alerts Pending Review
```python
malware_pending = [
    FilterInput.create_fulltext_search("description", ["malware", "virus", "trojan"]),
    FilterInput.create_string_equal("status", "NEW"),
    FilterInput.create_string_equal("analystVerdict", "INCONCLUSIVE")
]
```

## Filter Field Reference

Common filterable fields in the alerts system:

### Alert Fields
- `severity` - Alert severity level (HIGH, CRITICAL, etc.)
- `status` - Alert status (NEW, IN_PROGRESS, RESOLVED, FALSE_POSITIVE)
- `analystVerdict` - Analyst assessment (MALICIOUS, SUSPICIOUS, BENIGN, INCONCLUSIVE)
- `isResolved` - Boolean resolution status
- `assignedTo` - User ID of assigned analyst
- `priority` - Integer priority value
- `riskScore` - Integer risk assessment (0-100)

### Timestamp Fields
- `createdAt` - Alert creation timestamp
- `detectedAt` - Detection timestamp
- `updatedAt` - Last update timestamp
- `assignedAt` - Assignment timestamp
- `resolvedAt` - Resolution timestamp

### Text Fields (Full-text Search)
- `description` - Alert description text
- `name` - Alert name/title
- `details` - Additional alert details