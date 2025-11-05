# AI Agent Guidelines for Purple MCP

This document provides essential guidelines for AI agents contributing to the Purple MCP codebase. For comprehensive details, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Quick Reference

- **Language**: Python >=3.10
- **Package Manager**: `uv` (never use `pip install` or `uv pip`)
- **Code Quality**: Must pass `uv run ruff format`, `uv run ruff check --fix`, and `uv run mypy`
- **Testing**: Comprehensive tests required (unit + integration)
- **Architecture**: Strict separation between `libs/` (business logic) and `tools/` (MCP adapters)

## Project Overview

Purple MCP is a Model Context Protocol (MCP) server providing access to SentinelOne Purple AI and Singularity Data Lake capabilities. The project emphasizes:

- **Simplicity, readability, maintainability over cleverness**
- **Clean separation of concerns** (Tools vs Libraries)
- **Security-first development** (HTTPS required, no secrets in code)
- **Comprehensive testing** (unit + integration with real API validation)

### Current Tools and Libraries

The project provides the following MCP tools (in `src/purple_mcp/tools/`):
- **purple_ai**: Natural language queries to Purple AI
- **sdl**: Singularity Data Lake query execution and timestamp utilities
- **alerts**: Security alerts management (list, search, get details, notes, history)
- **misconfigurations**: Cloud/Kubernetes misconfiguration management
- **vulnerabilities**: Vulnerability management and tracking
- **inventory**: Unified Asset Inventory management
- **purple_utils**: Utility tools for Purple AI (status checks, available tools)

Each tool has a corresponding library in `src/purple_mcp/libs/` with standalone, reusable business logic.

## Critical Architecture Pattern: Tools vs Libraries

This is the **most important architectural concept** in the codebase:

### Libraries (`src/purple_mcp/libs/`)

Libraries implement **standalone, reusable business logic**:

```python
# ✅ CORRECT: Library with explicit configuration
from purple_mcp.libs.purple_ai import (
    PurpleAIConfig,
    PurpleAIUserDetails,
    PurpleAIConsoleDetails,
    ask_purple,
)

user_details = PurpleAIUserDetails(
    account_id="account-123",
    team_token="team-token",
    email_address="user@example.com",
    user_agent="purple-mcp/1.0",
    build_date="2024-01-01",
    build_hash="abc123",
)

console_details = PurpleAIConsoleDetails(
    base_url="https://your-console.sentinelone.net",
    version="1.0.0",
)

config = PurpleAIConfig(
    graphql_url="https://your-console.sentinelone.net/web/api/v2.1/graphql",
    auth_token="your-auth-token",
    timeout=120.0,
    user_details=user_details,
    console_details=console_details,
)

response_type, message = await ask_purple(config, "Is Salt Typhoon in my environment?")
```

**Library Requirements:**
- ❌ No global state or singletons
- ❌ No environment variable access
- ❌ No imports from `purple_mcp.config`
- ✅ All configuration via explicit parameters
- ✅ Fully testable in isolation
- ✅ Usable outside MCP context

### Tools (`src/purple_mcp/tools/`)

Tools are **thin MCP adapters** that bridge libraries with the MCP protocol:

```python
# ✅ CORRECT: Tool that uses global config and delegates to library
from purple_mcp.config import get_settings
from purple_mcp.libs.purple_ai import (
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIUserDetails,
    ask_purple,
)

async def purple_ai(query: str) -> str:
    # 1. Get global configuration
    settings = get_settings()

    # 2. Build library-specific configuration objects
    user_details = PurpleAIUserDetails(
        account_id=settings.purple_ai_account_id,
        team_token=settings.purple_ai_team_token,
        email_address=settings.purple_ai_email_address,
        user_agent=settings.purple_ai_user_agent,
        build_date=settings.purple_ai_build_date,
        build_hash=settings.purple_ai_build_hash,
    )

    console_details = PurpleAIConsoleDetails(
        base_url=settings.sentinelone_console_base_url,
        version=settings.purple_ai_console_version,
    )

    config = PurpleAIConfig(
        graphql_url=settings.graphql_full_url,
        auth_token=settings.graphql_service_token,
        user_details=user_details,
        console_details=console_details,
    )

    # 3. Delegate to library
    response_type, raw_message = await ask_purple(config, query)

    # 4. Handle response and return MCP-compatible string
    if response_type is None:
        raise PurpleAIClientError("Purple AI request failed", details=str(raw_message))

    return str(raw_message)
```

