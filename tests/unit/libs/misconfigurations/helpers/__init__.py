"""Test helpers for misconfigurations unit tests."""

import json
from typing import TypeVar
from unittest.mock import AsyncMock

import pytest

from purple_mcp.libs.misconfigurations import (
    MisconfigurationConnection,
    MisconfigurationDetail,
    MisconfigurationHistoryItemConnection,
    MisconfigurationNote,
    MisconfigurationNoteConnection,
    PageInfo,
)
from purple_mcp.type_defs import JsonDict

T = TypeVar("T")


class MockMisconfigurationsClientBuilder:
    """Factory for creating mock misconfigurations clients with common responses."""

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
            connection_type: Type of connection (MisconfigurationConnection, etc.)

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
    def assert_misconfiguration_response(
        result: str, misconfiguration_id: str | None = None
    ) -> JsonDict:
        """Assert that a JSON response contains valid misconfiguration data.

        Args:
            result: JSON string response
            misconfiguration_id: Expected misconfiguration ID (if specified)

        Returns:
            Parsed JSON data

        Raises:
            AssertionError: If response doesn't match expectations
        """
        data: JsonDict = json.loads(result)
        assert "id" in data, "Response missing 'id' field"
        assert "severity" in data, "Response missing 'severity' field"
        assert "name" in data, "Response missing 'name' field"

        if misconfiguration_id is not None:
            assert data["id"] == misconfiguration_id, (
                f"Expected misconfiguration ID {misconfiguration_id}, got {data['id']}"
            )

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


class MisconfigurationsTestData:
    """Common test data for misconfigurations tests."""

    @staticmethod
    def create_test_misconfiguration(
        misconfiguration_id: str = "misc-123",
        name: str = "Test Misconfiguration",
        severity: str = "HIGH",
        status: str = "NEW",
    ) -> MisconfigurationDetail:
        """Create a test misconfiguration with default or custom values.

        Args:
            misconfiguration_id: Misconfiguration ID
            name: Misconfiguration name
            severity: Misconfiguration severity
            status: Misconfiguration status

        Returns:
            MisconfigurationDetail instance for testing
        """
        from purple_mcp.libs.misconfigurations import MisconfigurationSeverity, Status
        from purple_mcp.libs.misconfigurations.models import (
            Account,
            Asset,
            AssetScopeLevel,
            Compliance,
            FindingData,
            Remediation,
            Scope,
        )

        return MisconfigurationDetail.model_construct(
            id=misconfiguration_id,
            external_id=f"ext-{misconfiguration_id}",
            name=name,
            severity=MisconfigurationSeverity(severity),
            status=Status(status),
            asset=Asset.model_construct(
                id="asset-1",
                name="Test Asset",
                type="server",
                category="compute",
                subcategory="vm",
            ),
            scope=Scope.model_construct(account=Account.model_construct(name="Test Account")),
            scope_level=AssetScopeLevel.account,
            product="test-product",
            vendor="test-vendor",
            detected_at="2024-01-01T00:00:00Z",
            event_time="2024-01-01T00:00:00Z",
            environment="production",
            compliance=Compliance.model_construct(),
            remediation=Remediation.model_construct(),
            finding_data=FindingData.model_construct(),
        )

    @staticmethod
    def create_test_note(
        note_id: str = "note-123",
        text: str = "Test note",
        misconfiguration_id: str = "misc-123",
    ) -> MisconfigurationNote:
        """Create a test note with default or custom values.

        Args:
            note_id: Note ID
            text: Note text
            misconfiguration_id: Associated misconfiguration ID

        Returns:
            MisconfigurationNote instance for testing
        """
        from purple_mcp.libs.misconfigurations.models import User

        return MisconfigurationNote.model_construct(
            id=note_id,
            text=text,
            author=User.model_construct(
                id="user-1", email="test@example.com", full_name="Test User"
            ),
            created_at="2024-01-01T00:00:00Z",
            misconfiguration_id=misconfiguration_id,
        )


# Export all helpers
__all__ = [
    "JSONAssertions",
    "MisconfigurationsTestData",
    "MockMisconfigurationsClientBuilder",
]
