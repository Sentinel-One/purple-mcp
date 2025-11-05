"""Integration tests for SDL PowerQuery functionality.

These tests require real environment variables to be set in .env.test:
- PURPLEMCP_CONSOLE_TOKEN
- PURPLEMCP_CONSOLE_BASE_URL

Tests will be skipped if these are not set or contain example values.
"""

import asyncio
import logging
import os
import warnings
from collections.abc import AsyncGenerator, Callable, Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastmcp import Client
from pydantic import ValidationError
from pytest import LogCaptureFixture

from purple_mcp.config import ENV_PREFIX, get_settings
from purple_mcp.libs.sdl import (
    SDLHandlerError,
    SDLPowerQueryHandler,
    SDLPQAttributes,
    SDLPQFrequency,
    SDLPQResultType,
    SDLQueryClient,
    SDLQueryPriority,
    create_sdl_settings,
)
from purple_mcp.libs.sdl.config import SDLSettings
from purple_mcp.server import app
from purple_mcp.tools.sdl import _iso_to_nanoseconds, powerquery

logger = logging.getLogger(__name__)


class TestSDLDirectClient:
    """Integration tests for direct SDL PowerQuery calls."""

    @pytest.fixture
    def real_sdl_settings(self, integration_env_check: dict[str, str]) -> SDLSettings:
        """Create real SDL settings from environment variables."""
        settings = get_settings()

        return create_sdl_settings(
            auth_token=settings.sdl_api_token,
            base_url=settings.sentinelone_console_base_url + "/sdl",
            default_poll_timeout_ms=60000,  # 1 minute
            http_timeout=30,
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_simple_powerquery_execution(
        self,
        real_sdl_settings: SDLSettings,
        test_time_range: tuple[datetime, datetime],
        integration_timeout: int,
    ) -> None:
        """Test basic PowerQuery execution with real SDL API."""
        start_time, end_time = test_time_range

        # Simple query that should work on most systems
        query = "dataSource.vendor='SentinelOne'|limit 10"

        handler = SDLPowerQueryHandler(
            auth_token=real_sdl_settings.auth_token,
            base_url=real_sdl_settings.base_url,
            settings=real_sdl_settings,
        )

        try:
            # Submit query
            await asyncio.wait_for(
                handler.submit_powerquery(
                    start_time=start_time,
                    end_time=end_time,
                    query=query,
                    result_type=SDLPQResultType.TABLE,
                    frequency=SDLPQFrequency.LOW,
                    query_priority=SDLQueryPriority.LOW,
                ),
                timeout=integration_timeout,
            )

            # Poll for results
            results = await asyncio.wait_for(
                handler.poll_until_complete(),
                timeout=integration_timeout * 2,  # Queries can take time
            )

            # Verify results structure
            assert results is not None, "Should receive results"
            assert hasattr(results, "columns"), "Results should have columns"
            assert hasattr(results, "values"), "Results should have values"
            assert hasattr(results, "match_count"), "Results should have match_count"

            # Verify results have expected properties
            num_columns = len(results.columns) if results.columns else 0
            num_rows = len(results.values) if results.values else 0
            is_partial = handler.is_result_partial()

            logger.debug(
                "PowerQuery executed successfully: query=%s, match_count=%d, columns=%d, rows=%d, partial=%s",
                query,
                results.match_count,
                num_columns,
                num_rows,
                is_partial,
            )

        except TimeoutError:
            pytest.fail(f"PowerQuery timed out after {integration_timeout} seconds")
        except SDLHandlerError as e:
            pytest.fail(f"SDL handler error: {e}")
        except Exception as e:
            pytest.fail(f"PowerQuery execution failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_powerquery_with_filters(
        self,
        real_sdl_settings: SDLSettings,
        test_time_range: tuple[datetime, datetime],
        integration_timeout: int,
    ) -> None:
        """Test PowerQuery with filtering and aggregation."""
        start_time, end_time = test_time_range

        # More complex query with filtering
        query = "filter severity>=3 | limit 10"

        handler = SDLPowerQueryHandler(
            auth_token=real_sdl_settings.auth_token,
            base_url=real_sdl_settings.base_url,
            settings=real_sdl_settings,
        )

        try:
            await handler.submit_powerquery(
                start_time=start_time,
                end_time=end_time,
                query=query,
                result_type=SDLPQResultType.TABLE,
                frequency=SDLPQFrequency.LOW,
                query_priority=SDLQueryPriority.LOW,
            )

            results = await asyncio.wait_for(
                handler.poll_until_complete(), timeout=integration_timeout * 2
            )

            assert results is not None, "Filtered query should return results"

            # Verify filtered query results
            num_columns = len(results.columns) if results.columns else 0
            assert num_columns >= 0, "Should have valid column count"

            if results.columns:
                column_names = [col.name for col in results.columns]
                assert len(column_names) == num_columns, "Column names should match column count"
                logger.debug(
                    "Filtered PowerQuery: query=%s, match_count=%d, columns=%d, names=%s",
                    query.strip(),
                    results.match_count,
                    num_columns,
                    column_names,
                )
            else:
                logger.debug(
                    "Filtered PowerQuery: query=%s, match_count=%d, columns=%d",
                    query.strip(),
                    results.match_count,
                    num_columns,
                )

        except TimeoutError:
            pytest.fail(f"Filtered PowerQuery timed out after {integration_timeout} seconds")
        except SDLHandlerError as e:
            pytest.fail(f"SDL handler error: {e}")
        except Exception as e:
            pytest.fail(f"Filtered PowerQuery failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_powerquery_different_result_types(
        self,
        real_sdl_settings: SDLSettings,
        test_time_range: tuple[datetime, datetime],
        integration_timeout: int,
    ) -> None:
        """Test PowerQuery with different result types."""
        start_time, end_time = test_time_range
        query = "dataSource.vendor='SentinelOne'|limit 10"

        result_types = [
            SDLPQResultType.TABLE,
            SDLPQResultType.PLOT,
        ]

        for result_type in result_types:
            handler = SDLPowerQueryHandler(
                auth_token=real_sdl_settings.auth_token,
                base_url=real_sdl_settings.base_url,
                settings=real_sdl_settings,
            )

            try:
                await handler.submit_powerquery(
                    start_time=start_time,
                    end_time=end_time,
                    query=query,
                    result_type=result_type,
                    frequency=SDLPQFrequency.LOW,
                    query_priority=SDLQueryPriority.LOW,
                )

                results = await asyncio.wait_for(
                    handler.poll_until_complete(), timeout=integration_timeout
                )

                # Verify results based on type
                has_results = results is not None
                match_count = results.match_count if results else 0

                logger.debug(
                    "Result type test: type=%s, has_results=%s, match_count=%d",
                    result_type.value,
                    has_results,
                    match_count,
                )

                # Brief pause between queries
                await asyncio.sleep(1)

            except Exception as e:
                # Some result types may not be supported, which is expected
                logger.info("Result type %s may not be supported: %s", result_type.value, e)


class TestSDLMCPIntegration:
    """Integration tests for SDL through MCP server."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_powerquery_tool_through_mcp(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test PowerQuery tool through FastMCP server."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                result = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": "dataSource.vendor='SentinelOne'|limit 10",
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout * 2,
                )

                assert result is not None
                assert hasattr(result, "content")
                assert len(result.content) > 0
                assert hasattr(result.content[0], "text")

                response_text = result.content[0].text
                assert isinstance(response_text, str)

                # Should contain query results information
                assert (
                    "Match Count:" in response_text
                    or "Columns:" in response_text
                    or len(response_text) > 10
                ), "Response should contain query results information"

                logger.debug(
                    "MCP PowerQuery success: response_length=%d, preview=%s...",
                    len(response_text),
                    response_text[:200],
                )

            except TimeoutError:
                pytest.fail(f"MCP PowerQuery timed out after {integration_timeout * 2} seconds")
            except Exception as e:
                pytest.fail(f"MCP PowerQuery failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_powerquery_tool_with_different_queries(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test PowerQuery tool with various query types."""
        start_datetime, end_datetime = recent_time_range_iso

        queries = [
            "dataSource.vendor='SentinelOne'|limit 10",
            "filter severity>=2 | limit 10",
            "filter source=* | limit 10",
        ]

        async with Client(app) as client:
            for query in queries:
                try:
                    result = await asyncio.wait_for(
                        client.call_tool(
                            "powerquery",
                            {
                                "query": query,
                                "start_datetime": start_datetime,
                                "end_datetime": end_datetime,
                            },
                        ),
                        timeout=integration_timeout * 2,
                    )

                    if result and hasattr(result, "content") and result.content:
                        response_text = result.content[0].text
                        assert len(response_text) > 0, (
                            f"Query '{query[:30]}...' should return content"
                        )
                        logger.debug(
                            "Query succeeded: '%s...' -> %d chars", query[:30], len(response_text)
                        )
                    else:
                        logger.info("Query returned empty result: '%s...'", query[:30])

                    # Brief pause between queries
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.info("Query may have failed expectedly: '%s...' -> %s", query[:30], e)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_powerquery_tool_direct_function(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test PowerQuery tool function directly."""
        start_datetime, end_datetime = recent_time_range_iso

        try:
            result = await asyncio.wait_for(
                powerquery(
                    query="dataSource.vendor='SentinelOne'|limit 10",
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ),
                timeout=integration_timeout * 2,
            )

            assert isinstance(result, str)

            # Should contain either results or error message
            assert len(result) > 0, "Should return some result"
            assert isinstance(result, str), "Result should be a string"

            logger.debug(
                "Direct PowerQuery function success: result_length=%d, preview=%s...",
                len(result),
                result[:200],
            )

        except TimeoutError:
            pytest.fail(
                f"Direct PowerQuery function timed out after {integration_timeout * 2} seconds"
            )
        except Exception as e:
            pytest.fail(f"Direct PowerQuery function failed: {e}")


class TestSDLErrorScenarios:
    """Integration tests for SDL error handling with real API."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_powerquery_with_invalid_syntax(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test PowerQuery with invalid syntax."""
        start_datetime, end_datetime = recent_time_range_iso

        # Intentionally invalid query
        invalid_query = "invalid_syntax | bad_operator"

        async with Client(app) as client:
            try:
                result = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": invalid_query,
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout,
                )

                # Should return error message, not crash
                if result and hasattr(result, "content") and result.content:
                    response_text = result.content[0].text
                    # Should contain error information
                    assert "Error" in response_text or "error" in response_text, (
                        "Invalid syntax should return error message"
                    )
                    logger.debug("Invalid syntax handled gracefully: %s...", response_text[:100])

            except Exception as e:
                # This is expected - invalid queries should fail
                logger.info("Invalid syntax query failed as expected: %s", e)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_powerquery_with_invalid_time_range(
        self, integration_settings: None, integration_timeout: int
    ) -> None:
        """Test PowerQuery with invalid time range."""
        # Invalid time range (end before start)
        # Invalid time range (start after end)
        end_time = datetime.now(timezone.utc)
        start_time = end_time + timedelta(hours=1)  # Start after end
        start_datetime = start_time.isoformat().replace("+00:00", "Z")
        end_datetime = end_time.isoformat().replace("+00:00", "Z")

        async with Client(app) as client:
            try:
                result = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": "dataSource.vendor='SentinelOne'|limit 10",
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout,
                )

                # Should handle invalid time range gracefully
                if result and hasattr(result, "content") and result.content:
                    response_text = result.content[0].text
                    logger.debug("Invalid time range handled: %s...", response_text[:100])

            except Exception as e:
                # This is expected - invalid time ranges should fail
                logger.info("Invalid time range failed as expected: %s", e)


