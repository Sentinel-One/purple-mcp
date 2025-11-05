# Purple AI Configuration Guide

Configuration options and setup for the Purple AI Library.

## Overview

The Purple AI library uses explicit configuration through the `PurpleAIConfig` class, providing flexibility for different deployment scenarios and console environments.

## Basic Configuration

### Required Settings

```python
from purple_mcp.libs.purple_ai import PurpleAIConfig

# Minimal configuration
config = PurpleAIConfig(
    graphql_url="https://your-console.sentinelone.net/web/api/v2.1/graphql",
    auth_token="your-service-token"
)
```

### Configuration Parameters

#### `graphql_url` (required)
Full URL to the SentinelOne GraphQL endpoint.

**Format:** `https://{console_domain}/web/api/v2.1/graphql`

**Validation:**
- Must use HTTPS protocol (HTTP is rejected for security)
- Leading/trailing whitespace is automatically stripped

**Examples:**
- `https://your-console.sentinelone.net/web/api/v2.1/graphql`

#### `auth_token` (required)
Authentication token for API access.

**How to get:**
1. Log into your SentinelOne console
2. Go to Settings → Users → Service Users
3. Create a new service user with appropriate permissions
4. Copy the generated API token

**Format:** The token should be provided as-is (without "Bearer " prefix)

**Validation:**
- Cannot be empty or whitespace-only
- Leading/trailing whitespace is automatically stripped

```python
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="your-api-token-here"  # No Bearer prefix needed
)
```

#### `timeout` (optional)
Request timeout in seconds for HTTP operations.

**Default:** 120.0 seconds

**Format:** Float value representing seconds

**Validation:**
- Must be greater than 0 (zero and negative values are rejected)

```python
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="your-api-token-here",
    timeout=60.0  # Custom timeout of 60 seconds
)
```

**When to adjust:**
- Increase for slower network connections or complex queries
- Decrease for faster timeout in high-availability scenarios
- Keep default (120s) for most use cases

## Optional Configuration

### Console Details

Provide additional context about your console environment:

```python
from purple_mcp.libs.purple_ai import PurpleAIConfig, PurpleAIConsoleDetails

config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="your-token",
    console_details=PurpleAIConsoleDetails(
        base_url="https://console.example.com",
        version="S-25.1.1#30"
    )
)
```

#### PurpleAIConsoleDetails Fields

##### `base_url` (required)
The base URL of your SentinelOne console.

**Format:** `https://{console_domain}`

**Validation:**
- Must use HTTPS protocol (HTTP is rejected for security)

**Where to find:**
1. The base domain of your SentinelOne console
2. Example: If you access the console at `https://console.example.com/dashboard`, use `https://console.example.com`

##### `version` (required)
Version of your SentinelOne console.

**Format:** `S-{version}#{build}` (e.g., `S-25.1.1#30`)

**Where to find:**
1. SentinelOne console → Help → About
2. Look for version information

##### `team_token` (optional)
Team-specific token for multi-tenant environments.

##### `console_version` (optional)
Version of your SentinelOne console.

**Format:** `S-{version}#{build}` (e.g., `S-25.1.1#30`)

**Where to find:**
1. SentinelOne console → Help → About
2. Look for version information

##### `build_date` (optional)
Build date of your console version.

**Format:** `MM/DD/YYYY, HH:MM:SS AM/PM`

##### `build_hash` (optional)
Unique hash for your console build.

### User Details

Provide context about the user making requests:

```python
from purple_mcp.libs.purple_ai import PurpleAIConfig, PurpleAIUserDetails

config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="your-token",
    user_details=PurpleAIUserDetails(
        email_address="analyst@company.com",
        user_agent="SecurityAnalysisTools/2.1"
    )
)
```

#### PurpleAIUserDetails Fields

##### `email_address` (optional)
Email address of the user making Purple AI requests.

**Use cases:**
- Audit logging
- Personalized responses
- Access control context

##### `user_agent` (optional)
Custom user agent string for API requests.

**Format:** `{ApplicationName}/{Version} ({Platform})`

