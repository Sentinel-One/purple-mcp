# Filter Reference

Comprehensive guide to the misconfigurations library filter system.

## Overview

The misconfigurations library uses a structured GraphQL filter format with `fieldId` and `filterType` keys. The library includes built-in DoS protection with maximum limits on filter counts and values.

## DoS Protection

- **Maximum 50 filters per request**
- **Maximum 100 values per filter**

These limits are enforced automatically and will raise `ValueError` if exceeded.

## Basic Filter Structure

```python
# Single filter
filter = {
    "fieldId": "severity",
    "filterType": "string_equals",
    "value": "HIGH"
}

# Multiple filters (AND logic)
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]

results = await client.search_misconfigurations(filters=filters, first=10)
```

## Filter Types

### String Filters

#### String Equality
```python
# Exact match
{"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}

# Status match
{"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
```

#### String Contains (if supported)
```python
# Contains text
{"fieldId": "name", "filterType": "string_contains", "value": "kubernetes"}
```

### Boolean Filters

```python
# Boolean equality
{"fieldId": "hasRemediation", "filterType": "boolean_equals", "value": True}
```

### Integer/Long Filters

#### Integer Equality
```python
# Exact match
{"fieldId": "assetCount", "filterType": "integer_equals", "value": 5}
```

#### Integer Range
```python
# Range filter
{"fieldId": "riskScore", "filterType": "integer_range", "min": 50, "max": 100}
```

## Complex Filter Examples

### Critical Open Misconfigurations
```python
critical_open = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]

results = await client.search_misconfigurations(filters=critical_open, first=20)
```

### High Severity with Specific Asset Criticality
```python
high_severity_critical_assets = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
    {"fieldId": "assetCriticality", "filterType": "string_equals", "value": "CRITICAL"}
]
```

### Compliance-Related Misconfigurations
```python
compliance_filters = [
    {"fieldId": "complianceFramework", "filterType": "string_contains", "value": "CIS"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
```

## Common Filter Patterns

### By Severity
```python
# Critical only
critical = [{"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"}]

# High and Critical
high_or_critical = [
    {"fieldId": "severity", "filterType": "string_in", "values": ["HIGH", "CRITICAL"]}
]
```

### By Status
```python
# Open misconfigurations
open_items = [{"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}]

# In Progress
in_progress = [{"fieldId": "status", "filterType": "string_equals", "value": "IN_PROGRESS"}]

# Resolved
resolved = [{"fieldId": "status", "filterType": "string_equals", "value": "RESOLVED"}]
```

### By Asset Type
```python
# Cloud assets
cloud_assets = [{"fieldId": "assetType", "filterType": "string_equals", "value": "CLOUD"}]

# Kubernetes resources
k8s_resources = [{"fieldId": "assetType", "filterType": "string_contains", "value": "kubernetes"}]
```

### By Policy
```python
# Specific policy
policy_filter = [{"fieldId": "policyName", "filterType": "string_contains", "value": "S3 Bucket"}]

# Policy category
category_filter = [{"fieldId": "policyCategory", "filterType": "string_equals", "value": "Storage"}]
```

## Filter Field Reference

Common filterable fields in the misconfigurations system:

### Misconfiguration Fields
- `severity` - Misconfiguration severity (LOW, MEDIUM, HIGH, CRITICAL)
- `status` - Current status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED)
- `analystVerdict` - Analyst assessment (VALID, INVALID, IN_REVIEW)
- `name` - Misconfiguration name/title
- `policyName` - Associated policy name
- `policyCategory` - Policy category

### Asset Fields
- `assetName` - Name of the affected asset
- `assetType` - Type of asset (Cloud, Endpoint, etc.)
- `assetCriticality` - Asset criticality level (LOW, MEDIUM, HIGH, CRITICAL)
- `assetStatus` - Asset status

### Cloud Fields
- `cloudProvider` - Cloud provider (AWS, Azure, GCP)
- `cloudRegion` - Cloud region
- `cloudAccountId` - Cloud account identifier
- `cloudResourceType` - Type of cloud resource

### Kubernetes Fields
- `kubernetesCluster` - Cluster name
- `kubernetesNamespace` - Namespace
- `kubernetesWorkloadType` - Workload type

### Compliance Fields
- `complianceFramework` - Compliance framework name (CIS, PCI-DSS, etc.)
- `complianceStatus` - Compliance status

### Temporal Fields
- `createdAt` - Misconfiguration creation timestamp
- `updatedAt` - Last update timestamp
- `resolvedAt` - Resolution timestamp (if resolved)

## Best Practices

### 1. Use Specific Filters
```python
# ✅ Good - Specific and efficient
specific = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"},
    {"fieldId": "assetCriticality", "filterType": "string_equals", "value": "CRITICAL"}
]

# ❌ Less efficient - Too broad
broad = [
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
```

### 2. Respect DoS Protection Limits
```python
# ✅ Within limits
filters = [
    {"fieldId": f"field{i}", "filterType": "string_equals", "value": "value"}
    for i in range(50)  # Exactly at limit
]

# ❌ Exceeds limits - will raise ValueError
too_many_filters = [
    {"fieldId": f"field{i}", "filterType": "string_equals", "value": "value"}
    for i in range(51)  # Over limit
]
```

### 3. Combine with Pagination
```python
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"}
]

all_results = []
cursor = None

while True:
    results = await client.search_misconfigurations(
        filters=filters,
        first=50,
        after=cursor
    )

    all_results.extend([edge.node for edge in results.edges])

    if not results.page_info.has_next_page:
        break
    cursor = results.page_info.end_cursor
```

### 4. Handle Filter Errors
```python
from purple_mcp.libs.misconfigurations.exceptions import MisconfigurationsGraphQLError

async def safe_search(client, filters):
    """Safely execute search with error handling."""
    try:
        # Validate filter count
        if len(filters) > 50:
            raise ValueError("Too many filters (max 50)")

        results = await client.search_misconfigurations(filters=filters, first=100)
        return [edge.node for edge in results.edges]

    except ValueError as e:
        print(f"Filter validation error: {e}")
        return []

    except MisconfigurationsGraphQLError as e:
        print(f"GraphQL error: {e}")
        return []
```

## Advanced Filtering Patterns

### Dynamic Filter Building
```python
def build_misconfiguration_filters(severity=None, status=None, asset_criticality=None):
    """Dynamically build filters based on parameters."""
    filters = []

    if severity:
        if isinstance(severity, list):
            filters.append({"fieldId": "severity", "filterType": "string_in", "values": severity})
        else:
            filters.append({"fieldId": "severity", "filterType": "string_equals", "value": severity})

    if status:
        filters.append({"fieldId": "status", "filterType": "string_equals", "value": status})

    if asset_criticality:
        filters.append({"fieldId": "assetCriticality", "filterType": "string_equals", "value": asset_criticality})

    return filters

# Usage
filters = build_misconfiguration_filters(
    severity=["HIGH", "CRITICAL"],
    status="OPEN",
    asset_criticality="CRITICAL"
)

results = await client.search_misconfigurations(filters=filters, first=100)
```

### Progressive Filtering
```python
async def progressive_filter(client, initial_filters, additional_criteria):
    """Apply filters progressively for complex queries."""

    # First query with initial filters
    initial_results = await client.search_misconfigurations(
        filters=initial_filters,
        first=1000
    )

    # Further filter in application code if needed
    filtered_results = [
        edge.node for edge in initial_results.edges
        if meets_additional_criteria(edge.node, additional_criteria)
    ]

    return filtered_results
```
