# API Reference

Complete reference for the Inventory Library API.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Asset Inventory system. All methods listed below are for reading and retrieving inventory data. No data modification operations are included in this library.

## InventoryClient

Main client class for interacting with the Unified Asset Inventory API.

### Constructor
```python
InventoryClient(config: InventoryConfig)
```

The client implements async context manager protocol:
```python
async with InventoryClient(config) as client:
    # Use client here
    pass
```

### Inventory Operations

#### `get_inventory_item(item_id: str) -> InventoryItem | None`
Retrieve a specific inventory item by ID.

**Parameters:**
- `item_id` (str): Unique identifier for the inventory item

**Returns:** InventoryItem object or None if not found

**Example:**
```python
item = await client.get_inventory_item("123")
if item:
    print(f"Item: {item.name} - Type: {item.resource_type}")
```

#### `list_inventory(surface: Surface | None = None, limit: int = 50, skip: int = 0) -> InventoryResponse`
List inventory items with pagination and optional surface filtering.

**Parameters:**
- `surface` (Surface, optional): Filter by asset surface (ENDPOINT, CLOUD, IDENTITY, NETWORK_DISCOVERY)
- `limit` (int): Number of items to retrieve per page (default: 50, max: 1000)
- `skip` (int): Number of items to skip for pagination (default: 0)

**Returns:** InventoryResponse with items and pagination info

**Example:**
```python
# List all inventory items
response = await client.list_inventory(limit=100, skip=0)

# List only endpoint items
endpoint_items = await client.list_inventory(surface=Surface.ENDPOINT, limit=50)
```

#### `search_inventory(filters: dict[str, Any] | None = None, limit: int = 50, skip: int = 0) -> InventoryResponse`
Search inventory with complex filters.

**Parameters:**
- `filters` (dict, optional): REST API format filters
- `limit` (int): Number of items to retrieve per page (default: 50, max: 1000)
- `skip` (int): Number of items to skip for pagination (default: 0)

**Returns:** InventoryResponse with filtered items

**Example:**
```python
# Search for Windows servers
filters = {
    "resourceType": ["Windows Server"],
    "assetStatus": ["Active"]
}
results = await client.search_inventory(filters=filters, limit=100)
```

## InventoryConfig

Configuration class for the inventory client.

### Fields
- `base_url: str` - Base console URL (e.g., "https://console.example.com") [required]
- `api_endpoint: str` - API endpoint path (e.g., "/web/api/v2.1/xdr/assets") [required]
- `api_token: str` - Bearer token for authentication [required]

### Example
```python
config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="your-bearer-token"
)
```

## Data Models

### Core Models
- `InventoryItem` - Main inventory item object with all asset fields
- `InventoryResponse` - Response wrapper with items list and pagination info
- `InventoryNote` - Note attached to an inventory item

### Surface Enum
Asset surface types:
- `Surface.ENDPOINT` - Physical and virtual endpoints (servers, workstations, VMs)
- `Surface.CLOUD` - Cloud resources (EC2 instances, S3 buckets, databases)
- `Surface.IDENTITY` - Identity entities (AD users, groups, Entra ID)
- `Surface.NETWORK_DISCOVERY` - Network-discovered devices (IoT, unmanaged devices)

### Key InventoryItem Fields
- `id: str` - Unique identifier
- `name: str` - Asset name
- `resource_type: str` - Type of asset/resource
- `asset_status: str` - Current status (Active, Inactive, etc.)
- `asset_criticality: str` - Criticality level (Critical, High, Medium, Low)
- `last_active_dt: datetime` - Last activity timestamp
- `surface: str` - Asset surface type
- `cloud_info: dict` - Cloud-specific metadata (if applicable)
- `kubernetes_info: dict` - Kubernetes metadata (if applicable)

## Exception Hierarchy

- `InventoryError` - Base exception for all inventory-related errors
  - `InventoryConfigError` - Configuration-related errors
  - `InventoryClientError` - HTTP/network-related errors
    - `InventoryAuthenticationError` - Authentication/authorization errors (401, 403)
    - `InventoryNotFoundError` - Resource not found errors (404)
    - `InventoryAPIError` - API errors
    - `InventoryNetworkError` - Network connectivity errors
    - `InventoryTransientError` - Transient errors that may succeed on retry (5xx)

### Example Error Handling

```python
from purple_mcp.libs.inventory.exceptions import (
    InventoryError,
    InventoryConfigError,
    InventoryClientError,
    InventoryAuthenticationError,
    InventoryNotFoundError,
    InventoryNetworkError,
    InventoryTransientError
)

try:
    item = await client.get_inventory_item("123")
except InventoryAuthenticationError:
    print("Check your API token")
except InventoryNotFoundError:
    print("Item not found")
except InventoryNetworkError as e:
    print(f"Network connection failed: {e}")
except InventoryTransientError as e:
    print(f"Transient error (may retry): {e}")
except InventoryClientError as e:
    print(f"Client error: {e}")
except InventoryConfigError as e:
    print(f"Configuration error: {e}")
except InventoryError as e:
    print(f"Inventory error: {e}")
```

## Pagination

The inventory API uses offset-based pagination:

```python
# First page
page1 = await client.list_inventory(limit=50, skip=0)

# Second page
page2 = await client.list_inventory(limit=50, skip=50)

# Third page
page3 = await client.list_inventory(limit=50, skip=100)
```

### Pagination Info
The `InventoryResponse` includes:
- `data: list[InventoryItem]` - List of items in current page
- `pagination: PaginationInfo | None` - Pagination metadata with attributes:
  - `total_count: int | None` - Total items matching query (also aliased as `totalCount`)
  - `limit: int | None` - Items per page
  - `skip: int | None` - Items skipped

## Context Manager Usage

The client implements async context manager for proper resource cleanup:

```python
async with InventoryClient(config) as client:
    # Client automatically manages HTTP connections
    item = await client.get_inventory_item("123")
    items = await client.list_inventory(limit=100)
    # Connections automatically closed on exit
```

Manual resource management:
```python
client = InventoryClient(config)
try:
    item = await client.get_inventory_item("123")
finally:
    await client.close()  # Manually close connections
```
