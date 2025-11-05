"""Alerts-specific integration test configuration and utilities.

This module provides fixtures and utilities specifically for alerts integration tests
that require real UAM environment variables and external service connections.
"""

import os
from collections.abc import AsyncGenerator, Generator
from datetime import datetime

import pytest

from purple_mcp.config import ENV_PREFIX, get_settings
from purple_mcp.libs.alerts import AlertsClient, AlertsConfig, FilterInput, ViewType
from purple_mcp.type_defs import JsonDict


def is_alerts_environment() -> tuple[bool, list[str]]:
    """Check if we have real environment variables for alerts integration testing.

    Returns:
        Tuple of (is_real, missing_or_example_vars)
    """
    # Load test environment first (from parent conftest)
    from tests.integration.conftest import load_test_env

    load_test_env()

    required_vars = {
        f"{ENV_PREFIX}CONSOLE_TOKEN": "Console API token for UAM access",
        f"{ENV_PREFIX}CONSOLE_BASE_URL": "Console base URL with UAM endpoint",
    }

    example_values = {
        "https://console.example.test",
        "console.example.test",
        "example.test",
        "test-token",
        "your-token-here",
        "Bearer your-token",
        "",
        "none",
        "null",
    }

    missing_or_example = []

    for var, description in required_vars.items():
        value = os.environ.get(var, "").strip()
        if not value or value.lower() in example_values:
            missing_or_example.append(f"{var} ({description})")

    return len(missing_or_example) == 0, missing_or_example


@pytest.fixture(scope="session")
def alerts_integration_env_check() -> Generator[dict[str, str], None, None]:
    """Check alerts integration environment and skip if not properly configured."""
    is_real, missing_vars = is_alerts_environment()

    if not is_real:
        missing_list = "\n  - ".join(missing_vars)
        pytest.skip(
            f"Alerts integration tests require real environment variables. "
            f"Missing or example values found for:\n  - {missing_list}\n\n"
            f"Please set these in .env.test file with real values for UAM access."
        )

    # Return environment variables for tests to use
    yield {
        f"{ENV_PREFIX}CONSOLE_TOKEN": os.environ[f"{ENV_PREFIX}CONSOLE_TOKEN"],
        f"{ENV_PREFIX}CONSOLE_BASE_URL": os.environ[f"{ENV_PREFIX}CONSOLE_BASE_URL"],
    }


@pytest.fixture
def alerts_integration_settings(
    alerts_integration_env_check: dict[str, str],
) -> Generator[None, None, None]:
    """Ensure settings are properly configured for alerts integration tests."""
    # Clear any cached settings from unit tests
    try:
        from purple_mcp.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass

    yield

    # Clean up after test
    try:
        from purple_mcp.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def alerts_timeout() -> int:
    """Provide extended timeout for alerts API calls."""
    return 90  # 90 seconds for UAM API calls


@pytest.fixture
def alerts_config(alerts_integration_env_check: dict[str, str]) -> AlertsConfig:
    """Create a real AlertsConfig for integration testing."""
    settings = get_settings()

    return AlertsConfig(
        graphql_url=settings.alerts_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=90.0,  # Extended timeout for integration tests
        supports_view_type=True,
        supports_data_sources=True,
    )


@pytest.fixture
def alerts_config_fallback(alerts_integration_env_check: dict[str, str]) -> AlertsConfig:
    """Create an AlertsConfig with fallback schema support for compatibility testing."""
    settings = get_settings()

    return AlertsConfig(
        graphql_url=settings.alerts_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=90.0,
        supports_view_type=False,  # Force fallback behavior
        supports_data_sources=False,
    )


@pytest.fixture
def alerts_client(alerts_config: AlertsConfig) -> AlertsClient:
    """Create a real AlertsClient for integration testing."""
    return AlertsClient(alerts_config)


@pytest.fixture
def alerts_client_fallback(alerts_config_fallback: AlertsConfig) -> AlertsClient:
    """Create an AlertsClient with fallback configuration for compatibility testing."""
    return AlertsClient(alerts_config_fallback)


