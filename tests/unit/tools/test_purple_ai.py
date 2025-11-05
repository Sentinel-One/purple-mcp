"""Tests for purple_ai tools."""

import os
from collections.abc import Callable, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from purple_mcp.config import ENV_PREFIX
from purple_mcp.libs.purple_ai import PurpleAIClientError, PurpleAIGraphQLError, PurpleAIResultType
from purple_mcp.tools.purple_ai import purple_ai


class TestPurpleAI:
    """Test purple_ai function."""

    @pytest.mark.asyncio
    async def test_purple_ai_success_message(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test successful message response from Purple AI."""
        mock_result = (PurpleAIResultType.MESSAGE, "This is a test response")

        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.purple_ai.ask_purple", new_callable=AsyncMock) as mock_ask,
        ):
            # Setup mock ask_purple
            mock_ask.return_value = mock_result

            result = await purple_ai("test query")

            assert result == "This is a test response"
            mock_ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_purple_ai_success_power_query(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test successful PowerQuery response from Purple AI."""
        mock_result = (PurpleAIResultType.POWER_QUERY, "EventType = 'Process Creation'")

        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.purple_ai.ask_purple", new_callable=AsyncMock) as mock_ask,
        ):
            # Setup mock ask_purple
            mock_ask.return_value = mock_result

            result = await purple_ai("generate powerquery for process creation")

            assert result == "EventType = 'Process Creation'"
            mock_ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_purple_ai_settings_error(self) -> None:
        """Test that settings errors raise RuntimeError."""
        with patch(
            "purple_mcp.tools.purple_ai.get_settings",
            side_effect=RuntimeError("Settings not configured"),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                await purple_ai("test query")

            assert "Settings not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_purple_ai_graphql_error(self, mock_settings: Callable[..., MagicMock]) -> None:
        """Test that GraphQL errors are preserved."""
        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch(
                "purple_mcp.tools.purple_ai.ask_purple",
                new_callable=AsyncMock,
                side_effect=PurpleAIGraphQLError("GraphQL query failed"),
            ),
        ):
            with pytest.raises(PurpleAIGraphQLError) as exc_info:
                await purple_ai("test query")

            assert "GraphQL query failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_purple_ai_client_error(self, mock_settings: Callable[..., MagicMock]) -> None:
        """Test that client errors are preserved."""
        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch(
                "purple_mcp.tools.purple_ai.ask_purple",
                new_callable=AsyncMock,
                side_effect=PurpleAIClientError("Network connection failed"),
            ),
        ):
            with pytest.raises(PurpleAIClientError) as exc_info:
                await purple_ai("test query")

            assert "Network connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_purple_ai_none_result_type_raises_client_error(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that (None, message) responses raise PurpleAIClientError."""
        error_message = "GraphQL endpoint returned invalid response"
        mock_result = (None, error_message)

        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.purple_ai.ask_purple", new_callable=AsyncMock) as mock_ask,
        ):
            # Setup mock to return (None, error_message)
            mock_ask.return_value = mock_result

            with pytest.raises(PurpleAIClientError) as exc_info:
                await purple_ai("test query")

            # Verify the exception includes the error context
            assert "Purple AI request failed" in str(exc_info.value)
            assert error_message in str(exc_info.value)
            mock_ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_purple_ai_none_result_type_with_network_error(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that (None, message) responses for network errors raise PurpleAIClientError."""
        network_error = "Network error while communicating with Purple AI: Connection timeout"
        mock_result = (None, network_error)

        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.purple_ai.ask_purple", new_callable=AsyncMock) as mock_ask,
        ):
            # Setup mock to return (None, network_error)
            mock_ask.return_value = mock_result

            with pytest.raises(PurpleAIClientError) as exc_info:
                await purple_ai("test query")

            # Verify the exception preserves the original error context
            assert "Purple AI request failed" in str(exc_info.value)
            assert "Network error while communicating with Purple AI" in str(exc_info.value)
            mock_ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_purple_ai_none_result_type_with_missing_response_field(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that (None, message) responses for missing fields raise PurpleAIClientError."""
        field_error = "Missing purpleLaunchQuery in response"
        mock_result = (None, field_error)

        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.purple_ai.ask_purple", new_callable=AsyncMock) as mock_ask,
        ):
            # Setup mock to return (None, field_error)
            mock_ask.return_value = mock_result

            with pytest.raises(PurpleAIClientError) as exc_info:
                await purple_ai("test query")

            # Verify the exception includes the field error details
            assert "Purple AI request failed" in str(exc_info.value)
            assert field_error in str(exc_info.value)
            mock_ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_purple_ai_unknown_error_returns_friendly_message(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that UNKNOWN errors from LaunchQueryManager return a user-friendly message."""
        # Simulate the error message from Purple AI with UNKNOWN errorType
        error_message = "Error from Purple AI: {'errorDetail': None, 'errorType': 'UNKNOWN', 'origin': 'LaunchQueryManager'}"
        mock_result = (None, error_message)

        with (
            patch("purple_mcp.tools.purple_ai.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.purple_ai.ask_purple", new_callable=AsyncMock) as mock_ask,
        ):
            # Setup mock to return (None, error_message)
            mock_ask.return_value = mock_result

            # Should return a friendly message instead of raising an exception
            result = await purple_ai("test query")

            # Verify we get the user-friendly error message
            assert (
                result
                == "Purple AI encountered an error with this question. Please try rephrasing your question and submitting it again."
            )
            mock_ask.assert_called_once()


class TestPurpleAIRealClient:
    """Test purple_ai with real client instantiation and HTTP mocking using respx.

    These tests validate the full request path from tool invocation through
    configuration, client instantiation, and HTTP request construction.
    Unlike mock-based tests that stub _get_*_client, these tests:

    1. Use real Settings configuration from environment variables
    2. Instantiate actual client objects (PurpleAIClient)
    3. Construct real HTTP requests with proper headers and payloads
    4. Mock only the HTTP layer using respx to avoid network calls

    This approach provides stronger confidence that:
    - Configuration is correctly assembled and passed to clients
    - Clients format requests correctly (URL, headers, auth, payload structure)
    - Error handling works with real exceptions from the HTTP layer
    - Integration between tool → config → client → HTTP works end-to-end

    Benefits over pure mocking:
    - Catches configuration drift (wrong URL joins, missing headers)
    - Validates actual request payloads sent over the wire
    - Tests work closer to production code paths
    - Easier to debug when requests don't match expectations
    """

    @pytest.fixture(scope="session")
    def original_environment_state(self) -> dict[str, str | None]:
        """Capture the original state of sensitive environment variables at session start.

        This fixture runs once at the beginning of the test session and records
        which environment variables were present. The regression guard uses this
        to distinguish between legitimately set env vars and leaked ones.
        """
        return {
            f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT": os.environ.get(
                f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT"
            ),
            f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT": os.environ.get(
                f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT"
            ),
        }

    @pytest.fixture(autouse=True)
    def clean_environment(
        self, original_environment_state: dict[str, str | None]
    ) -> Generator[None, None, None]:
        """Set up test environment variables for all tests in this class.

        This fixture saves the original environment, sets test values, yields
        for the test to run, then restores the original environment and clears
        the settings cache to prevent test pollution.

        It also includes a regression guard to detect if CLI tests have leaked
        environment variables (particularly PURPLEMCP_CONSOLE_GRAPHQL_ENDPOINT)
        into this test's execution context.
        """
        from purple_mcp.config import get_settings

        # Regression guard: Fail fast if CLI tests leaked environment state
        # This helps catch cases where CLI tests don't properly clean up after
        # themselves, which can cause intermittent failures under pytest-xdist.
        # Only flag vars that weren't set at the start of the test session.
        leaked_vars = []
        for var, original_value in original_environment_state.items():
            current_value = os.environ.get(var)
            # If var exists now but didn't exist originally, it's a leak
            if current_value is not None and original_value is None:
                leaked_vars.append(f"{var}={current_value}")

        if leaked_vars:
            pytest.fail(
                f"Environment pollution detected! CLI tests (or other tests) "
                f"leaked environment variables that should have been cleaned up:\n"
                f"{', '.join(leaked_vars)}\n\n"
                f"This causes TestPurpleAIRealClient to use the wrong GraphQL endpoint "
                f"and fail with 'RESPX: ... not mocked!' errors under pytest-xdist.\n\n"
                f"Root cause: Tests that call _apply_environment_overrides or mutate "
                f"os.environ must restore the original values afterwards."
            )

        # Save original environment
        original_env = os.environ.copy()

        # Clear settings cache to ensure fresh settings
        get_settings.cache_clear()

        # Set test environment variables
        os.environ[f"{ENV_PREFIX}PURPLE_AI_ACCOUNT_ID"] = "test-account-123"
        os.environ[f"{ENV_PREFIX}PURPLE_AI_TEAM_TOKEN"] = "test-team-token"
        os.environ[f"{ENV_PREFIX}PURPLE_AI_EMAIL_ADDRESS"] = "test@example.test"
        os.environ[f"{ENV_PREFIX}PURPLE_AI_USER_AGENT"] = "test-agent/1.0"
        os.environ[f"{ENV_PREFIX}PURPLE_AI_BUILD_DATE"] = "2025-01-15"
        os.environ[f"{ENV_PREFIX}PURPLE_AI_BUILD_HASH"] = "abc123def456"
        os.environ[f"{ENV_PREFIX}CONSOLE_BASE_URL"] = "https://console.test"
        os.environ[f"{ENV_PREFIX}PURPLE_AI_CONSOLE_VERSION"] = "1.0.0"
        os.environ[f"{ENV_PREFIX}CONSOLE_TOKEN"] = "Bearer test-graphql-token"
        os.environ[f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN"] = "test-sdl-token"
        os.environ[f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT"] = "/web/api/v2.1/graphql"

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

        # Clear settings cache again to ensure subsequent tests don't see our test config
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_message_response(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test purple_ai with real client and mocked HTTP response for MESSAGE type."""
        # Mock the GraphQL response with proper structure
        mock_response = {
            "data": {
                "purpleLaunchQuery": {
                    "status": {},  # Empty status means no error
                    "resultType": "MESSAGE",
                    "result": {
                        "message": "This is a test response from Purple AI",
                    },
                }
            }
        }

        # Mock the HTTP POST request - URL is constructed from base_url + endpoint
        # Default endpoint is /web/api/v2.1/graphql
        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await purple_ai("test query")

        assert result == "This is a test response from Purple AI"

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_power_query_response(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test purple_ai with real client and mocked HTTP response for POWER_QUERY type."""
        # Mock the GraphQL response with proper structure
        mock_response = {
            "data": {
                "purpleLaunchQuery": {
                    "status": {},  # Empty status means no error
                    "resultType": "POWER_QUERY",
                    "result": {
                        "powerQuery": {
                            "query": "EventType = 'Process Creation' AND ProcessName = 'powershell.exe'",
                        },
                    },
                }
            }
        }

        # Mock the HTTP POST request
        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await purple_ai("generate powerquery for process creation")

        assert result == "EventType = 'Process Creation' AND ProcessName = 'powershell.exe'"

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_validates_request_structure(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test that purple_ai constructs proper GraphQL request with real client."""
        request_data = None

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal request_data
            request_data = request.content.decode("utf-8")
            return httpx.Response(
                200,
                json={
                    "data": {
                        "purpleLaunchQuery": {
                            "status": {},
                            "resultType": "MESSAGE",
                            "result": {"message": "Success"},
                        }
                    }
                },
            )

        # Mock the HTTP POST request with side effect to capture request
        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            side_effect=capture_request
        )

        await purple_ai("test security query")

        # Verify request was captured
        assert request_data is not None

        # Parse the request to validate structure properly
        import json

        request_json = json.loads(request_data)

        # Verify request contains expected GraphQL structure
        assert "query" in request_json
        assert "purpleLaunchQuery" in request_json["query"]
        assert "contentType" in request_json["query"]
        assert "NATURAL_LANGUAGE" in request_json["query"]

        # Verify the query input contains the user's query
        assert "variables" in request_json
        assert request_json["variables"].get("input") == "test security query"

        # Verify configuration values are included in the GraphQL query
        assert "test-account-123" in request_json["query"]
        # Verify console base URL is properly included in the query
        assert "baseUrl" in request_json["query"]
        assert "console.test" in request_json["query"]

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_includes_auth_header(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test that purple_ai includes proper authentication header."""
        captured_headers = None

        def capture_headers(request: httpx.Request) -> httpx.Response:
            nonlocal captured_headers
            captured_headers = request.headers
            return httpx.Response(
                200,
                json={
                    "data": {
                        "purpleLaunchQuery": {
                            "status": {},
                            "resultType": "MESSAGE",
                            "result": {"message": "Success"},
                        }
                    }
                },
            )

        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            side_effect=capture_headers
        )

        await purple_ai("test query")

        # Verify auth header was set
        # The client prepends "ApiToken" to the token
        # httpx.Headers is case-insensitive
        assert captured_headers is not None
        auth_header = captured_headers.get("authorization")
        assert auth_header is not None
        assert "ApiToken" in auth_header
        assert "test-graphql-token" in auth_header

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_includes_user_agent(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test that purple_ai includes proper user-agent header."""
        captured_headers = None

        def capture_headers(request: httpx.Request) -> httpx.Response:
            nonlocal captured_headers
            captured_headers = request.headers
            return httpx.Response(
                200,
                json={
                    "data": {
                        "purpleLaunchQuery": {
                            "status": {},
                            "resultType": "MESSAGE",
                            "result": {"message": "Success"},
                        }
                    }
                },
            )

        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            side_effect=capture_headers
        )

        await purple_ai("test query")

        # Verify user-agent header includes purple-mcp
        # httpx.Headers is case-insensitive
        assert captured_headers is not None
        user_agent = captured_headers.get("user-agent")
        assert user_agent is not None
        assert "purple-mcp" in user_agent.lower()

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_graphql_error_handling(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test that real client properly handles GraphQL errors."""
        # Mock a GraphQL error response
        mock_response = {
            "errors": [{"message": "Invalid query syntax"}],
            "data": None,
        }

        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # GraphQL errors are caught by ask_purple and returned as (None, error_message)
        # The tool then raises PurpleAIClientError with that message
        with pytest.raises(PurpleAIClientError) as exc_info:
            await purple_ai("invalid query")

        assert "Purple AI request failed" in str(exc_info.value)
        assert "GraphQL errors" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_network_error_handling(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test that real client properly handles network errors."""
        # Mock a network error
        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with pytest.raises(PurpleAIClientError) as exc_info:
            await purple_ai("test query")

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_purple_ai_real_client_http_error_handling(
        self, clean_environment: None, respx_mock: respx.MockRouter
    ) -> None:
        """Test that real client properly handles HTTP errors."""
        # Mock an HTTP 500 error
        respx_mock.post("https://console.test/web/api/v2.1/graphql").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        # HTTP errors are caught and converted to (None, error_message) by ask_purple
        # The tool then raises PurpleAIClientError
        with pytest.raises(PurpleAIClientError) as exc_info:
            await purple_ai("test query")

        # The status_code may not be preserved in the wrapped error
        assert "Purple AI request failed" in str(exc_info.value)
