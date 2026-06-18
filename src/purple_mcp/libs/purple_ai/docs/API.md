# Purple AI API Reference

Complete reference for the Purple AI Library API.

## Core Functions

### `ask_purple(question: str, config: PurpleAIConfig) -> tuple[PurpleAIResultType | None, str]`

Ask Purple AI a question asynchronously.

**Parameters:**

- `question` (str): The question to ask Purple AI
- `config` (PurpleAIConfig): Configuration for Purple AI connection

**Returns:** Tuple of `(result_type, response_text)`

- `result_type` (PurpleAIResultType | None): Type of response (`MESSAGE` or `POWER_QUERY`), or
  `None` on error
- `response_text` (str): Purple AI's response text or error message

**Example:**

```python
import asyncio
from purple_mcp.libs.purple_ai import (
    ask_purple,
    PurpleAIConfig,
    PurpleAIUserDetails,
    PurpleAIConsoleDetails,
    PurpleAIResultType,
)

async def main():
    config = PurpleAIConfig(
        graphql_url="https://console.sentinelone.net/web/api/v2.1/graphql",
        auth_token="your-service-token",
        user_details=PurpleAIUserDetails(
            user_agent="MyApp/1.0",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://console.sentinelone.net",
        ),
    )

    # Unpack the result tuple
    result_type, response = await ask_purple(
        "Are there any suspicious processes running?", config
    )

    if result_type is None:
        print(f"Error: {response}")
    elif result_type == PurpleAIResultType.MESSAGE:
        print(f"Purple AI: {response}")
    elif result_type == PurpleAIResultType.POWER_QUERY:
        print(f"Power Query: {response}")

asyncio.run(main())
```

### `sync_ask_purple(question: str, config: PurpleAIConfig) -> str`

Ask Purple AI a question synchronously.

**Parameters:**

- `question` (str): The question to ask Purple AI
- `config` (PurpleAIConfig): Configuration for Purple AI connection

**Returns:** Purple AI's response as a string

**Example:**

```python
from purple_mcp.libs.purple_ai import sync_ask_purple, PurpleAIConfig, PurpleAIUserDetails, PurpleAIConsoleDetails

config = PurpleAIConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/graphql",
    auth_token="your-service-token",
    user_details=PurpleAIUserDetails(
        user_agent="MyApp/1.0",
    ),
    console_details=PurpleAIConsoleDetails(
        base_url="https://console.sentinelone.net",
    )
)

response = sync_ask_purple("What are the latest security alerts?", config)
print(response)
```

## Configuration Classes

### PurpleAIConfig

Main configuration class for Purple AI connection.

#### Constructor

```python
PurpleAIConfig(
    graphql_url: str,
    auth_token: str,
    user_details: PurpleAIUserDetails,
    console_details: PurpleAIConsoleDetails
)
```

#### Fields

- `graphql_url: str` - GraphQL endpoint URL for SentinelOne console
- `auth_token: str` - Service token for authentication
- `timeout: float` - Request timeout in seconds (default: 120.0)
- `user_details: PurpleAIUserDetails` - User-specific details (required)
- `console_details: PurpleAIConsoleDetails` - Console-specific details (required)

#### Example

```python
from purple_mcp.libs.purple_ai import (
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIUserDetails
)

config = PurpleAIConfig(
    graphql_url="https://console.sentinelone.net/web/api/v2.1/graphql",
    auth_token="your-service-token",
    console_details=PurpleAIConsoleDetails(
        base_url="https://console.sentinelone.net",
    ),
    user_details=PurpleAIUserDetails(
        user_agent="MyApp/1.0",
    )
)
```

### PurpleAIConsoleDetails

Console-specific configuration details.

#### Constructor

```python
PurpleAIConsoleDetails(
    base_url: str,
    tenant_id: str | None = None,
    account_id: str | None = None,
    site_id: str | None = None,
)
```

#### Fields

- `base_url: str` - Base URL of the console
- `version: str` - Version of the console (defaults to `S`)
- `console_id: str | None` - Console (deployment) ID
- `tenant_id: str | None` - Tenant scope ID
- `account_id: str | None` - Account scope ID
- `site_id: str | None` - Site scope ID

