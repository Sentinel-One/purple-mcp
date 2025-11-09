# Contributing to Purple MCP

Thank you for your interest in contributing to the Purple MCP project! This document outlines our development standards, code style, and contribution process.

## Table of Contents

- [Development Philosophy](#development-philosophy)
- [Getting Started](#getting-started)
- [Architecture: Tools vs Libraries](#architecture-tools-vs-libraries)
- [Code Style and Standards](#code-style-and-standards)
- [Development Workflow](#development-workflow)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Security Guidelines](#security-guidelines)
- [Pull Request Process](#pull-request-process)
- [Code Review Guidelines](#code-review-guidelines)

## Development Philosophy

Purple MCP follows these core principles:

- **Simplicity, readability, maintainability over cleverness**
- **Consider performance without sacrificing clarity**
- **Write testable, reusable code**
- **Less code = less debt**
- **Build iteratively, test frequently**
- **Clean core logic, push implementation details to edges**

## Getting Started

### Prerequisites

- **Python >=3.10**
- **uv**: Modern Python package manager (required for dependency management)
- **Git**: Version control

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd purple-mcp

# Initialize Git submodules for source code reference (optional)
# Contains fastmcp and pydantic-ai source code for reference
git submodule update --init

# Install all dependencies (development and test)
uv sync --group dev --group test
```

### Project Structure

```
src/purple_mcp/
├── cli.py                      # Command-line interface
├── server.py                   # FastMCP server implementation
├── config.py                   # Configuration management
├── libs/                       # Core business logic
│   ├── purple_ai/             # Purple AI client implementation
│   ├── sdl/                   # SDL integration library
│   ├── alerts/                # Unified Alerts Management library
│   ├── misconfigurations/     # Security misconfigurations library
│   ├── vulnerabilities/       # Vulnerabilities management library
│   └── inventory/             # Unified Asset Inventory library
└── tools/                     # MCP tool implementations
    ├── purple_ai.py           # Purple AI MCP tool
    ├── purple_utils.py        # Purple AI utility tools
    ├── sdl.py                 # SDL PowerQuery MCP tool
    ├── alerts.py              # Alerts MCP tools
    ├── misconfigurations.py   # Misconfigurations MCP tools
    ├── vulnerabilities.py     # Vulnerabilities MCP tools
    └── inventory.py           # Inventory MCP tools
```

### Git Submodules

The project includes Git submodules for dependency source code reference:

```
deps/
├── fastmcp/                   # FastMCP framework source
└── pydantic-ai/              # Pydantic-AI evaluation framework source
```

These submodules are **optional** and provide source code for reference during development. They are not required for building or running the project.

To work with submodules:

```bash
# Initialize and fetch all submodules
git submodule update --init --recursive

# Update submodules to latest commit
git submodule update --remote

# Clone including submodules
git clone --recurse-submodules <repository-url>
```

**Note**: All submodules use HTTPS URLs for consistent access without SSH keys.

### Docker

Build and run the Docker image locally:

```bash
# Build locally
DOCKER_BUILDKIT=1 docker build -t purple-mcp:dev .

# Test a specific mode
export PURPLEMCP_CONSOLE_TOKEN="your_token"
export PURPLEMCP_CONSOLE_BASE_URL="https://your-console.sentinelone.net"

docker run -p 8000:8000 \
  -e PURPLEMCP_CONSOLE_TOKEN \
  -e PURPLEMCP_CONSOLE_BASE_URL \
  purple-mcp:dev \
  --mode streamable-http

# Test all modes with compose
cat > .env << EOF
PURPLEMCP_CONSOLE_TOKEN=your_token
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net
EOF

docker compose --profile all up
```

Note: For production deployments, build the image locally and push to your container registry. See [DOCKER.md](DOCKER.md) for deployment options and [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) for production with authentication.

## Architecture: Tools vs Libraries

Purple MCP follows a strict separation between **libraries** (`libs/`) and **tools** (`tools/`). Understanding this distinction is crucial for contributors:

### Libraries (`src/purple_mcp/libs/`)

Libraries are **standalone, reusable components** that implement core business logic:

- **No Global State**: Libraries must not maintain any global configuration objects or singletons
- **Explicit Configuration**: All configuration must be passed explicitly via constructor parameters or function arguments
- **Environment-Agnostic**: Libraries should not directly read environment variables or access global settings
- **Testable**: Can be unit tested in isolation without external dependencies
- **Reusable**: Can be imported and used in any Python project

**Example - Good Library Design**:
```python
# ✅ Good: Explicit configuration required
from purple_mcp.libs.sdl import create_sdl_settings, SDLPowerQueryHandler

settings = create_sdl_settings(
    base_url="https://example.com",
    auth_token="Bearer your-token",
    http_timeout=60
)

handler = SDLPowerQueryHandler(
    auth_token=settings.auth_token,
    base_url=settings.base_url,
    settings=settings
)
```

**Example - Bad Library Design**:
```python
# ❌ Bad: Using global state or implicit configuration
from purple_mcp.libs.sdl import handler  # Global instance

# This would be wrong - no explicit configuration
result = await handler.execute_query("query")
```

### Tools (`src/purple_mcp/tools/`)

Tools are **MCP interface adapters** that bridge libraries with the MCP protocol:

- **Configuration Integration**: Tools read from the global `get_settings()` configuration
- **Library Instantiation**: Tools create library instances with explicit configuration
- **Protocol Adaptation**: Tools handle MCP-specific concerns (serialization, error handling)
- **Business Logic Delegation**: Tools delegate actual work to libraries

**Example - Tool Implementation Pattern**:
```python
async def my_tool(query: str) -> str:
    # 1. Get global configuration
    settings = get_settings()
    
    # 2. Create explicit library configuration
    lib_config = MyLibConfig(
        api_url=settings.my_service_url,
        auth_token=settings.my_service_token
    )
    
    # 3. Instantiate library with explicit config
    client = MyLibClient(lib_config)
    
    # 4. Delegate to library
    result = await client.perform_operation(query)
    
    # 5. Return MCP-compatible response
    return str(result)
```

### Library Configuration Pattern

Libraries should use `_ProgrammaticSettings` to ensure explicit configuration:

```python
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

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("URL must use HTTPS")
        return v.rstrip("/")
```

**Why this pattern?**
- Prevents libraries from reading environment variables
- Ensures explicit configuration only
- Makes libraries truly standalone and reusable
- Improves testability

### Implementation Guidelines

When implementing new functionality:

1. **Start with the Library**: Implement core logic as a standalone library with explicit configuration
2. **Use `_ProgrammaticSettings`**: Ensure library configs only accept programmatic initialization
3. **Add the Tool**: Create a thin MCP adapter that uses the library
4. **Test Separately**: Unit test the library independently, integration test the tool
5. **Document Both**: Libraries need API docs, tools need usage examples

## Code Style and Standards

### Python Standards

- **Target Python >=3.10**
- **Pass mypy strict mode**: All code must pass type checking
- **Pass ruff checks and formatting**: Code style is enforced
- **PEP 8 naming conventions**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants

### Type Hints

```python
# ✅ Good: Comprehensive type hints
def process_query(query: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Process a query with proper type hints."""
    return {"status": "success", "data": query}

# ❌ Bad: Missing type hints
def process_query(query, timeout=30.0):
    return {"status": "success", "data": query}
```

### Documentation Standards

- **Google-style docstrings**: Use consistent docstring format
- **f-strings for formatting**: Prefer f-strings over other formatting methods, except in logging
- **Comprehensive module docstrings**: Every module should have a detailed docstring
- **No test counts in docs**: Documentation should never reference test counts as they become outdated

```python
# ✅ Good: Google-style docstring
def submit_query(query: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Submit a query to the Purple AI API.
    
    Args:
        query: The query string to submit
        timeout: Request timeout in seconds
        
    Returns:
        Dict containing the API response
        
    Raises:
        ValueError: If query is empty
        TimeoutError: If request times out
    """
    if not query:
        raise ValueError("Query cannot be empty")
    # Implementation...
```

### Code Organization

- **Use early returns**: Reduce nesting with early returns
- **Descriptive names**: Use clear, descriptive variable and function names
- **Prefix handlers with "handle"**: `handle_api_error`, `handle_timeout`
- **Use typed constants over functions when possible**
- **Follow DRY principles**: Don't repeat yourself
- **Prefer functional/immutable approaches**

```python
# ✅ Good: Early return pattern
def validate_token(token: str) -> bool:
    """Validate authentication token."""
    if not token:
        return False
    
    if len(token) < 10:
        return False
    
    return token.startswith("sk-")

# ❌ Bad: Nested conditions
def validate_token(token: str) -> bool:
    """Validate authentication token."""
    if token:
        if len(token) >= 10:
            if token.startswith("sk-"):
                return True
    return False
```

### Error Handling

- **Use structured exception hierarchy**: Custom exceptions for different error types
- **Provide actionable error messages**: Help users understand what went wrong
- **Log errors appropriately**: Use proper logging levels
- **Never expose sensitive information**: Sanitize error messages

```python
# ✅ Good: Structured error handling
class SDLError(Exception):
    """Base exception for SDL operations."""
    pass

class SDLAuthenticationError(SDLError):
    """Authentication failed for SDL operations."""
    pass

def authenticate_sdl(token: str) -> None:
    """Authenticate with SDL API."""
    if not token:
        raise SDLAuthenticationError("SDL token is required")
    
    # Authentication logic...
```

### Security Guidelines

- **Never commit secrets**: Use environment variables for sensitive data
- **Validate all inputs**: Use Pydantic for comprehensive validation
- **Use HTTPS by default**: Require secure connections
- **Implement TLS verification warnings**: Strong warnings for TLS bypass
- **Log security-relevant events**: Monitor for suspicious activity

```python
# ✅ Good: Security-aware configuration
@field_validator("skip_tls_verify")
@classmethod
def validate_tls_config(cls, v: bool) -> bool:
    """Validate TLS configuration with security warnings."""
    if v:
        # Check for production environment
        env = os.getenv("PURPLEMCP_ENV", "production").lower()
        if env in ("production", "prod"):
            raise ValueError(
                "TLS verification bypass is FORBIDDEN in production environments"
            )

        # Issue strong security warning
        warnings.warn(
            "SECURITY WARNING: TLS certificate verification is DISABLED!",
            UserWarning,
            stacklevel=3,
        )

    return v
```

## Development Workflow

### 1. Dependency Management

**Always use uv commands for dependency management:**

```bash
# ✅ Good: Use uv for package management
uv add package-name
uv run tool-name

# ❌ Bad: Don't use these
uv pip install package-name
pip install package-name
```

### 2. Code Quality Checks

Run these commands before committing:

```bash
# Format code
uv run ruff format

# Run linting and fix issues
uv run ruff check --fix

# Run type checking
# IMPORTANT: Always run mypy on the full project, not individual files
uv run mypy

# All checks must pass before commits
```

**Note**: When running `mypy`, always run it on the entire project scope rather than individual files to ensure consistent type checking across all modules.

### 3. Development Process

1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Write tests first**: Follow TDD when possible
3. **Implement feature**: Follow code style guidelines
4. **Run quality checks**: Ensure all checks pass
5. **Update documentation**: Keep docs current
6. **Submit pull request**: Follow PR guidelines

## Testing Requirements

### Test Structure

```
tests/
├── unit/                       # Unit tests
│   ├── conftest.py            # Unit test fixtures
│   ├── tools/                 # Tool-level unit tests
│   │   └── test_*.py
│   ├── libs/                  # Library-specific tests
│   │   ├── alerts/
│   │   │   ├── helpers/       # Test helpers (base classes, factories)
│   │   │   └── test_*.py
│   │   ├── misconfigurations/
│   │   │   ├── helpers/
│   │   │   └── test_*.py
│   │   └── vulnerabilities/
│   │       ├── helpers/
│   │       └── test_*.py
│   └── test_*.py              # General unit tests (config, utils, etc.)
└── integration/               # Integration tests
    ├── conftest.py            # Integration test fixtures
    └── test_*_integration.py  # Integration tests
```

### Testing Standards

- **Write tests for all features**: Aim for 80%+ coverage
- **Use proper fixtures**: Shared test setup in conftest.py
- **Test error conditions**: Don't just test happy paths
- **Use descriptive test names**: `test_purple_ai_handles_authentication_error`
- **Mock external dependencies**: Use proper mocking for external APIs
- **Use `.test` TLD for unit tests**: When creating test URLs, use `.test` as the top-level domain

### Test Helper Infrastructure

Some libraries (alerts, misconfigurations, vulnerabilities) have comprehensive test helper infrastructure:

- **Base test classes**: `AlertsTestBase`, `MisconfigurationsTestBase`, etc.
  - `assert_tool_success()`: Test successful tool execution
  - `assert_tool_error()`: Test error handling
  - `assert_tool_validation_error()`: Test parameter validation

- **Mock factory classes**: `MockAlertsClientBuilder`, etc.
  - `create_mock()`: Create configured mock clients
  - `create_empty_connection()`: Create empty paginated responses

- **JSON assertion helpers**: `JSONAssertions`
  - `assert_connection_response()`: Validate paginated responses
  - `assert_alert_response()`: Validate alert data structure
  - `assert_error_message()`: Validate exception messages

- **Test data factories**: `AlertsTestData`, etc.
  - `create_test_alert()`: Create test Alert objects
  - `create_test_note()`: Create test Note objects

For libraries without test helpers (purple_ai, sdl, inventory), use standard mocking patterns as shown in examples.

```python
# ✅ Good: Comprehensive test with mocking
@pytest.mark.asyncio
async def test_purple_ai_handles_authentication_error(mock_settings):
    """Test that Purple AI client handles authentication errors properly."""
    mock_result = (None, "Authentication failed")

    with (
        patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
        patch(
            "purple_mcp.tools.purple_ai.ask_purple",
            new_callable=AsyncMock,
            return_value=mock_result
        ),
    ):
        with pytest.raises(PurpleAIClientError) as exc_info:
            await purple_ai("test query")

        assert "Purple AI request failed" in str(exc_info.value)
```

### Running Tests

#### Parallel Execution (Recommended)

The test suite supports parallel execution using `pytest-xdist` for significantly faster feedback:

```bash
# Run all tests in parallel (recommended)
uv run --group test pytest -n auto

# Run unit tests in parallel
uv run --group test pytest tests/unit/ -n auto

# Run specific test file or function (without xdist for single tests)
uv run --group test pytest tests/unit/tools/test_purple_ai.py::test_specific_function

# Run with coverage in parallel
uv run --group test pytest -n auto --cov=src/purple_mcp --cov-report=html
```

**Important**: Use `pytest-xdist` (`-n auto`) for running multiple tests in parallel, but **do not use it** when running a single test or test function. Running a single test with xdist adds unnecessary overhead.

#### Serial Execution

```bash
# Run all tests serially
uv run --group test pytest

# Run unit tests only
uv run --group test pytest tests/unit/

# Run with coverage
uv run --group test pytest --cov=src/purple_mcp --cov-report=html
```

#### Parallel Testing Guidelines

- **All tests must be parallel-safe**: Tests should not share mutable global state
- **Use proper fixtures**: Environment isolation is handled via existing fixtures
- **No hardcoded resources**: Avoid fixed ports, file paths, or external dependencies
- **Performance**: Parallel execution provides ~50% faster feedback
- **CI Integration**: All CI runs use parallel execution by default

## Documentation Standards

### Module Documentation

Every module must have a comprehensive docstring:

```python
"""SDL Query API Client.

This module provides the HTTP client for interacting with the Singularity Data Lake
PowerQuery API. It handles authentication, request/response processing, and error
handling for SDL operations.

Key Components:
    - SDLQueryClient: Main HTTP client for SDL API operations
    - Retry logic with exponential backoff
    - TLS configuration with security warnings
    - Request/response logging and monitoring

Usage:
    ```python
    from purple_mcp.libs.sdl.sdl_query_client import SDLQueryClient
    from purple_mcp.libs.sdl.config import create_sdl_settings

    config = create_sdl_settings(
        base_url="https://your-console.sentinelone.net/sdl",
        auth_token="Bearer your-token"
    )
    client = SDLQueryClient(base_url=config.base_url, settings=config)

    async with client:
        response = await client.submit_request("/api/query", payload)
    ```

Security:
    This client includes TLS verification bypass capability for development.
    Strong warnings are issued when TLS verification is disabled, and the
    feature is blocked in production environments.
"""
```

### Function Documentation

```python
def submit_powerquery(
    self,
    query: str,
    start_datetime: str,
    end_datetime: str,
) -> Dict[str, Any]:
    """Submit a PowerQuery to the SDL API.
    
    Args:
        query: The PowerQuery string to execute
        start_datetime: Query start time in ISO 8601 format (e.g., "2024-01-15T10:30:00Z")
        end_datetime: Query end time in ISO 8601 format (e.g., "2024-01-15T11:30:00Z")
        
    Returns:
        Dict containing the query response and metadata
        
    Raises:
        SDLError: If query submission fails
        ValidationError: If parameters are invalid
        
    Example:
        ```python
        result = await client.submit_powerquery(
            "filter event.type == 'DNS'",
            1640995200000000000,  # Start time
            1640995300000000000   # End time
        )
        ```
    """
```

## Security Guidelines

### Authentication and Secrets

- **Never hardcode credentials**: Use environment variables
- **Use secure token validation**: Validate token format and presence
- **Log authentication events**: Monitor for security issues
- **Implement proper error handling**: Don't expose sensitive information

### TLS and Network Security

- **Require HTTPS by default**: Never use HTTP for production
- **Implement strong TLS warnings**: Make security risks explicit
- **Block TLS bypass in production**: Prevent dangerous configurations
- **Log security-relevant events**: Monitor for suspicious activity

```python
# ✅ Good: Security-aware TLS configuration
def _validate_tls_security(self) -> None:
    """Validate TLS configuration with runtime security checks."""
    if self.skip_tls_verify:
        # Check for production environment
        env = os.getenv("PURPLEMCP_ENV", "production").lower()
        if env in ("production", "prod"):
            raise ValueError(
                "SECURITY ERROR: TLS verification bypass is FORBIDDEN in production"
            )

        # Issue strong runtime warning
        warnings.warn(
            "SECURITY WARNING: TLS verification DISABLED! "
            "This creates a security vulnerability.",
            UserWarning,
            stacklevel=3,
        )

        # Enhanced security logging
        logger.critical(
            "TLS verification DISABLED - CRITICAL SECURITY RISK! "
            f"Target URL: {self.base_url}"
        )
```

## Pull Request Process

### Before Submitting

1. **Run all quality checks**: Ensure code passes all checks
2. **Write comprehensive tests**: Include unit and integration tests
3. **Update documentation**: Keep all docs current
4. **Test manually**: Verify functionality works as expected
5. **Review your own code**: Do a self-review first

### PR Description Template

```markdown
## Summary
Brief description of the changes and why they're needed.

## Changes Made
- List of specific changes
- Include any breaking changes
- Mention new dependencies

## Testing
- Describe testing approach
- Include manual testing steps
- Note any test coverage changes

## Security Considerations
- List any security implications
- Describe mitigation strategies
- Note any new attack vectors

## Documentation
- List documentation updates
- Include any breaking changes to APIs
- Note any new configuration options
```

### PR Requirements

- [ ] All tests pass
- [ ] Code passes ruff format, ruff check, and mypy
- [ ] Test coverage maintained or improved
- [ ] Documentation updated
- [ ] Security considerations addressed
- [ ] No breaking changes (unless approved)
- [ ] Commit messages follow conventional format

## Code Review Guidelines

### For Authors

- **Keep PRs focused**: One feature or fix per PR
- **Write clear descriptions**: Explain what and why
- **Respond to feedback**: Address all review comments
- **Update based on feedback**: Don't argue, improve

### For Reviewers

- **Be constructive**: Provide helpful feedback
- **Focus on code quality**: Check for adherence to standards
- **Verify testing**: Ensure adequate test coverage
- **Check security**: Look for potential vulnerabilities
- **Approve when ready**: Don't block unnecessarily

## Getting Help

- **Check existing issues**: Look for similar problems
- **Read the documentation**: Check README and docs/
- **Ask questions**: Create issues for clarification
- **Join discussions**: Participate in PR discussions

## Git Workflow Notes

### Commit Messages

- **No amendments unless requested**: Do not amend past commits unless explicitly asked by the user
- **Conventional format**: Follow conventional commit message format when appropriate

## Additional Resources

- [Python Documentation](https://docs.python.org/)
- [uv Package Manager](https://docs.astral.sh/uv/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [ruff Documentation](https://docs.astral.sh/ruff/)

## License

By contributing to Purple MCP, you agree that your contributions will be licensed under the same license as the project.