**Tool Requirements:**
- ✅ Use `get_settings()` for configuration
- ✅ Create explicit library config objects
- ✅ Delegate business logic to libraries
- ✅ Handle MCP-specific concerns (serialization, error formatting)

### Why This Matters

❌ **WRONG** - Library with global state:
```python
# This violates the architecture and will be rejected
from purple_mcp.libs.my_lib import client  # Global client instance
result = client.query("data")  # Uses implicit global configuration
```

✅ **CORRECT** - Library with explicit config:
```python
from purple_mcp.libs.my_lib import MyClient, MyConfig

config = MyConfig(api_key="key", base_url="url")
client = MyClient(config)
result = client.query("data")
```

## Code Style Requirements

### Type Hints (Strict)

```python
# ✅ CORRECT: Complete type hints
def process_query(query: str, timeout: float = 30.0) -> dict[str, Any]:
    """Process a query with proper type hints."""
    return {"status": "success", "data": query}

# ❌ WRONG: Missing type hints
def process_query(query, timeout=30.0):
    return {"status": "success", "data": query}
```

### Documentation (Google Style)

```python
# ✅ CORRECT: Comprehensive Google-style docstring
def submit_query(query: str, timeout: float = 30.0) -> dict[str, Any]:
    """Submit a query to the Purple AI API.

    Args:
        query: The query string to submit
        timeout: Request timeout in seconds

    Returns:
        Dict containing the API response with 'status' and 'data' keys

    Raises:
        ValueError: If query is empty
        TimeoutError: If request exceeds timeout
    """
    if not query:
        raise ValueError("Query cannot be empty")
    # Implementation...
```

### Code Organization

```python
# ✅ CORRECT: Early return pattern (reduces nesting)
def validate_token(token: str) -> bool:
    """Validate authentication token."""
    if not token:
        return False

    if len(token) < 10:
        return False

    return token.startswith("sk-")

# ❌ WRONG: Nested conditions
def validate_token(token: str) -> bool:
    """Validate authentication token."""
    if token:
        if len(token) >= 10:
            if token.startswith("sk-"):
                return True
    return False
```

### Naming Conventions

- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Handler functions: Prefix with `handle_` (e.g., `handle_api_error`)

## Security Requirements

### Never Commit Secrets

```python
# ✅ CORRECT: Use environment variables
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_token: str = Field(..., alias="API_TOKEN")

# ❌ WRONG: Hardcoded credentials
API_TOKEN = "sk-1234567890abcdef"  # NEVER DO THIS
```

### HTTPS Required

```python
# ✅ CORRECT: Validate HTTPS
@field_validator("base_url")
@classmethod
def validate_base_url(cls, v: str) -> str:
    """Validate that the URL uses HTTPS."""
    if not v.startswith("https://"):
        raise ValueError("URL must use HTTPS (https://)")
    return v
```

### TLS Verification

- Default to TLS verification enabled
- Issue strong warnings when TLS verification disabled
- Block TLS bypass in production environments

## Testing Requirements

### Test Structure

```
tests/
├── unit/                          # Unit tests (isolated, mocked)
│   ├── conftest.py                # Unit test fixtures
│   ├── tools/                     # Tool-level unit tests
│   │   └── test_*.py
│   ├── libs/                      # Library-specific tests
│   │   ├── alerts/
│   │   │   ├── helpers/           # Test helpers (base classes, factories, assertions)
│   │   │   └── test_*.py
│   │   ├── misconfigurations/
│   │   │   ├── helpers/
│   │   │   └── test_*.py
│   │   └── vulnerabilities/
│   │       ├── helpers/
│   │       └── test_*.py
│   └── test_*.py                  # General unit tests (config, utils, etc.)
└── integration/                   # Integration tests (real APIs)
    ├── conftest.py                # Integration test fixtures
    └── test_*_integration.py
```

### Writing Tests

We use test helper infrastructure to reduce boilerplate and ensure consistency. Tests follow established patterns with base classes, mock factories, and assertion helpers.

