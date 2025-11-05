# SDL Configuration Guide

Configuration options and settings for the SDL Library.

## Overview

The SDL library uses explicit, programmatic configuration through the `SDLSettings` class, providing type safety, validation, and environment-specific configuration support.

## Basic Configuration

### Creating Settings

```python
from purple_mcp.libs.sdl import create_sdl_settings

# Basic configuration
settings = create_sdl_settings(
    base_url="https://your-console.sentinelone.net/sdl",
    auth_token="Bearer your-api-token"
)
```

### Configuration is Always Explicit

All SDL configuration must be explicitly created using `create_sdl_settings()`. There are no default or global settings objects.

```python
from purple_mcp.libs.sdl import create_sdl_settings

# Always create explicit configuration
settings = create_sdl_settings(
    base_url="https://your-console.sentinelone.net/sdl",
    auth_token="Bearer your-token"
)
print(f"Base URL: {settings.base_url}")
print(f"HTTP timeout: {settings.http_timeout}")
```

## Configuration Parameters

### Required Settings

#### `base_url` (required)
Base URL for the SDL API endpoint.

**Format:** `https://{console_domain}/sdl`

**Security Requirement:** Only HTTPS URLs are accepted. HTTP URLs will be rejected with a validation error to ensure TLS encryption for all SDL communications.

**Examples:**
- `https://your-console.sentinelone.net/sdl`

#### `auth_token` (required)
Bearer token for API authentication.

**Format:** Must include "Bearer " prefix or will be automatically added

**Example:**
```python
# Both formats work
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer your-token"  # Explicit Bearer prefix
)

settings = create_sdl_settings(
    base_url="https://console.example.com/sdl", 
    auth_token="your-token"  # Bearer prefix added automatically
)
```

### Optional Settings

#### `http_timeout` (default: 30)
HTTP request timeout in seconds.

**Range:** 1-300 seconds

```python
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    http_timeout=60  # 60 second timeout
)
```

#### `max_timeout_seconds` (default: 30)
Maximum timeout for SDL operations.

```python
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    max_timeout_seconds=120  # 2 minute max timeout
)
```

#### `http_max_retries` (default: 3)
Maximum number of HTTP request retries on failure.

```python
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    http_max_retries=5  # Retry up to 5 times
)
```

#### `skip_tls_verify` (default: False)
Skip TLS certificate verification. **Not recommended for production.**

```python
# Only for development/testing
dev_settings = create_sdl_settings(
    base_url="https://dev-console.example.com/sdl",
    auth_token="Bearer token",
    skip_tls_verify=True  # WARNING: Security risk
)
```

#### `default_poll_timeout_ms` (default: 30000)
Default polling timeout in milliseconds for query completion.

```python
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    default_poll_timeout_ms=60000  # 1 minute polling timeout
)
```

#### `default_poll_interval_ms` (default: 100)
Default polling interval in milliseconds.

```python
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    default_poll_interval_ms=500  # Poll every 500ms
)
```

#### `max_query_results` (default: 10000)
Maximum number of query results to retrieve.

```python
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    max_query_results=50000  # Retrieve up to 50k results
)
```

#### `query_ttl_seconds` (default: 300)
Query time-to-live in seconds (how long queries persist on server).

```python
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    query_ttl_seconds=600  # Queries live for 10 minutes
)
```

## Environment-Specific Configuration

### Development Configuration

```python
from purple_mcp.libs.sdl import create_sdl_settings

dev_settings = create_sdl_settings(
    base_url="https://dev-console.company.com/sdl",
    auth_token=os.getenv("SDL_DEV_TOKEN"),
    http_timeout=60,  # Longer timeout for development
    skip_tls_verify=True,  # Only for dev environments
    default_poll_timeout_ms=120000,  # 2 minutes for complex queries
    max_query_results=1000  # Smaller result sets for testing
)
```

### Production Configuration

```python
prod_settings = create_sdl_settings(
    base_url="https://prod-console.company.com/sdl",
    auth_token=os.getenv("SDL_PROD_TOKEN"),
    http_timeout=30,  # Standard timeout
    http_max_retries=5,  # More retries for reliability
    default_poll_timeout_ms=60000,  # 1 minute timeout
    max_query_results=100000  # Larger result sets
)
```

### Testing Configuration

```python
test_settings = create_sdl_settings(
    base_url="https://test-console.company.com/sdl",
    auth_token="test-token",
    http_timeout=10,  # Quick timeouts for tests
    default_poll_timeout_ms=5000,  # 5 second test timeout
    max_query_results=100  # Small test datasets
)
```

## Configuration Validation

### Automatic Validation

The library validates all configuration parameters:

```python
from pydantic import ValidationError
from purple_mcp.libs.sdl import create_sdl_settings

try:
    # This will raise a pydantic ValidationError
    invalid_settings = create_sdl_settings(
        base_url="not-a-url",  # Invalid URL format
        auth_token="",  # Empty token
        http_timeout=-1  # Invalid timeout
    )
except ValidationError as e:
    print(f"Configuration validation error: {e}")
```

### Validation Rules

- **base_url**: Must be valid HTTPS URL (HTTP URLs are rejected per security policy)
- **auth_token**: Must be non-empty string
- **http_timeout**: Must be positive integer (1-300)
- **http_max_retries**: Must be non-negative integer
- **poll timeouts**: Must be positive integers
- **max_query_results**: Must be positive integer