@pytest.fixture
async def sample_alert_id(alerts_client: AlertsClient) -> AsyncGenerator[str | None, None]:
    """Get a sample alert ID for testing, or None if no alerts available."""
    try:
        alerts_connection = await alerts_client.list_alerts(first=1, view_type=ViewType.ALL)

        if alerts_connection.edges:
            yield alerts_connection.edges[0].node.id
        else:
            yield None
    except Exception:
        yield None


@pytest.fixture
def test_filters() -> list[FilterInput]:
    """Provide sample filter inputs for testing."""
    return [
        FilterInput.create_string_in("severity", ["HIGH", "CRITICAL"]),
        FilterInput.create_string_equal("status", "NEW"),
    ]


@pytest.fixture
def severity_filter() -> FilterInput:
    """Provide a simple severity filter for testing."""
    return FilterInput.create_string_equal("severity", "HIGH")


@pytest.fixture
def status_filter() -> FilterInput:
    """Provide a simple status filter for testing."""
    return FilterInput.create_string_equal("status", "RESOLVED", is_negated=True)


@pytest.fixture
def test_note_text() -> str:
    """Generate unique test note text."""
    timestamp = datetime.now().isoformat()
    return f"Integration test note created at {timestamp}"


@pytest.fixture
def pagination_sizes() -> list[int]:
    """Provide different page sizes for pagination testing."""
    return [1, 5, 10, 25, 50]


@pytest.fixture
def view_types() -> list[ViewType]:
    """Provide all view types for testing."""
    return [ViewType.ALL, ViewType.ASSIGNED_TO_ME, ViewType.UNASSIGNED, ViewType.MY_TEAM]


class AlertsTestHelper:
    """Helper class for alerts integration testing."""

    def __init__(self, client: AlertsClient) -> None:
        """Initialize the alerts test helper with a client."""
        self.client = client
        self._created_notes: list[str] = []

    async def get_any_alert_id(self) -> str | None:
        """Get any available alert ID for testing."""
        try:
            connection = await self.client.list_alerts(first=1)
            if connection.edges:
                return str(connection.edges[0].node.id)
            return None
        except Exception:
            return None

    async def get_alert_with_notes(self) -> str | None:
        """Find an alert that has notes, or None if none found."""
        try:
            connection = await self.client.list_alerts(first=10)
            for edge in connection.edges:
                alert = edge.node
                if alert.note_exists:
                    return str(alert.id)
            return None
        except Exception:
            return None

    async def create_test_note(self, alert_id: str, text: str | None = None) -> str | None:
        """Create a test note and track it for cleanup."""
        if text is None:
            text = f"Test note created at {datetime.now().isoformat()}"

        # Note: add_alert_note functionality has been removed
        return None

    async def find_alerts_by_severity(self, severity: str, limit: int = 5) -> list[str]:
        """Find alert IDs with specific severity."""
        try:
            filters = [FilterInput.create_string_equal("severity", severity)]
            connection = await self.client.search_alerts(filters=filters, first=limit)
            return [edge.node.id for edge in connection.edges]
        except Exception:
            return []

    async def count_alerts_by_status(self, status: str) -> int:
        """Count alerts with specific status (up to 100)."""
        try:
            filters = [FilterInput.create_string_equal("status", status)]
            connection = await self.client.search_alerts(filters=filters, first=100)
            return len(connection.edges)
        except Exception:
            return 0

    def cleanup_notes(self) -> list[str]:
        """Return list of created note IDs for cleanup."""
        created = self._created_notes.copy()
        self._created_notes.clear()
        return created


@pytest.fixture
async def alerts_helper(alerts_client: AlertsClient) -> AsyncGenerator[AlertsTestHelper, None]:
    """Provide alerts test helper with automatic cleanup."""
    helper = AlertsTestHelper(alerts_client)
    yield helper

    # Cleanup created notes (note: actual deletion would require delete API)
    created_notes = helper.cleanup_notes()
    if created_notes:
        # Log created notes for manual cleanup if needed
        print(f"Integration test created {len(created_notes)} notes: {created_notes}")


@pytest.fixture(scope="session")
def concurrent_request_count() -> int:
    """Number of concurrent requests to use in performance tests."""
    return 5


