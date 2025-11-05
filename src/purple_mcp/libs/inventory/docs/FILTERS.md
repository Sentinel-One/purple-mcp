# Filter Reference

Comprehensive guide to the inventory library filter system.

## Overview

The inventory library uses REST API filter format with flexible operators for field filtering. Filters are passed as dictionaries to the `search_inventory` method.

## Basic Filter Structure

```python
# Simple field equality
filters = {"resourceType": ["Windows Server"]}

# Search with filters
results = await client.search_inventory(filters=filters, limit=100)
```

## Filter Operators

### Equality (Default)
Match exact values. Multiple values use OR logic.

```python
# Single value
filters = {"resourceType": ["Windows Server"]}

# Multiple values (OR logic)
filters = {"resourceType": ["Windows Server", "Linux Server"]}

# Multiple fields (AND logic)
filters = {
    "resourceType": ["Windows Server"],
    "assetStatus": ["Active"]
}
```

### Contains Operator
Search for fields containing specified substrings.

```python
# Field contains value
filters = {"name__contains": ["prod"]}

# Multiple contain values (OR logic)
filters = {"name__contains": ["prod", "production"]}
```

### In Operator
Check if field value is in a list.

```python
# ID in list
filters = {"id__in": ["id1", "id2", "id3"]}

# Resource type in list
filters = {"resourceType__in": ["Windows Server", "Linux Server", "Database"]}
```

### Between Operator
Date and numeric range filtering.

```python
# Date range
filters = {
    "lastActiveDt__between": {
        "from": "2024-01-01T00:00:00Z",
        "to": "2024-12-31T23:59:59Z"
    }
}

# Numeric range (if supported)
filters = {
    "riskScore__between": {
        "from": 50,
        "to": 100
    }
}
```

## Complex Filter Examples

### Multiple Field Filters (AND Logic)
```python
filters = {
    "resourceType": ["Windows Server"],
    "assetStatus": ["Active"],
    "assetCriticality": ["Critical", "High"]
}

results = await client.search_inventory(filters=filters, limit=100)
```

### Text Search with Contains
```python
# Find all production resources
prod_filters = {
    "name__contains": ["prod", "production"]
}

# Find resources by location
location_filters = {
    "name__contains": ["us-east", "us-west"]
}
```

### Date Range Filtering
```python
from datetime import datetime, timedelta

# Last 30 days
thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

recent_active_filters = {
    "lastActiveDt__between": {
        "from": thirty_days_ago,
        "to": now
    }
}
```

### Combining Operators
```python
# Complex filter combining multiple operators
complex_filters = {
    "resourceType": ["Windows Server", "Linux Server"],  # Equality
    "name__contains": ["prod"],  # Contains
    "assetStatus": ["Active"],  # Equality
    "lastActiveDt__between": {  # Between
        "from": "2024-01-01T00:00:00Z",
        "to": "2024-12-31T23:59:59Z"
    }
}

results = await client.search_inventory(filters=complex_filters, limit=200)
```

## Common Filter Patterns

### Active Critical Assets
```python
active_critical = {
    "assetCriticality": ["Critical"],
    "assetStatus": ["Active"]
}
```

### Cloud Resources by Type
```python
cloud_databases = {
    "resourceType": ["RDS", "DynamoDB", "Aurora", "Redshift"]
}
```

### Recently Active Servers
```python
from datetime import datetime, timedelta

last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

recent_servers = {
    "resourceType__in": ["Windows Server", "Linux Server"],
    "lastActiveDt__between": {
        "from": last_week,
        "to": now
    }
}
```

### Production Resources
```python
production_filters = {
    "name__contains": ["prod", "production"],
    "assetStatus": ["Active"]
}
```

### Specific Asset Types
```python
endpoints_filters = {
    "resourceType": ["Desktop", "Laptop", "Server"]
}

cloud_compute_filters = {
    "resourceType": ["EC2", "Azure VM", "GCE Instance"]
}

identity_filters = {
    "resourceType": ["User", "Group", "Service Account"]
}
```

## Filter Field Reference

Common filterable fields in the inventory system:

### Asset Identification
- `id` - Unique asset identifier
- `name` - Asset name/hostname
- `resourceType` - Type of resource (Server, Desktop, EC2, etc.)

### Asset Status
- `assetStatus` - Current status (Active, Inactive, etc.)
- `assetCriticality` - Criticality level (Critical, High, Medium, Low)

### Temporal Fields
- `lastActiveDt` - Last activity timestamp
- `createdAt` - Asset creation/discovery timestamp (if available)
- `updatedAt` - Last update timestamp (if available)

