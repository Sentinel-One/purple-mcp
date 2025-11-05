"""Purple AI client implementation for GraphQL-based AI interactions.

This module provides the PurpleAIClient class for communicating with the Purple AI
service through GraphQL queries, handling conversation management, and parsing
structured responses using typed Pydantic models.
"""

import asyncio
import json
import logging
import os
import secrets
import string
import time
from datetime import timedelta
from enum import Enum
from http import HTTPStatus
from typing import cast

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from purple_mcp.libs.purple_ai.config import (
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIUserDetails,
)
from purple_mcp.libs.purple_ai.exceptions import PurpleAIClientError, PurpleAIGraphQLError
from purple_mcp.type_defs import JsonDict
from purple_mcp.user_agent import get_user_agent

logger = logging.getLogger(__name__)


class PurpleAIResultType(str, Enum):
    """The possible result types from Purple AI."""

    MESSAGE = "MESSAGE"
    POWER_QUERY = "POWER_QUERY"


def _random_conv_id(length: int) -> str:
    """Generate a cryptographically strong random string of fixed length.

    Uses the secrets module to ensure unpredictable identifiers suitable for
    security-sensitive contexts like telemetry and logging correlation.

    Args:
        length: The desired length of the random string.

    Returns:
        A random string containing ASCII letters and digits.
    """
    letters = string.ascii_letters + string.digits
    return "".join(secrets.choice(letters) for i in range(length))


def _build_graphql_request(
    *,
    start_time: int,
    end_time: int,
    base_url: str,
    version: str,
    account_id: str,
    team_token: str,
    email_address: str,
    user_agent: str,
    build_date: str,
    build_hash: str,
    conversation_id: str,
) -> str:
    """Construct a GraphQL request with properly escaped string values.

    Builds a Purple AI GraphQL query by safely escaping all dynamic
    configuration values using json.dumps(), preventing GraphQL injection
    vulnerabilities that could occur with raw string substitution when values
    contain quotes, backslashes, or other special characters.

    Args:
        start_time: Start time in milliseconds since epoch
        end_time: End time in milliseconds since epoch
        base_url: Console base URL
        version: Console version
        account_id: User account ID
        team_token: User team token
        email_address: User email address
        user_agent: User agent string
        build_date: Build date string
        build_hash: Build hash string
        conversation_id: Conversation identifier

    Returns:
        A GraphQL query string with all dynamic values safely escaped.

    Note:
        The $input variable placeholder is intentionally left unescaped as it
        will be provided as a GraphQL variable in the query execution.
    """
    # Use json.dumps to safely escape string values for GraphQL
    # This handles quotes, backslashes, Unicode, and other special characters
    return f"""\
    query SimpleTestQuery($input: String!) {{
        purpleLaunchQuery(
            request: {{
                isAsync: false
                contentType: NATURAL_LANGUAGE
                consoleDetails: {{
                    baseUrl: {json.dumps(base_url)}
                    version: {json.dumps(version)}
                }}
                conversation: {{ id: {json.dumps(conversation_id)}, messages: [], entitlements: null }}
                inputContent: {{
                    userInput: $input
                    displayedTimeRange: {{ start: {start_time}, end: {end_time} }}
                    viewSelector: EDR
                    contentType: NATURAL_LANGUAGE
                    userDetails: {{
                        accountId: {json.dumps(account_id)}
                        teamToken: {json.dumps(team_token)}
                        emailAddress: {json.dumps(email_address)}
                        userAgent: {json.dumps(user_agent)}
                        buildDate: {json.dumps(build_date)}
                        buildHash: {json.dumps(build_hash)}
                    }}
                }}
            }}
        ) {{
            result {{
                message
                summary
                powerQuery {{
                    query
                    timeRange {{
                        start
                        end
                    }}
                    viewSelector
                }}
                starRule
                suggestedActions {{
                    payload
                    label
                    actionId
                }}
                suggestedQuestions {{
                    powerQuery
                    question
                }}
                maskedMetadata
            }}
            resultType
            status {{
                state
                error {{
                    errorDetail
                    errorType
                    origin
                }}
            }}
            stepsCompleted
            token
        }}
    }}
"""