**Examples:**
- `SecurityDashboard/1.0 (Python/3.11)`
- `ThreatHunting/2.1 (Linux)`
- `AutomatedAnalysis/1.5`

## Environment-Based Configuration

### Using Environment Variables

```python
import os
from purple_mcp.libs.purple_ai import PurpleAIConfig, PurpleAIConsoleDetails, PurpleAIUserDetails

def create_config_from_env():
    """Create Purple AI config from environment variables."""
    
    # Required from environment
    base_url = os.getenv("PURPLEMCP_CONSOLE_BASE_URL")
    if not base_url:
        raise ValueError("PURPLEMCP_CONSOLE_BASE_URL environment variable required")

    service_token = os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    if not service_token:
        raise ValueError("PURPLEMCP_CONSOLE_TOKEN environment variable required")
    
    # Build GraphQL URL
    graphql_url = base_url.rstrip("/") + "/web/api/v2.1/graphql"
    
    # Optional console details
    console_details = None
    if os.getenv("PURPLEMCP_PURPLE_AI_ACCOUNT_ID"):
        console_details = PurpleAIConsoleDetails(
            account_id=os.getenv("PURPLEMCP_PURPLE_AI_ACCOUNT_ID"),
            team_token=os.getenv("PURPLEMCP_PURPLE_AI_TEAM_TOKEN"),
            console_version=os.getenv("PURPLEMCP_PURPLE_AI_CONSOLE_VERSION"),
            build_date=os.getenv("PURPLEMCP_PURPLE_AI_BUILD_DATE"),
            build_hash=os.getenv("PURPLEMCP_PURPLE_AI_BUILD_HASH")
        )

    # Optional user details
    user_details = None
    if os.getenv("PURPLEMCP_PURPLE_AI_EMAIL_ADDRESS"):
        user_details = PurpleAIUserDetails(
            email_address=os.getenv("PURPLEMCP_PURPLE_AI_EMAIL_ADDRESS"),
            user_agent=os.getenv("PURPLEMCP_PURPLE_AI_USER_AGENT")
        )
    
    return PurpleAIConfig(
        graphql_url=graphql_url,
        auth_token=service_token,
        console_details=console_details,
        user_details=user_details
    )

# Usage
config = create_config_from_env()
```

### Environment Variable Reference

#### Required Variables
```bash
# Base URL of your SentinelOne console
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net

# Service token for API access
PURPLEMCP_CONSOLE_TOKEN=your-service-token
```

#### Optional Variables
```bash
# Console details
PURPLEMCP_PURPLE_AI_ACCOUNT_ID=123456789
PURPLEMCP_PURPLE_AI_TEAM_TOKEN=team-specific-token
PURPLEMCP_PURPLE_AI_CONSOLE_VERSION=S-25.1.1#30
PURPLEMCP_PURPLE_AI_BUILD_DATE="01/15/2025, 10:30:00 AM"
PURPLEMCP_PURPLE_AI_BUILD_HASH=abc123def456

# User details
PURPLEMCP_PURPLE_AI_EMAIL_ADDRESS=analyst@company.com
PURPLEMCP_PURPLE_AI_USER_AGENT="MyApplication/1.0"
```

## Environment-Specific Configurations

### Development Configuration

```python
def create_dev_config():
    """Configuration for development environment."""

    return PurpleAIConfig(
        graphql_url="https://dev-console.company.com/web/api/v2.1/graphql",
        auth_token=os.getenv("DEV_PURPLEMCP_CONSOLE_TOKEN"),
        console_details=PurpleAIConsoleDetails(
            account_id=os.getenv("DEV_PURPLEMCP_PURPLE_AI_ACCOUNT_ID"),
            console_version="S-25.1.1#30"
        ),
        user_details=PurpleAIUserDetails(
            email_address="dev@company.com",
            user_agent="DevTools/1.0 (Development)"
        )
    )
```

### Production Configuration

