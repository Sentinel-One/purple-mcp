"""Base class for GraphQL clients with shared HTTP/retry/error-handling logic.

This module provides a reusable abstraction for GraphQL clients that encapsulates
common patterns including:
- HTTP request execution with automatic retry on transient failures
- Header construction with authentication
- Error handling and exception mapping
- Response parsing and validation
- Debug logging with optional sensitive data scrubbing
"""

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from http import HTTPStatus
from typing import Generic, TypeVar

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from purple_mcp.type_defs import JsonDict
from purple_mcp.user_agent import get_user_agent

logger = logging.getLogger(__name__)

# Type variables for exception classes
TClientError = TypeVar("TClientError")
TGraphQLError = TypeVar("TGraphQLError")


class GraphQLClientBase(ABC, Generic[TClientError, TGraphQLError]):
    """Base class for GraphQL clients with shared HTTP/retry/error-handling logic.

    This class provides a reusable abstraction that encapsulates common GraphQL client
    patterns. Subclasses must provide the API-specific configuration and exception types.

    Subclasses must implement abstract properties that provide live access to configuration
    values (graphql_url, auth_token, timeout). This ensures that configuration updates on
    long-lived clients are respected in subsequent requests.

    Type Parameters:
        TClientError: The client error exception type (e.g., AlertsClientError)
        TGraphQLError: The GraphQL error exception type (e.g., AlertsGraphQLError)
    """

    def __init__(
        self,
        api_name: str,
        client_error_class: Callable[..., TClientError],
        graphql_error_class: Callable[..., TGraphQLError],
    ) -> None:
        """Initialize the GraphQL client base.

        Args:
            api_name: Name of the API for error messages (e.g., "alerts API").
            client_error_class: Exception class for HTTP/network errors.
            graphql_error_class: Exception class for GraphQL errors.
        """
        self.api_name = api_name
        self._client_error_class = client_error_class
        self._graphql_error_class = graphql_error_class

    @property
    @abstractmethod
    def graphql_url(self) -> str:
        """Return the current GraphQL endpoint URL.

        This property should provide live access to the configuration value,
        allowing dynamic updates to be reflected in subsequent requests.
        """
        pass

    @property
    @abstractmethod
    def auth_token(self) -> str:
        """Return the current authentication token.

        This property should provide live access to the configuration value,
        allowing credential rotation on long-lived clients.
        """
        pass

    @property
    @abstractmethod
    def timeout(self) -> float:
        """Return the current request timeout in seconds.

        This property should provide live access to the configuration value,
        allowing timeout adjustments on long-lived clients.
        """
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _execute_http_request(
        self, query: str, variables: JsonDict, headers: dict[str, str]
    ) -> httpx.Response:
        """Execute the HTTP request with automatic retry on transient failures.

        This internal method allows httpx exceptions to bubble up so tenacity can retry them.

        Args:
            query: The GraphQL query string.
            variables: Variables for the GraphQL query.
            headers: HTTP headers for the request.

        Returns:
            The httpx Response object.

        Raises:
            httpx.TimeoutException: If the request times out (retried automatically).
            httpx.NetworkError: If a network error occurs (retried automatically).
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers=headers,
            )
        return response

    async def execute_query(self, query: str, variables: JsonDict | None = None) -> JsonDict:  # noqa: C901
        """Execute a GraphQL query with automatic retry on transient failures.

        Args:
            query: The GraphQL query string.
            variables: Variables for the GraphQL query.

        Returns:
            The GraphQL response data.

        Raises:
            TClientError: If there's an HTTP/network error.
            TGraphQLError: If there's a GraphQL error in the response.
        """
        variables = variables or {}

        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": get_user_agent(),
        }

        # Only log full variables if unsafe debugging is explicitly enabled
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.debug("Executing GraphQL query", extra={"variables": variables})
        else:
            logger.debug(
                "Executing GraphQL query",
                extra={
                    "variable_count": len(variables),
                    "variable_keys": list(variables.keys()),
                },
            )

        try:
            response = await self._execute_http_request(query, variables, headers)
        except RetryError as e:
            # Unwrap the retry error to get the original exception
            original_exception = e.last_attempt.exception()
            if isinstance(original_exception, httpx.TimeoutException):
                raise self._client_error_class(  # type: ignore[misc]
                    f"Request timed out while communicating with {self.api_name}",
                    details=str(original_exception),
                ) from original_exception
            elif isinstance(original_exception, (httpx.NetworkError, httpx.RequestError)):
                raise self._client_error_class(  # type: ignore[misc]
                    f"Network error while communicating with {self.api_name}",
                    details=str(original_exception),
                ) from original_exception
            else:
                # Re-raise if it's not a known httpx exception
                raise
        except httpx.TimeoutException as e:
            # This handles the case where httpx exception is raised before retry decorator
            raise self._client_error_class(  # type: ignore[misc]
                f"Request timed out while communicating with {self.api_name}",
                details=str(e),
            ) from e
        except (httpx.NetworkError, httpx.RequestError) as e:
            # This handles the case where httpx exception is raised before retry decorator
            raise self._client_error_class(  # type: ignore[misc]
                f"Network error while communicating with {self.api_name}",
                details=str(e),
            ) from e

        logger.debug(
            "Received response from %s",
            self.api_name,
            extra={"status_code": response.status_code},
        )

        if response.status_code != HTTPStatus.OK:
            raise self._client_error_class(  # type: ignore[misc]
                f"HTTP error from {self.api_name}",
                status_code=response.status_code,
                details=response.text,
            )

        try:
            response_data: JsonDict = response.json()
        except Exception as exc:
            raise self._client_error_class(  # type: ignore[misc]
                f"Failed to parse JSON response from {self.api_name}",
            ) from exc

        if "errors" in response_data:
            errors = response_data["errors"]
            graphql_errors: list[JsonDict] | None = None
            if isinstance(errors, list):
                graphql_errors = [e for e in errors if isinstance(e, dict)]
            raise self._graphql_error_class(  # type: ignore[misc]
                f"GraphQL errors in {self.api_name} response",
                graphql_errors=graphql_errors,
            )

        if "data" not in response_data:
            raise self._graphql_error_class(  # type: ignore[misc]
                f"No data field in {self.api_name} response"
            )

        data = response_data["data"]
        if not isinstance(data, dict):
            raise self._graphql_error_class(  # type: ignore[misc]
                f"Data field is not a dictionary in {self.api_name} response"
            )

        return data