#### Example

```python
console_details = PurpleAIConsoleDetails(
    base_url="https://console.example.com",
    tenant_id="1234567890123456789",
    account_id="1234567890123456789",
    site_id="1234567890123456789",
)
```

### PurpleAIUserDetails

User-specific configuration details.

#### Constructor

```python
PurpleAIUserDetails(
    session_id: str | None,
    email_address: str | None = None,
    user_agent: str | None,
    build_date: str | None = None,
    build_hash: str | None = None,
    user_time: datetime | None = datetime.now().astimezone(),
)
```

#### Fields

- `session_id: str | None` - Session ID for the user
- `email_address: str | None` - Email address of the user
- `user_agent: str | None` - User agent for the request
- `build_date: str | None` - Build date of the client
- `build_hash: str | None` - Build hash of the client
- `user_time: datetime | None` - Timezone-aware local timestamp of the request. Defaults to the
  current local time; pass `None` to omit it.

#### Example

```python
user_details = PurpleAIUserDetails(
    session_id="abc123",
    email_address="security.analyst@company.com",
    user_agent="SecurityTools/2.1 (Python/3.11)",
    build_date="2025-01-15",
    build_hash="abc123def"
)
```

## Enums

### PurpleAIResultType

Enumeration of possible Purple AI response types.

#### Values

- `MESSAGE` - Text message response with analysis/recommendations
- `POWER_QUERY` - SDL PowerQuery code for data analysis

#### Example

```python
from purple_mcp.libs.purple_ai import PurpleAIResultType

# The response type is automatically determined by Purple AI
# You can check what type was returned, but cannot control it directly
if response_type == PurpleAIResultType.MESSAGE:
    print("Purple AI returned a text message")
elif response_type == PurpleAIResultType.POWER_QUERY:
    print("Purple AI returned a PowerQuery")
```

## Internal Functions

These functions are used internally but may be useful for advanced usage:

### `_random_conv_id(length: int) -> str`

Generate a random conversation ID.

**Parameters:**

- `length` (int): Length of the ID to generate

**Returns:** Random alphanumeric string

**Example:**

```python
from purple_mcp.libs.purple_ai.client import _random_conv_id

conv_id = _random_conv_id(16)  # "a1B2c3D4e5F6g7H8"
```

## GraphQL Integration

The library communicates with SentinelOne's GraphQL API. While you typically don't need to interact
with GraphQL directly, understanding the structure can be helpful.

### GraphQL Query Structure

The library sends queries similar to:

```graphql
mutation askPurple($input: AskPurpleInput!) {
  askPurple(input: $input) {
    resultType
    result
    conversationId
  }
}
```

### Input Variables

The `AskPurpleInput` includes:

- `question`: The user's question
- `conversationId`: Unique conversation identifier
- `consoleDetails`: Console URL and (optionally) scope information
- `userDetails`: User context information

## Error Handling

### Common Exceptions

The library may raise standard Python exceptions:

#### `httpx.HTTPError`

Network-related errors when communicating with the GraphQL API.

```python
import httpx
from purple_mcp.libs.purple_ai import ask_purple, PurpleAIConfig

try:
_result_type, response = await ask_purple("What threats exist?", config)
except httpx.HTTPError as e:
    print(f"Network error: {e}")
```

#### `ValueError`

Configuration or input validation errors.

```python
try:
    # Missing required environment variable
_result_type, response = await ask_purple("Question", config_with_missing_token)
except ValueError as e:
    print(f"Configuration error: {e}")
```

#### `KeyError`

Missing expected fields in API response.

```python
try:
_result_type, response = await ask_purple("Question", config)
except KeyError as e:
    print(f"API response missing expected field: {e}")
```

### Error Handling Patterns

#### Robust Error Handling