### Cloud-Specific (when applicable)
- `cloudProvider` - Cloud provider name (AWS, Azure, GCP)
- `cloudRegion` - Cloud region
- `cloudAccountId` - Cloud account identifier

### Network-Specific (when applicable)
- `ipAddress` - IP address
- `macAddress` - MAC address

### Kubernetes-Specific (when applicable)
- `kubernetesCluster` - Cluster name
- `kubernetesNamespace` - Namespace
- `kubernetesWorkloadType` - Workload type (Pod, Deployment, etc.)

## Surface-Specific Filtering

### Endpoint Surface
```python
# Use list_inventory with surface parameter
from purple_mcp.libs.inventory import Surface

# For surface filtering, use list_inventory
endpoint_response = await client.list_inventory(surface=Surface.ENDPOINT, limit=100)

# For additional filtering within a surface, combine with search_inventory
endpoint_filters = {
    "resourceType": ["Windows Server"],
    "assetStatus": ["Active"]
}
endpoint_search = await client.search_inventory(filters=endpoint_filters, limit=100)
```

### Cloud Surface
```python
# Cloud-specific filters
cloud_filters = {
    "resourceType": ["EC2", "S3", "RDS"],
    "assetCriticality": ["Critical"]
}

cloud_response = await client.search_inventory(filters=cloud_filters, limit=100)
```

### Identity Surface
```python
# Identity-specific filters
identity_filters = {
    "resourceType": ["User", "Group"],
    "assetStatus": ["Active"]
}

identity_response = await client.search_inventory(filters=identity_filters, limit=100)
```

## Filter Best Practices

### 1. Use Specific Filters
```python
# ✅ Good - Specific and efficient
specific_filters = {
    "resourceType": ["Windows Server"],
    "assetCriticality": ["Critical"],
    "assetStatus": ["Active"]
}

# ❌ Less efficient - Too broad
broad_filters = {
    "assetStatus": ["Active"]  # May return too many results
}
```

### 2. Combine with Pagination
```python
# Always use pagination for large result sets
filters = {
    "resourceType": ["Windows Server"]
}

all_results = []
skip = 0
limit = 100

while True:
    response = await client.search_inventory(
        filters=filters,
        limit=limit,
        skip=skip
    )

    all_results.extend(response.data)

    if len(response.data) < limit:
        break

    skip += limit
```

### 3. Date Range Best Practices
```python
from datetime import datetime, timedelta

# Use reasonable date ranges
recent_filters = {
    "lastActiveDt__between": {
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
}

# Avoid overly broad ranges that may timeout
# ❌ Too broad
all_time_filters = {
    "lastActiveDt__between": {
        "from": "2000-01-01T00:00:00Z",
        "to": "2030-01-01T00:00:00Z"
    }
}
```

### 4. Use Surface Parameter When Possible
```python
# ✅ Better - Use surface parameter for surface-specific queries
endpoint_response = await client.list_inventory(surface=Surface.ENDPOINT, limit=100)

# Then filter further if needed
specific_filters = {
    "resourceType": ["Windows Server"]
}
filtered_endpoints = await client.search_inventory(filters=specific_filters, limit=100)
```

## Error Handling with Filters

```python
from purple_mcp.libs.inventory.exceptions import InventoryAPIError

async def safe_filtered_search(client, filters):
    """Safely execute filtered search with error handling."""
    try:
        response = await client.search_inventory(filters=filters, limit=100)
        return response.data

    except InventoryAPIError as e:
        print(f"Filter search failed: {e}")
        # Log the filters that failed
        print(f"Filters used: {filters}")
        return []
```

## Advanced Filtering Patterns

### Progressive Filtering
```python
async def progressive_filter(client, initial_filters, additional_filters):
    """Apply filters progressively for complex queries."""

    # First query with initial filters
    initial_results = await client.search_inventory(
        filters=initial_filters,
        limit=1000
    )

    # Further filter in application code if needed
    filtered_results = [
        item for item in initial_results.data
        if meets_additional_criteria(item, additional_filters)
    ]

    return filtered_results
```

### Dynamic Filter Building
```python
def build_filters(resource_types=None, status=None, criticality=None, date_range=None):
    """Dynamically build filters based on parameters."""
    filters = {}

    if resource_types:
        filters["resourceType"] = resource_types

    if status:
        filters["assetStatus"] = status

    if criticality:
        filters["assetCriticality"] = criticality

    if date_range:
        filters["lastActiveDt__between"] = date_range

    return filters

# Usage
filters = build_filters(
    resource_types=["Windows Server"],
    status=["Active"],
    criticality=["Critical", "High"]
)

results = await client.search_inventory(filters=filters, limit=100)
```