```python
# ✅ CORRECT: Using test helpers for clean, maintainable tests
import pytest
from unittest.mock import Mock, patch

from purple_mcp.tools import alerts
from purple_mcp.libs.alerts import AlertsClientError

from tests.unit.libs.alerts.helpers import (
    AlertsTestBase,
    AlertsTestData,
    JSONAssertions,
)

class TestGetAlert(AlertsTestBase):
    """Test get_alert tool."""

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_success(self, mock_get_client: Mock) -> None:
        """Test successful alert retrieval."""
        mock_alert = AlertsTestData.create_test_alert()

        result = await self.assert_tool_success(
            alerts.get_alert,
            mock_get_client,
            mock_alert,
            "get_alert",
            tool_args={"alert_id": "alert-123"},
        )

        # Verify JSON response
        JSONAssertions.assert_alert_response(result, "alert-123")

    @patch("purple_mcp.tools.alerts._get_alerts_client")
    @pytest.mark.asyncio
    async def test_get_alert_client_error(self, mock_get_client: Mock) -> None:
        """Test client error handling."""
        await self.assert_tool_error(
            alerts.get_alert,
            mock_get_client,
            AlertsClientError("Network error"),
            "get_alert",
            "Failed to retrieve alert alert-123",
            tool_args={"alert_id": "alert-123"},
        )
```

### Test Helper Infrastructure

**Note:** Not all libraries have test helper infrastructure. Currently, alerts, misconfigurations, and vulnerabilities have comprehensive test helpers. Other libraries (purple_ai, sdl, inventory) use more straightforward mocking patterns.

Libraries with test helpers provide:

- **Base test classes** (`AlertsTestBase`, `MisconfigurationsTestBase`, etc.):
  - `assert_tool_success()`: Test successful tool execution
  - `assert_tool_error()`: Test error handling
  - `assert_tool_validation_error()`: Test parameter validation

- **Mock factory classes** (`MockAlertsClientBuilder`, etc.):
  - `create_mock()`: Create configured mock clients
  - `create_empty_connection()`: Create empty paginated responses

- **JSON assertion helpers** (`JSONAssertions`):
  - `assert_connection_response()`: Validate paginated responses
  - `assert_alert_response()`: Validate alert data structure
  - `assert_error_message()`: Validate exception messages

- **Test data factories** (`AlertsTestData`, etc.):
  - `create_test_alert()`: Create test Alert objects
  - `create_test_note()`: Create test Note objects

Example helper usage:
```python
from tests.unit.libs.alerts.helpers import AlertsTestData

# Create test data with defaults
alert = AlertsTestData.create_test_alert()

# Create test data with custom values
alert = AlertsTestData.create_test_alert(
    alert_id="custom-123",
    severity="HIGH",
    status="NEW"
)
```

**For libraries without test helpers** (purple_ai, sdl, etc.), use standard mocking patterns:
```python
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
async def test_purple_ai_success(mock_settings):
    """Test successful Purple AI query."""
    mock_result = (PurpleAIResultType.MESSAGE, "Test response")

    with (
        patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
        patch("purple_mcp.tools.purple_ai.ask_purple", new_callable=AsyncMock) as mock_ask,
    ):
        mock_ask.return_value = mock_result
        result = await purple_ai("test query")
        assert result == "Test response"
        mock_ask.assert_called_once()
```

### Running Tests

```bash
# Run all tests in parallel (recommended)
uv run --group test pytest -n auto

# Run unit tests only
uv run --group test pytest tests/unit/ -n auto

# Run specific test file or function (without xdist for single tests)
uv run --group test pytest tests/unit/tools/test_purple_ai.py::test_specific_function

# Run with coverage
uv run --group test pytest -n auto --cov=src/purple_mcp --cov-report=html
```

**Important**: Use `pytest-xdist` (`-n auto`) for running multiple tests in parallel, but **do not use it** when running a single test or test function. Running a single test with xdist adds unnecessary overhead.

### Test Requirements

- ✅ Test happy paths and error conditions
- ✅ Use descriptive test names: `test_<component>_<behavior>_<expected_result>`
- ✅ Mock external dependencies (APIs, databases)
- ✅ Tests must be parallel-safe (no shared mutable state)
- ✅ Use `.test` TLD for unit tests: When creating test URLs, use `.test` as the top-level domain

## Development Workflow

### Before Every Commit

```bash
# 1. Format code
uv run ruff format

# 2. Run linting and auto-fix
uv run ruff check --fix

# 3. Run type checking (IMPORTANT: always run on full project, not individual files)
uv run mypy

# 4. Run tests
uv run --group test pytest -n auto

# All checks must pass ✅
```

**Note**: When running `mypy`, always run it on the entire project scope rather than individual files to ensure consistent type checking across all modules.

### Adding Dependencies

```bash
# ✅ CORRECT: Use uv add
uv add package-name

# ❌ WRONG: Don't use these
uv pip install package-name  # WRONG
pip install package-name      # WRONG
```

