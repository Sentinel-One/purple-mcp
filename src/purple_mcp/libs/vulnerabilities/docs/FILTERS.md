# Filter Reference

Comprehensive guide to the vulnerabilities library filter system.

## Overview

The vulnerabilities library uses a structured GraphQL filter format with `fieldId` and `filterType` keys. The library includes built-in DoS protection with maximum limits on filter counts and values.

## DoS Protection

- **Maximum 50 filters per request**
- **Maximum 100 values per filter**

## Basic Filter Structure

```python
# Single filter
filter = {
    "fieldId": "severity",
    "filterType": "string_equals",
    "value": "CRITICAL"
}

# Multiple filters (AND logic)
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]

results = await client.search_vulnerabilities(filters=filters, first=10)
```

## Filter Types

### String Filters

#### String Equality
```python
{"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}
{"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
```

#### String Contains
```python
{"fieldId": "cveName", "filterType": "string_contains", "value": "CVE-2024"}
{"fieldId": "softwareName", "filterType": "string_contains", "value": "Apache"}
```

### Boolean Filters

```python
{"fieldId": "hasExploit", "filterType": "boolean_equals", "value": True}
{"fieldId": "isPatchAvailable", "filterType": "boolean_equals", "value": False}
```

## Common Filter Patterns

### By Severity
```python
# Critical only
critical = [{"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}]

# High and Critical
high_critical = [
    {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH", "CRITICAL"]}
]
```

### By Status
```python
# Open vulnerabilities
open_vulns = [{"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}]

# Resolved
resolved = [{"fieldId": "status", "filterType": "string_equals", "value": "RESOLVED"}]
```

### By CVE
```python
# Specific CVE
specific_cve = [{"fieldId": "cveName", "filterType": "string_equals", "value": "CVE-2024-1234"}]

# CVEs from specific year
year_2024 = [{"fieldId": "cveName", "filterType": "string_contains", "value": "CVE-2024"}]
```

### By Exploit Status
```python
# Has known exploit
with_exploit = [
    {"fieldId": "hasExploit", "filterType": "boolean_equals", "value": True},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
```

### By Asset
```python
# Specific asset type
asset_type = [{"fieldId": "assetType", "filterType": "string_equals", "value": "SERVER"}]

# High criticality assets
critical_assets = [
    {"fieldId": "assetCriticality", "filterType": "string_equals", "value": "CRITICAL"}
]
```

## Complex Filter Examples

### Critical Open Vulnerabilities with Exploits
```python
critical_exploitable = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"},
    {"fieldId": "hasExploit", "filterType": "boolean_equals", "value": True}
]
```

### Unpatched High/Critical Vulnerabilities
```python
unpatched_high = [
    {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH", "CRITICAL"]},
    {"fieldId": "isPatchAvailable", "filterType": "boolean_equals", "value": False},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
```

## Filter Field Reference

Common filterable fields:

### Vulnerability Fields
- `severity` - Vulnerability severity (LOW, MEDIUM, HIGH, CRITICAL)
- `status` - Current status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED)
- `cveName` - CVE identifier
- `hasExploit` - Whether exploit exists
- `isPatchAvailable` - Whether patch is available

### Asset Fields
- `assetName` - Name of affected asset
- `assetType` - Type of asset
- `assetCriticality` - Asset criticality level

### Software Fields
- `softwareName` - Name of vulnerable software
- `softwareVersion` - Software version
- `softwareType` - Type of software (APPLICATION, SYSTEM, LIBRARY)

### Risk Fields
- `cvssScore` - CVSS base score
- `exploitMaturity` - Exploit maturity level
- `remediationLevel` - Remediation availability

## Best Practices

### 1. Use Specific Filters
```python
# ✅ Good
specific = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
    {"fieldId": "hasExploit", "filterType": "boolean_equals", "value": True},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
```

### 2. Respect DoS Protection Limits
```python
# ✅ Within limits (50 filters max)
filters = [{"fieldId": f"field{i}", "filterType": "string_equals", "value": "value"} for i in range(50)]

# ❌ Exceeds limits - will raise ValueError
too_many = [{"fieldId": f"field{i}", "filterType": "string_equals", "value": "value"} for i in range(51)]
```

### 3. Combine with Pagination
```python
filters = [{"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}]
all_results = []
cursor = None

while True:
    results = await client.search_vulnerabilities(filters=filters, first=50, after=cursor)
    all_results.extend([edge.node for edge in results.edges])
    if not results.page_info.has_next_page:
        break
    cursor = results.page_info.end_cursor
```

### 4. Handle Filter Errors
```python
async def safe_search(client, filters):
    """Safely execute search with error handling."""
    try:
        if len(filters) > 50:
            raise ValueError("Too many filters (max 50)")
        results = await client.search_vulnerabilities(filters=filters, first=100)
        return [edge.node for edge in results.edges]
    except ValueError as e:
        print(f"Filter validation error: {e}")
        return []
```

## Dynamic Filter Building

```python
def build_vulnerability_filters(severity=None, status=None, has_exploit=None):
    """Dynamically build filters based on parameters."""
    filters = []

    if severity:
        if isinstance(severity, list):
            filters.append({"fieldId": "severity", "filterType": "string_in", "values": severity})
        else:
            filters.append({"fieldId": "severity", "filterType": "string_equals", "value": severity})

    if status:
        filters.append({"fieldId": "status", "filterType": "string_equals", "value": status})

    if has_exploit is not None:
        filters.append({"fieldId": "hasExploit", "filterType": "boolean_equals", "value": has_exploit})

    return filters

# Usage
filters = build_vulnerability_filters(
    severity=["HIGH", "CRITICAL"],
    status="OPEN",
    has_exploit=True
)
```