```python
def create_prod_config():
    """Configuration for production environment."""

    return PurpleAIConfig(
        graphql_url="https://prod-console.company.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PROD_PURPLEMCP_CONSOLE_TOKEN"),
        console_details=PurpleAIConsoleDetails(
            account_id=os.getenv("PROD_PURPLEMCP_PURPLE_AI_ACCOUNT_ID"),
            console_version=os.getenv("PROD_PURPLEMCP_PURPLE_AI_CONSOLE_VERSION"),
            build_date=os.getenv("PROD_PURPLEMCP_PURPLE_AI_BUILD_DATE")
        ),
        user_details=PurpleAIUserDetails(
            email_address=os.getenv("PROD_PURPLEMCP_PURPLE_AI_EMAIL_ADDRESS"),
            user_agent=f"ProductionTools/{os.getenv('APP_VERSION', '1.0')}"
        )
    )
```

### Testing Configuration

```python
def create_test_config():
    """Configuration for testing environment."""
    
    return PurpleAIConfig(
        graphql_url="https://test-console.company.com/web/api/v2.1/graphql",
        auth_token="test-token",
        console_details=PurpleAIConsoleDetails(
            account_id="test-account-123",
            console_version="S-25.1.1#30"
        ),
        user_details=PurpleAIUserDetails(
            email_address="test@company.com",
            user_agent="TestSuite/1.0"
        )
    )
```

## Configuration Validation

### Automatic Validation

The library automatically validates configuration values using Pydantic validators:

```python
from pydantic import ValidationError
from purple_mcp.libs.purple_ai import PurpleAIConfig, PurpleAIConsoleDetails, PurpleAIUserDetails

try:
    # This will work - valid HTTPS URL and non-empty token
    valid_config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token="valid-token",
        user_details=PurpleAIUserDetails(
            account_id="test",
            team_token="test",
            email_address="test@example.test",
            user_agent="test",
            build_date="2025-01-01",
            build_hash="test"
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://console.example.com",
            version="1.0.0"
        )
    )

    # This will raise ValidationError - HTTP instead of HTTPS
    invalid_config = PurpleAIConfig(
        graphql_url="http://console.example.com/web/api/v2.1/graphql",  # Must be HTTPS
        auth_token="valid-token",
        user_details=PurpleAIUserDetails(
            account_id="test",
            team_token="test",
            email_address="test@example.test",
            user_agent="test",
            build_date="2025-01-01",
            build_hash="test"
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://console.example.com",
            version="1.0.0"
        )
    )

except ValidationError as e:
    print(f"Configuration validation error: {e}")

# Examples of validation errors:

# Empty auth_token after stripping whitespace
try:
    PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token="   ",  # Whitespace-only is invalid
        user_details=PurpleAIUserDetails(
            account_id="test",
            team_token="test",
            email_address="test@example.test",
            user_agent="test",
            build_date="2025-01-01",
            build_hash="test"
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://console.example.com",
            version="1.0.0"
        )
    )
except ValidationError as e:
    print("Error: auth_token cannot be empty")

# Invalid timeout (must be positive)
try:
    PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token="valid-token",
        timeout=0.0,  # Must be > 0
        user_details=PurpleAIUserDetails(
            account_id="test",
            team_token="test",
            email_address="test@example.test",
            user_agent="test",
            build_date="2025-01-01",
            build_hash="test"
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://console.example.com",
            version="1.0.0"
        )
    )
except ValidationError as e:
    print("Error: timeout must be greater than 0")

# Console base_url must be HTTPS
try:
    PurpleAIConsoleDetails(
        base_url="http://console.example.com",  # Must be HTTPS
        version="1.0.0"
    )
except ValidationError as e:
    print("Error: base_url must use HTTPS protocol")
```

### Validation Rules

The following validation rules are enforced:

**PurpleAIConfig:**
- `graphql_url`: Must start with `https://`, whitespace is stripped
- `auth_token`: Cannot be empty or whitespace-only, whitespace is stripped
- `timeout`: Must be greater than 0

**PurpleAIConsoleDetails:**
- `base_url`: Must start with `https://`

### Custom Validation

You can add additional validation on top of the built-in rules:

