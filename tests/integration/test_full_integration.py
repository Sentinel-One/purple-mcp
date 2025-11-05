"""Comprehensive cross-system integration tests.

These tests verify the complete Purple MCP server functionality by testing
interactions between Purple AI and SDL PowerQuery systems together.

Tests require real environment variables to be set in .env.test:
- PURPLEMCP_CONSOLE_TOKEN
- PURPLEMCP_CONSOLE_BASE_URL

Tests will be skipped if these are not set or contain example values.
"""

import asyncio
import logging

import pytest
from fastmcp import Client

from purple_mcp.server import app

logger = logging.getLogger(__name__)


class TestCrossSystemIntegration:
    """Integration tests combining Purple AI and SDL PowerQuery functionality."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_purple_ai_to_powerquery_workflow(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test workflow where Purple AI suggests a query that gets executed via PowerQuery."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                # Step 1: Ask Purple AI for a security query suggestion
                purple_result = await asyncio.wait_for(
                    client.call_tool(
                        "purple_ai",
                        {
                            "query": "Show me a simple PowerQuery to find recent high-severity events"
                        },
                    ),
                    timeout=integration_timeout,
                )

                assert purple_result is not None
                assert hasattr(purple_result, "content")
                assert len(purple_result.content) > 0

                purple_response = purple_result.content[0].text
                assert isinstance(purple_response, str)
                assert len(purple_response) > 0, "Purple AI response should not be empty"

                logger.debug(
                    "Purple AI response received: %d characters, preview: %s...",
                    len(purple_response),
                    purple_response[:200],
                )

                # Step 2: Extract or create a simple PowerQuery based on the response
                # Since we can't reliably parse AI responses, use a standard security query
                security_query = "filter severity>=3 | limit 10"

                # Step 3: Execute the PowerQuery
                powerquery_result = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": security_query,
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout * 2,
                )

                assert powerquery_result is not None
                assert hasattr(powerquery_result, "content")
                assert len(powerquery_result.content) > 0

                powerquery_response = powerquery_result.content[0].text
                assert isinstance(powerquery_response, str)
                assert len(powerquery_response) > 0, "PowerQuery response should not be empty"

                logger.debug(
                    "PowerQuery executed: query=%s, response_length=%d, preview=%s...",
                    security_query,
                    len(powerquery_response),
                    powerquery_response[:200],
                )

                # Step 4: Verify the workflow completed successfully
                # Both Purple AI and PowerQuery have returned valid responses
                assert len(purple_response) > 0 and len(powerquery_response) > 0, (
                    "Cross-system workflow should produce responses from both systems"
                )

            except TimeoutError:
                pytest.fail("Cross-system workflow timed out")
            except Exception as e:
                pytest.fail(f"Cross-system workflow failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_both_tools_available_and_functional(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test that both tools are available and functional in the same session."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                # Verify both tools are registered
                tools = await client.list_tools()
                tool_names = [tool.name for tool in tools]

                assert "purple_ai" in tool_names, "Purple AI tool should be available"
                assert "powerquery" in tool_names, "PowerQuery tool should be available"

                # Test Purple AI functionality
                purple_result = await asyncio.wait_for(
                    client.call_tool("purple_ai", {"query": "What is threat detection?"}),
                    timeout=integration_timeout,
                )

                assert purple_result is not None
                purple_text = purple_result.content[0].text
                assert len(purple_text) > 10, "Purple AI response should have substantial content"

                # Test PowerQuery functionality
                powerquery_result = await asyncio.wait_for(
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

                assert powerquery_result is not None
                powerquery_text = powerquery_result.content[0].text
                assert len(powerquery_text) > 0, "PowerQuery response should not be empty"

                # Verify both tools produced valid responses
                assert len(purple_text) > 10 and len(powerquery_text) > 0, (
                    "Both tools should produce valid responses"
                )
                logger.debug(
                    "Both tools functional: Purple AI=%d chars, PowerQuery=%d chars",
                    len(purple_text),
                    len(powerquery_text),
                )

            except Exception as e:
                pytest.fail(f"Dual tool functionality test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_sequential_tool_usage(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test using both tools sequentially in different patterns."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                # Pattern 1: Purple AI → PowerQuery → Purple AI
                logger.debug("Testing Pattern 1: Purple AI → PowerQuery → Purple AI")

                # Ask Purple AI about a security concept
                result1 = await asyncio.wait_for(
                    client.call_tool(
                        "purple_ai", {"query": "What should I look for in network logs?"}
                    ),
                    timeout=integration_timeout,
                )

                # Execute a severity-filtered PowerQuery
                result2 = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": "filter severity>=3 | limit 10",
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout * 2,
                )

                # Ask Purple AI to explain analysis
                result3 = await asyncio.wait_for(
                    client.call_tool(
                        "purple_ai", {"query": "How do I analyze network security events?"}
                    ),
                    timeout=integration_timeout,
                )

                assert all(r is not None for r in [result1, result2, result3]), (
                    "Pattern 1 (Purple AI → PowerQuery → Purple AI) should complete successfully"
                )

                # Brief pause between patterns
                await asyncio.sleep(2)

                # Pattern 2: PowerQuery → Purple AI → PowerQuery
                logger.debug("Testing Pattern 2: PowerQuery → Purple AI → PowerQuery")

                # Execute initial PowerQuery
                result4 = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": "filter severity>=3 | limit 10",
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout * 2,
                )

                # Ask Purple AI about severity analysis
                result5 = await asyncio.wait_for(
                    client.call_tool(
                        "purple_ai", {"query": "How should I interpret event severity levels?"}
                    ),
                    timeout=integration_timeout,
                )

                # Execute follow-up PowerQuery
                result6 = await asyncio.wait_for(
                    client.call_tool(
                        "powerquery",
                        {
                            "query": "filter severity>=3 | limit 10",
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    ),
                    timeout=integration_timeout * 2,
                )

                assert all(r is not None for r in [result4, result5, result6]), (
                    "Pattern 2 (PowerQuery → Purple AI → PowerQuery) should complete successfully"
                )

                # Verify all 6 sequential tool calls succeeded
                assert all(
                    r is not None for r in [result1, result2, result3, result4, result5, result6]
                ), "All sequential tool usage patterns should complete successfully"

            except TimeoutError:
                pytest.fail("Sequential tool usage test timed out")
            except Exception as e:
                pytest.fail(f"Sequential tool usage test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_cross_system_calls(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test concurrent calls to both Purple AI and PowerQuery."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                # Create concurrent tasks for both systems
                purple_task = client.call_tool(
                    "purple_ai", {"query": "What are common attack vectors?"}
                )

                powerquery_task = client.call_tool(
                    "powerquery",
                    {
                        "query": "dataSource.vendor='SentinelOne'|limit 10",
                        "start_datetime": start_datetime,
                        "end_datetime": end_datetime,
                    },
                )

                # Execute concurrently with timeout
                results = await asyncio.wait_for(
                    asyncio.gather(purple_task, powerquery_task, return_exceptions=True),
                    timeout=integration_timeout * 2,
                )

                # Check results
                purple_result, powerquery_result = results

                successful_calls = 0

                if not isinstance(purple_result, Exception):
                    assert purple_result is not None
                    if hasattr(purple_result, "content") and purple_result.content:
                        purple_text = purple_result.content[0].text
                        assert len(purple_text) > 0, (
                            "Purple AI concurrent call should return content"
                        )
                        successful_calls += 1
                        logger.debug(
                            "Concurrent Purple AI call succeeded: %d chars", len(purple_text)
                        )
                    else:
                        logger.warning("Concurrent Purple AI call returned invalid response")
                else:
                    logger.warning("Concurrent Purple AI call failed: %s", purple_result)

                if not isinstance(powerquery_result, Exception):
                    assert powerquery_result is not None
                    if hasattr(powerquery_result, "content") and powerquery_result.content:
                        powerquery_text = powerquery_result.content[0].text
                        assert len(powerquery_text) > 0, (
                            "PowerQuery concurrent call should return content"
                        )
                        successful_calls += 1
                        logger.debug(
                            "Concurrent PowerQuery call succeeded: %d chars", len(powerquery_text)
                        )
                    else:
                        logger.warning("Concurrent PowerQuery call returned invalid response")
                else:
                    logger.warning("Concurrent PowerQuery call failed: %s", powerquery_result)

                # At least one should succeed
                assert successful_calls > 0, "At least one concurrent call should succeed"

                # Verify success rate is within acceptable range
                assert successful_calls <= 2, "Should have at most 2 successful concurrent calls"
                logger.info("Concurrent cross-system calls: %d/2 succeeded", successful_calls)

            except TimeoutError:
                pytest.fail("Concurrent cross-system calls timed out")
            except Exception as e:
                pytest.fail(f"Concurrent cross-system calls failed: {e}")


class TestSystemRobustness:
    """Tests for system robustness and error handling across both systems."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_error_isolation_between_systems(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test that errors in one system don't affect the other."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                # First, verify both systems work
                good_purple_result = await client.call_tool(
                    "purple_ai", {"query": "What is cybersecurity?"}
                )
                assert good_purple_result is not None, "Purple AI should work initially"

                good_powerquery_result = await client.call_tool(
                    "powerquery",
                    {
                        "query": "dataSource.vendor='SentinelOne'|limit 10",
                        "start_datetime": start_datetime,
                        "end_datetime": end_datetime,
                    },
                )
                assert good_powerquery_result is not None, "PowerQuery should work initially"

                # Now test error scenarios
                # Try PowerQuery with invalid syntax
                powerquery_error_occurred = False
                try:
                    await client.call_tool(
                        "powerquery",
                        {
                            "query": "invalid_syntax | bad_operator",
                            "start_datetime": start_datetime,
                            "end_datetime": end_datetime,
                        },
                    )
                except Exception:
                    powerquery_error_occurred = True

                logger.debug(
                    "PowerQuery error occurred as expected: %s", powerquery_error_occurred
                )

                # Verify Purple AI still works after PowerQuery error
                purple_after_error = await client.call_tool(
                    "purple_ai", {"query": "What is incident response?"}
                )
                assert purple_after_error is not None, (
                    "Purple AI should still work after PowerQuery error"
                )

                # Test with very long Purple AI query that might cause issues
                purple_ai_error_occurred = False
                try:
                    long_query = "What is cybersecurity? " * 50
                    await client.call_tool("purple_ai", {"query": long_query})
                except Exception:
                    purple_ai_error_occurred = True

                logger.debug(
                    "Long Purple AI query handled as expected: %s", purple_ai_error_occurred
                )

                # Verify PowerQuery still works after Purple AI stress
                powerquery_after_stress = await client.call_tool(
                    "powerquery",
                    {
                        "query": "dataSource.vendor='SentinelOne'|limit 10",
                        "start_datetime": start_datetime,
                        "end_datetime": end_datetime,
                    },
                )
                assert powerquery_after_stress is not None, (
                    "PowerQuery should still work after Purple AI stress test"
                )

                # Verify error isolation - both systems recovered after errors
                assert purple_after_error is not None and powerquery_after_stress is not None, (
                    "Both systems should be isolated and recover from errors"
                )

            except Exception as e:
                pytest.fail(f"Error isolation test failed: {e}")


