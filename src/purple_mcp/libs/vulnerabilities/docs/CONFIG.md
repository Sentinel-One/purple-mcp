# Configuration Guide

Configuration options and schema compatibility for the Vulnerabilities Library.

> **📖 Read-Only Library**: This library provides read-only access to the XSPM Vulnerabilities
> management system. Configuration settings apply to all usage contexts, supporting data retrieval
> operations only.

## Basic Configuration

### Required Settings

```python
from purple_mcp.libs.vulnerabilities import VulnerabilitiesConfig

config = VulnerabilitiesConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token="your-bearer-token"
)
```

### Configuration Parameters

#### `graphql_url` (required)

Full URL to the XSPM Vulnerabilities GraphQL endpoint.

**Format:** `https://{console_domain}/web/api/v2.1/xspm/findings/vulnerabilities/graphql`

**Examples:**

- `https://your-console.sentinelone.net/web/api/v2.1/xspm/findings/vulnerabilities/graphql`

#### `auth_token` (required)

Bearer token for API authentication. Must have appropriate permissions for vulnerability
operations.

**How to get:**

1. Log into your SentinelOne console
2. Go to Policy & Settings → Service Users
3. Create a new service user with XSPM read permissions
4. Copy the generated token

#### `timeout` (optional)

Request timeout in seconds.

**Default:** `30.0` **Range:** `1.0` to `300.0` (5 minutes max)

```python
config = VulnerabilitiesConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token="your-token",
    timeout=60.0  # 1 minute timeout
)
```

## Environment-Based Configuration

### Environment Variables

```python
import os
from purple_mcp.libs.vulnerabilities import VulnerabilitiesConfig

def create_config_from_env():
    return VulnerabilitiesConfig(
        graphql_url=os.getenv("VULNERABILITIES_GRAPHQL_URL"),
        auth_token=os.getenv("VULNERABILITIES_AUTH_TOKEN"),
        timeout=float(os.getenv("VULNERABILITIES_TIMEOUT", "30.0"))
    )

config = create_config_from_env()
```

## Configuration Examples

### Release Configuration

```python
release_config = VulnerabilitiesConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token=os.getenv("PROD_VULNERABILITIES_TOKEN"),
    timeout=60.0,
)
```

### Development Configuration

```python
dev_config = VulnerabilitiesConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token=os.getenv("DEV_VULNERABILITIES_TOKEN"),
    timeout=15.0,
)
```

## Troubleshooting Configuration

### Common Configuration Errors

#### Invalid URL Format

```python
# ❌ Wrong
config = VulnerabilitiesConfig(
    graphql_url="console.sentinelone.net/graphql",  # Missing protocol
    auth_token="token"
)

# ✅ Correct
config = VulnerabilitiesConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token="token"
)
```

### Testing Configuration

```python
async def test_configuration(config: VulnerabilitiesConfig):
    """Test if configuration is working."""
    try:
        client = VulnerabilitiesClient(config)
        vulnerabilities = await client.list_vulnerabilities(first=1)
        print("✅ Configuration successful")
        return True
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False
```

### Debug Logging

```python
import logging
logging.getLogger("purple_mcp.libs.vulnerabilities").setLevel(logging.DEBUG)
```

## Security Considerations

### Token Security

- Never hardcode API tokens in source code
- Use environment variables or secure secret management
- Rotate tokens regularly
- Use least-privilege tokens with only necessary permissions

```python
# ✅ Good practice
config = VulnerabilitiesConfig(
    graphql_url=os.getenv("VULNERABILITIES_GRAPHQL_URL"),
    auth_token=os.getenv("VULNERABILITIES_AUTH_TOKEN")
)

# ❌ Bad practice
config = VulnerabilitiesConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token="hardcoded-token-12345"  # Never do this!
)
```
