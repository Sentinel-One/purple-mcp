# Usage Guide

Comprehensive usage examples and patterns for the Inventory Library.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Asset Inventory system. All examples below demonstrate data retrieval and analysis operations.

## Basic Operations

### Getting Started
```python
import asyncio
from purple_mcp.libs.inventory import InventoryClient, InventoryConfig

async def main():
    config = InventoryConfig(
        base_url="https://console.example.com",
        api_endpoint="/web/api/v2.1/xdr/assets",
        api_token="your-bearer-token"
    )

    async with InventoryClient(config) as client:
        # Your inventory operations here
        pass

asyncio.run(main())
```

### Retrieving Inventory Items

#### Get a Specific Item
```python
async def get_item_details(client: InventoryClient, item_id: str):
    item = await client.get_inventory_item(item_id)
    if item:
        print(f"Item: {item.name}")
        print(f"Type: {item.resource_type}")
        print(f"Status: {item.asset_status}")
        print(f"Criticality: {item.asset_criticality}")
    else:
        print("Item not found")
```

#### List All Inventory Items
```python
async def list_all_items(client: InventoryClient):
    response = await client.list_inventory(limit=100, skip=0)

    print(f"Found {len(response.data)} items")
    for item in response.data:
        print(f"- {item.name} ({item.resource_type})")
```

### Surface-Specific Queries

#### Query by Asset Surface
```python
from purple_mcp.libs.inventory import Surface

async def list_endpoints(client: InventoryClient):
    """List all endpoint assets."""
    response = await client.list_inventory(
        surface=Surface.ENDPOINT,
        limit=50
    )
    return response.data

async def list_cloud_resources(client: InventoryClient):
    """List all cloud resources."""
    response = await client.list_inventory(
        surface=Surface.CLOUD,
        limit=50
    )
    return response.data

async def list_identities(client: InventoryClient):
    """List all identity entities."""
    response = await client.list_inventory(
        surface=Surface.IDENTITY,
        limit=50
    )
    return response.data

async def list_network_devices(client: InventoryClient):
    """List all network-discovered devices."""
    response = await client.list_inventory(
        surface=Surface.NETWORK_DISCOVERY,
        limit=50
    )
    return response.data
```

### Searching with Filters

#### Basic Filter Search
```python
async def search_windows_servers(client: InventoryClient):
    """Search for Windows Server assets."""
    filters = {
        "resourceType": ["Windows Server"]
    }

    response = await client.search_inventory(filters=filters, limit=100)
    return response.data
```

#### Complex Filter Search
```python
async def search_critical_active_servers(client: InventoryClient):
    """Search for critical, active server assets."""
    filters = {
        "resourceType": ["Windows Server", "Linux Server"],
        "assetStatus": ["Active"],
        "assetCriticality": ["Critical", "High"]
    }

    response = await client.search_inventory(filters=filters, limit=200)
    return response.data
```

#### Filter with Contains
```python
async def search_prod_resources(client: InventoryClient):
    """Search for resources with 'prod' in the name."""
    filters = {
        "name__contains": ["prod", "production"]
    }

    response = await client.search_inventory(filters=filters, limit=100)
    return response.data
```

#### Filter with Date Range
```python
async def search_recently_active(client: InventoryClient):
    """Search for recently active assets."""
    filters = {
        "lastActiveDt__between": {
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-12-31T23:59:59Z"
        }
    }

    response = await client.search_inventory(filters=filters, limit=100)
    return response.data
```

#### Filter with IN Operator
```python
async def search_specific_items(client: InventoryClient, item_ids: list[str]):
    """Search for specific items by ID."""
    filters = {
        "id__in": item_ids
    }

    response = await client.search_inventory(filters=filters, limit=len(item_ids))
    return response.data
```

## Pagination Patterns