class PurpleAIClient:
    """Client for interacting with the Purple AI GraphQL API."""

    def __init__(self, config: PurpleAIConfig) -> None:
        """Initialize the PurpleAIClient.

        Args:
            config: Configuration for the Purple AI client.
        """
        self.config = config

    def _generate_query(self, query: str, conversation_id_for_tests: str | None = None) -> str:
        """Generate a Purple AI query string with a predefined query structure.

        Args:
            query: The user input query string.
            conversation_id_for_tests: A predefined conversation ID for testing purposes.

        Returns:
            A string representing a Purple AI query with the user input and a predefined time range.
        """
        current_time_millis = int(time.time() * 1000)
        previous_time_millis = current_time_millis - int(timedelta(days=1).total_seconds() * 1000)

        # Only log full query if unsafe debugging is explicitly enabled
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.debug("Generating Purple AI query", extra={"query_input": query})
        else:
            logger.debug(
                "Generating Purple AI query",
                extra={"query_length": len(query), "has_query": bool(query)},
            )

        conversation_id = "PURPLE-MCP" + _random_conv_id(10)
        if conversation_id_for_tests:
            conversation_id = conversation_id_for_tests

        # Use the secure builder that properly escapes all dynamic values
        return _build_graphql_request(
            start_time=previous_time_millis,
            end_time=current_time_millis,
            base_url=self.config.console_details.base_url,
            version=self.config.console_details.version,
            account_id=self.config.user_details.account_id,
            team_token=self.config.user_details.team_token,
            email_address=self.config.user_details.email_address,
            user_agent=self.config.user_details.user_agent,
            build_date=self.config.user_details.build_date,
            build_hash=self.config.user_details.build_hash,
            conversation_id=conversation_id,
        )

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
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self.config.graphql_url,
                json={"query": query, "variables": variables},
                headers=headers,
            )
        return response

    async def execute_query(self, query: str, variables: JsonDict | None = None) -> JsonDict:  # noqa: C901
        """Execute a GraphQL query against the Purple AI API with automatic retry on transient failures.

        Args:
            query: The GraphQL query string.
            variables: Variables for the GraphQL query.

        Returns:
            The GraphQL response data.

        Raises:
            PurpleAIClientError: If there's an HTTP/network error.
            PurpleAIGraphQLError: If there's a GraphQL error in the response.
        """
        variables = variables or {}

        headers = {
            "Authorization": f"ApiToken {self.config.auth_token}",
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
                raise PurpleAIClientError(
                    "Request timed out while communicating with Purple AI",
                    details=str(original_exception),
                ) from original_exception
            elif isinstance(original_exception, (httpx.NetworkError, httpx.RequestError)):
                raise PurpleAIClientError(
                    "Network error while communicating with Purple AI",
                    details=str(original_exception),
                ) from original_exception
            else:
                # Re-raise if it's not a known httpx exception
                raise
        except httpx.TimeoutException as e:
            # This handles the case where httpx exception is raised before retry decorator
            raise PurpleAIClientError(
                "Request timed out while communicating with Purple AI", details=str(e)
            ) from e
        except (httpx.NetworkError, httpx.RequestError) as e:
            # This handles the case where httpx exception is raised before retry decorator
            raise PurpleAIClientError(
                "Network error while communicating with Purple AI", details=str(e)
            ) from e

        logger.debug(
            "Received response from Purple AI",
            extra={
                "status_code": response.status_code,
                "response_size_bytes": len(response.content),
            },
        )

        if response.status_code != HTTPStatus.OK:
            raise PurpleAIClientError(
                "HTTP error from Purple AI",
                status_code=response.status_code,
                details=response.text,
            )

        try:
            response_data = response.json()
        except Exception as e:
            raise PurpleAIClientError(
                "Failed to parse JSON response from Purple AI", details=str(e)
            ) from e

        # Guard against null or non-dict responses from transient console hiccups
        if not isinstance(response_data, dict):
            raise PurpleAIGraphQLError(
                "Invalid JSON response from Purple AI: expected dict, got "
                f"{type(response_data).__name__}"
            )

        if "errors" in response_data:
            raise PurpleAIGraphQLError(
                "GraphQL errors in Purple AI response", graphql_errors=response_data["errors"]
            )

        if "data" not in response_data or response_data["data"] is None:
            raise PurpleAIGraphQLError("No data field in Purple AI response")

        # Guard against non-dict data field (e.g., {"data": []})
        if not isinstance(response_data["data"], dict):
            raise PurpleAIGraphQLError(
                "Invalid data field in Purple AI response: expected dict, got "
                f"{type(response_data['data']).__name__}"
            )

        return cast(JsonDict, response_data["data"])

    async def ask_purple(self, raw_query: str) -> tuple[PurpleAIResultType | None, str]:  # noqa: C901
        """Ask Purple AI a query.

        Args:
            raw_query: The raw user query to ask Purple AI.

        Returns:
            Tuple of (result_type, response_text). Returns (None, error_message) on error.
        """
        # Only log full query if unsafe debugging is explicitly enabled
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.info("Querying Purple AI", extra={"raw_query": raw_query})
        else:
            logger.info(
                "Querying Purple AI",
                extra={"query_length": len(raw_query), "has_query": bool(raw_query)},
            )

        graphql_request = self._generate_query(raw_query)

        try:
            data = await self.execute_query(graphql_request, {"input": raw_query})
        except (PurpleAIClientError, PurpleAIGraphQLError) as e:
            msg = str(e)
            logger.error(msg)
            return None, msg

        # Only log full response if unsafe debugging is explicitly enabled
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.debug("Response from Purple AI processed", extra={"response": data})
        else:
            logger.debug(
                "Response from Purple AI processed",
                extra={
                    "has_response": bool(data),
                    "response_keys": list(data.keys()) if isinstance(data, dict) else None,
                },
            )

        purple_response = data.get("purpleLaunchQuery")
        if not purple_response or not isinstance(purple_response, dict):
            msg = "Missing purpleLaunchQuery in response"
            logger.error(msg)
            return None, msg

        status = purple_response.get("status")
        if not isinstance(status, dict):
            msg = "Missing status in response"
            logger.error(msg)
            return None, msg

        if status.get("error"):
            msg = f"Error from Purple AI: {status['error']}"
            logger.error(msg)
            return None, msg

        try:
            result_type_value = purple_response.get("resultType")
            if not isinstance(result_type_value, str):
                msg = "Invalid result type in response"
                logger.error(msg)
                return None, msg
            response_type = PurpleAIResultType(result_type_value)
        except ValueError:
            msg = f"Unexpected result type from Purple AI: {purple_response.get('resultType')}"
            logger.error(msg)
            return None, msg

        result = purple_response.get("result")
        if not isinstance(result, dict):
            msg = "Missing or invalid result in response"
            logger.error(msg)
            return None, msg

        if response_type is PurpleAIResultType.MESSAGE:
            message = result.get("message")
            return response_type, str(message) if message is not None else ""
        elif response_type is PurpleAIResultType.POWER_QUERY:
            power_query = result.get("powerQuery")
            if isinstance(power_query, dict):
                query = power_query.get("query")
                return response_type, str(query) if query is not None else ""
            msg = "Invalid powerQuery in response"
            logger.error(msg)
            return None, msg
        else:
            msg = f"Unhandled result type from Purple AI: {response_type}"
            logger.error(msg)
            return None, msg


# Backward compatibility functions
async def ask_purple(
    config: PurpleAIConfig, raw_query: str
) -> tuple[PurpleAIResultType | None, str]:
    """Ask Purple AI a query with automatic retry on transient failures.

    This is a backward-compatible function wrapper around PurpleAIClient.

    Args:
        config: The Purple AI configuration.
        raw_query: The raw user query to ask Purple AI.

    Returns:
        The response from Purple AI.
    """
    client = PurpleAIClient(config)
    return await client.ask_purple(raw_query)


def sync_ask_purple(config: PurpleAIConfig, raw_query: str) -> str:
    """Synchronous wrapper for ask_purple.

    This function provides a synchronous interface to the async ask_purple function.
    It cannot be called from within an existing event loop (e.g., Jupyter notebooks,
    ASGI contexts, or Trio bridges). If you're in such an environment, use the
    async ask_purple function directly with await.

    Args:
        config: The Purple AI configuration.
        raw_query: The raw user query to ask Purple AI.

    Returns:
        The response from Purple AI as a string.

    Raises:
        RuntimeError: If called from within a running event loop. Use the async
            ask_purple function instead.
    """
    try:
        # Check if we're already in an event loop
        asyncio.get_running_loop()
        # If we get here, there's a running loop - can't use asyncio.run()
        raise RuntimeError(
            "sync_ask_purple cannot be called from a running event loop. "
            "You are likely in an environment like Jupyter, ASGI, or Trio. "
            "Please use the async version: await ask_purple(config, raw_query)"
        )
    except RuntimeError as e:
        # If the error message is about running event loop, re-raise it
        if "cannot be called from a running event loop" in str(e):
            raise
        # Otherwise, it's the expected "no running event loop" error, continue
        pass

    _result_type, response = asyncio.run(ask_purple(config, raw_query))
    return str(response)


if __name__ == "__main__":

    async def main() -> None:
        """Run a test query against Purple AI."""
        config = PurpleAIConfig(
            user_details=PurpleAIUserDetails(
                account_id="AIMONITORING",
                team_token="AIMONITORING",
                email_address="ai+purple-mcp@sentinelone.com",
                user_agent="IsaacAsimovMonitoringInc",
                build_date="02/28/2025, 00:00:00 AM",
                build_hash="N/A",
            ),
            console_details=PurpleAIConsoleDetails(
                base_url="https://console.example.com",
                version="S-25.1.1#30",
            ),
        )
        result = await ask_purple(config, "What's the weather in Tokyo?")
        print(result)

    asyncio.run(main())
