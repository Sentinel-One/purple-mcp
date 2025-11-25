"""Tests for purple_mcp.server module.

This module tests the FastMCP server initialization, tool registration,
health check endpoint, and HTTP app configuration.
"""

import inspect
import uuid
from collections.abc import Callable
from typing import Any, Literal, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client
from fastmcp.server.http import StreamableHTTPASGIApp, StreamableHTTPSessionManager
from starlette.routing import Route

from purple_mcp import server
from purple_mcp.openai_schema import OpenAISchemaGenerator, OpenAIToolExtractor


class TestServerInitialization:
    """Tests for server initialization and configuration."""

    def _test_http_app_mode(
        self, mode: Literal["http", "streamable-http", "sse"], stateless_http: bool
    ) -> None:
        mock_settings = MagicMock()
        mock_settings.transport_mode = mode
        mock_settings.stateless_http = stateless_http

        http_app = server.get_http_app(server.app, mock_settings)

        assert http_app is not None
        # The http_app should be a Starlette application instance
        assert hasattr(http_app, "routes")

        for route in http_app.routes:
            _route = cast(Route, route)
            if _route.name == "health_check":
                continue

            if mode in ["http", "streamable-http"]:
                endpoint: StreamableHTTPASGIApp = cast(StreamableHTTPASGIApp, _route.endpoint)

                session_manager = cast(StreamableHTTPSessionManager, endpoint.session_manager)
                assert session_manager.stateless == stateless_http
            else:
                # stateless setting doesn't apply to sse mode - the prop isn't accessible in any
                # meaningful sense when http_app is initialized using sse.
                pass

    def test_server_name(self) -> None:
        """Test that the server has the correct name."""
        from purple_mcp.server import app

        assert app.name == "PurpleAIMCP"

    def test_http_app_creation(self) -> None:
        """Test that HTTP app is created with correct transport."""
        from purple_mcp.server import http_app

        assert http_app is not None
        # The http_app should be a Starlette application instance
        assert hasattr(http_app, "routes")

    def test_http_app_permutations(self) -> None:
        """Verify various settings that can be passed to http_app."""
        self._test_http_app_mode("http", stateless_http=True)
        self._test_http_app_mode("sse", stateless_http=True)
        self._test_http_app_mode("streamable-http", stateless_http=True)
        self._test_http_app_mode("http", stateless_http=False)
        self._test_http_app_mode("sse", stateless_http=False)
        self._test_http_app_mode("streamable-http", stateless_http=False)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """Test health check endpoint returns correct status."""
        from purple_mcp.server import app, http_app

        async with Client(app) as _:
            # Test the health endpoint directly through the server
            # Since it's a custom route, we need to test it via HTTP
            from starlette.testclient import TestClient

            test_client = TestClient(http_app)
            response = test_client.get("/health")

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_check_endpoint_method(self) -> None:
        """Test health check endpoint only accepts GET requests."""
        from starlette.testclient import TestClient

        from purple_mcp.server import http_app

        test_client = TestClient(http_app)

        # Test that POST is not allowed
        post_response = test_client.post("/health")
        assert post_response.status_code == 405  # Method Not Allowed

        # Test that PUT is not allowed
        put_response = test_client.put("/health")
        assert put_response.status_code == 405  # Method Not Allowed