@pytest.fixture
def performance_page_sizes() -> list[int]:
    """Page sizes for performance testing."""
    return [10, 25, 50, 100]


class AlertsPerformanceTracker:
    """Track performance metrics during integration tests."""

    def __init__(self) -> None:
        """Initialize performance tracker with empty metrics."""
        self.request_times: list[float] = []
        self.response_sizes: list[int] = []
        self.error_count: int = 0

    def record_request(self, duration: float, response_size: int = 0, error: bool = False) -> None:
        """Record a request's performance metrics."""
        self.request_times.append(duration)
        self.response_sizes.append(response_size)
        if error:
            self.error_count += 1

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        return sum(self.request_times) / len(self.request_times) if self.request_times else 0.0

    @property
    def max_response_time(self) -> float:
        """Get maximum response time."""
        return max(self.request_times) if self.request_times else 0.0

    @property
    def min_response_time(self) -> float:
        """Get minimum response time."""
        return min(self.request_times) if self.request_times else 0.0

    @property
    def total_requests(self) -> int:
        """Get total number of requests."""
        return len(self.request_times)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_requests - self.error_count) / self.total_requests

    def get_summary(self) -> JsonDict:
        """Get performance summary."""
        return {
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "avg_response_time": self.avg_response_time,
            "min_response_time": self.min_response_time,
            "max_response_time": self.max_response_time,
        }


@pytest.fixture
def perf_tracker() -> AlertsPerformanceTracker:
    """Provide performance tracking for tests."""
    return AlertsPerformanceTracker()


# Raw GraphQL queries for testing
@pytest.fixture
def test_queries() -> dict[str, str]:
    """Provide sample GraphQL queries for testing."""
    return {
        "simple_list": """
        query SimpleList {
            alerts(first: 3) {
                edges {
                    node {
                        id
                        name
                        severity
                        status
                    }
                }
            }
        }
        """,
        "with_filters": """
        query WithFilters($filters: [FilterInput!]) {
            searchAlerts(filters: $filters, first: 5) {
                edges {
                    node {
                        id
                        name
                        severity
                        status
                        detectedAt
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """,
        "detailed_alert": """
        query DetailedAlert($alertId: ID!) {
            alert(id: $alertId) {
                id
                name
                severity
                status
                description
                detectedAt
                firstSeenAt
                lastSeenAt
                analystVerdict
                classification
                confidenceLevel
                detectionSource {
                    product
                    vendor
                }
                asset {
                    id
                    name
                    type
                }
                assignee {
                    userId
                    email
                    fullName
                }
                noteExists
                storylineId
                ticketId
            }
        }
        """,
        "alert_notes": """
        query AlertNotes($alertId: ID!) {
            alertNotes(alertId: $alertId, first: 10) {
                edges {
                    node {
                        id
                        text
                        createdAt
                        author {
                            userId
                            email
                            fullName
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                }
            }
        }
        """,
    }


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest for alerts integration tests."""
    # Add custom markers for alerts tests
    config.addinivalue_line(
        "markers",
        "alerts_integration: marks tests as alerts integration tests requiring real UAM access",
    )
    config.addinivalue_line(
        "markers", "alerts_performance: marks tests as alerts performance tests"
    )

    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests requiring external services"
    )
    config.addinivalue_line("markers", "slow: marks tests as slow running tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark alerts integration tests."""
    for item in items:
        # Mark tests that use alerts fixtures
        if any(fixture.startswith("alerts_") for fixture in getattr(item, "fixturenames", [])):
            item.add_marker(pytest.mark.alerts_integration)
            item.add_marker(pytest.mark.integration)

        # Mark performance tests
        if (
            "performance" in item.name
            or "concurrent" in item.name
            or "large_pagination" in item.name
            or "perf_" in item.name
        ):
            item.add_marker(pytest.mark.alerts_performance)
            item.add_marker(pytest.mark.slow)

        # Mark integration tests based on file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)

        # Mark specific test types
        if "timeout" in item.name or "network" in item.name:
            item.add_marker(pytest.mark.slow)
