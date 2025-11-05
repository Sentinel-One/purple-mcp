"""Test helpers for alerts unit tests."""

import json
from typing import TypeVar
from unittest.mock import AsyncMock

import pytest

from purple_mcp.libs.alerts import (
    Alert,
    AlertConnection,
    AlertHistoryConnection,
    AlertNote,
    AlertNoteConnection,
    PageInfo,
)
from purple_mcp.type_defs import JsonDict

T = TypeVar("T")


class MockAlertsClientBuilder:
    """Factory for creating mock alerts clients with common responses."""

    @staticmethod
    def create_mock(
        method_name: str,
        return_value: object = None,
        side_effect: Exception | None = None,
    ) -> AsyncMock:
        """Create a mock client with specified method behavior.

        Args:
            method_name: Name of the method to mock
            return_value: Value to return when method is called
            side_effect: Exception to raise when method is called

        Returns:
            AsyncMock client with configured method
        """
        mock_client = AsyncMock()
        method = getattr(mock_client, method_name)

        if side_effect:
            method.side_effect = side_effect
        else:
            method.return_value = return_value

        return mock_client

    @staticmethod
    def create_empty_connection(connection_type: type[T]) -> T:
        """Create an empty connection response.

        Args:
            connection_type: Type of connection (AlertConnection, etc.)

        Returns:
            Connection instance with empty edges
        """
        return connection_type(  # type: ignore[call-arg]
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False,
                hasPreviousPage=False,
                startCursor=None,
                endCursor=None,
            ),
        )

    @staticmethod
    def create_alert_connection(alerts: list[Alert] | None = None) -> AlertConnection:
        """Create an AlertConnection with provided alerts.

        Args:
            alerts: List of alerts to include in edges

        Returns:
            AlertConnection with alerts as edges
        """
        if alerts is None:
            return MockAlertsClientBuilder.create_empty_connection(AlertConnection)

        from purple_mcp.libs.alerts.models import AlertEdge

        edges = [AlertEdge(node=alert, cursor=f"cursor-{alert.id}") for alert in alerts]

        return AlertConnection(
            edges=edges,
            pageInfo=PageInfo(
                hasNextPage=len(edges) > 0,
                hasPreviousPage=False,
                startCursor=edges[0].cursor if edges else None,
                endCursor=edges[-1].cursor if edges else None,
            ),
        )