### Basic Pagination
```python
async def paginate_through_inventory(client: InventoryClient):
    """Retrieve all inventory items using pagination."""
    all_items = []
    skip = 0
    limit = 100

    while True:
        response = await client.list_inventory(limit=limit, skip=skip)
        all_items.extend(response.data)

        print(f"Fetched {len(response.data)} items (total: {len(all_items)})")

        # Check if we've fetched all items
        total_items = response.pagination.total_count if response.pagination else 0
        if skip + len(response.data) >= total_items:
            break

        skip += limit

    return all_items
```

### Surface-Specific Pagination
```python
async def paginate_cloud_resources(client: InventoryClient):
    """Paginate through all cloud resources."""
    all_cloud_items = []
    skip = 0
    limit = 100

    while True:
        response = await client.list_inventory(
            surface=Surface.CLOUD,
            limit=limit,
            skip=skip
        )

        all_cloud_items.extend(response.data)

        total_items = response.pagination.total_count if response.pagination else 0
        if skip + len(response.data) >= total_items or len(response.data) == 0:
            break

        skip += limit

    return all_cloud_items
```

### Filtered Pagination
```python
async def paginate_critical_assets(client: InventoryClient):
    """Paginate through all critical assets."""
    filters = {
        "assetCriticality": ["Critical"]
    }

    all_critical = []
    skip = 0
    limit = 100

    while True:
        response = await client.search_inventory(
            filters=filters,
            limit=limit,
            skip=skip
        )

        all_critical.extend(response.data)

        total_items = response.pagination.total_count if response.pagination else 0
        if skip + len(response.data) >= total_items or len(response.data) == 0:
            break

        skip += limit

    return all_critical
```

## Advanced Patterns

### Multi-Surface Analysis
```python
async def analyze_asset_distribution(client: InventoryClient):
    """Analyze asset distribution across surfaces."""
    surfaces = [Surface.ENDPOINT, Surface.CLOUD, Surface.IDENTITY, Surface.NETWORK_DISCOVERY]

    distribution = {}
    for surface in surfaces:
        response = await client.list_inventory(surface=surface, limit=1)
        total = response.pagination.total_count if response.pagination else 0
        distribution[surface.value] = total

    print("Asset Distribution:")
    for surface, count in distribution.items():
        print(f"  {surface}: {count} assets")

    return distribution
```

### Criticality Analysis
```python
async def analyze_criticality_breakdown(client: InventoryClient):
    """Analyze assets by criticality level."""
    criticality_levels = ["Critical", "High", "Medium", "Low"]

    breakdown = {}
    for level in criticality_levels:
        filters = {"assetCriticality": [level]}
        response = await client.search_inventory(filters=filters, limit=1)
        count = response.pagination.total_count if response.pagination else 0
        breakdown[level] = count

    print("Criticality Breakdown:")
    for level, count in breakdown.items():
        print(f"  {level}: {count} assets")

    return breakdown
```

### Cloud Resource Analysis
```python
async def analyze_cloud_resources(client: InventoryClient):
    """Detailed analysis of cloud resources."""
    response = await client.list_inventory(surface=Surface.CLOUD, limit=1000)

    cloud_by_type = {}
    cloud_by_provider = {}

    for item in response.data:
        # Analyze by resource type
        resource_type = item.resource_type
        cloud_by_type[resource_type] = cloud_by_type.get(resource_type, 0) + 1

        # Analyze by cloud provider (if available in cloud_info)
        if item.cloud_info and 'provider' in item.cloud_info:
            provider = item.cloud_info['provider']
            cloud_by_provider[provider] = cloud_by_provider.get(provider, 0) + 1

    print("Cloud Resources by Type:")
    for res_type, count in sorted(cloud_by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"  {res_type}: {count}")

    print("\nCloud Resources by Provider:")
    for provider, count in sorted(cloud_by_provider.items(), key=lambda x: x[1], reverse=True):
        print(f"  {provider}: {count}")

    return {
        'by_type': cloud_by_type,
        'by_provider': cloud_by_provider
    }
```

