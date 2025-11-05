"""Base test class for alerts functionality."""

import json
from collections.abc import Callable, Mapping
from typing import Any, Protocol, TypeVar
from unittest.mock import AsyncMock, Mock

import pytest

from purple_mcp.libs.alerts import (
    Alert,
    AlertConnection,
    AlertHistoryConnection,
    AlertNote,
    AlertNoteConnection,
)
from purple_mcp.libs.alerts.models import PageInfo
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.alerts.helpers import JSONAssertions, MockAlertsClientBuilder

T = TypeVar("T")


class ToolFunction(Protocol):
    """Protocol for tool functions that can be tested.

    Uses Any for maximum flexibility since test helpers need to work with
    diverse tool function signatures (get_alert(str), search_alerts(list[JsonDict], int, str), etc.)
    and don't require type safety for passed-through arguments.
    """

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        """Execute the tool with the given arguments."""
        ...


class AlertsTestBase:
    """Base class with common test utilities for alerts tests."""

    @staticmethod
    async def assert_tool_success(
        tool_func: ToolFunction,
        mock_get_client: Mock,
        mock_response: str
        | JsonDict
        | list[JsonDict]
        | Alert
        | AlertConnection
        | AlertNote
        | AlertNoteConnection
        | AlertHistoryConnection
        | None,
        expected_client_method: str,
        expected_client_args: JsonDict | None = None,
        tool_args: JsonDict | None = None,
        response_validator: Callable[[str], None] | None = None,
    ) -> str:
        """Test successful tool execution with common assertions.

        Args:
            tool_func: The tool function to test
            mock_get_client: Mock for _get_alerts_client
            mock_response: Response to return from mock client
            expected_client_method: Expected method to be called on client
            expected_client_args: Expected arguments for client method (None = just check called)
            tool_args: Arguments to pass to tool function
            response_validator: Optional function to validate response

        Returns:
            The tool function's response

        Example:
            await self.assert_tool_success(
                alerts.get_alert,
                mock_get_client,
                mock_alert,
                "get_alert",
                None,  # Just verify method was called
                {"alert_id": "123"}
            )
        """
        # Setup mock
        mock_client = MockAlertsClientBuilder.create_mock(expected_client_method, mock_response)
        mock_get_client.return_value = mock_client

        # Execute tool
        result = await tool_func(**(tool_args or {}))

        # Verify client method was called
        method = getattr(mock_client, expected_client_method)
        if expected_client_args is not None:
            method.assert_called_once_with(**expected_client_args)
        else:
            method.assert_called_once()

        # Validate response if validator provided
        if response_validator:
            response_validator(result)

        return result

    @staticmethod
    async def assert_tool_error(
        tool_func: ToolFunction,
        mock_get_client: Mock,
        mock_side_effect: Exception,
        expected_client_method: str,
        expected_error_message: str,
        expected_client_args: JsonDict | None = None,
        tool_args: JsonDict | None = None,
    ) -> None:
        """Test tool error handling with common assertions.

        Args:
            tool_func: The tool function to test
            mock_get_client: Mock for _get_alerts_client
            mock_side_effect: Exception to raise from mock client
            expected_client_method: Expected method to be called on client
            expected_error_message: Expected error message substring
            expected_client_args: Expected arguments to be passed to client method
            tool_args: Arguments to pass to tool function

        Example:
            await self.assert_tool_error(
                alerts.get_alert,
                mock_get_client,
                AlertsClientError("Network error"),
                "get_alert",
                "Failed to retrieve alert",
                {"alert_id": "123"}
            )
        """
        # Setup mock to raise error
        mock_client = MockAlertsClientBuilder.create_mock(
            expected_client_method, side_effect=mock_side_effect
        )
        mock_get_client.return_value = mock_client

        # Execute and expect error
        with pytest.raises(RuntimeError) as exc_info:
            await tool_func(**(tool_args or {}))

        JSONAssertions.assert_error_message(exc_info, expected_error_message)

    @staticmethod
    async def assert_tool_validation_error(
        tool_func: ToolFunction,
        tool_args: Mapping[str, object],
        expected_error: str,
    ) -> None:
        """Test tool parameter validation.

        Args:
            tool_func: The tool function to test
            tool_args: Invalid arguments to pass to tool
            expected_error: Expected validation error message

        Example:
            await self.assert_tool_validation_error(
                alerts.list_alerts,
                {"first": 0},
                "first must be between 1 and 100"
            )
        """
        with pytest.raises(ValueError) as exc_info:
            await tool_func(**tool_args)

        JSONAssertions.assert_error_message(exc_info, expected_error)

    @staticmethod
    def assert_json_response_equals(
        result: str, expected: str | JsonDict | list[JsonDict]
    ) -> None:
        """Assert JSON response equals expected value.

        Args:
            result: JSON string response
            expected: Expected value (will be JSON encoded for comparison)
        """
        actual = json.loads(result)
        expected_json = json.loads(json.dumps(expected, default=str))
        assert actual == expected_json, f"Expected {expected_json}, got {actual}"

    @staticmethod
    def create_mock_with_connection(
        method_name: str,
        connection_type: type[AlertConnection],
        items: list[Alert] | None = None,
    ) -> AsyncMock:
        """Create a mock client that returns a connection response.

        Args:
            method_name: Client method name
            connection_type: Type of connection to create
            items: Items to include in connection edges

        Returns:
            Configured mock client

        Example:
            mock_client = self.create_mock_with_connection(
                "list_alerts",
                AlertConnection,
                [test_alert1, test_alert2]
            )
        """
        if items:
            # Create connection with items
            from purple_mcp.libs.alerts.models import AlertEdge, AlertHistoryEdge, AlertNoteEdge

            edge_class = {
                "AlertConnection": AlertEdge,
                "AlertNoteConnection": AlertNoteEdge,
                "AlertHistoryConnection": AlertHistoryEdge,
            }.get(connection_type.__name__, AlertEdge)

            edges = [edge_class(node=item, cursor=f"cursor-{item.id}") for item in items]

            connection = connection_type(
                edges=edges,
                pageInfo=PageInfo(
                    hasNextPage=False,
                    hasPreviousPage=False,
                    startCursor=edges[0].cursor if edges else None,
                    endCursor=edges[-1].cursor if edges else None,
                ),
            )
        else:
            # Empty connection
            connection = MockAlertsClientBuilder.create_empty_connection(connection_type)

        return MockAlertsClientBuilder.create_mock(method_name, connection)
