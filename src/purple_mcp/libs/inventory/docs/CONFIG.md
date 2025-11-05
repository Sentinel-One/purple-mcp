# Configuration Guide

Configuration options and setup for the Inventory Library.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Asset Inventory system. Configuration settings apply to all usage contexts, supporting data retrieval operations only.

## Basic Configuration

### Required Settings
```python
from purple_mcp.libs.inventory import InventoryConfig

config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="your-bearer-token"
)
```

### Configuration Parameters

#### `base_url` (required)
Base URL of the SentinelOne console.

**Format:** `https://{console_domain}`

**Examples:**
- `https://your-console.sentinelone.net`

**Note:** Do not include the API endpoint path in the base_url. The API endpoint is configured separately.

#### `api_endpoint` (required)
API endpoint path for the inventory API.

**Example value:** `/web/api/v2.1/xdr/assets`

**Note:** This must be explicitly provided - there is no default value.

```python
config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="your-token"
)
```

#### `api_token` (required)
Bearer token for API authentication. Must have appropriate permissions for inventory operations.

**How to get:**
1. Log into your SentinelOne console
2. Go to Policy & Settings → Service Users
3. Create a new service user with inventory read permissions
4. Copy the generated token

## Environment-Based Configuration

### Environment Variables
While the library uses programmatic configuration, you can load from environment variables:

```python
import os
from purple_mcp.libs.inventory import InventoryConfig

def create_config_from_env():
    return InventoryConfig(
        base_url=os.getenv("INVENTORY_BASE_URL"),
        api_endpoint=os.getenv("INVENTORY_API_ENDPOINT"),
        api_token=os.getenv("INVENTORY_API_TOKEN")
    )

config = create_config_from_env()
```

### Configuration Validation
The library validates configuration at multiple levels:

```python
from pydantic import ValidationError
from purple_mcp.libs.inventory.exceptions import InventoryAPIError

# 1. Pydantic validates required fields at instantiation
try:
    config = InventoryConfig(
        base_url="https://console.example.com"
        # Missing api_endpoint and api_token - raises ValidationError
    )
except ValidationError as e:
    print(f"Config validation error: {e}")

# 2. Runtime validation during API calls
try:
    config = InventoryConfig(
        base_url="http://invalid-url",  # Invalid protocol - accepted by config
        api_endpoint="/web/api/v2.1/xdr/assets",
        api_token="invalid-token"  # Invalid token - discovered at runtime
    )
    async with InventoryClient(config) as client:
        item = await client.get_inventory_item("123")
except ValidationError as e:
    print(f"URL validation error: {e}")  # HTTPS requirement enforced
except InventoryAPIError as e:
    print(f"API error: {e}")  # Authentication/network errors
```

## Configuration Examples

### Production Configuration
```python
production_config = InventoryConfig(
    base_url="https://production-console.company.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token=os.getenv("PRODUCTION_INVENTORY_TOKEN")
)
```

### Development Configuration
```python
dev_config = InventoryConfig(
    base_url="https://dev-console.company.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token=os.getenv("DEV_INVENTORY_TOKEN")
)
```

### High-Volume Configuration
```python
high_volume_config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token=os.getenv("INVENTORY_TOKEN")
)
```

## Troubleshooting Configuration

### Common Configuration Errors

#### Invalid URL Format
```python
# ❌ Wrong
config = InventoryConfig(
    base_url="console.example.com",  # Missing protocol
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="token"
)

# ✅ Correct
config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="token"
)
```

#### Including API Endpoint in Base URL
```python
# ❌ Wrong
config = InventoryConfig(
    base_url="https://console.example.com/web/api/v2.1/xdr/assets",  # Too specific
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="token"
)

# ✅ Correct
config = InventoryConfig(
    base_url="https://console.example.com",  # Just the base URL
    api_endpoint="/web/api/v2.1/xdr/assets",  # Endpoint separate
    api_token="token"
)
```

#### Missing Required Fields
```python
# ❌ Wrong
config = InventoryConfig(
    base_url="https://console.example.com",
    api_token=""  # Empty token - also missing api_endpoint
)

# ✅ Correct
config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="your-actual-bearer-token"
)
```

### Testing Configuration
```python
async def test_configuration(config: InventoryConfig):
    """Test if configuration is working."""
    try:
        async with InventoryClient(config) as client:
            # Try a simple query
            response = await client.list_inventory(limit=1)
            print("✅ Configuration successful")
            total = response.pagination.total_count if response.pagination else "unknown"
            print(f"   Total items available: {total}")
            return True

    except InventoryAuthenticationError:
        print("❌ Authentication failed - check your API token")
        return False
    except InventoryNetworkError as e:
        print(f"❌ Network error - check your base_url: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False
```

### Debug Logging
Enable debug logging to see configuration and request details:

```python
import logging

# Enable debug logging for the inventory library
logging.getLogger("purple_mcp.libs.inventory").setLevel(logging.DEBUG)

# This will show:
# - Configuration validation
# - HTTP requests and responses
# - API endpoint construction
# - Error details
```

## Advanced Configuration

### Custom HTTP Client Settings
The library uses httpx internally with these settings:

```python
# Internal httpx configuration (not directly modifiable):
# - headers: {"Authorization": f"Bearer {api_token}"}
# - follow_redirects: True
# - verify: True (SSL verification enabled)
```

### Connection Pooling
The library automatically manages HTTP connection pooling for efficiency:

```python
# Connection pooling is handled automatically
# The async context manager reuses the same connection pool
async with InventoryClient(config) as client:
    # All these requests reuse connections
    item1 = await client.get_inventory_item("id1")
    item2 = await client.get_inventory_item("id2")
    items = await client.list_inventory(limit=100)
```

## Security Considerations

### Token Security
- Never hardcode API tokens in source code
- Use environment variables or secure secret management
- Rotate tokens regularly
- Use least-privilege tokens with only necessary permissions

```python
# ✅ Good practice
config = InventoryConfig(
    base_url=os.getenv("INVENTORY_BASE_URL"),
    api_endpoint=os.getenv("INVENTORY_API_ENDPOINT"),
    api_token=os.getenv("INVENTORY_API_TOKEN")
)

# ❌ Bad practice
config = InventoryConfig(
    base_url="https://console.example.com",
    api_endpoint="/web/api/v2.1/xdr/assets",
    api_token="hardcoded-token-12345"  # Never do this!
)
```

### SSL Verification
The library always uses SSL verification. Do not disable SSL verification in production environments.

### Network Security
Ensure the console URL is accessible from your network and appropriate firewall rules are in place.
