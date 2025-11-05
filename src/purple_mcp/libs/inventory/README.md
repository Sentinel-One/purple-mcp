# Inventory Library

A standalone Python library for interacting with the Unified Asset Inventory REST API.

## Overview

This library provides a typed, async interface to the Unified Asset Inventory API, supporting multiple asset surfaces and comprehensive filtering capabilities. It's designed to be completely independent and can be used outside of the MCP context.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Asset Inventory system. It supports retrieving and searching inventory items, but does not include any data modification operations.

## Installation

```bash
pip install purple-mcp
```

## Quick Start

> **Note**: This library is designed for read-only operations and works consistently across all usage contexts.

```python
import asyncio
from purple_mcp.libs.inventory import InventoryClient, InventoryConfig, Surface

async def main():
    config = InventoryConfig(
        base_url="https://console.example.com",
        api_endpoint="/web/api/v2.1/xdr/assets",
        api_token="your-bearer-token"
    )

    async with InventoryClient(config) as client:
        # Get a specific inventory item
        item = await client.get_inventory_item(item_id="123")
        if item:
            print(f"Item: {item.name} - Type: {item.resource_type}")

        # List all inventory items with pagination
        response = await client.list_inventory(limit=50, skip=0)
        print(f"Found {len(response.data)} items")

        # Search with filters (use list_inventory for surface filtering)
        filters = {
            "resourceType": ["Windows Server"],
            "assetStatus": ["Active"]
        }
        results = await client.search_inventory(
            filters=filters,
            limit=100
        )
        print(f"Found {len(results.data)} Windows servers")

        # For surface-specific queries, use list_inventory
        endpoint_items = await client.list_inventory(surface=Surface.ENDPOINT, limit=50)
        print(f"Found {len(endpoint_items.data)} endpoint items")

asyncio.run(main())
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage examples and patterns
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Filter Reference](docs/FILTERS.md)** - Detailed filter format and examples
- **[Configuration](docs/CONFIG.md)** - Configuration options and setup

## Key Features

- **Read-Only Design**: Safe, read-only access to inventory data
- **Typed Interface**: Full type safety with pydantic models
- **Multi-Surface Support**: Query across ENDPOINT, CLOUD, IDENTITY, and NETWORK_DISCOVERY surfaces
- **Rich Filtering**: Support for complex REST API filters including contains, in, between operators
- **Pagination Support**: Built-in offset-based pagination
- **Error Handling**: Comprehensive exception hierarchy
- **Async/Await**: Native async support for efficient operations

## Asset Surfaces

The library supports querying across multiple asset surfaces:

- **ENDPOINT**: Physical and virtual endpoints (servers, workstations, VMs)
- **CLOUD**: Cloud resources (EC2 instances, S3 buckets, databases)
- **IDENTITY**: Identity entities (AD users, groups, Entra ID)
- **NETWORK_DISCOVERY**: Network-discovered devices (IoT, unmanaged devices)

```python
from purple_mcp.libs.inventory import Surface

# Query specific surface
response = await client.list_inventory(surface=Surface.CLOUD)

# Or query all surfaces (default)
response = await client.list_inventory()
```

## Configuration Requirements

```python
from purple_mcp.libs.inventory import InventoryConfig

config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",  # Required
    api_token="your-bearer-token"
)
```

## Filter Syntax

The library supports the REST API filter format:

```python
# Simple field equality
filters = {"resourceType": ["Windows Server", "Linux Server"]}

# Field contains
filters = {"name__contains": ["prod"]}

# Field in list
filters = {"id__in": ["id1", "id2", "id3"]}

# Date range
filters = {
    "lastActiveDt__between": {
        "from": "2024-01-01T00:00:00Z",
        "to": "2024-12-31T23:59:59Z"
    }
}

# Complex filters (combined)
filters = {
    "resourceType": ["Windows Server"],
    "assetStatus": ["Active"],
    "assetCriticality": ["Critical", "High"]
}
```

## Error Handling

The library provides a structured exception hierarchy:

```python
from purple_mcp.libs.inventory.exceptions import (
    InventoryAPIError,              # Base exception for all errors
    InventoryAuthenticationError,   # Authentication/authorization errors
    InventoryNotFoundError,         # Resource not found errors
    InventoryNetworkError,          # Network connectivity errors
)

try:
    item = await client.get_inventory_item("123")
except InventoryAuthenticationError:
    print("Check your API token")
except InventoryNotFoundError:
    print("Item not found")
except InventoryNetworkError:
    print("Network connection failed")
except InventoryAPIError as e:
    print(f"API error: {e}")
```

## Contributing

This library follows the purple-mcp project's contribution guidelines. See the main project's CONTRIBUTING.md for details.