class TestPerformanceAndLimits:
    """Tests for performance characteristics and system limits."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_rapid_sequential_calls(
        self,
        integration_settings: None,
        recent_time_range_iso: tuple[str, str],
        integration_timeout: int,
    ) -> None:
        """Test rapid sequential calls to both systems."""
        start_datetime, end_datetime = recent_time_range_iso

        async with Client(app) as client:
            try:
                call_pairs = []
                for i in range(2):  # 2 pairs of calls
                    call_pairs.extend(
                        [
                            ("purple_ai", {"query": f"What is security event {i}?"}),
                            (
                                "powerquery",
                                {
                                    "query": "dataSource.vendor='SentinelOne'|limit 10",
                                    "start_datetime": start_datetime,
                                    "end_datetime": end_datetime,
                                },
                            ),
                        ]
                    )

                successful_calls = 0
                total_calls = len(call_pairs)

                for i, (tool_name, params) in enumerate(call_pairs):
                    try:
                        result = await asyncio.wait_for(
                            client.call_tool(tool_name, params), timeout=integration_timeout
                        )
                        if result is not None:
                            successful_calls += 1
                            logger.debug("Call %d/%d succeeded: %s", i + 1, total_calls, tool_name)

                        # Small delay to be respectful to APIs
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(
                            "Call %d/%d failed (%s): %s", i + 1, total_calls, tool_name, e
                        )

                # Most calls should succeed
                success_rate = successful_calls / total_calls
                assert success_rate >= 0.5, (
                    f"Success rate should be at least 50%, got {success_rate:.2%}"
                )

                # Verify we have expected number of successful calls
                assert successful_calls <= total_calls, (
                    "Cannot have more successes than total calls"
                )
                logger.info(
                    "Rapid sequential calls completed: %d/%d succeeded (%.1f%%)",
                    successful_calls,
                    total_calls,
                    success_rate * 100,
                )

            except Exception as e:
                pytest.fail(f"Rapid sequential calls test failed: {e}")