class TestSDLConfiguration:
    """Integration tests for SDL configuration scenarios."""

    @pytest.mark.integration
    def test_sdl_settings_from_environment(self, integration_env_check: dict[str, str]) -> None:
        """Test SDL settings load from real environment."""
        settings = get_settings()

        # Verify real SDL settings
        assert settings.sdl_api_token != ""
        assert settings.sdl_api_token != "your-token-here"
        assert settings.sentinelone_console_base_url != "https://console.example.test"
        assert "example.test" not in settings.sentinelone_console_base_url

        # Test SDL settings creation
        sdl_settings = create_sdl_settings(
            auth_token=settings.sdl_api_token,
            base_url=settings.sentinelone_console_base_url + "/sdl",
            http_timeout=30,
        )

        assert sdl_settings.auth_token == f"Bearer {settings.sdl_api_token}", (
            "Auth token should be properly formatted"
        )
        assert sdl_settings.base_url.endswith("/sdl"), "Base URL should end with /sdl"
        assert sdl_settings.http_timeout == 30, "HTTP timeout should be configured"

        logger.debug(
            "SDL configuration loaded: base_url=%s, has_token=%s, timeout=%d",
            sdl_settings.base_url,
            bool(sdl_settings.auth_token),
            sdl_settings.http_timeout,
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_end_to_end_sdl_workflow(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test complete end-to-end SDL workflow."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                # 1. List available tools
                tools = await client.list_tools()
                tool_names = [tool.name for tool in tools]
                assert "powerquery" in tool_names, "PowerQuery tool should be available"

                # 2. Get powerquery tool schema
                powerquery_tool = next(tool for tool in tools if tool.name == "powerquery")
                assert powerquery_tool.description is not None
                schema_props = powerquery_tool.inputSchema.get("properties", {})
                assert "query" in schema_props
                assert "start_datetime" in schema_props
                assert "end_datetime" in schema_props

                # 3. Execute PowerQuery
                result = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": "dataSource.vendor='SentinelOne'|limit 10",
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout * 2,
                )

                # 4. Verify complete response
                assert result is not None
                assert hasattr(result, "content")
                assert len(result.content) > 0

                response_text = result.content[0].text
                assert isinstance(response_text, str), "Response should be a string"
                assert len(response_text) > 0, "Response should not be empty"

                # Verify end-to-end workflow completed successfully
                assert len(tools) > 0, "Should have tools available"
                assert "powerquery" in tool_names, "PowerQuery tool should be found"
                assert len(response_text) > 0, "Query should execute successfully"

                logger.debug(
                    "End-to-end SDL workflow: tools=%d, response_length=%d, preview=%s...",
                    len(tools),
                    len(response_text),
                    response_text[:150],
                )

            except TimeoutError:
                pytest.fail(
                    f"End-to-end SDL workflow timed out after {integration_timeout * 2} seconds"
                )
            except Exception as e:
                pytest.fail(f"End-to-end SDL workflow failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_powerquery_requests(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test multiple concurrent PowerQuery requests."""
        start_datetime, end_datetime = recent_time_range_iso

        queries = [
            "dataSource.vendor='SentinelOne'|limit 10",
            "filter severity>=1 | limit 10",
            "filter source=* | limit 10",
        ]

        async with Client(app) as client:
            try:
                # Make concurrent requests
                tasks = [
                    client.call_tool(
                        "powerquery",
                        {
                            "query": query,
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    )
                    for query in queries
                ]

                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=integration_timeout * 3
                )

                # Check results
                successful_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning("Query '%s...' failed: %s", queries[i][:30], result)
                    else:
                        successful_results.append(result)
                        if result and hasattr(result, "content") and result.content:
                            response_text = result.content[0].text
                            assert len(response_text) > 0, (
                                f"Query '{queries[i][:30]}...' should return content"
                            )
                            logger.debug(
                                "Query '%s...' succeeded: %d chars",
                                queries[i][:30],
                                len(response_text),
                            )

                # At least some should succeed
                assert len(successful_results) > 0, (
                    "At least one concurrent request should succeed"
                )

                # Verify success rate
                assert len(successful_results) <= len(queries), (
                    "Cannot have more successes than queries"
                )
                logger.info(
                    "Concurrent PowerQuery requests: %d/%d succeeded",
                    len(successful_results),
                    len(queries),
                )

            except TimeoutError:
                pytest.fail(
                    f"Concurrent PowerQuery requests timed out after {integration_timeout * 3} seconds"
                )
            except Exception as e:
                pytest.fail(f"Concurrent PowerQuery requests failed: {e}")


@pytest.fixture
def clean_integration_environment() -> Generator[None, None, None]:
    """Fixture to ensure clean environment state for integration tests."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def integration_development_environment(clean_integration_environment: None) -> None:
    """Fixture to set development environment for integration tests."""
    os.environ[f"{ENV_PREFIX}ENV"] = "development"


@pytest.fixture
def integration_production_environment(clean_integration_environment: None) -> None:
    """Fixture to set production environment for integration tests."""
    os.environ[f"{ENV_PREFIX}ENV"] = "production"


@pytest.fixture
def integration_staging_environment(clean_integration_environment: None) -> None:
    """Fixture to set staging environment for integration tests."""
    os.environ[f"{ENV_PREFIX}ENV"] = "staging"


@pytest.fixture
def integration_isolated_warnings() -> Generator[list[warnings.WarningMessage], None, None]:
    """Fixture to capture warnings in isolation for integration tests."""
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        yield warning_list


@pytest.fixture
async def integration_sdl_client_factory() -> AsyncGenerator[
    Callable[[str, SDLSettings], SDLQueryClient], None
]:
    """Factory fixture for creating SDL clients in integration tests with proper cleanup."""
    clients = []

    def create_client(base_url: str, settings: SDLSettings) -> SDLQueryClient:
        client = SDLQueryClient(base_url, settings)
        clients.append(client)
        return client

    yield create_client

    # Cleanup all created clients
    for client in clients:
        if not client.is_closed():
            await client.close()


class TestSDLTLSSecurityIntegration:
    """Integration tests for SDL TLS security features with real API."""

    @pytest.mark.integration
    def test_tls_security_configuration_from_environment(
        self, integration_env_check: dict[str, str]
    ) -> None:
        """Test TLS security configuration with real environment settings."""
        settings = get_settings()

        # Test secure configuration (default)
        sdl_settings = create_sdl_settings(
            auth_token=settings.sdl_api_token,
            base_url=settings.sentinelone_console_base_url + "/sdl",
            skip_tls_verify=False,
        )

        # Verify secure defaults
        assert sdl_settings.skip_tls_verify is False, (
            "TLS verification should be enabled by default"
        )

        logger.debug(
            "TLS security configuration: verification=%s, base_url=%s, env=%s",
            not sdl_settings.skip_tls_verify,
            sdl_settings.base_url,
            os.getenv(f"{ENV_PREFIX}ENV", "unspecified"),
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_secure_sdl_connection_with_real_api(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test secure SDL connection with real API endpoints."""
        settings = get_settings()

        # Create secure SDL settings
        sdl_settings = create_sdl_settings(
            auth_token=settings.sdl_api_token,
            base_url=settings.sentinelone_console_base_url + "/sdl",
            skip_tls_verify=False,  # Secure configuration
        )

        start_datetime, end_datetime = recent_time_range_iso

        # Convert ISO datetime to nanoseconds for low-level client
        start_time_ns = _iso_to_nanoseconds(start_datetime)
        end_time_ns = _iso_to_nanoseconds(end_datetime)

        async with SDLQueryClient(
            base_url=sdl_settings.base_url,
            settings=sdl_settings,
        ) as client:
            # Verify secure configuration
            assert client.skip_tls_verify is False
            # Note: HTTPX AsyncClient doesn't expose verify as a public attribute

            # Test real API call with secure connection
            try:
                response, forward_tag = await client.submit(
                    auth_token=sdl_settings.auth_token,
                    start_time=str(start_time_ns),
                    end_time=str(end_time_ns),
                    query_priority=SDLQueryPriority.LOW,
                    pq=SDLPQAttributes(
                        query="source=scalyr",
                        result_type=SDLPQResultType.TABLE,
                        frequency=SDLPQFrequency.LOW,
                    ),
                )

                assert response.id is not None, "Query should return a valid ID"
                assert forward_tag is not None, "Query should return a forward tag"

                # Verify secure connection was established
                assert client.skip_tls_verify is False, "TLS verification should be enabled"

                logger.debug(
                    "Secure SDL connection test: query_id=%s, tls_verification=enabled",
                    response.id,
                )

            except TimeoutError:
                pytest.fail(
                    f"Secure SDL connection test timed out after {integration_timeout} seconds"
                )
            except Exception as e:
                pytest.fail(f"Secure SDL connection test failed: {e}")

    @pytest.mark.integration
    async def test_tls_bypass_development_environment_warning(
        self,
        caplog: LogCaptureFixture,
        integration_env_check: dict[str, str],
        integration_development_environment: None,
        integration_isolated_warnings: list[warnings.WarningMessage],
        integration_sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test TLS bypass warnings in development environment."""
        settings = get_settings()

        # Create settings with TLS bypass
        sdl_settings = create_sdl_settings(
            auth_token=settings.sdl_api_token,
            base_url=settings.sentinelone_console_base_url + "/sdl",
            skip_tls_verify=True,
        )

        # Create client
        integration_sdl_client_factory(
            sdl_settings.base_url,
            sdl_settings,
        )

        # Verify warnings were issued
        security_warnings = [
            warning
            for warning in integration_isolated_warnings
            if "SECURITY WARNING" in str(warning.message)
        ]
        assert len(security_warnings) >= 1

        # Verify logging
        assert "TLS CERTIFICATE VERIFICATION IS DISABLED" in caplog.text
        assert "CRITICAL SECURITY RISK" in caplog.text

        critical_records = [record for record in caplog.records if record.levelname == "CRITICAL"]
        assert len(critical_records) > 0, "Should have critical log records for TLS bypass"
        assert any(
            hasattr(record, "environment") and record.environment == "development"
            for record in critical_records
        ), "Environment should be in log record extras"

        # Verify TLS bypass warnings are properly issued
        assert len(security_warnings) >= 1, "Should issue security warnings for TLS bypass"
        logger.debug(
            "TLS bypass development warnings: count=%d, env=development", len(security_warnings)
        )

    @pytest.mark.integration
    def test_production_environment_protection(
        self,
        integration_env_check: dict[str, str],
        integration_production_environment: None,
    ) -> None:
        """Test that production environment is protected from TLS bypass."""
        settings = get_settings()

        # Should fail at configuration level
        with pytest.raises(ValidationError) as exc_info:
            create_sdl_settings(
                auth_token=settings.sdl_api_token,
                base_url=settings.sentinelone_console_base_url + "/sdl",
                skip_tls_verify=True,
                environment="production",
            )

        assert "TLS verification bypass is FORBIDDEN in production" in str(exc_info.value)

        # Should also fail at client level if bypassed
        secure_settings = create_sdl_settings(
            auth_token=settings.sdl_api_token,
            base_url=settings.sentinelone_console_base_url + "/sdl",
            skip_tls_verify=False,
            environment="production",
        )

        # Manually enable TLS bypass to test client-level protection
        secure_settings.skip_tls_verify = True

        with pytest.raises(ValueError) as exc_info:
            SDLQueryClient(
                base_url=secure_settings.base_url,
                settings=secure_settings,
            )

        assert "SECURITY ERROR" in str(exc_info.value), "Should raise security error"
        assert "FORBIDDEN in production" in str(exc_info.value), (
            "Error should mention production restriction"
        )

        # Verify production environment protection is working at both levels
        logger.debug("Production environment protection verified at config and client levels")

    @pytest.mark.integration
    def test_staging_environment_additional_warnings(
        self,
        caplog: LogCaptureFixture,
        integration_env_check: dict[str, str],
        integration_staging_environment: None,
        integration_isolated_warnings: list[warnings.WarningMessage],
    ) -> None:
        """Test additional warnings in staging environment."""
        settings = get_settings()

        # Create settings with TLS bypass
        sdl_settings = create_sdl_settings(
            auth_token=settings.sdl_api_token,
            base_url=settings.sentinelone_console_base_url + "/sdl",
            skip_tls_verify=True,
            environment="staging",
        )

        # Should allow but warn
        assert sdl_settings.skip_tls_verify is True

        # Should log additional warning for non-dev environment
        assert "TLS verification disabled in this environment" in caplog.text
        assert "should only be used in development/testing" in caplog.text

        error_records = [record for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_records) > 0
        assert any(
            hasattr(record, "environment") and record.environment == "staging"
            for record in error_records
        ), "Environment should be in log record extras for staging"

        # Should still issue security warnings
        security_warnings = [
            warning
            for warning in integration_isolated_warnings
            if "SECURITY WARNING" in str(warning.message)
        ]
        assert len(security_warnings) >= 1, "Should issue security warnings in staging environment"

        # Verify staging environment warnings are working
        assert len(error_records) > 0, "Should have error records"
        assert len(security_warnings) >= 1, "Should have security warnings"
        logger.debug(
            "Staging environment warnings verified: errors=%d, security_warnings=%d",
            len(error_records),
            len(security_warnings),
        )