class TestToolRegistration:
    """Tests for MCP tool registration."""

    @pytest.mark.asyncio
    async def test_purple_ai_tool_registered(self, valid_env_config: dict[str, str]) -> None:
        """Test that purple_ai tool is properly registered."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # List all available tools
            tools = await client.list_tools()

            # Check that purple_ai tool is registered
            tool_names = [tool.name for tool in tools]
            assert "purple_ai" in tool_names

            # Find the purple_ai tool and verify its properties
            purple_ai_tool = next(tool for tool in tools if tool.name == "purple_ai")
            assert purple_ai_tool.description.startswith(
                "Interact with SentinelOne's Purple AI, a cybersecurity assistant that helps you investigate threats, generate PowerQueries"
            )

            # Check that it has the expected input schema
            assert purple_ai_tool.inputSchema is not None
            assert purple_ai_tool.inputSchema.get("type") == "object"
            assert "query" in purple_ai_tool.inputSchema.get("properties", {})

    @pytest.mark.asyncio
    async def test_powerquery_tool_registered(self, valid_env_config: dict[str, str]) -> None:
        """Test that powerquery tool is properly registered."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # List all available tools
            tools = await client.list_tools()

            # Check that powerquery tool is registered
            tool_names = [tool.name for tool in tools]
            assert "powerquery" in tool_names

            # Find the powerquery tool and verify its properties
            powerquery_tool = next(tool for tool in tools if tool.name == "powerquery")
            assert powerquery_tool.description.startswith(
                "Execute advanced PowerQuery analytics on data in SentinelOne's Singularity Data Lake for complex threat hunting and data analysis."
            )

            # Check that it has the expected input schema
            assert powerquery_tool.inputSchema is not None
            assert powerquery_tool.inputSchema.get("type") == "object"
            properties = powerquery_tool.inputSchema.get("properties", {})
            assert "query" in properties
            assert "start_datetime" in properties
            assert "end_datetime" in properties

    @pytest.mark.asyncio
    async def test_get_timestamp_range_tool_registered(
        self, valid_env_config: dict[str, str]
    ) -> None:
        """Test that get_timestamp_range tool is properly registered."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # List all available tools
            tools = await client.list_tools()

            # Check that get_timestamp_range tool is registered
            tool_names = [tool.name for tool in tools]
            assert "get_timestamp_range" in tool_names

            # Find the get_timestamp_range tool and verify its properties
            timestamp_tool = next(tool for tool in tools if tool.name == "get_timestamp_range")
            assert timestamp_tool.description.startswith(
                "Generate time range timestamps for PowerQuery analytics in SentinelOne's Singularity Data Lake."
            )

            # Check that it has the expected input schema
            assert timestamp_tool.inputSchema is not None
            assert timestamp_tool.inputSchema.get("type") == "object"
            properties = timestamp_tool.inputSchema.get("properties", {})
            assert "reference_time" in properties
            assert "direction" in properties
            assert "years" in properties
            assert "months" in properties
            assert "weeks" in properties
            assert "days" in properties
            assert "hours" in properties
            assert "minutes" in properties
            assert "seconds" in properties


class TestToolExecution:
    """Tests for tool execution through the MCP protocol."""

    @pytest.mark.asyncio
    async def test_purple_ai_tool_execution_error_without_config(
        self, clean_env: dict[str, str | None]
    ) -> None:
        """Test purple_ai tool execution fails gracefully without configuration."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # Try to call purple_ai tool without proper environment configuration
            with pytest.raises(Exception) as exc_info:
                await client.call_tool("purple_ai", {"query": "test query"})

            # Should get a configuration error
            assert (
                "Settings not initialized" in str(exc_info.value)
                or "configuration" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_powerquery_tool_execution_error_without_config(
        self, clean_env: dict[str, str | None]
    ) -> None:
        """Test powerquery tool execution fails gracefully without configuration."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # Try to call powerquery tool without proper environment configuration
            with pytest.raises(Exception) as exc_info:
                await client.call_tool(
                    "powerquery",
                    {
                        "query": "test query",
                        "start_datetime": "2022-01-01T00:00:00Z",
                        "end_datetime": "2022-01-01T00:01:00Z",
                    },
                )

            # Should get a configuration error
            assert (
                "configuration" in str(exc_info.value).lower()
                or "token" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_purple_ai_tool_with_mocked_dependencies(
        self, valid_env_config: dict[str, str]
    ) -> None:
        """Test purple_ai tool execution with mocked dependencies."""
        from purple_mcp.server import app

        # Mock the settings and ask_purple function to avoid external API calls
        with (
            patch("purple_mcp.tools.purple_ai.get_settings") as mock_get_settings,
            patch("purple_mcp.tools.purple_ai.ask_purple") as mock_ask_purple,
        ):
            # Mock settings to return a valid config
            mock_settings = MagicMock()
            mock_settings.purple_ai_account_id = "test_account"
            mock_settings.purple_ai_team_token = "test_token"
            mock_settings.purple_ai_session_id = uuid.uuid4().hex
            mock_settings.purple_ai_email_address = "test@example.test"
            mock_settings.purple_ai_user_agent = "test_agent"
            mock_settings.purple_ai_build_date = "2025-01-01"
            mock_settings.purple_ai_build_hash = "test_hash"
            mock_settings.sentinelone_console_base_url = "https://test.example.test"
            mock_settings.purple_ai_console_version = "1.0.0"
            mock_settings.graphql_full_url = "https://test.example.test/graphql"
            mock_settings.graphql_service_token = "test_console_token"
            mock_get_settings.return_value = mock_settings

            mock_ask_purple.return_value = ("MESSAGE", "Mocked response from Purple AI")

            async with Client(app) as client:
                result = await client.call_tool("purple_ai", {"query": "test query"})

                assert result.content[0].text == "Mocked response from Purple AI"
                mock_ask_purple.assert_called_once()

    @pytest.mark.asyncio
    async def test_powerquery_tool_with_mocked_dependencies(
        self, valid_env_config: dict[str, str]
    ) -> None:
        """Test powerquery tool execution with mocked dependencies."""
        # Mock the SDL components to avoid external API calls
        mock_handler = AsyncMock()
        mock_handler.submit_powerquery = AsyncMock()
        mock_handler.poll_until_complete = AsyncMock()
        mock_handler.is_result_partial = AsyncMock(return_value=False)

        # Mock the result structure
        from types import SimpleNamespace

        from purple_mcp.server import app

        mock_results = AsyncMock()
        mock_results.match_count = 5
        mock_results.columns = [SimpleNamespace(name="column1"), SimpleNamespace(name="column2")]
        mock_results.values = [["value1", "value2"], ["value3", "value4"]]
        mock_results.warnings = None
        mock_handler.poll_until_complete.return_value = mock_results

        with (
            patch("purple_mcp.tools.sdl.get_settings") as mock_get_settings,
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler", return_value=mock_handler),
        ):
            # Mock settings to return a valid config
            mock_settings = MagicMock()
            mock_settings.sdl_api_token = "test_token"
            mock_settings.sentinelone_console_base_url = "https://test.example.test"
            mock_settings.environment = "development"
            mock_get_settings.return_value = mock_settings

            async with Client(app) as client:
                result = await client.call_tool(
                    "powerquery",
                    {
                        "query": "test query",
                        "start_datetime": "2022-01-01T00:00:00Z",
                        "end_datetime": "2022-01-01T00:01:00Z",
                    },
                )

                assert result.content[0].text is not None
                assert "Match Count: 5" in result.content[0].text
                assert "Columns: 2" in result.content[0].text
                assert "Rows: 2" in result.content[0].text


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self) -> None:
        """Test calling a non-existent tool."""
        from purple_mcp.server import app

        async with Client(app) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call_tool("nonexistent_tool", {"param": "value"})

            # Should get a tool not found error
            assert (
                "tool" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_tool_with_invalid_parameters(self, valid_env_config: dict[str, str]) -> None:
        """Test calling a tool with invalid parameters."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # Test purple_ai with missing required parameter
            with pytest.raises((Exception, ValueError, TypeError)):
                await client.call_tool("purple_ai", {})

            # Test powerquery with missing required parameters
            with pytest.raises((Exception, ValueError, TypeError)):
                await client.call_tool("powerquery", {"query": "test"})

    @pytest.mark.asyncio
    async def test_tool_with_wrong_parameter_types(self, valid_env_config: dict[str, str]) -> None:
        """Test calling a tool with wrong parameter types."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # Test powerquery with wrong timestamp types
            with pytest.raises((Exception, ValueError, TypeError)):
                await client.call_tool(
                    "powerquery",
                    {
                        "query": "test query",
                        "start_datetime": "not_an_iso_datetime",
                        "end_datetime": "not_an_iso_datetime",
                    },
                )


class TestServerIntegration:
    """Integration tests for the complete server setup."""

    @pytest.mark.asyncio
    async def test_server_initialization_complete(self, valid_env_config: dict[str, str]) -> None:
        """Test that server initializes completely with all components."""
        from purple_mcp.server import app

        async with Client(app) as client:
            # Test that we can connect to the server
            assert client is not None

            # Test that we can list tools (server is responsive)
            tools = await client.list_tools()
            assert len(tools) == 22

            # Test that all expected tools are present
            tool_names = [tool.name for tool in tools]
            assert "purple_ai" in tool_names
            assert "powerquery" in tool_names
            assert "get_timestamp_range" in tool_names

    def test_http_app_has_correct_routes(self) -> None:
        """Test that HTTP app has the expected routes."""
        from starlette.testclient import TestClient

        from purple_mcp.server import http_app

        test_client = TestClient(http_app)

        # Test that health route exists
        response = test_client.get("/health")
        assert response.status_code == 200

        # Test that root route exists (FastMCP default)
        response = test_client.get("/")
        assert response.status_code in [200, 404]  # May vary based on FastMCP version

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, valid_env_config: dict[str, str]) -> None:
        """Test that server can handle concurrent tool calls."""
        import asyncio

        from purple_mcp.server import app

        # Mock the dependencies to avoid external calls
        with (
            patch("purple_mcp.tools.purple_ai.get_settings") as mock_get_settings,
            patch("purple_mcp.tools.purple_ai.ask_purple") as mock_ask_purple,
        ):
            # Mock settings to return a valid config
            mock_settings = MagicMock()
            mock_settings.purple_ai_account_id = "test_account"
            mock_settings.purple_ai_team_token = "test_token"
            mock_settings.purple_ai_session_id = uuid.uuid4().hex
            mock_settings.purple_ai_email_address = "test@example.test"
            mock_settings.purple_ai_user_agent = "test_agent"
            mock_settings.purple_ai_build_date = "2025-01-01"
            mock_settings.purple_ai_build_hash = "test_hash"
            mock_settings.sentinelone_console_base_url = "https://test.example.test"
            mock_settings.purple_ai_console_version = "1.0.0"
            mock_settings.graphql_full_url = "https://test.example.test/graphql"
            mock_settings.graphql_service_token = "test_console_token"
            mock_get_settings.return_value = mock_settings

            mock_ask_purple.return_value = ("MESSAGE", "Concurrent response")

            async with Client(app) as client:
                # Make multiple concurrent calls
                tasks = [client.call_tool("purple_ai", {"query": f"query {i}"}) for i in range(3)]

                results = await asyncio.gather(*tasks)

                # All calls should succeed
                assert len(results) == 3
                for result in results:
                    assert result.content[0].text == "Concurrent response"

                # ask_purple should have been called 3 times
                assert mock_ask_purple.call_count == 3


class TestOpenAICompatibility:
    """Tests for OpenAI function schema compatibility."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.schema_generator = OpenAISchemaGenerator()
        self.tool_extractor = OpenAIToolExtractor()

    async def test_all_tools_are_openai_compatible(self) -> None:
        """Test that all registered MCP tools generate OpenAI-compatible schemas."""
        tools = await self._get_tools_for_testing()
        assert len(tools) > 0, "No tools found to test"

        all_errors: list[str] = []
        tested_tools: list[str] = []

        for tool in tools:
            func = self.tool_extractor.extract_function_from_tool(tool)
            if func is None:
                continue

            func_name = getattr(func, "__name__", str(func))
            tested_tools.append(func_name)

            schema = self.schema_generator.generate_schema(func)
            errors = self.schema_generator.validate_schema(schema, func_name)
            all_errors.extend(errors)

            # Additional checks for specific known issues
            if func_name == "search_alerts":
                search_errors = self.schema_generator.validate_search_alerts_filters(schema)
                all_errors.extend(search_errors)

        self._verify_all_expected_tools_tested(tested_tools)
        self._check_for_validation_errors(all_errors)

    async def _get_tools_for_testing(self) -> list[Callable[..., Any]]:
        """Get all tools for testing from app or fallback imports.

        Uses Any for return type because test needs to handle diverse tool functions
        with different signatures (async vs sync, str vs dict returns, etc.)
        This is appropriate in test code for validating schema generation.
        """
        from purple_mcp.server import app

        try:
            # Use public API to get registered tools (preferred method)
            tools_dict = await app.get_tools()
            return [tool.fn for tool in tools_dict.values() if hasattr(tool, "fn")]
        except Exception:
            # Fallback to direct imports if app.get_tools() is not available
            from purple_mcp.tools.alerts import (
                get_alert,
                get_alert_history,
                get_alert_notes,
                list_alerts,
                search_alerts,
            )
            from purple_mcp.tools.inventory import (
                get_inventory_item,
                list_inventory_items,
                search_inventory_items,
            )
            from purple_mcp.tools.misconfigurations import (
                get_misconfiguration,
                get_misconfiguration_history,
                get_misconfiguration_notes,
                list_misconfigurations,
                search_misconfigurations,
            )
            from purple_mcp.tools.purple_ai import purple_ai
            from purple_mcp.tools.purple_utils import iso_to_unix_timestamp
            from purple_mcp.tools.sdl import get_timestamp_range, powerquery
            from purple_mcp.tools.vulnerabilities import (
                get_vulnerability,
                get_vulnerability_history,
                get_vulnerability_notes,
                list_vulnerabilities,
                search_vulnerabilities,
            )

            return [
                purple_ai,
                powerquery,
                get_timestamp_range,
                iso_to_unix_timestamp,
                get_alert,
                list_alerts,
                search_alerts,
                get_alert_notes,
                get_alert_history,
                get_misconfiguration,
                list_misconfigurations,
                search_misconfigurations,
                get_misconfiguration_notes,
                get_misconfiguration_history,
                get_vulnerability,
                list_vulnerabilities,
                search_vulnerabilities,
                get_vulnerability_notes,
                get_vulnerability_history,
                get_inventory_item,
                list_inventory_items,
                search_inventory_items,
            ]

    def _verify_all_expected_tools_tested(self, tested_tools: list[str]) -> None:
        """Verify that all expected tools were tested."""
        expected_tools = [
            "purple_ai",
            "powerquery",
            "get_timestamp_range",
            "iso_to_unix_timestamp",
            "get_alert",
            "list_alerts",
            "search_alerts",
            "get_alert_notes",
            "get_alert_history",
            "get_misconfiguration",
            "list_misconfigurations",
            "search_misconfigurations",
            "get_misconfiguration_notes",
            "get_misconfiguration_history",
            "get_vulnerability",
            "list_vulnerabilities",
            "search_vulnerabilities",
            "get_vulnerability_notes",
            "get_vulnerability_history",
            "get_inventory_item",
            "list_inventory_items",
            "search_inventory_items",
        ]

        for expected in expected_tools:
            assert expected in tested_tools, f"Expected tool '{expected}' was not tested"

    def _check_for_validation_errors(self, all_errors: list[str]) -> None:
        """Check for validation errors and fail if any found."""
        if all_errors:
            error_msg = "OpenAI compatibility errors found:\n" + "\n".join(
                f"  - {e}" for e in all_errors
            )
            pytest.fail(error_msg)

    def test_optional_parameters_not_in_required_array(self) -> None:
        """Test that optional parameters are correctly excluded from required arrays."""
        from typing import Optional, get_origin

        from purple_mcp.tools.alerts import get_alert_history, list_alerts, search_alerts

        # Functions with optional parameters
        # Using Any for function signatures in test code to handle diverse tool functions
        functions_with_optional_params: list[tuple[Callable[..., Any], list[str]]] = [
            (search_alerts, ["filters", "after"]),
            (list_alerts, ["after"]),
            (get_alert_history, ["after"]),
        ]

        for func, optional_params in functions_with_optional_params:
            sig = inspect.signature(func)

            for param_name in optional_params:
                param = sig.parameters.get(param_name)
                assert param is not None, f"{func.__name__}: Parameter '{param_name}' not found"

                # Check that parameter has Optional type annotation
                param_type = param.annotation
                is_optional = get_origin(param_type) is Optional or (
                    hasattr(param_type, "__args__") and type(None) in param_type.__args__
                )

                assert is_optional, (
                    f"{func.__name__}: Parameter '{param_name}' should have Optional type annotation"
                )

                # Check that parameter has None as default
                assert param.default is None, (
                    f"{func.__name__}: Parameter '{param_name}' should have None as default value"
                )
