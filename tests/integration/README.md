# Integration Tests

This directory contains integration tests that verify purple-mcp functionality against real external services. Unlike unit tests which use mocks, integration tests make actual API calls to verify end-to-end functionality.

## ⚠️ Important Safety Notice

**Integration tests make real API calls but are read-only safe!**

- Tests only read data from your UAM system (no modifications)
- Tests execute read-only queries against your console
- **Safe to run against production environments** (read-only access)
- Still recommended to use test/development environments for testing
- Ensure you have proper read permissions for UAM access

## Quick Start

1. **Copy the environment template:**
   ```bash
   cp .env.test.example .env.test
   ```

2. **Edit `.env.test` with your real credentials:**
   ```bash
   # Required for all tests
   PURPLEMCP_CONSOLE_BASE_URL=https://your-test-console.sentinelone.net
   # Note: Token must have Account or Site level permissions (not Global)
   PURPLEMCP_CONSOLE_TOKEN=your-api-token-here
   ```

3. **Install test dependencies:**
   ```bash
   uv sync --group test
   ```

4. **Run integration tests:**
   ```bash
   # Run all integration tests
   uv run python -m pytest tests/integration/ -v
   
   # Run only alerts integration tests
   uv run python -m pytest tests/integration/test_alerts_integration.py -v
   
   # All tests are read-only safe
   uv run python -m pytest tests/integration/ -v
   ```

## Environment Setup

### Required Environment Variables

Create a `.env.test` file in the project root with these variables:

```bash
# Console Configuration (Required)
PURPLEMCP_CONSOLE_BASE_URL=https://your-console-url.com    # No trailing slash
PURPLEMCP_CONSOLE_TOKEN=your-console-api-token             # API token with Account or Site permissions (not Global)
                                                            # Used for both Console and SDL access
```

### Optional Environment Variables

```bash
# Purple AI Configuration (uses defaults if not specified)
PURPLEMCP_PURPLE_AI_ACCOUNT_ID=AIMONITORING
PURPLEMCP_PURPLE_AI_TEAM_TOKEN=AIMONITORING
PURPLEMCP_PURPLE_AI_EMAIL_ADDRESS=ai+test@yourcompany.com
PURPLEMCP_PURPLE_AI_USER_AGENT=TestClient

# GraphQL Endpoint (usually don't change)
PURPLEMCP_CONSOLE_GRAPHQL_ENDPOINT=/web/api/v2.1/graphql
PURPLEMCP_ALERTS_GRAPHQL_ENDPOINT=/web/api/v2.1/unifiedalerts/graphql
```

### Getting API Tokens

1. **Console Token (`PURPLEMCP_CONSOLE_TOKEN`)**:
   - Log into your SentinelOne console
   - Go to Settings > Users > API Tokens
   - Generate a new token with **Account** or **Site** level permissions (not Global)
   - This token is used for both Console and SDL (PowerQuery) access
   - Copy the token value

### URL Construction

The integration tests automatically construct service URLs:
- **Purple AI**: `{PURPLEMCP_CONSOLE_BASE_URL}/web/api/v2.1/graphql`
- **Alerts**: `{PURPLEMCP_CONSOLE_BASE_URL}/web/api/v2.1/unifiedalerts/graphql`
- **SDL**: Uses separate SDL endpoint configuration

## Test Categories

### By Service

- **`test_alerts_integration.py`** - Unified Alerts Management (UAM) tests
- **`test_purple_ai_integration.py`** - Purple AI functionality tests  
- **`test_sdl_integration.py`** - SDL/PowerQuery tests
- **`test_full_integration.py`** - Cross-service integration tests

### By Impact Level

#### Safe Tests (Read-only)
- List and search operations
- Data retrieval and parsing
- Schema compatibility testing
- Performance measurements

#### Read-Only Tests (All tests are safe)
- **✅ All tests are read-only!**
- Retrieve and analyze existing data
- No data modifications or mutations
- Safe to run in any environment