```python
import asyncio
import httpx
from purple_mcp.libs.purple_ai import ask_purple, PurpleAIConfig

async def robust_purple_ai_query(question: str, config: PurpleAIConfig) -> str | None:
    """Ask Purple AI with comprehensive error handling."""

    try:
_result_type, response = await ask_purple(question, config)
        return response

    except ValueError as e:
        print(f"Configuration error: {e}")
        return None

    except httpx.TimeoutException:
        print("Request timed out - Purple AI may be busy")
        return None

    except httpx.HTTPStatusError as e:
        print(f"HTTP error {e.response.status_code}: {e}")
        return None

    except httpx.HTTPError as e:
        print(f"Network error: {e}")
        return None

    except KeyError as e:
        print(f"Unexpected API response format: {e}")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

#### Retry Logic

```python
import asyncio
from typing import Optional

async def ask_purple_with_retry(
    question: str,
    config: PurpleAIConfig,
    max_retries: int = 3,
    delay: float = 1.0
) -> Optional[str]:
    """Ask Purple AI with retry logic."""

    for attempt in range(max_retries):
        try:
_result_type, response = await ask_purple(question, config)
            return response

        except httpx.HTTPError as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return None

            print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff

    return None
```

## Advanced Usage

### Custom HTTP Client Configuration

While the library uses httpx internally with default settings, you can understand the HTTP
behavior:

```python
# The library internally uses these settings:
# - Timeout: Configurable via PurpleAIConfig.timeout (default: 120.0 seconds)
# - SSL verification: Enabled
# - Follow redirects: Enabled
# - Headers: Authorization with Bearer token

# To customize the timeout:
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token="your-token",
    timeout=60.0  # Custom 60-second timeout
)
```

### Environment Variable Integration

The library can use environment variables for configuration:

```python
import os
from purple_mcp.libs.purple_ai import PurpleAIConfig

def create_config_from_env():
    """Create Purple AI config from environment variables."""

    return PurpleAIConfig(
        graphql_url=os.getenv("PURPLEMCP_CONSOLE_BASE_URL", "").rstrip("/") + "/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN", ""),
        user_details=PurpleAIUserDetails(
            user_agent=os.getenv("PURPLEMCP_PURPLE_AI_USER_AGENT", "MyPurpleMCP"),
        ),
        console_details=PurpleAIConsoleDetails(
            base_url=os.getenv("PURPLEMCP_CONSOLE_BASE_URL"),
        )
    )

# Usage
config = create_config_from_env()
```

### Conversation Context

Each Purple AI interaction generates a unique conversation ID. The library handles this
automatically, but you can understand the flow:

1. Generate random conversation ID
2. Send question with conversation ID
3. Purple AI maintains context within that conversation
4. Each new function call starts a new conversation

```python
# Each call to ask_purple() starts a new conversation
_result_type, response1 = await ask_purple("What threats exist?", config)  # Conversation A
_result_type, response2 = await ask_purple("Tell me more details", config)  # Conversation B (new context)
```

## Testing Support

### Mock Configuration

For testing, you can create mock configurations:

```python
from purple_mcp.libs.purple_ai import PurpleAIConfig

# Test configuration
test_config = PurpleAIConfig(
    graphql_url="https://test.example.com/web/api/v2.1/graphql",
    auth_token="test-token",
    user_details=PurpleAIUserDetails(
        user_agent="TestClient/1.0",
    ),
    console_details=PurpleAIConsoleDetails(
        base_url="https://test.example.com",
    )
)
```

### Integration Testing

For integration tests with real Purple AI:

```python
import os
import pytest
from purple_mcp.libs.purple_ai import ask_purple, PurpleAIConfig

@pytest.mark.asyncio
async def test_purple_ai_integration():
    """Test Purple AI integration (requires real credentials)."""

    # Skip if no credentials
    if not os.getenv("PURPLEMCP_CONSOLE_TOKEN"):
        pytest.skip("No PURPLEMCP_CONSOLE_TOKEN set for integration test")

    config = PurpleAIConfig(
        graphql_url=os.getenv("PURPLEMCP_CONSOLE_BASE_URL") + "/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN"),
        user_details=PurpleAIUserDetails(
            user_agent=os.getenv("PURPLEMCP_PURPLE_AI_USER_AGENT", "IntegrationTest/1.0"),
        ),
        console_details=PurpleAIConsoleDetails(
        )
    )

_result_type, response = await ask_purple("What is SentinelOne?", config)

    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)
```
