"""Unit tests for SDL result size limit enforcement.

These tests verify that the max_query_results configuration is properly
enforced during result accumulation in SDLPowerQueryHandler.process_results().
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from purple_mcp.libs.sdl import SDLSettings, create_sdl_settings
from purple_mcp.libs.sdl.enums import PQColumnType
from purple_mcp.libs.sdl.models import SDLColumn, SDLQueryResult, SDLTableResultData
from purple_mcp.libs.sdl.sdl_powerquery_handler import SDLPowerQueryHandler


@pytest.fixture
def sdl_settings() -> SDLSettings:
    """Create test SDL settings with a low result limit for testing."""
    return create_sdl_settings(
        base_url="https://test.example.test/sdl",
        auth_token="Bearer test-token",
        max_query_results=100,  # Low limit for easier testing
        default_poll_timeout_ms=2000,
        default_poll_interval_ms=50,
        http_timeout=30,
    )


@pytest.fixture
def handler(sdl_settings: SDLSettings) -> SDLPowerQueryHandler:
    """Create a test handler with mocked client."""
    handler = SDLPowerQueryHandler(
        auth_token="Bearer test-token",
        base_url="https://test.example.test/sdl",
        settings=sdl_settings,
        poll_results_timeout_ms=2000,
        poll_interval_ms=50,
    )
    # Mock the client to prevent actual HTTP calls
    handler.sdl_query_client.close = AsyncMock()  # type: ignore[method-assign]
    handler.sdl_query_client.is_closed = MagicMock(return_value=False)  # type: ignore[method-assign]
    return handler


def create_test_response(row_count: int) -> SDLQueryResult:
    """Create a test query response with the specified number of rows.

    Args:
        row_count: Number of rows to include in the response.

    Returns:
        A mock SDLQueryResult with test data.
    """
    columns = [
        SDLColumn(name="id", type=PQColumnType.STRING),
        SDLColumn(name="value", type=PQColumnType.NUMBER),
    ]
    values = [[f"id_{i}", i] for i in range(row_count)]

    return SDLQueryResult(
        id="test-query-id",
        steps_completed=1,
        total_steps=1,
        data=SDLTableResultData(
            match_count=float(row_count),
            values=values,  # type: ignore[arg-type]
            columns=columns,
        ),
    )


class TestResultSizeLimitEnforcement:
    """Test suite for result size limit enforcement."""

    @pytest.mark.asyncio
    async def test_results_under_limit_not_truncated(self, handler: SDLPowerQueryHandler) -> None:
        """Test that results under the limit are not truncated."""
        # Process 50 rows (under the 100 limit)
        response = create_test_response(50)
        await handler.process_results(response)

        assert len(handler.results.values) == 50  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is False  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_results_at_exact_limit_not_truncated(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that results exactly at the limit are not truncated."""
        # Process exactly 100 rows (at the limit)
        response = create_test_response(100)
        await handler.process_results(response)

        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is False  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_single_batch_exceeding_limit_truncated(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that a single batch exceeding the limit is truncated."""
        # Process 150 rows in one batch (exceeds 100 limit)
        response = create_test_response(150)
        await handler.process_results(response)

        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_multiple_batches_stop_at_limit(self, handler: SDLPowerQueryHandler) -> None:
        """Test that multiple batches stop accumulating at the limit."""
        # First batch: 60 rows
        response1 = create_test_response(60)
        await handler.process_results(response1)
        assert len(handler.results.values) == 60  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is False  # type: ignore[union-attr]

        # Second batch: 30 rows (total would be 90, still under limit)
        response2 = create_test_response(30)
        await handler.process_results(response2)
        assert len(handler.results.values) == 90  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is False  # type: ignore[union-attr]

        # Third batch: 30 rows (total would be 120, exceeds limit)
        response3 = create_test_response(30)
        await handler.process_results(response3)
        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_partial_truncation_preserves_correct_rows(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that partial truncation preserves the first N rows correctly."""
        # First batch: 80 rows
        response1 = create_test_response(80)
        await handler.process_results(response1)

        # Second batch: 50 rows (only 20 should be added)
        response2 = create_test_response(50)
        await handler.process_results(response2)

        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]

        # Verify the last row is the 20th from the second batch
        assert handler.results.values[99] == ["id_19", 19]  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_results_after_limit_reached_ignored(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that results received after limit is reached are ignored."""
        # First batch: exactly 100 rows (at limit)
        response1 = create_test_response(100)
        await handler.process_results(response1)
        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is False  # type: ignore[union-attr]

        # Second batch: 50 more rows (should be ignored)
        response2 = create_test_response(50)
        await handler.process_results(response2)
        assert len(handler.results.values) == 100  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_empty_response_does_not_affect_limit(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that empty responses don't affect limit tracking."""
        # First batch: 50 rows
        response1 = create_test_response(50)
        await handler.process_results(response1)

        # Empty response
        empty_response = SDLQueryResult(
            id="test-query-id",
            steps_completed=2,
            total_steps=3,
            data=None,
        )
        await handler.process_results(empty_response)

        # Third batch: 50 more rows (total exactly 100)
        response3 = create_test_response(50)
        await handler.process_results(response3)

        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is False  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_truncation_flag_affects_is_result_partial(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that truncated_at_limit flag makes is_result_partial() return True."""
        # Process results exceeding limit
        response = create_test_response(150)
        await handler.process_results(response)

        # Mark query as completed (needed to check is_result_partial)
        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.total_steps = 1
        handler.steps_completed = 1
        handler.last_step_seen = 1

        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]
        assert handler.is_result_partial() is True

    @pytest.mark.asyncio
    async def test_warning_logged_on_truncation(
        self, handler: SDLPowerQueryHandler, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a warning is logged when results are truncated."""
        import logging

        caplog.set_level(logging.WARNING)

        # Process results exceeding limit
        response = create_test_response(150)
        await handler.process_results(response)

        # Check that warning was logged
        assert any("Query result limit reached" in record.message for record in caplog.records)
        assert any("truncating results" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_warning_logged_when_additional_results_skipped(
        self, handler: SDLPowerQueryHandler, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a warning is logged when additional results are skipped after limit."""
        import logging

        caplog.set_level(logging.WARNING)

        # First batch: exactly at limit
        response1 = create_test_response(100)
        await handler.process_results(response1)

        # Second batch: should be skipped
        response2 = create_test_response(50)
        await handler.process_results(response2)

        # Check that warning was logged
        assert any(
            "Query result limit reached, skipping additional results" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_custom_limit_respected(self) -> None:
        """Test that a custom max_query_results setting is respected."""
        custom_settings = create_sdl_settings(
            base_url="https://test.example.test/sdl",
            auth_token="Bearer test-token",
            max_query_results=50,  # Custom lower limit
            http_timeout=30,
        )

        handler = SDLPowerQueryHandler(
            auth_token="Bearer test-token",
            base_url="https://test.example.test/sdl",
            settings=custom_settings,
        )
        handler.sdl_query_client.close = AsyncMock()  # type: ignore[method-assign]
        handler.sdl_query_client.is_closed = MagicMock(return_value=False)  # type: ignore[method-assign]

        # Process 80 rows (exceeds custom 50 limit)
        response = create_test_response(80)
        await handler.process_results(response)

        assert len(handler.results.values) == 50  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_columns_preserved_during_truncation(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that column metadata is preserved when results are truncated."""
        response = create_test_response(150)
        await handler.process_results(response)

        assert len(handler.results.columns) == 2  # type: ignore[union-attr]
        assert handler.results.columns[0].name == "id"  # type: ignore[union-attr]
        assert handler.results.columns[1].name == "value"  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_match_count_preserved_during_truncation(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that match_count reflects total matches, not truncated count."""
        response = create_test_response(150)
        await handler.process_results(response)

        # match_count should reflect the server's reported count (150)
        # even though we only kept 100 rows
        assert handler.results.match_count == 150.0  # type: ignore[union-attr]
        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_other_partial_flags_still_detected(self, handler: SDLPowerQueryHandler) -> None:
        """Test that other partial result indicators still work with truncation flag."""
        # Create response with partial_results_due_to_time_limit flag
        response = SDLQueryResult(
            id="test-query-id",
            steps_completed=1,
            total_steps=1,
            data=SDLTableResultData(
                match_count=50.0,
                values=[["id_0", 0]] * 50,
                columns=[
                    SDLColumn(name="id", type=PQColumnType.STRING),
                    SDLColumn(name="value", type=PQColumnType.NUMBER),
                ],
                partial_results_due_to_time_limit=True,
            ),
        )
        await handler.process_results(response)

        # Mark query as completed (needed to check is_result_partial)
        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.total_steps = 1
        handler.steps_completed = 1
        handler.last_step_seen = 1

        assert handler.results.partial_results_due_to_time_limit is True  # type: ignore[union-attr]
        assert handler.is_result_partial() is True

    @pytest.mark.asyncio
    async def test_very_large_initial_batch(self, handler: SDLPowerQueryHandler) -> None:
        """Test handling of a very large initial batch (10x the limit)."""
        # Process 1000 rows in one batch (10x the 100 limit)
        response = create_test_response(1000)
        await handler.process_results(response)

        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]
        # Verify first and last rows
        assert handler.results.values[0] == ["id_0", 0]  # type: ignore[union-attr]
        assert handler.results.values[99] == ["id_99", 99]  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_sequential_small_batches_accumulate_correctly(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that many small batches accumulate correctly up to the limit."""
        # Process 10 batches of 12 rows each (total 120, exceeds 100 limit)
        for i in range(10):
            response = create_test_response(12)
            await handler.process_results(response)

            if i < 8:  # First 8 batches = 96 rows
                assert handler.results.truncated_at_limit is False  # type: ignore[union-attr]
            else:  # 9th batch brings us to 108, should truncate at 100
                assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]
                assert len(handler.results.values) == 100  # type: ignore[union-attr]

        # Final check
        assert len(handler.results.values) == 100  # type: ignore[union-attr]
        assert handler.results.truncated_at_limit is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_metadata_updated_after_limit_reached(
        self, handler: SDLPowerQueryHandler
    ) -> None:
        """Test that metadata is updated even after limit is reached.

        Verifies that match_count, warnings, partial_results_due_to_time_limit,
        and other metadata fields continue to be updated from subsequent pages
        even when the row limit has been reached and no more rows are added.
        """
        # First batch: 100 rows (at limit)
        response1 = create_test_response(100)
        assert response1.data is not None
        response1.data.match_count = 100.0
        response1.data.warnings = []
        response1.data.partial_results_due_to_time_limit = False
        await handler.process_results(response1)

        assert handler.results is not None
        assert len(handler.results.values) == 100
        assert handler.results.match_count == 100.0
        assert handler.results.warnings == []
        assert handler.results.partial_results_due_to_time_limit is False

        # Second batch: 50 more rows (exceeds limit)
        # But metadata should still be updated with authoritative values
        response2 = create_test_response(50)
        assert response2.data is not None
        response2.data.match_count = 150.0  # Total matches from server
        response2.data.warnings = ["query timeout"]
        response2.data.partial_results_due_to_time_limit = True
        response2.data.omitted_events = 10
        await handler.process_results(response2)

        # Rows should NOT increase (we're at limit)
        assert len(handler.results.values) == 100
        assert handler.results.truncated_at_limit is True

        # But metadata SHOULD be updated with latest authoritative values
        assert handler.results.match_count == 150.0
        assert handler.results.warnings == ["query timeout"]
        assert handler.results.partial_results_due_to_time_limit is True
        assert handler.results.omitted_events == 10

        # Third batch: Another 50 rows
        # Metadata should continue updating
        response3 = create_test_response(50)
        assert response3.data is not None
        response3.data.match_count = 200.0  # Even higher total
        response3.data.warnings = ["query timeout", "data limit"]
        response3.data.omitted_events = 25
        await handler.process_results(response3)

        # Rows still capped at limit
        assert len(handler.results.values) == 100

        # Metadata continues to update
        assert handler.results.match_count == 200.0
        assert handler.results.warnings == ["query timeout", "data limit"]
        assert handler.results.omitted_events == 25
