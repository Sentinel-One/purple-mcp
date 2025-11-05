# Configuration Guide

Configuration options and schema compatibility for the Alerts Library.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Alerts Management system. Configuration settings apply to all usage contexts, supporting data retrieval operations only.

## Basic Configuration

### Required Settings
```python
from purple_mcp.libs.alerts import AlertsConfig

config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-bearer-token"
)
```

### Configuration Parameters

#### `graphql_url` (required)
Full URL to the UAM GraphQL endpoint.

**Format:** `https://{console_domain}/web/api/v2.1/unifiedalerts/graphql`

**Examples:**
- `https://your-console.sentinelone.net/web/api/v2.1/unifiedalerts/graphql`

#### `auth_token` (required)
Bearer token for API authentication. Must have appropriate permissions for alert operations.

**How to get:**
1. Log into your SentinelOne console
2. Go to Settings → Users → Service Users
3. Create a new service user with alert management permissions
4. Copy the generated token

#### `timeout` (optional)
Request timeout in seconds.

**Default:** `30.0`
**Range:** `1.0` to `300.0` (5 minutes max)

```python
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-token",
    timeout=60.0  # 1 minute timeout
)
```

## Schema Compatibility

The library automatically handles different UAM schema versions through compatibility flags.

### Compatibility Flags

#### `supports_view_type` (optional)
Whether the schema supports the `viewType` parameter for filtering alerts by view.

**Default:** `True`
**When to disable:** Older UAM schemas that don't support view-based filtering

```python
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-token",
    supports_view_type=False  # Disable for older schemas
)
```

#### `supports_data_sources` (optional)
Whether the schema supports the `dataSources` field in alert responses.

**Default:** `True`
**When to disable:** Older schemas that don't include data source information

```python
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-token",
    supports_data_sources=False  # Disable for older schemas
)
```

## Schema Version Detection

### Automatic Detection
The library attempts to detect schema compatibility automatically. When a query fails due to unsupported fields or parameters, it automatically retries with fallback queries.

```python
# This will automatically fall back to compatible queries if needed
config = AlertsConfig(
    graphql_url="https://older-console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-token"
)

client = AlertsClient(config)
# Will work even if schema doesn't support all features
alerts = await client.list_alerts()
```

### Manual Configuration
For known schema versions, you can explicitly configure compatibility:

```python
# For older schemas
legacy_config = AlertsConfig(
    graphql_url="https://legacy-console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-token",
    supports_view_type=False,
    supports_data_sources=False
)

# For newest schemas
modern_config = AlertsConfig(
    graphql_url="https://latest-console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-token",
    supports_view_type=True,
    supports_data_sources=True
)
```

## Environment-Based Configuration

### Environment Variables
While the library uses programmatic configuration, you can load from environment variables:

```python
import os
from purple_mcp.libs.alerts import AlertsConfig

def create_config_from_env():
    return AlertsConfig(
        graphql_url=os.getenv("ALERTS_GRAPHQL_URL"),
        auth_token=os.getenv("ALERTS_AUTH_TOKEN"),
        timeout=float(os.getenv("ALERTS_TIMEOUT", "30.0"))
    )

config = create_config_from_env()
```

### Configuration Validation
The library validates configuration on client creation:

```python
from purple_mcp.libs.alerts.exceptions import AlertsConfigError

try:
    config = AlertsConfig(
        graphql_url="invalid-url",  # Will raise error
        auth_token=""  # Will raise error
    )
    client = AlertsClient(config)
except AlertsConfigError as e:
    print(f"Configuration error: {e}")
```

## Advanced Configuration

### Custom HTTP Client Settings
The library uses httpx internally. While not directly configurable, you can understand the HTTP behavior:

```python
# The library internally uses these httpx settings:
# - timeout: As specified in config
# - headers: {"Authorization": f"Bearer {auth_token}"}
# - follow_redirects: True
# - verify: True (SSL verification enabled)
```

### Connection Pooling
The library automatically manages HTTP connection pooling for efficiency:

```python
# Connection pooling is handled automatically
# Multiple requests reuse the same connection pool
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-token"
)

client = AlertsClient(config)

# All these requests will reuse connections
alert1 = await client.get_alert("id1")
alert2 = await client.get_alert("id2")
alerts = await client.list_alerts()
```

## Configuration Examples

### Production Configuration
```python
production_config = AlertsConfig(
    graphql_url="https://production-console.company.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token=os.getenv("PRODUCTION_ALERTS_TOKEN"),
    timeout=60.0,  # Longer timeout for production
    supports_view_type=True,
    supports_data_sources=True
)
```

### Development Configuration
```python
dev_config = AlertsConfig(
    graphql_url="https://dev-console.company.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token=os.getenv("DEV_ALERTS_TOKEN"),
    timeout=15.0,  # Shorter timeout for development
    supports_view_type=True,
    supports_data_sources=True
)
```

### Legacy System Configuration
```python
legacy_config = AlertsConfig(
    graphql_url="https://legacy-console.company.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token=os.getenv("LEGACY_ALERTS_TOKEN"),
    timeout=45.0,  # Longer timeout for slower systems
    supports_view_type=False,  # Older schema
    supports_data_sources=False  # Older schema
)
```

## Troubleshooting Configuration

### Common Configuration Errors

#### Invalid URL Format
```python
# ❌ Wrong
config = AlertsConfig(
    graphql_url="console.example.com/graphql",  # Missing protocol
    auth_token="token"
)

# ✅ Correct
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="token"
)
```

#### Missing Authentication
```python
# ❌ Wrong
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token=""  # Empty token
)

# ✅ Correct
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-actual-bearer-token"
)
```

### Testing Configuration
```python
async def test_configuration(config: AlertsConfig):
    """Test if configuration is working."""
    try:
        client = AlertsClient(config)
        
        # Try a simple query
        alerts = await client.list_alerts(first=1)
        print("✅ Configuration successful")
        print(f"   Schema supports view_type: {config.supports_view_type}")
        print(f"   Schema supports data_sources: {config.supports_data_sources}")
        return True
        
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False
```

### Debug Logging
Enable debug logging to see configuration and request details:

```python
import logging

# Enable debug logging for the alerts library
logging.getLogger("purple_mcp.libs.alerts").setLevel(logging.DEBUG)

# This will show:
# - Configuration validation
# - HTTP requests and responses  
# - Schema compatibility decisions
# - Error details
```