```python
def validate_purple_ai_config(config: PurpleAIConfig) -> bool:
    """Add custom validation on top of built-in validation."""

    # Built-in validation already checked:
    # - graphql_url uses HTTPS
    # - auth_token is not empty
    # - timeout is positive
    # - console base_url uses HTTPS

    # Additional custom checks
    if not config.graphql_url.endswith("/web/api/v2.1/graphql"):
        raise ValueError("GraphQL URL must end with /web/api/v2.1/graphql")

    if len(config.auth_token) < 10:
        raise ValueError("Service token appears to be invalid (too short)")

    print("✅ Purple AI configuration is valid")
    return True

# Usage
try:
    validate_purple_ai_config(config)
except ValueError as e:
    print(f"❌ Configuration error: {e}")
```

## Regional Console Support

Purple AI supports different regional consoles:

### US Console
```python
us_config = PurpleAIConfig(
    graphql_url="https://usea1-console.sentinelone.net/web/api/v2.1/graphql",
    auth_token="your-token"
)
```

### EU Console  
```python
eu_config = PurpleAIConfig(
    graphql_url="https://eur1-console.sentinelone.net/web/api/v2.1/graphql", 
    auth_token="your-token"
)
```

### APAC Console
```python
apac_config = PurpleAIConfig(
    graphql_url="https://apac1-console.sentinelone.net/web/api/v2.1/graphql",
    auth_token="your-token"
)
```

### Custom/Private Console
```python
custom_config = PurpleAIConfig(
    graphql_url="https://your-console.sentinelone.net/web/api/v2.1/graphql",
    auth_token="your-token"
)
```

## Security Best Practices

### 1. Secure Token Storage

Never hardcode tokens in source code:

```python
# ❌ Bad - hardcoded token
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="hardcoded-token-here"  # Security risk
)

# ✅ Good - from environment
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
)
```

### 2. Environment Separation

Use different tokens for different environments:

```python
def get_config_for_environment(env: str):
    """Get configuration based on environment."""
    
    token_map = {
        "development": os.getenv("DEV_PURPLEMCP_CONSOLE_TOKEN"),
        "staging": os.getenv("STAGING_PURPLEMCP_CONSOLE_TOKEN"),
        "production": os.getenv("PROD_PURPLEMCP_CONSOLE_TOKEN")
    }
    
    url_map = {
        "development": "https://dev-console.company.com/web/api/v2.1/graphql",
        "staging": "https://staging-console.company.com/web/api/v2.1/graphql",
        "production": "https://prod-console.company.com/web/api/v2.1/graphql"
    }
    
    return PurpleAIConfig(
        graphql_url=url_map[env],
        auth_token=token_map[env]
    )
```

### 3. Token Rotation Support

Design for token rotation:

```python
class RotatingTokenConfig:
    """Configuration that supports token rotation."""
    
    def __init__(self, graphql_url: str, token_provider):
        self.graphql_url = graphql_url
        self.token_provider = token_provider
    
    def get_current_config(self) -> PurpleAIConfig:
        """Get current config with fresh token."""
        current_token = self.token_provider()
        
        return PurpleAIConfig(
            graphql_url=self.graphql_url,
            auth_token=current_token
        )

# Usage
def get_token_from_vault():
    # Retrieve current token from secure storage
    return "current-valid-token"

rotating_config = RotatingTokenConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    token_provider=get_token_from_vault
)

# Get fresh config each time
config = rotating_config.get_current_config()
```

## Troubleshooting Configuration

### Common Issues

#### Invalid URL Format
```python
from pydantic import ValidationError

# ❌ Wrong - using HTTP instead of HTTPS (will raise ValidationError)
try:
    config = PurpleAIConfig(
        graphql_url="http://console.example.com/web/api/v2.1/graphql",  # Must be HTTPS
        auth_token="token",
        user_details=PurpleAIUserDetails(...),
        console_details=PurpleAIConsoleDetails(...)
    )
except ValidationError as e:
    print("Error: graphql_url must use HTTPS protocol")

# ❌ Wrong - missing protocol (will raise ValidationError)
try:
    config = PurpleAIConfig(
        graphql_url="console.example.com/web/api/v2.1/graphql",  # Missing https://
        auth_token="token",
        user_details=PurpleAIUserDetails(...),
        console_details=PurpleAIConsoleDetails(...)
    )
except ValidationError as e:
    print("Error: graphql_url must use HTTPS protocol")

# ✅ Correct - HTTPS URL
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="token",
    user_details=PurpleAIUserDetails(...),
    console_details=PurpleAIConsoleDetails(...)
)
```