#### Performance Tests (`alerts_performance`)
- Concurrent request testing
- Large pagination tests
- Load testing with multiple requests
- Response time measurements

## Running Tests

### Basic Test Execution

```bash
# Run all integration tests
uv run python -m pytest tests/integration/ -v

# Run specific test file
uv run python -m pytest tests/integration/test_alerts_integration.py -v

# Run specific test class
uv run python -m pytest tests/integration/test_alerts_integration.py::TestAlertsDirectClient -v

# Run specific test method
uv run python -m pytest tests/integration/test_alerts_integration.py::TestAlertsDirectClient::test_list_alerts_real_api -v
```

### Using Test Markers

```bash
# Run only alerts tests
uv run python -m pytest tests/integration/ -v -m "alerts_integration"

# All tests are read-only safe
uv run python -m pytest tests/integration/ -v

# Run only performance tests
uv run python -m pytest tests/integration/ -v -m "alerts_performance"

# Run only non-performance tests (all are read-only safe)
uv run python -m pytest tests/integration/ -v -m "not alerts_performance"
```

### Parallel Execution

```bash
# Run tests in parallel (faster but harder to debug)
uv run python -m pytest tests/integration/ -v -n auto

# Run with specific number of workers
uv run python -m pytest tests/integration/ -v -n 4
```

### Verbose Output

```bash
# Extra verbose with stdout capture
uv run python -m pytest tests/integration/ -vv -s

# Show test durations
uv run python -m pytest tests/integration/ -v --durations=10

# Generate coverage report
uv run python -m pytest tests/integration/ -v --cov=purple_mcp
```

## What the Tests Do

### Alerts Integration Tests

#### Client Tests (`TestAlertsDirectClient`)
- ✅ Test AlertsClient initialization with real config
- ✅ List alerts from real UAM API with pagination
- ✅ Search alerts with various filter combinations
- ✅ Retrieve specific alerts by ID
- ✅ Get alert notes and history
- ✅ Read existing alert notes (read-only)
- ✅ Test schema compatibility and fallback behavior
- ✅ Verify error handling with invalid data
- ✅ Test concurrent requests and performance

#### MCP Tools Tests (`TestAlertsMCPTools`)
- ✅ Test all 7 MCP tools through direct function calls
- ✅ Verify JSON response formatting
- ✅ Test parameter validation and error handling
- ✅ Cross-reference tool responses with client responses

#### MCP Server Tests (`TestAlertsMCPServer`)
- ✅ Test tools through FastMCP client interface
- ✅ Verify MCP protocol compliance
- ✅ Test error handling through MCP layer

#### Performance Tests (`TestAlertsPerformance`)
- ✅ Concurrent request handling (5+ simultaneous requests)
- ✅ Large pagination with maximum page sizes
- ✅ Response time measurements
- ✅ Memory and resource usage validation

### Other Integration Tests

- **Purple AI**: Natural language query processing
- **SDL**: PowerQuery execution and log analysis  
- **Full Integration**: Cross-service functionality

## Automatic Retry Behavior

Integration tests interact with live external services that may experience temporary issues. To improve reliability, the inventory client (and other clients) automatically retry transient failures:

### Retry Configuration
- **Retryable errors**: HTTP 502 (Bad Gateway), 503 (Service Unavailable), 504 (Gateway Timeout)
- **Max attempts**: 3 attempts total (initial + 2 retries)
- **Backoff strategy**: Exponential backoff (2s, 4s, 8s between attempts)
- **Non-retryable errors**: All other HTTP errors (400, 401, 404, 500, etc.) fail immediately

### What This Means for Tests
- Tests are resilient to temporary gateway/service issues
- Occasional 5xx responses from upstream services won't cause test failures
- Tests may take longer when retries are triggered (up to ~14 seconds per request)
- If all retries are exhausted, the test will fail with clear error messaging

### When Retries Don't Help
Tests will still fail immediately for non-transient errors:
- Authentication errors (401, 403)
- Client errors (400, 404)
- Internal server errors (500, 501) - these indicate bugs, not transient issues
- Network connectivity issues after retries exhausted