## Using Configuration

### With SDLQueryClient

```python
from purple_mcp.libs.sdl import SDLQueryClient, create_sdl_settings

settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token"
)

async with SDLQueryClient(settings.base_url, settings=settings) as client:
    # Client uses configuration settings
    pass
```

### With SDLPowerQueryHandler

```python
from purple_mcp.libs.sdl import SDLPowerQueryHandler, create_sdl_settings

settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    default_poll_timeout_ms=60000
)

handler = SDLPowerQueryHandler(
    auth_token=settings.auth_token,
    base_url=settings.base_url,
    settings=settings  # Pass custom settings
)
```

## Environment Variable Integration

### Loading from Environment

```python
import os
from purple_mcp.libs.sdl import create_sdl_settings

def create_config_from_env():
    return create_sdl_settings(
        base_url=os.getenv("SDL_BASE_URL"),
        auth_token=os.getenv("SDL_AUTH_TOKEN"),
        http_timeout=int(os.getenv("SDL_HTTP_TIMEOUT", "30")),
        default_poll_timeout_ms=int(os.getenv("SDL_POLL_TIMEOUT_MS", "30000"))
    )

settings = create_config_from_env()
```

### Environment Variable Names

Common environment variable patterns:

```bash
# Required
SDL_BASE_URL=https://console.example.com/sdl
SDL_AUTH_TOKEN=Bearer your-token

# Optional
SDL_HTTP_TIMEOUT=60
SDL_MAX_RETRIES=5
SDL_POLL_TIMEOUT_MS=60000
SDL_POLL_INTERVAL_MS=500
SDL_MAX_RESULTS=50000
```

## Configuration Best Practices

### 1. Environment-Specific Settings

Create separate configurations for each environment:

```python
def get_sdl_config(environment: str):
    configs = {
        "development": create_sdl_settings(
            base_url="https://dev.example.com/sdl",
            auth_token=os.getenv("SDL_DEV_TOKEN"),
            skip_tls_verify=True,
            http_timeout=60
        ),
        "staging": create_sdl_settings(
            base_url="https://staging.example.com/sdl",
            auth_token=os.getenv("SDL_STAGING_TOKEN"),
            http_timeout=45
        ),
        "production": create_sdl_settings(
            base_url="https://prod.example.com/sdl",
            auth_token=os.getenv("SDL_PROD_TOKEN"),
            http_timeout=30,
            http_max_retries=5
        )
    }
    return configs[environment]
```

### 2. Configuration Validation

Always validate configuration before use:

```python
def validate_sdl_config(settings):
    """Validate SDL configuration before use."""
    if not settings.auth_token:
        raise ValueError("SDL auth token is required")

    if not settings.base_url.startswith("https://"):
        raise ValueError("SDL base URL must be valid HTTPS URL")

    return settings
```

### 3. Secure Token Handling

Never hardcode tokens in source code:

```python
# ❌ Bad - hardcoded token
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer hardcoded-token"  # Security risk
)

# ✅ Good - from environment
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token=os.getenv("SDL_AUTH_TOKEN")
)
```

### 4. Timeout Configuration

Configure timeouts based on query complexity:

```python
# For simple, fast queries
quick_settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token=os.getenv("SDL_TOKEN"),
    http_timeout=15,
    default_poll_timeout_ms=10000  # 10 seconds
)

# For complex, long-running queries
complex_settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token=os.getenv("SDL_TOKEN"),
    http_timeout=60,
    default_poll_timeout_ms=300000  # 5 minutes
)
```

## Troubleshooting Configuration

### Common Configuration Issues

#### Invalid URL Format

```python
# ❌ Wrong - missing protocol
settings = create_sdl_settings(
    base_url="console.example.com/sdl",  # Missing https://
    auth_token="Bearer token"
)

# ✅ Correct
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token"
)
```

#### Token Format Issues

```python
# ❌ Wrong - malformed token
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token=""  # Empty token
)

# ✅ Correct - the library will add Bearer prefix if missing
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl", 
    auth_token="your-actual-token"  # Bearer prefix added automatically
)
```

#### Timeout Issues

```python
# ❌ Wrong - timeout too low for complex queries
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    default_poll_timeout_ms=1000  # 1 second - too short
)

# ✅ Correct - reasonable timeout
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token",
    default_poll_timeout_ms=60000  # 1 minute
)
```

### Testing Configuration

```python
async def test_sdl_configuration(settings):
    """Test SDL configuration."""
    try:
        from purple_mcp.libs.sdl import SDLQueryClient
        
        async with SDLQueryClient(settings.base_url, settings=settings) as client:
            # Try a minimal operation to test connectivity
            print("✅ SDL configuration is valid")
            return True
            
    except Exception as e:
        print(f"❌ SDL configuration failed: {e}")
        return False
```

### Debug Logging

Enable debug logging to see configuration details:

```python
import logging

# Enable debug logging for SDL
logging.getLogger("purple_mcp.libs.sdl").setLevel(logging.DEBUG)

# Configuration creation and validation will be logged
settings = create_sdl_settings(
    base_url="https://console.example.com/sdl",
    auth_token="Bearer token"
)
```