#### Empty or Invalid Tokens
```python
from pydantic import ValidationError

# ❌ Wrong - empty token (will raise ValidationError)
try:
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token="",  # Empty token
        user_details=PurpleAIUserDetails(...),
        console_details=PurpleAIConsoleDetails(...)
    )
except ValidationError as e:
    print("Error: auth_token cannot be empty")

# ❌ Wrong - whitespace-only token (will raise ValidationError)
try:
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token="   ",  # Whitespace-only
        user_details=PurpleAIUserDetails(...),
        console_details=PurpleAIConsoleDetails(...)
    )
except ValidationError as e:
    print("Error: auth_token cannot be empty")

# ✅ Correct - real token from environment
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN"),
    user_details=PurpleAIUserDetails(...),
    console_details=PurpleAIConsoleDetails(...)
)
```

#### Invalid Timeout Values
```python
from pydantic import ValidationError

# ❌ Wrong - zero timeout (will raise ValidationError)
try:
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token="token",
        timeout=0.0,  # Must be > 0
        user_details=PurpleAIUserDetails(...),
        console_details=PurpleAIConsoleDetails(...)
    )
except ValidationError as e:
    print("Error: timeout must be greater than 0")

# ❌ Wrong - negative timeout (will raise ValidationError)
try:
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token="token",
        timeout=-10.0,  # Must be > 0
        user_details=PurpleAIUserDetails(...),
        console_details=PurpleAIConsoleDetails(...)
    )
except ValidationError as e:
    print("Error: timeout must be greater than 0")

# ✅ Correct - positive timeout
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="token",
    timeout=60.0,  # Valid positive value
    user_details=PurpleAIUserDetails(...),
    console_details=PurpleAIConsoleDetails(...)
)
```

#### Invalid Console Base URL
```python
from pydantic import ValidationError

# ❌ Wrong - HTTP console URL (will raise ValidationError)
try:
    console = PurpleAIConsoleDetails(
        base_url="http://console.example.com",  # Must be HTTPS
        version="1.0.0"
    )
except ValidationError as e:
    print("Error: base_url must use HTTPS protocol")

# ✅ Correct - HTTPS console URL
console = PurpleAIConsoleDetails(
    base_url="https://console.example.com",
    version="1.0.0"
)
```

### Testing Configuration

```python
import httpx
from purple_mcp.libs.purple_ai import ask_purple, PurpleAIConfig

async def test_purple_ai_config(config: PurpleAIConfig) -> bool:
    """Test Purple AI configuration with a simple question."""
    
    try:
        # Ask a simple question to test connectivity
        response = await ask_purple("What is SentinelOne?", config)
        
        if response and len(response) > 0:
            print("✅ Purple AI configuration is working")
            return True
        else:
            print("❌ Purple AI returned empty response")
            return False
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed - check your service token")
        elif e.response.status_code == 404:
            print("❌ GraphQL endpoint not found - check your URL")
        else:
            print(f"❌ HTTP error {e.response.status_code}: {e}")
        return False
        
    except httpx.ConnectError:
        print("❌ Cannot connect to server - check your URL and network")
        return False
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

# Usage
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
)

success = await test_purple_ai_config(config)
```

### Debug Logging

Enable debug logging to see configuration details:

```python
import logging

# Enable debug logging
logging.getLogger("purple_mcp.libs.purple_ai").setLevel(logging.DEBUG)

# This will show:
# - Configuration values (tokens will be masked)
# - HTTP requests and responses
# - GraphQL queries and responses
# - Error details
```