## Test Data and Cleanup

### Data Access (Read-Only)
- Tests only read existing data from your UAM system
- No data creation, modification, or deletion occurs
- Tests work with whatever data exists in your environment
- No cleanup required as no data is modified

### Test Data Requirements
- Tests require existing alerts in the system for full coverage
- Some tests are skipped if no alerts are available
- Performance tests work better with larger datasets

## Troubleshooting

### Common Issues

#### Environment Not Configured
```
SKIPPED - Integration tests require real environment variables
```
**Solution**: Set up `.env.test` with real values (not example values)

#### Authentication Errors
```
AlertsClientError: HTTP error from alerts API (401)
```
**Solutions**:
- Verify `PURPLEMCP_CONSOLE_TOKEN` is valid and not expired
- Check token permissions for UAM access
- Ensure `PURPLEMCP_CONSOLE_BASE_URL` is correct

#### Network/Timeout Errors
```
AlertsClientError: Request timed out while communicating with alerts API
```
**Solutions**:
- Check network connectivity to console
- Verify firewall/proxy settings
- Increase timeout in test configuration
- Check console availability/status

**Note**: Integration tests automatically retry transient failures (502, 503, 504) with exponential backoff. If you see these errors after retries, the upstream service may be experiencing persistent issues.

#### API Endpoint Errors
```
AlertsClientError: HTTP error from alerts API (404)
```
**Solutions**:
- Verify UAM is enabled on your console
- Check the GraphQL endpoint URL construction
- Ensure console version supports UAM API

#### Permission Errors
```
AlertsGraphQLError: GraphQL errors in alerts API response
```
**Solutions**:
- Verify token has UAM read permissions
- Check if UAM write permissions needed for note tests
- Review user role and permissions

### Debug Mode

Enable debug logging to see detailed API interactions:

```python
import logging
logging.getLogger("purple_mcp.libs.alerts").setLevel(logging.DEBUG)
```

Or set environment variable:
```bash
export PURPLE_MCP_LOG_LEVEL=DEBUG
```

### Test Environment Validation

Run environment check without executing tests:

```bash
uv run python -c "
from tests.integration.conftest import is_real_environment
is_real, missing = is_real_environment()
print(f'Environment ready: {is_real}')
if missing:
    print(f'Missing: {missing}')
"
```

## Best Practices

### Safety
1. **Read-only safe** - can run against production environments
2. **Monitor API usage** and rate limits for read operations
3. **Rotate test tokens** periodically for security
4. **Verify read permissions** are sufficient for UAM access
5. **No data cleanup needed** as tests are read-only

### Performance
1. **Run in parallel** when possible (`-n auto`)
2. **Use markers** to run only needed tests
3. **Monitor resource usage** during large tests
4. **Consider timeout settings** for slow networks

### Development
1. **Run integration tests** before major releases
2. **Update tests** when adding new features  
3. **Document test scenarios** and expected behaviors
4. **Use fixtures** to avoid code duplication

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync --group test
      - name: Run integration tests
        env:
          PURPLEMCP_CONSOLE_BASE_URL: ${{ secrets.TEST_CONSOLE_BASE_URL }}
          PURPLEMCP_CONSOLE_TOKEN: ${{ secrets.TEST_CONSOLE_TOKEN }}
        run: |
          uv run python -m pytest tests/integration/ -v \
            --timeout=300
```

### Test Secrets Management
- Store credentials in CI/CD secrets, never in code
- Use different tokens for different environments  
- Implement token rotation in CI/CD pipelines
- Monitor token usage and expiration

## Support

For issues with integration tests:

1. **Check this README** for common solutions
2. **Review test output** for specific error messages  
3. **Enable debug logging** for detailed API interactions
4. **Verify environment setup** with validation commands
5. **Check console logs** for server-side issues

Integration tests are critical for ensuring purple-mcp works correctly with real SentinelOne environments. Run them regularly but safely!