class JSONAssertions:
    """Helper methods for common JSON response assertions."""

    @staticmethod
    def assert_connection_response(result: str, expected_edges: int | None = None) -> JsonDict:
        """Assert that a JSON response has connection structure.

        Args:
            result: JSON string response
            expected_edges: Expected number of edges (if specified)

        Returns:
            Parsed JSON data

        Raises:
            AssertionError: If response doesn't match expectations
        """
        data: JsonDict = json.loads(result)
        assert "edges" in data, "Response missing 'edges' field"
        assert "page_info" in data, "Response missing 'page_info' field"

        if expected_edges is not None:
            edges = data["edges"]
            assert isinstance(edges, list), "edges field must be a list"
            actual_edges = len(edges)
            assert actual_edges == expected_edges, (
                f"Expected {expected_edges} edges, got {actual_edges}"
            )

        return data

    @staticmethod
    def assert_alert_response(result: str, alert_id: str | None = None) -> JsonDict:
        """Assert that a JSON response contains valid alert data.

        Args:
            result: JSON string response
            alert_id: Expected alert ID (if specified)

        Returns:
            Parsed JSON data

        Raises:
            AssertionError: If response doesn't match expectations
        """
        data: JsonDict = json.loads(result)
        assert "id" in data, "Response missing 'id' field"
        assert "severity" in data, "Response missing 'severity' field"
        assert "name" in data, "Response missing 'name' field"

        if alert_id is not None:
            assert data["id"] == alert_id, f"Expected alert ID {alert_id}, got {data['id']}"

        return data

    @staticmethod
    def assert_note_response(result: str, note_id: str | None = None) -> JsonDict:
        """Assert that a JSON response contains valid note data.

        Args:
            result: JSON string response
            note_id: Expected note ID (if specified)

        Returns:
            Parsed JSON data

        Raises:
            AssertionError: If response doesn't match expectations
        """
        data: JsonDict = json.loads(result)
        assert "id" in data, "Response missing 'id' field"
        assert "text" in data, "Response missing 'text' field"
        assert "created_at" in data, "Response missing 'created_at' field"

        if note_id is not None:
            assert data["id"] == note_id, f"Expected note ID {note_id}, got {data['id']}"

        return data

    @staticmethod
    def assert_error_message(
        exc_info: pytest.ExceptionInfo[BaseException],
        expected_message: str,
        expected_cause_message: str | None = None,
    ) -> None:
        """Assert that an exception contains expected message and optionally validates cause.

        Args:
            exc_info: pytest.ExceptionInfo instance
            expected_message: Expected error message substring
            expected_cause_message: Optional expected underlying cause
                message substring. If provided, validates exception
                chaining.

        Raises:
            AssertionError: If message not found in exception or cause
                validation fails.
        """
        actual_message = str(exc_info.value)
        assert expected_message in actual_message, (
            f"Expected error message to contain '{expected_message}', but got: '{actual_message}'"
        )

        # If cause message expected, validate exception chaining
        if expected_cause_message is not None:
            cause = exc_info.value.__cause__
            assert cause is not None, (
                "Expected exception to have underlying cause, but __cause__ was None."
            )
            assert expected_cause_message in str(cause)

    @staticmethod
    def assert_null_response(result: str) -> None:
        """Assert that a JSON response is null.

        Args:
            result: JSON string response

        Raises:
            AssertionError: If response is not null
        """
        data = json.loads(result)
        assert data is None, f"Expected null response, got: {data}"


class AlertsTestData:
    """Common test data for alerts tests."""

    @staticmethod
    def create_test_alert(
        alert_id: str = "alert-123",
        name: str = "Test Alert",
        severity: str = "HIGH",
        status: str = "NEW",
    ) -> Alert:
        """Create a test alert with default or custom values.

        Args:
            alert_id: Alert ID
            name: Alert name
            severity: Alert severity
            status: Alert status

        Returns:
            Alert instance for testing
        """
        from purple_mcp.libs.alerts import Severity, Status

        return Alert(
            id=alert_id,
            name=name,
            severity=Severity(severity),
            status=Status(status),
            detectedAt="2024-01-01T00:00:00Z",
        )

    @staticmethod
    def create_test_note(
        note_id: str = "note-123",
        text: str = "Test note",
        alert_id: str = "alert-123",
    ) -> AlertNote:
        """Create a test note with default or custom values.

        Args:
            note_id: Note ID
            text: Note text
            alert_id: Associated alert ID

        Returns:
            AlertNote instance for testing
        """
        return AlertNote(
            id=note_id,
            text=text,
            createdAt="2024-01-01T00:00:00Z",
            alertId=alert_id,
        )

    @staticmethod
    def create_page_info(
        has_next: bool = False,
        has_prev: bool = False,
        start_cursor: str | None = None,
        end_cursor: str | None = None,
    ) -> JsonDict:
        """Create page info dict for connection responses.

        Args:
            has_next: Whether there's a next page
            has_prev: Whether there's a previous page
            start_cursor: Start cursor value
            end_cursor: End cursor value

        Returns:
            Page info dictionary
        """
        return {
            "hasNextPage": has_next,
            "hasPreviousPage": has_prev,
            "startCursor": start_cursor,
            "endCursor": end_cursor,
        }


# Export all helpers
__all__ = [
    "AlertsTestData",
    "JSONAssertions",
    "MockAlertsClientBuilder",
]