### Inactive Asset Detection
```python
from datetime import datetime, timedelta

async def find_inactive_assets(client: InventoryClient, days_threshold: int = 30):
    """Find assets that haven't been active recently."""
    # Calculate threshold date
    threshold_date = datetime.now() - timedelta(days=days_threshold)
    threshold_str = threshold_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Search for assets last active before threshold
    filters = {
        "lastActiveDt__between": {
            "from": "2020-01-01T00:00:00Z",
            "to": threshold_str
        }
    }

    inactive_assets = []
    skip = 0
    limit = 100

    while True:
        response = await client.search_inventory(
            filters=filters,
            limit=limit,
            skip=skip
        )

        inactive_assets.extend(response.data)

        if len(response.data) < limit:
            break

        skip += limit

    print(f"Found {len(inactive_assets)} assets inactive for >{days_threshold} days")
    return inactive_assets
```

## Error Handling Patterns

### Comprehensive Error Handling
```python
from purple_mcp.libs.inventory.exceptions import (
    InventoryAPIError,
    InventoryAuthenticationError,
    InventoryNotFoundError,
    InventoryNetworkError,
    InventoryTransientError
)

async def robust_inventory_retrieval(client: InventoryClient, item_id: str):
    try:
        item = await client.get_inventory_item(item_id)
        return item

    except InventoryAuthenticationError as e:
        print(f"Authentication error: {e}")
        print("Check your API token")
        return None

    except InventoryNotFoundError as e:
        print(f"Item not found: {e}")
        return None

    except InventoryNetworkError as e:
        print(f"Network error: {e}")
        print("Check connectivity to console")
        return None

    except InventoryTransientError as e:
        print(f"Transient error (may retry): {e}")
        return None

    except InventoryAPIError as e:
        print(f"API error: {e}")
        return None
```

### Retry with Exponential Backoff
```python
import asyncio

async def resilient_inventory_fetch(
    client: InventoryClient,
    item_id: str,
    max_retries: int = 3
):
    """Fetch inventory item with retry logic."""

    for attempt in range(max_retries):
        try:
            item = await client.get_inventory_item(item_id)
            return item

        except InventoryTransientError as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return None

            # Exponential backoff
            delay = 2 ** attempt
            print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            await asyncio.sleep(delay)

        except (InventoryAuthenticationError, InventoryNotFoundError):
            # Don't retry these errors
            return None

    return None
```

## Resource Management

### Context Manager (Recommended)
```python
async def use_context_manager():
    """Recommended: Use async context manager for automatic cleanup."""
    config = InventoryConfig(
        base_url="https://console.example.com",
        api_endpoint="/web/api/v2.1/xdr/assets",
        api_token="your-token"
    )

    async with InventoryClient(config) as client:
        # Resources automatically managed
        item = await client.get_inventory_item("123")
        items = await client.list_inventory(limit=100)
        # Connections automatically closed on exit
```

### Manual Resource Management
```python
async def manual_resource_management():
    """Manual cleanup when not using context manager."""
    config = InventoryConfig(
        base_url="https://console.example.com",
        api_endpoint="/web/api/v2.1/xdr/assets",
        api_token="your-token"
    )

    client = InventoryClient(config)
    try:
        item = await client.get_inventory_item("123")
        items = await client.list_inventory(limit=100)
    finally:
        await client.close()  # Manually close connections
```

## Testing Patterns

### Mock Testing Setup
```python
from unittest.mock import AsyncMock, patch

async def test_inventory_operations():
    """Example of how to test inventory operations."""

    config = InventoryConfig(
        base_url="https://test.example.com",
        api_endpoint="/web/api/v2.1/xdr/assets",
        api_token="test-token"
    )

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        # Mock successful response
        mock_get.return_value.json.return_value = {
            "data": [{
                "id": "123",
                "name": "Test Server",
                "resourceType": "Windows Server",
                "assetStatus": "Active"
            }],
            "pagination": {
                "totalCount": 1,
                "limit": 50,
                "skip": 0
            }
        }

        async with InventoryClient(config) as client:
            response = await client.list_inventory(limit=50)

            assert len(response.data) == 1
            assert response.data[0].id == "123"
            assert response.data[0].name == "Test Server"
```
