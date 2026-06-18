# AI Agent Guidelines for Purple MCP

This document provides essential guidelines for AI agents contributing to the Purple MCP codebase.
For comprehensive details, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Quick Reference

- **Language**: Python >=3.11
- **Package Manager**: `uv` (never use `pip install` or `uv pip`)
- **Code Quality**: Must pass `uv run ruff format`, `uv run ruff check . --fix`, and
  `uv run mypy src tests`
- **Testing**: Comprehensive tests required (unit + integration)
- **Architecture**: Strict separation between `libs/` (business logic) and `tools/` (MCP adapters)

## Project Overview

Purple MCP is a Model Context Protocol (MCP) server providing access to SentinelOne Purple AI and
Singularity Data Lake capabilities. The project emphasizes:

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

Each tool has a corresponding library in `src/purple_mcp/libs/` with standalone, reusable business
logic.

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
    session_id="abc123",
    user_agent="purple-mcp/1.0",
)

console_details = PurpleAIConsoleDetails(
    base_url="https://your-console.sentinelone.net",
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
        session_id=settings.purple_ai_session_id,
        user_agent=settings.purple_ai_user_agent,
    )

    console_details = PurpleAIConsoleDetails(
        base_url=settings.sentinelone_console_base_url,
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

**Configuration Access Rule:**

Tools MUST use `get_settings()` to access configuration. Never read environment variables directly
with `os.getenv()` or access `purple_mcp.config` module variables, as this bypasses the request
override system and breaks remote authentication mode.

```python
# ✅ CORRECT: Use get_settings()
from purple_mcp.config import get_settings

async def my_tool(query: str) -> str:
    settings = get_settings()  # Automatically applies request overrides
    # Use settings.graphql_service_token, settings.sentinelone_console_base_url, etc.

# ❌ WRONG: Direct environment variable access
import os

async def my_tool(query: str) -> str:
    token = os.getenv("PURPLEMCP_CONSOLE_TOKEN")  # Breaks remote auth!
    # This bypasses request overrides and always uses static config
```

The `get_settings()` function automatically applies request-scoped overrides when available (remote
auth mode with per-request headers) and falls back to static configuration otherwise. Direct
environment access breaks this mechanism.

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
- Block TLS bypass in release environments

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

We use pytest tooling to reduce boilerplate and ensure consistency. Use pytest fixtures and
parameterization where appropriate to reduce duplication. Fixtures used by multiple test-modules
should go in conftest.py. Use `pytest.raises` with the `match` argument to check error types and
error-message fragments. Use Mocks when necessary to prevent calls to external systems from
unit-tests.

```python
# ✅ CORRECT: Using pytest tooling for clean, maintainable tests
import json
from unittest.mock import AsyncMock, create_autospec

import pytest

from purple_mcp.libs.alerts import (
    Alert,
    AlertConnection,
    AlertHistoryConnection,
    AlertNoteConnection,
    AlertsClient,
    AlertsClientError,
    AlertsGraphQLError,
    Severity,
    Status,
)
from purple_mcp.tools import alerts
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.alerts.helpers import MockAlertsClientBuilder


@pytest.fixture()
def fake_alert() -> Alert:
    """Create a fake alert for testing."""
    alert_id = "alert-123"
    name = "Test Alert"
    severity = "HIGH"
    status = "NEW"
    timestamp = "2024-01-01T00:00:00Z"

    return Alert(
        id=alert_id,
        name=name,
        severity=Severity(severity),
        status=Status(status),
        detectedAt=timestamp,
    )


class TestGetAlert:
    """Test get_alert tool."""

    @pytest.mark.asyncio
    async def test_get_alert_success(
        self, fake_alert: Alert, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successful alert retrieval."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert = AsyncMock(return_value=fake_alert)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        result = await alerts.get_alert(fake_alert.id)

        # assert
        # check method
        mock_client.get_alert.assert_called_with(alert_id=fake_alert.id)
        # check result
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, dict)
        fake_alert_dict = fake_alert.model_dump(mode="json")
        for k, v in data.items():
            assert v == fake_alert_dict[k]

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test alert not found raises an error."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert = AsyncMock(side_effect=AlertsGraphQLError("Dummy Error"))
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        with pytest.raises(RuntimeError, match=r"Failed to retrieve alert nonexistent-alert"):
            await alerts.get_alert("nonexistent-alert")
```

#### Mocking with pytest.monkeypatch

Always use `pytest.monkeypatch` instead of `unittest.mock.patch` and use references e.g.
`.__name__` for usage safety.

```python
# ❌ WRONG: Using patch with strings
from unittest.mock import MagicMock
def test_something():
    with patch("purple_mcp.cli.Settings") as mock_settings:
        mock_settings.return_value = MagicMock()
        ...

# ✅ CORRECT: Use monkeypatch with symbolic references
import pytest
from unittest.mock import MagicMock
from purple_mcp import cli
from purple_mcp.config import Settings

def test_something(monkeypatch: pytest.MonkeyPatch):
    mock_settings = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(cli, Settings.__name__, mock_settings)
    ...
```

### Test Helper Infrastructure

**Note:** Not all libraries have test helper infrastructure. Currently, misconfigurations, and
vulnerabilities have comprehensive test helpers. Other libraries (purple_ai, sdl, inventory) use
more straightforward mocking patterns.

Libraries with test helpers provide:

- **Base test classes** (`MisconfigurationsTestBase`, etc.):
  - `assert_tool_success()`: Test successful tool execution
  - `assert_tool_error()`: Test error handling
  - `assert_tool_validation_error()`: Test parameter validation

- **Mock factory classes** (`MockAlertsClientBuilder`, etc.):
  - `create_empty_connection()`: Create empty paginated responses

- **JSON assertion helpers** (`JSONAssertions`):
  - `assert_connection_response()`: Validate paginated responses
  - `assert_error_message()`: Validate exception messages

**For libraries without test helpers** (purple_ai, sdl, etc.), use standard mocking patterns:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from purple_mcp.tools import purple_ai
from purple_mcp.libs.purple_ai import PurpleAIResultType

@pytest.mark.asyncio
async def test_purple_ai_success(monkeypatch: pytest.MonkeyPatch, mock_settings):
    """Test successful Purple AI query."""
    mock_result = (PurpleAIResultType.MESSAGE, "Test response")
    mock_ask = AsyncMock(return_value=mock_result)

    monkeypatch.setattr(purple_ai, purple_ai.get_settings.__name__, MagicMock(return_value=mock_settings()))
    monkeypatch.setattr(purple_ai, purple_ai.ask_purple.__name__, mock_ask)

    result = await purple_ai.purple_ai("test query")
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

**Important**: Use `pytest-xdist` (`-n auto`) for running multiple tests in parallel, but **do not
use it** when running a single test or test function. Running a single test with xdist adds
unnecessary overhead.

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
uv run ruff check . --fix

# 3. Run type checking (IMPORTANT: always run on full project, not individual files)
uv run mypy src tests

# 4. Run tests
uv run --group test pytest -n auto

# All checks must pass ✅
```

**Note**: When running `mypy`, always run it on the entire project scope rather than individual
files to ensure consistent type checking across all modules.

### Adding Dependencies

```bash
# ✅ CORRECT: Use uv add
uv add package-name

# ❌ WRONG: Don't use these
uv pip install package-name  # WRONG
pip install package-name     # WRONG
```

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

Library configuration classes should use `_ProgrammaticSettings` to disable environment variable
loading:

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
uv sync --all-groups
```

### Type Checking Fails

```bash
# Problem: mypy reports errors
# Solution: Add proper type hints and run mypy
uv run mypy src tests

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
6. **Document Thoroughly**: Google-style docstrings for all public functions, never reference test
   counts
7. **Use uv**: Always use `uv add`, never `pip install`
8. **Run mypy broadly**: Always run `mypy` on the full project, not individual files
9. **Use xdist wisely**: Use `-n auto` for multiple tests, but not for single test execution

## Resources

- [CONTRIBUTING.md](CONTRIBUTING.md) - Comprehensive contribution guide
- [README.md](README.md) - Project overview and setup
- [SECURITY.md](SECURITY.md) - Security guidelines
- [Python 3.11+ Docs](https://docs.python.org/3.11/)
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