`uv pip` in only allowed in the validate_submodules.py script.

### Creating a New Feature

1. **Plan the architecture**:
   - Business logic → `libs/` (explicit config)
   - MCP interface → `tools/` (uses `get_settings()`)

2. **Write tests first** (TDD when possible)

3. **Implement library** (`libs/`):
   - Standalone, no global state
   - Explicit configuration
   - Comprehensive docstrings

4. **Implement tool** (`tools/`):
   - Thin wrapper around library
   - Uses `get_settings()`
   - MCP-compatible return types

5. **Run quality checks** (format, lint, type check, test)

6. **Update documentation** if needed

## Common Patterns

### Error Handling

```python
# ✅ CORRECT: Structured exception hierarchy
class SDLError(Exception):
    """Base exception for SDL operations."""

class SDLAuthenticationError(SDLError):
    """Authentication failed for SDL operations."""

class SDLQueryError(SDLError):
    """Query execution failed."""

# Usage
try:
    result = await execute_query(query)
except SDLAuthenticationError as e:
    logger.exception("Authentication failed.")
    raise
except SDLQueryError as e:
    logger.exception("Query failed.")
```

### Configuration Patterns

Library configuration classes should use `_ProgrammaticSettings` to disable environment variable loading:

```python
# ✅ CORRECT: Library config that only accepts programmatic initialization
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class _ProgrammaticSettings(BaseSettings):
    """Base class to disable environment variable loading for settings."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Disable all settings sources except for programmatic initialization."""
        return (init_settings,)


class MyLibConfig(_ProgrammaticSettings):
    """Configuration for MyLib."""

    api_token: str = Field(..., description="API authentication token")
    base_url: str = Field(..., description="Base URL for API")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("URL must use HTTPS")
        return v.rstrip("/")

    @field_validator("api_token")
    @classmethod
    def validate_api_token(cls, v: str) -> str:
        """Validate that api_token is not empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("api_token cannot be empty")
        return stripped
```

**Why `_ProgrammaticSettings`?**
- Ensures library configs are **explicit** and never read from environment variables
- Prevents accidental coupling to global environment state
- Makes libraries fully testable and reusable outside MCP context

### Async Patterns

```python
# ✅ CORRECT: Async context manager for HTTP clients
import httpx

async def fetch_data(url: str, token: str) -> dict[str, Any]:
    """Fetch data from API using async context manager."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
```

## Quick Troubleshooting

### Import Errors

```bash
# Problem: ModuleNotFoundError: No module named 'purple_mcp'
# Solution: Install project with dependencies
uv sync --group dev --group test
```

### Type Checking Fails

```bash
# Problem: mypy reports errors
# Solution: Add proper type hints and run mypy
uv run mypy

# Check specific file
uv run mypy src/purple_mcp/libs/my_module.py

# Check specific directory
uv run mypy tests/unit/
```

### Tests Fail

```bash
# Problem: Tests fail or can't be found
# Solution: Ensure test dependencies installed
uv sync --group test

# Run specific test file
uv run --group test pytest tests/unit/test_config.py -v
```

## Key Takeaways for AI Agents

1. **Architecture First**: Always separate business logic (libs/) from MCP interface (tools/)
2. **No Global State in Libraries**: Libraries must have explicit configuration
3. **Type Everything**: Strict type hints required (`mypy` strict mode)
4. **Security Conscious**: HTTPS required, no secrets in code, validate inputs
5. **Test Comprehensively**: Unit tests + integration tests required
6. **Document Thoroughly**: Google-style docstrings for all public functions, never reference test counts
7. **Use uv**: Always use `uv add`, never `pip install`
8. **Run mypy broadly**: Always run `mypy` on the full project, not individual files
9. **Use xdist wisely**: Use `-n auto` for multiple tests, but not for single test execution

## Resources

- [CONTRIBUTING.md](CONTRIBUTING.md) - Comprehensive contribution guide
- [README.md](README.md) - Project overview and setup
- [SECURITY.md](SECURITY.md) - Security guidelines
- [Python 3.10+ Docs](https://docs.python.org/3.10/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Questions?

When in doubt, follow these principles:

1. Check existing code for patterns
2. Prefer simplicity over cleverness
3. Write code that's easy to test
4. Use explicit configuration over implicit
5. Default to secure options

For detailed guidance on any topic, refer to [CONTRIBUTING.md](CONTRIBUTING.md).
