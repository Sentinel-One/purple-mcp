"""Test helpers for alerts unit tests."""

from typing import TypeVar

from purple_mcp.libs.alerts import PageInfo

T = TypeVar("T")


class MockAlertsClientBuilder:
    """Factory for creating mock alerts clients with common responses."""

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
