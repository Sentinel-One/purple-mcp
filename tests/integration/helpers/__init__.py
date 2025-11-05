"""Integration test helpers for alerts tests."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, ParamSpec, Protocol, TypedDict, TypeVar

import pytest

from purple_mcp.libs.alerts import Alert, AlertConnection, AlertsClient, FilterInput, ViewType
from purple_mcp.type_defs import JsonDict

T = TypeVar("T")
P = ParamSpec("P")


class AsyncOperation(Protocol):
    """Protocol for async operations that can be measured."""

    def __call__(self, *args: object, **kwargs: object) -> Awaitable[object]:
        """Execute the operation with positional and keyword arguments."""
        ...


class PaginationResults(TypedDict):
    """Results from pagination testing."""

    all_items: list[Alert]
    page_count: int
    total_items: int
    cursors_seen: int


class IntegrationTestBase:
    """Base class for integration tests with common patterns."""

    @staticmethod
    async def with_timeout(
        coro: Awaitable[T], timeout: int = 30, error_message: str = "Operation timed out"
    ) -> T:
        """Execute a coroutine with timeout.

        Args:
            coro: Coroutine to execute
            timeout: Timeout in seconds
            error_message: Error message on timeout

        Returns:
            Result of the coroutine

        Raises:
            TimeoutError: If operation times out
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except TimeoutError:
            raise TimeoutError(error_message) from None

    @staticmethod
    async def assert_api_accessible(client: AlertsClient) -> None:
        """Assert that the API is accessible.

        Args:
            client: AlertsClient instance

        Raises:
            AssertionError: If API is not accessible
        """
        try:
            # Try a simple query
            result = await client.list_alerts(first=1, view_type=ViewType.ALL)
            assert result is not None, "API returned None response"
        except Exception as e:
            pytest.fail(f"API not accessible: {e}")

    @staticmethod
    async def get_test_alert_id(client: AlertsClient) -> str | None:
        """Get a valid alert ID for testing.

        Args:
            client: AlertsClient instance

        Returns:
            Alert ID or None if no alerts available
        """
        try:
            connection = await client.list_alerts(first=1, view_type=ViewType.ALL)
            if connection and connection.edges:
                return str(connection.edges[0].node.id)
            return None
        except Exception:
            return None

    @staticmethod
    def assert_connection_valid(
        connection: AlertConnection,
        min_items: int | None = None,
        max_items: int | None = None,
    ) -> None:
        """Assert that a connection response is valid.

        Args:
            connection: Connection response
            min_items: Minimum expected items
            max_items: Maximum expected items

        Raises:
            AssertionError: If connection is invalid
        """
        assert connection is not None, "Connection is None"
        assert hasattr(connection, "edges"), "Connection missing edges"
        assert hasattr(connection, "page_info"), "Connection missing page_info"

        item_count = len(connection.edges)
        if min_items is not None:
            assert item_count >= min_items, (
                f"Expected at least {min_items} items, got {item_count}"
            )
        if max_items is not None:
            assert item_count <= max_items, f"Expected at most {max_items} items, got {item_count}"

    @staticmethod
    def create_timestamp_note(prefix: str = "Integration test") -> str:
        """Create a timestamped note text.

        Args:
            prefix: Prefix for the note

        Returns:
            Timestamped note text
        """
        timestamp = datetime.now().isoformat()
        return f"{prefix} - {timestamp}"


class PaginationTestHelper:
    """Helper for pagination testing."""

    @staticmethod
    async def test_pagination_consistency(
        fetch_func: Callable[[int, str | None], Awaitable[AlertConnection]],
        page_size: int = 5,
        max_pages: int = 3,
    ) -> PaginationResults:
        """Test pagination consistency across pages.

        Args:
            fetch_func: Function to fetch a page (takes 'first' and 'after' params)
            page_size: Size of each page
            max_pages: Maximum pages to test

        Returns:
            Dict with test results including all_items and page_count
        """
        all_items = []
        cursors_seen = set()
        page_count = 0
        current_cursor = None

        for _ in range(max_pages):
            # Fetch page
            result = await fetch_func(page_size, current_cursor)

            if not result or not result.edges:
                break

            page_count += 1

            # Check for duplicate items
            for edge in result.edges:
                if edge.cursor in cursors_seen:
                    raise AssertionError(f"Duplicate cursor found: {edge.cursor}")
                cursors_seen.add(edge.cursor)
                all_items.append(edge.node)

            # Check if there's a next page
            if not result.page_info.has_next_page:
                break

            current_cursor = result.page_info.end_cursor

        return {
            "all_items": all_items,
            "page_count": page_count,
            "total_items": len(all_items),
            "cursors_seen": len(cursors_seen),
        }


