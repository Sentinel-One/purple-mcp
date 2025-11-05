# Configuration Guide

Configuration options and schema compatibility for the Misconfigurations Library.

> **📖 Read-Only Library**: This library provides read-only access to the XSPM Misconfigurations management system. Configuration settings apply to all usage contexts, supporting data retrieval operations only.

## Basic Configuration

### Required Settings
```python
from purple_mcp.libs.misconfigurations import MisconfigurationsConfig

config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="your-bearer-token"
)
```

### Configuration Parameters

#### `graphql_url` (required)
Full URL to the XSPM Misconfigurations GraphQL endpoint.

**Format:** `https://{console_domain}/web/api/v2.1/xspm/findings/misconfigurations/graphql`

**Examples:**
- `https://your-console.sentinelone.net/web/api/v2.1/xspm/findings/misconfigurations/graphql`

#### `auth_token` (required)
Bearer token for API authentication. Must have appropriate permissions for misconfiguration operations.

**How to get:**
1. Log into your SentinelOne console
2. Go to Policy & Settings → Service Users
3. Create a new service user with XSPM read permissions
4. Copy the generated token

#### `timeout` (optional)
Request timeout in seconds.

**Default:** `30.0`
**Range:** `1.0` to `300.0` (5 minutes max)

```python
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="your-token",
    timeout=60.0  # 1 minute timeout
)
```

## Environment-Based Configuration

### Environment Variables
While the library uses programmatic configuration, you can load from environment variables:

```python
import os
from purple_mcp.libs.misconfigurations import MisconfigurationsConfig

def create_config_from_env():
    return MisconfigurationsConfig(
        graphql_url=os.getenv("MISCONFIGURATIONS_GRAPHQL_URL"),
        auth_token=os.getenv("MISCONFIGURATIONS_AUTH_TOKEN"),
        timeout=float(os.getenv("MISCONFIGURATIONS_TIMEOUT", "30.0"))
    )

config = create_config_from_env()
```

### Configuration Validation
The library validates configuration on client creation:

```python
from purple_mcp.libs.misconfigurations.exceptions import MisconfigurationsConfigError

try:
    config = MisconfigurationsConfig(
        graphql_url="invalid-url",  # Will raise error
        auth_token=""  # Will raise error
    )
    client = MisconfigurationsClient(config)
except MisconfigurationsConfigError as e:
    print(f"Configuration error: {e}")
```

## Configuration Examples

### Production Configuration
```python
production_config = MisconfigurationsConfig(
    graphql_url="https://production-console.company.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token=os.getenv("PRODUCTION_MISCONFIGURATIONS_TOKEN"),
    timeout=60.0,  # Longer timeout for production
)
```

### Development Configuration
```python
dev_config = MisconfigurationsConfig(
    graphql_url="https://dev-console.company.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token=os.getenv("DEV_MISCONFIGURATIONS_TOKEN"),
    timeout=15.0,  # Shorter timeout for development
)
```

## Troubleshooting Configuration

### Common Configuration Errors

#### Invalid URL Format
```python
# ❌ Wrong
config = MisconfigurationsConfig(
    graphql_url="console.example.com/graphql",  # Missing protocol
    auth_token="token"
)

# ✅ Correct
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="token"
)
```

#### Missing Authentication
```python
# ❌ Wrong
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token=""  # Empty token
)

# ✅ Correct
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="your-actual-bearer-token"
)
```

### Testing Configuration
```python
async def test_configuration(config: MisconfigurationsConfig):
    """Test if configuration is working."""
    try:
        client = MisconfigurationsClient(config)

        # Try a simple query
        misconfigurations = await client.list_misconfigurations(first=1)
        print("✅ Configuration successful")
        return True

    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False
```

### Debug Logging
Enable debug logging to see configuration and request details:

```python
import logging

# Enable debug logging for the misconfigurations library
logging.getLogger("purple_mcp.libs.misconfigurations").setLevel(logging.DEBUG)

# This will show:
# - Configuration validation
# - HTTP requests and responses
# - GraphQL queries and responses
# - Error details
```

## Advanced Configuration

### Custom HTTP Client Settings
The library uses httpx internally with these settings:

```python
# Internal httpx configuration (not directly modifiable):
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
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="your-token"
)

client = MisconfigurationsClient(config)

# All these requests will reuse connections
misconfiguration1 = await client.get_misconfiguration("id1")
misconfiguration2 = await client.get_misconfiguration("id2")
misconfigurations = await client.list_misconfigurations()
```

## Security Considerations

### Token Security
- Never hardcode API tokens in source code
- Use environment variables or secure secret management
- Rotate tokens regularly
- Use least-privilege tokens with only necessary permissions

```python
# ✅ Good practice
config = MisconfigurationsConfig(
    graphql_url=os.getenv("MISCONFIGURATIONS_GRAPHQL_URL"),
    auth_token=os.getenv("MISCONFIGURATIONS_AUTH_TOKEN")
)

# ❌ Bad practice
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="hardcoded-token-12345"  # Never do this!
)
```

### SSL Verification
The library always uses SSL verification. Do not disable SSL verification in production environments.
