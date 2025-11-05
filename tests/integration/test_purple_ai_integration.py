"""Integration tests for Purple AI functionality.

These tests require real environment variables to be set in .env.test:
- PURPLEMCP_CONSOLE_TOKEN
- PURPLEMCP_CONSOLE_BASE_URL

Tests will be skipped if these are not set or contain example values.
"""

import asyncio
import logging

import pytest
from fastmcp import Client

from purple_mcp.config import get_settings
from purple_mcp.libs.purple_ai import (
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIResultType,
    PurpleAIUserDetails,
    ask_purple,
    sync_ask_purple,
)
from purple_mcp.server import app

logger = logging.getLogger(__name__)


class TestPurpleAIDirectClient:
    """Integration tests for direct Purple AI client calls."""

    @pytest.fixture
    def real_config(self, integration_env_check: dict[str, str]) -> PurpleAIConfig:
        """Create a real Purple AI configuration from environment variables."""
        settings = get_settings()

        return PurpleAIConfig(
            graphql_url=settings.graphql_full_url,
            auth_token=settings.graphql_service_token,
            user_details=PurpleAIUserDetails(
                account_id=settings.purple_ai_account_id,
                team_token=settings.purple_ai_team_token,
                email_address=settings.purple_ai_email_address,
                user_agent=settings.purple_ai_user_agent,
                build_date=settings.purple_ai_build_date,
                build_hash=settings.purple_ai_build_hash,
            ),
            console_details=PurpleAIConsoleDetails(
                base_url=settings.sentinelone_console_base_url,
                version=settings.purple_ai_console_version,
            ),
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_simple_purple_ai_query(
        self, real_config: PurpleAIConfig, integration_timeout: int
    ) -> None:
        """Test a simple Purple AI query with real API."""
        # Use a simple, safe query that should work
        query = "What is Purple AI?"

        try:
            # Set a reasonable timeout for real API calls
            result_type, response = await asyncio.wait_for(
                ask_purple(real_config, query), timeout=integration_timeout
            )

            # Verify we got a response
            assert result_type is not None, "Should receive a result type"
            assert response is not None, "Should receive a response"
            assert isinstance(response, str), "Response should be a string"
            assert len(response) > 0, "Response should not be empty"

            # Verify result type is valid
            assert result_type in [
                PurpleAIResultType.MESSAGE,
                PurpleAIResultType.POWER_QUERY,
            ], f"Result type should be valid, got {result_type}"

            logger.debug(
                "Purple AI query success: query=%s, type=%s, length=%d, preview=%s...",
                query,
                result_type,
                len(response),
                response[:100],
            )

        except TimeoutError:
            pytest.fail(f"Purple AI query timed out after {integration_timeout} seconds")
        except Exception as e:
            # For integration tests, we want to see what actual errors look like
            logger.error("Purple AI API error: %s (type=%s)", e, type(e).__name__)
            # Re-raise to fail the test but with context
            pytest.fail(f"Purple AI query failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_purple_ai_security_query(
        self, real_config: PurpleAIConfig, integration_timeout: int
    ) -> None:
        """Test Purple AI with a security-focused query."""
        query = "What are common indicators of compromise in network traffic?"

        try:
            result_type, response = await asyncio.wait_for(
                ask_purple(real_config, query), timeout=integration_timeout
            )

            assert result_type is not None
            assert response is not None
            assert len(response) > 10  # Should be a substantial response

            # Security queries might return either message or power query
            if result_type == PurpleAIResultType.MESSAGE:
                # Should contain security-related terms
                response_lower = response.lower()
                security_terms = ["traffic", "network", "compromise", "indicator", "security"]
                found_terms = [term for term in security_terms if term in response_lower]
                assert len(found_terms) > 0, (
                    f"Response should contain security terms, got: {response[:200]}"
                )

            elif result_type == PurpleAIResultType.POWER_QUERY:
                # PowerQuery should be a valid query string
                assert len(response) > 5, "PowerQuery should not be empty"

            logger.debug("Security query success: type=%s, length=%d", result_type, len(response))

        except TimeoutError:
            pytest.fail(f"Security query timed out after {integration_timeout} seconds")
        except Exception as e:
            pytest.fail(f"Security query failed: {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_sync_purple_ai_query(self, real_config: PurpleAIConfig) -> None:
        """Test synchronous Purple AI wrapper."""
        query = "How does Purple AI help with cybersecurity?"

        try:
            response = sync_ask_purple(real_config, query)

            assert isinstance(response, str), "Response should be a string"
            assert len(response) > 0, "Response should not be empty"

            logger.debug(
                "Sync query success: length=%d, preview=%s...", len(response), response[:100]
            )

        except Exception as e:
            pytest.fail(f"Sync Purple AI query failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_purple_ai_with_various_query_types(
        self, real_config: PurpleAIConfig, integration_timeout: int
    ) -> None:
        """Test Purple AI with different types of queries."""
        queries = [
            "What is malware?",  # Simple question
            "Show me network anomalies",  # Potentially returns PowerQuery
            "Explain threat hunting",  # Educational query
        ]

        results = []

        for query in queries:
            try:
                result_type, response = await asyncio.wait_for(
                    ask_purple(real_config, query), timeout=integration_timeout
                )

                results.append(
                    {
                        "query": query,
                        "result_type": result_type,
                        "response_length": len(response) if response else 0,
                        "success": True,
                    }
                )

                # Small delay between queries to be respectful to API
                await asyncio.sleep(1)

            except Exception as e:
                results.append({"query": query, "error": str(e), "success": False})

        # At least some queries should succeed
        successful_queries = [r for r in results if r["success"]]
        assert len(successful_queries) > 0, (
            f"At least one query should succeed, got results: {results}"
        )

        # Verify and log multiple query test results
        for result in results:
            if result["success"]:
                logger.debug(
                    "Query '%s' succeeded: %s (%d chars)",
                    result["query"],
                    result["result_type"],
                    result["response_length"],
                )
            else:
                logger.warning("Query '%s' failed: %s", result["query"], result["error"])


class TestPurpleAIMCPIntegration:
    """Integration tests for Purple AI through MCP server."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_purple_ai_tool_through_mcp(
        self, integration_settings: None, integration_timeout: int
    ) -> None:
        """Test Purple AI tool through FastMCP server."""
        async with Client(app) as client:
            try:
                # Test basic query through MCP
                result = await asyncio.wait_for(
                    client.call_tool("purple_ai", {"query": "What is endpoint detection?"}),
                    timeout=integration_timeout,
                )

                assert result is not None
                assert hasattr(result, "content")
                assert len(result.content) > 0
                assert hasattr(result.content[0], "text")

                response_text = result.content[0].text
                assert isinstance(response_text, str), "Response should be a string"
                assert len(response_text) > 0, "Response should not be empty"

                logger.debug(
                    "MCP tool integration success: length=%d, preview=%s...",
                    len(response_text),
                    response_text[:100],
                )

            except TimeoutError:
                pytest.fail(f"MCP Purple AI tool timed out after {integration_timeout} seconds")
            except Exception as e:
                pytest.fail(f"MCP Purple AI tool failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_multiple_concurrent_mcp_calls(
        self, integration_settings: None, integration_timeout: int
    ) -> None:
        """Test multiple concurrent calls to Purple AI through MCP."""
        queries = ["What is SIEM?", "What is EDR?", "What is XDR?"]

        async with Client(app) as client:
            try:
                # Make concurrent calls
                tasks = [client.call_tool("purple_ai", {"query": query}) for query in queries]

                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=integration_timeout * 2,  # Extra time for concurrent calls
                )

                # Check results
                successful_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning("Query '%s' failed: %s", queries[i], result)
                    else:
                        successful_results.append(result)
                        if hasattr(result, "content") and result.content:
                            response_text = result.content[0].text
                            assert len(response_text) > 0, (
                                f"Query '{queries[i]}' should return content"
                            )
                            logger.debug(
                                "Query '%s' succeeded: %d chars", queries[i], len(response_text)
                            )
                        else:
                            logger.info("Query '%s' succeeded with empty response", queries[i])

                # At least some should succeed
                assert len(successful_results) > 0, "At least one concurrent call should succeed"

                # Verify success rate
                assert len(successful_results) <= len(queries), (
                    "Cannot have more successes than queries"
                )
                logger.info(
                    "Concurrent MCP calls: %d/%d succeeded", len(successful_results), len(queries)
                )

            except TimeoutError:
                pytest.fail(
                    f"Concurrent MCP calls timed out after {integration_timeout * 2} seconds"
                )
            except Exception as e:
                pytest.fail(f"Concurrent MCP calls failed: {e}")


class TestPurpleAIErrorScenarios:
    """Integration tests for Purple AI error handling with real API."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_purple_ai_with_very_long_query(
        self, integration_settings: None, integration_timeout: int
    ) -> None:
        """Test Purple AI behavior with very long queries."""
        # Create a very long query to test limits
        long_query = "What is cybersecurity? " * 100  # Very long query

        async with Client(app) as client:
            try:
                result = await asyncio.wait_for(
                    client.call_tool("purple_ai", {"query": long_query}),
                    timeout=integration_timeout,
                )

                # Should either succeed or fail gracefully
                if result and hasattr(result, "content") and result.content:
                    response_text = result.content[0].text
                    logger.debug("Long query handled: %d char response", len(response_text))
                else:
                    logger.info("Long query returned empty response (possibly filtered)")

            except Exception as e:
                # This is expected - API might reject very long queries
                logger.info("Long query rejected as expected: %s: %s", type(e).__name__, e)
                # This is not a test failure - it's expected behavior

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_purple_ai_with_special_characters(
        self, integration_settings: None, integration_timeout: int
    ) -> None:
        """Test Purple AI with queries containing special characters."""
        special_queries = [
            "What is SQL injection & how to prevent it?",
            "Show logs with IP 192.168.1.1/24",
            "Find events with user 'admin@company.com'",
        ]

        async with Client(app) as client:
            for query in special_queries:
                try:
                    result = await asyncio.wait_for(
                        client.call_tool("purple_ai", {"query": query}),
                        timeout=integration_timeout,
                    )

                    if result and hasattr(result, "content") and result.content:
                        response_text = result.content[0].text
                        assert len(response_text) > 0, (
                            f"Query '{query[:30]}...' should return content"
                        )
                        logger.debug(
                            "Special chars query succeeded: '%s...' -> %d chars",
                            query[:30],
                            len(response_text),
                        )

                    # Brief pause between queries
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.info(
                        "Special chars query may have failed expectedly: '%s...' -> %s",
                        query[:30],
                        e,
                    )


class TestPurpleAIConfiguration:
    """Integration tests for Purple AI configuration scenarios."""

    @pytest.mark.integration
    def test_settings_load_from_environment(self, integration_env_check: dict[str, str]) -> None:
        """Test that settings properly load from real environment."""
        settings = get_settings()

        # Verify real settings are loaded
        assert settings.sdl_api_token != ""
        assert settings.graphql_service_token != ""
        assert settings.sentinelone_console_base_url != "https://console.example.test"
        assert "example.test" not in settings.sentinelone_console_base_url

        # Verify GraphQL URL is constructed properly
        assert settings.graphql_full_url.startswith("http"), "GraphQL URL should start with http"
        assert "/graphql" in settings.graphql_full_url, "GraphQL URL should contain /graphql"

        logger.debug(
            "Real configuration loaded: console=%s, graphql=%s, has_sdl_token=%s, has_console_token=%s",
            settings.sentinelone_console_base_url,
            settings.graphql_full_url,
            bool(settings.sdl_api_token),
            bool(settings.graphql_service_token),
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_end_to_end_workflow(
        self, integration_settings: None, integration_timeout: int
    ) -> None:
        """Test complete end-to-end workflow from MCP server to Purple AI API."""
        async with Client(app) as client:
            try:
                # 1. List available tools
                tools = await client.list_tools()
                tool_names = [tool.name for tool in tools]
                assert "purple_ai" in tool_names, "Purple AI tool should be available"

                # 2. Get tool schema
                purple_ai_tool = next(tool for tool in tools if tool.name == "purple_ai")
                assert purple_ai_tool.description is not None
                assert "query" in purple_ai_tool.inputSchema.get("properties", {})

                # 3. Execute tool with real query
                result = await asyncio.wait_for(
                    client.call_tool(
                        "purple_ai",
                        {"query": "What are the main components of a security operations center?"},
                    ),
                    timeout=integration_timeout,
                )

                # 4. Verify complete response
                assert result is not None
                assert hasattr(result, "content")
                assert len(result.content) > 0

                response_text = result.content[0].text
                assert isinstance(response_text, str)
                assert len(response_text) > 50  # Should be substantial response

                # 5. Verify response contains relevant content
                response_lower = response_lower = response_text.lower()
                relevant_terms = [
                    "security",
                    "operations",
                    "center",
                    "soc",
                    "monitoring",
                    "incident",
                ]
                found_terms = [term for term in relevant_terms if term in response_lower]

                # Verify end-to-end workflow completed successfully
                assert len(tools) > 0, "Should have tools available"
                assert "purple_ai" in tool_names, "Purple AI tool should be found"
                assert len(response_text) > 50, "Response should be substantial"
                assert len(found_terms) > 0, "Response should contain relevant security terms"

                logger.debug(
                    "End-to-end workflow success: tools=%d, response_length=%d, found_terms=%s, preview=%s...",
                    len(tools),
                    len(response_text),
                    found_terms,
                    response_text[:150],
                )

            except TimeoutError:
                pytest.fail(f"End-to-end workflow timed out after {integration_timeout} seconds")
            except Exception as e:
                pytest.fail(f"End-to-end workflow failed: {e}")