class FilterTestHelper:
    """Helper for filter testing."""

    @staticmethod
    def create_severity_filters(severities: list[str]) -> list[FilterInput]:
        """Create filter inputs for severity filtering.

        Args:
            severities: List of severity values to filter by

        Returns:
            List of FilterInput objects
        """
        return [FilterInput.create_string_in("severity", severities)]

    @staticmethod
    def create_status_filter(status: str, negate: bool = False) -> FilterInput:
        """Create status filter input.

        Args:
            status: Status value
            negate: Whether to use NOT_EQUALS

        Returns:
            FilterInput object
        """
        return FilterInput.create_string_equal("status", status, is_negated=negate)

    @staticmethod
    async def verify_filter_results(
        client: AlertsClient,
        filters: list[FilterInput],
        expected_field: str,
        expected_values: set[str],
        sample_size: int = 10,
    ) -> None:
        """Verify that filter results match expectations.

        Args:
            client: AlertsClient instance
            filters: Filters to apply
            expected_field: Field to check in results
            expected_values: Expected values for the field
            sample_size: Number of results to check

        Raises:
            AssertionError: If results don't match expectations
        """
        result = await client.search_alerts(
            filters=filters, first=sample_size, view_type=ViewType.ALL
        )

        if result and result.edges:
            for edge in result.edges:
                alert = edge.node
                field_value = getattr(alert, expected_field, None)
                if field_value:
                    # Convert enum to string if needed
                    if hasattr(field_value, "value"):
                        field_value = field_value.value
                    else:
                        field_value = str(field_value)
                    assert field_value in expected_values, (
                        f"Alert {alert.id} has {expected_field}={field_value}, "
                        f"expected one of {expected_values}"
                    )


class PerformanceTestHelper:
    """Helper for performance testing."""

    def __init__(self) -> None:
        """Initialize performance test helper with empty measurements."""
        self.measurements: list[JsonDict] = []

    async def measure_operation(
        self, name: str, operation: AsyncOperation, *args: object, **kwargs: object
    ) -> tuple[str, float]:
        """Measure the performance of an operation.

        Args:
            name: Name of the operation
            operation: Async callable to measure
            *args: Positional arguments to pass to operation
            **kwargs: Keyword arguments to pass to operation

        Returns:
            Tuple of (result, duration_seconds)
        """
        import time

        start = time.perf_counter()
        result = ""
        try:
            actual_result = await operation(*args, **kwargs)
            result = str(actual_result)
            duration = time.perf_counter() - start
            success = True
            error = None
        except Exception as e:
            duration = time.perf_counter() - start
            success = False
            error = str(e)

        measurement: JsonDict = {
            "name": name,
            "duration": duration,
            "success": success,
            "error": error,
        }
        self.measurements.append(measurement)

        if not success:
            raise Exception(f"Operation {name} failed: {error}")

        return (result, duration)

    def get_summary(self) -> JsonDict:
        """Get performance summary.

        Returns:
            Dict with performance metrics
        """
        if not self.measurements:
            return {
                "total_operations": 0,
                "successful_operations": 0,
                "avg_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
                "success_rate": 0.0,
                "operations": [],
            }

        durations = []
        for m in self.measurements:
            if m["success"]:
                duration = m["duration"]
                if isinstance(duration, int | float):
                    durations.append(float(duration))
        success_count = sum(1 for m in self.measurements if m["success"])

        return {
            "total_operations": len(self.measurements),
            "successful_operations": success_count,
            "avg_duration": sum(durations) / len(durations) if durations else 0.0,
            "min_duration": min(durations) if durations else 0.0,
            "max_duration": max(durations) if durations else 0.0,
            "success_rate": float(success_count) / len(self.measurements),
            "operations": len(self.measurements),
        }


# Export all helpers
__all__ = [
    "FilterTestHelper",
    "IntegrationTestBase",
    "PaginationTestHelper",
    "PerformanceTestHelper",
]
