"""Unit tests for SDLHandler timeout and polling logic.

These tests verify that the timeout mechanism in poll_until_complete()
correctly handles time unit conversions and triggers timeouts appropriately.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from purple_mcp.libs.sdl import SDLHandler, SDLSettings, create_sdl_settings
from purple_mcp.libs.sdl.models import SDLPingResponse, SDLQueryResult, SDLTableResultData
from purple_mcp.libs.sdl.sdl_exceptions import SDLHandlerError


class FakeClock:
    """Helper class to mock time for testing without actual sleep delays."""

    def __init__(self, start_time: float = 0.0) -> None:
        """Initialize the fake clock.

        Args:
            start_time: The initial time in seconds.
        """
        self.current_time = start_time

    def advance(self, seconds: float) -> None:
        """Advance the fake clock by the specified number of seconds.

        Args:
            seconds: Number of seconds to advance.
        """
        self.current_time += seconds

    def timer(self) -> float:
        """Get the current time.

        Returns:
            The current time in seconds.
        """
        return self.current_time


class ConcreteSDLHandler(SDLHandler):
    """Concrete implementation of SDLHandler for testing."""

    def __init__(
        self,
        auth_token: str,
        base_url: str,
        settings: SDLSettings,
        poll_results_timeout_ms: int | None = None,
        poll_interval_ms: float | None = None,
    ) -> None:
        """Initialize the concrete test handler."""
        super().__init__(auth_token, base_url, settings, poll_results_timeout_ms, poll_interval_ms)
        self.results = SDLTableResultData(match_count=0, values=[], columns=[])
        self.process_results_called = 0

    async def process_results(self, response: SDLQueryResult) -> None:
        """Mock implementation of abstract method."""
        self.process_results_called += 1

    def is_result_partial(self) -> bool:
        """Mock implementation of abstract method."""
        return not self.is_query_completed()


@pytest.fixture
def sdl_settings() -> SDLSettings:
    """Create test SDL settings."""
    return create_sdl_settings(
        base_url="https://test.example.test/sdl",
        auth_token="Bearer test-token",
        default_poll_timeout_ms=2000,  # 2 seconds for faster tests
        default_poll_interval_ms=50,  # 50ms minimum required
        http_timeout=30,
    )


@pytest.fixture
def handler(sdl_settings: SDLSettings) -> ConcreteSDLHandler:
    """Create a test handler with mocked client."""
    handler = ConcreteSDLHandler(
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


class TestSDLHandlerTimeoutUnits:
    """Test suite for timeout unit consistency."""

    @pytest.mark.asyncio
    async def test_timeout_uses_correct_units(self, handler: ConcreteSDLHandler) -> None:
        """Test that timeout comparison uses consistent millisecond units.

        This is a regression test for the bug where default_timer() returns seconds
        but was being compared directly to poll_results_timeout_ms (milliseconds),
        causing a 1000x inflation in the actual timeout.

        Uses mocked time to avoid real sleep delays.
        """
        # Set a short timeout to trigger quickly
        handler.poll_results_timeout_ms = 200  # 200 milliseconds
        handler.poll_interval_ms = 50  # 50 milliseconds (minimum)

        # Mark query as submitted but never completing
        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.x_dataset_query_forward_tag = "test-tag"
        handler.total_steps = 10
        handler.steps_completed = 0
        handler.last_step_seen = 0

        fake_clock = FakeClock(start_time=0.0)

        # Mock ping_query to never complete
        async def mock_ping_that_never_completes() -> SDLPingResponse:
            # Query never completes
            handler.steps_completed = 5
            return SDLPingResponse(
                id="test-query-id",
                total_steps=10,
                steps_completed=5,
                error=None,
            )

        handler.ping_query = AsyncMock(side_effect=mock_ping_that_never_completes)  # type: ignore[method-assign]

        # Mock asyncio.sleep to advance fake clock instead of waiting
        async def mock_sleep(seconds: float) -> None:
            fake_clock.advance(seconds)

        # Patch both asyncio.sleep and default_timer
        with (
            patch("asyncio.sleep", side_effect=mock_sleep),
            patch(
                "purple_mcp.libs.sdl.sdl_query_handler.default_timer",
                side_effect=fake_clock.timer,
            ),
            pytest.raises(SDLHandlerError, match=r"Query timed out after .* seconds"),
        ):
            await handler.poll_until_complete()

        # Verify the fake clock advanced to approximately the timeout value
        # 200ms timeout with 50ms intervals = 4 sleeps of 50ms = 200ms total
        elapsed_ms = fake_clock.current_time * 1000
        assert 200 <= elapsed_ms <= 250, (
            f"Fake clock advanced {elapsed_ms:.2f}ms, expected ~200ms. "
            f"This indicates the timeout logic is working correctly with millisecond units."
        )

    @pytest.mark.asyncio
    async def test_timeout_calculation_uses_milliseconds(
        self, handler: ConcreteSDLHandler
    ) -> None:
        """Verify that elapsed time is properly converted to milliseconds for comparison.

        Uses mocked time to avoid real sleep delays.
        """
        handler.poll_results_timeout_ms = 300
        handler.poll_interval_ms = 50

        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.x_dataset_query_forward_tag = "test-tag"
        handler.total_steps = 100
        handler.steps_completed = 0
        handler.last_step_seen = 0

        call_count = 0
        fake_clock = FakeClock(start_time=0.0)

        async def mock_ping_slow() -> SDLPingResponse:
            nonlocal call_count
            call_count += 1
            # Never complete
            return SDLPingResponse(
                id="test-query-id",
                total_steps=100,
                steps_completed=call_count,
                error=None,
            )

        handler.ping_query = AsyncMock(side_effect=mock_ping_slow)  # type: ignore[method-assign]

        async def mock_sleep(seconds: float) -> None:
            fake_clock.advance(seconds)

        with (
            patch("asyncio.sleep", side_effect=mock_sleep),
            patch(
                "purple_mcp.libs.sdl.sdl_query_handler.default_timer",
                side_effect=fake_clock.timer,
            ),
            pytest.raises(SDLHandlerError, match=r"Query timed out after .* seconds"),
        ):
            await handler.poll_until_complete()

        # With 300ms timeout and 50ms interval, we should get roughly 6 calls
        # (first call at 0ms, then after 50ms, 100ms, 150ms, 200ms, 250ms = 6 calls, timeout at 300ms)
        assert 6 <= call_count <= 7, f"Expected 6-7 calls, got {call_count}"

    @pytest.mark.asyncio
    async def test_poll_completes_within_timeout(self, handler: ConcreteSDLHandler) -> None:
        """Test that polling completes successfully when query finishes before timeout.

        Uses mocked time to avoid real sleep delays.
        """
        handler.poll_results_timeout_ms = 2000  # 2 seconds
        handler.poll_interval_ms = 50

        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.x_dataset_query_forward_tag = "test-tag"
        handler.total_steps = 5
        handler.steps_completed = 0
        handler.last_step_seen = 0

        call_count = 0
        fake_clock = FakeClock(start_time=0.0)

        async def mock_ping_completes() -> SDLPingResponse:
            nonlocal call_count
            call_count += 1

            # Complete after 3 calls
            if call_count >= 3:
                handler.steps_completed = 5
                handler.last_step_seen = 5
                handler.total_steps = 5
            else:
                handler.steps_completed = call_count
                handler.last_step_seen = call_count

            return SDLPingResponse(
                id="test-query-id",
                total_steps=5,
                steps_completed=handler.steps_completed,
                error=None,
            )

        handler.ping_query = AsyncMock(side_effect=mock_ping_completes)  # type: ignore[method-assign]
        handler.delete_query = AsyncMock(return_value=True)  # type: ignore[method-assign]

        async def mock_sleep(seconds: float) -> None:
            fake_clock.advance(seconds)

        with (
            patch("asyncio.sleep", side_effect=mock_sleep),
            patch(
                "purple_mcp.libs.sdl.sdl_query_handler.default_timer",
                side_effect=fake_clock.timer,
            ),
        ):
            result = await handler.poll_until_complete()

        # Should complete quickly without real sleep delays (instant in fake time)
        # With mocked time, elapsed time should be exactly 2 intervals (100ms)
        # Allow small tolerance for floating point arithmetic
        elapsed_ms = fake_clock.current_time * 1000
        assert elapsed_ms <= 151, f"Query took {elapsed_ms:.2f}ms, should complete instantly"
        assert call_count == 3, f"Expected 3 calls to ping_query, got {call_count}"
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_short_timeout_triggers_correctly(
        self, handler: ConcreteSDLHandler
    ) -> None:
        """Test that even very short timeouts (e.g., 50ms) work correctly.

        This test would fail with the bug where seconds are compared to milliseconds,
        as 100ms would be interpreted as 100 seconds.

        Uses mocked time to avoid real sleep delays.
        """
        handler.poll_results_timeout_ms = 100  # 100 milliseconds
        handler.poll_interval_ms = 50  # 50 milliseconds (minimum)

        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.x_dataset_query_forward_tag = "test-tag"
        handler.total_steps = 1000
        handler.steps_completed = 0
        handler.last_step_seen = 0

        fake_clock = FakeClock(start_time=0.0)

        async def mock_ping_never_completes() -> SDLPingResponse:
            return SDLPingResponse(
                id="test-query-id",
                total_steps=1000,
                steps_completed=1,
                error=None,
            )

        handler.ping_query = AsyncMock(side_effect=mock_ping_never_completes)  # type: ignore[method-assign]

        async def mock_sleep(seconds: float) -> None:
            fake_clock.advance(seconds)

        with (
            patch("asyncio.sleep", side_effect=mock_sleep),
            patch(
                "purple_mcp.libs.sdl.sdl_query_handler.default_timer",
                side_effect=fake_clock.timer,
            ),
            pytest.raises(SDLHandlerError, match=r"Query timed out after .* seconds"),
        ):
            await handler.poll_until_complete()

        elapsed_ms = fake_clock.current_time * 1000

        # Should timeout around 100ms
        # Allow small tolerance for floating point arithmetic
        assert 100 <= elapsed_ms <= 151, (
            f"100ms timeout advanced clock by {elapsed_ms:.2f}ms. "
            f"With the bug, this would take ~100 seconds."
        )

    @pytest.mark.asyncio
    async def test_default_timeout_value(self, sdl_settings: SDLSettings) -> None:
        """Test that default timeout from settings is used correctly."""
        # Default is 1000ms from fixture
        handler = ConcreteSDLHandler(
            auth_token="Bearer test-token",
            base_url="https://test.example.test/sdl",
            settings=sdl_settings,
        )

        # Should use default from settings
        assert handler.poll_results_timeout_ms == sdl_settings.default_poll_timeout_ms

    @pytest.mark.asyncio
    async def test_custom_timeout_overrides_default(self, sdl_settings: SDLSettings) -> None:
        """Test that custom timeout overrides settings default."""
        custom_timeout = 5000  # 5 seconds

        handler = ConcreteSDLHandler(
            auth_token="Bearer test-token",
            base_url="https://test.example.test/sdl",
            settings=sdl_settings,
            poll_results_timeout_ms=custom_timeout,
        )

        assert handler.poll_results_timeout_ms == custom_timeout
        assert handler.poll_results_timeout_ms != sdl_settings.default_poll_timeout_ms


class TestSDLHandlerPolling:
    """Test suite for general polling behavior."""

    @pytest.mark.asyncio
    async def test_poll_interval_is_respected(self, handler: ConcreteSDLHandler) -> None:
        """Test that poll interval creates appropriate delays between calls.

        Uses mocked time to avoid real sleep delays.
        """
        handler.poll_interval_ms = 100  # 100ms between polls
        handler.poll_results_timeout_ms = 1000

        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.x_dataset_query_forward_tag = "test-tag"
        handler.total_steps = 3
        handler.steps_completed = 0
        handler.last_step_seen = 0

        call_times = []
        fake_clock = FakeClock(start_time=0.0)

        async def mock_ping_with_timing() -> SDLPingResponse:
            call_times.append(fake_clock.current_time)
            current_step = len(call_times)

            if current_step >= 3:
                handler.steps_completed = 3
                handler.last_step_seen = 3
            else:
                handler.steps_completed = current_step
                handler.last_step_seen = current_step

            return SDLPingResponse(
                id="test-query-id",
                total_steps=3,
                steps_completed=handler.steps_completed,
                error=None,
            )

        handler.ping_query = AsyncMock(side_effect=mock_ping_with_timing)  # type: ignore[method-assign]
        handler.delete_query = AsyncMock(return_value=True)  # type: ignore[method-assign]

        async def mock_sleep(seconds: float) -> None:
            fake_clock.advance(seconds)

        with (
            patch("asyncio.sleep", side_effect=mock_sleep),
            patch(
                "purple_mcp.libs.sdl.sdl_query_handler.default_timer",
                side_effect=fake_clock.timer,
            ),
        ):
            await handler.poll_until_complete()

        # Check intervals between calls
        for i in range(1, len(call_times)):
            interval_ms = (call_times[i] - call_times[i - 1]) * 1000
            # Should be exactly 100ms with mocked time
            assert interval_ms == 100, f"Interval {i} was {interval_ms:.2f}ms, expected 100ms"

    @pytest.mark.asyncio
    async def test_polling_updates_progress(self, handler: ConcreteSDLHandler) -> None:
        """Test that polling correctly updates query progress.

        Uses mocked time to avoid real sleep delays.
        """
        handler.poll_results_timeout_ms = 2000
        handler.poll_interval_ms = 50

        handler.query_submitted = True
        handler.query_id = "test-query-id"
        handler.x_dataset_query_forward_tag = "test-tag"
        handler.total_steps = 5
        handler.steps_completed = 0
        handler.last_step_seen = 0

        call_count = 0
        fake_clock = FakeClock(start_time=0.0)

        async def mock_ping_progress() -> SDLPingResponse:
            nonlocal call_count
            call_count += 1

            handler.steps_completed = call_count
            handler.last_step_seen = call_count

            return SDLPingResponse(
                id="test-query-id",
                total_steps=5,
                steps_completed=call_count,
                error=None,
            )

        handler.ping_query = AsyncMock(side_effect=mock_ping_progress)  # type: ignore[method-assign]
        handler.delete_query = AsyncMock(return_value=True)  # type: ignore[method-assign]

        async def mock_sleep(seconds: float) -> None:
            fake_clock.advance(seconds)

        with (
            patch("asyncio.sleep", side_effect=mock_sleep),
            patch(
                "purple_mcp.libs.sdl.sdl_query_handler.default_timer",
                side_effect=fake_clock.timer,
            ),
        ):
            await handler.poll_until_complete()

        assert handler.steps_completed == 5
        assert handler.last_step_seen == 5
        assert handler.is_query_completed()


class TestSDLHandlerExceptionChaining:
    """Test suite for exception chaining in error handling."""

    @pytest.mark.asyncio
    async def test_handle_error_and_close_preserves_exception_chain(
        self, handler: ConcreteSDLHandler
    ) -> None:
        """Test that _handle_error_and_close preserves the original exception cause.

        This verifies that when an exception is passed to _handle_error_and_close,
        it is properly chained using 'raise ... from exc' pattern, preserving the
        original stack trace and error context.
        """
        # Create an original exception with a specific message
        original_error = ValueError("Original error: database connection failed")

        # Call _handle_error_and_close with the exception
        with pytest.raises(SDLHandlerError) as exc_info:
            await handler._handle_error_and_close("Failed to process query", exc=original_error)

        # Verify the raised exception is SDLHandlerError
        raised_exception = exc_info.value
        assert isinstance(raised_exception, SDLHandlerError)
        assert str(raised_exception) == "Failed to process query"

        # Verify the original exception is preserved in the chain
        assert raised_exception.__cause__ is original_error
        assert raised_exception.__cause__ is not None
        assert isinstance(raised_exception.__cause__, ValueError)
        assert str(raised_exception.__cause__) == "Original error: database connection failed"

    @pytest.mark.asyncio
    async def test_handle_error_and_close_without_exception(
        self, handler: ConcreteSDLHandler
    ) -> None:
        """Test that _handle_error_and_close works correctly without an exception.

        When no exception is provided, the method should raise SDLHandlerError
        without a __cause__ attribute set.
        """
        with pytest.raises(SDLHandlerError) as exc_info:
            await handler._handle_error_and_close("Simple error without cause")

        raised_exception = exc_info.value
        assert isinstance(raised_exception, SDLHandlerError)
        assert str(raised_exception) == "Simple error without cause"

        # Verify no cause is set when exc is None
        assert raised_exception.__cause__ is None

    @pytest.mark.asyncio
    async def test_handle_error_and_close_closes_client(self, handler: ConcreteSDLHandler) -> None:
        """Test that _handle_error_and_close closes the client before raising.

        This ensures that resources are properly cleaned up even when errors occur.
        """
        # Ensure client is not closed initially
        handler.sdl_query_client.is_closed = MagicMock(return_value=False)  # type: ignore[method-assign]
        handler.sdl_query_client.close = AsyncMock()  # type: ignore[method-assign]

        original_error = ConnectionError("Network timeout")

        with pytest.raises(SDLHandlerError):
            await handler._handle_error_and_close("Connection failed", exc=original_error)

        # Verify client.close() was called
        handler.sdl_query_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_and_close_skips_close_if_already_closed(
        self, handler: ConcreteSDLHandler
    ) -> None:
        """Test that _handle_error_and_close doesn't try to close an already-closed client."""
        # Mark client as already closed
        handler.sdl_query_client.is_closed = MagicMock(return_value=True)  # type: ignore[method-assign]
        handler.sdl_query_client.close = AsyncMock()  # type: ignore[method-assign]

        with pytest.raises(SDLHandlerError):
            await handler._handle_error_and_close("Error with closed client")

        # Verify client.close() was NOT called since it was already closed
        handler.sdl_query_client.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_chain_with_nested_exceptions(
        self, handler: ConcreteSDLHandler
    ) -> None:
        """Test that exception chaining works with nested exception chains.

        This verifies that if the original exception already has a cause,
        the entire chain is preserved.
        """
        # Create a nested exception chain
        root_cause = OSError("Disk full")
        intermediate_error = RuntimeError("Failed to write to file")
        intermediate_error.__cause__ = root_cause

        with pytest.raises(SDLHandlerError) as exc_info:
            await handler._handle_error_and_close("Query execution failed", exc=intermediate_error)

        raised_exception = exc_info.value

        # Verify the immediate cause
        assert raised_exception.__cause__ is intermediate_error
        assert isinstance(raised_exception.__cause__, RuntimeError)

        # Verify the root cause is still accessible through the chain
        assert raised_exception.__cause__.__cause__ is root_cause
        assert isinstance(raised_exception.__cause__.__cause__, IOError)
        assert str(raised_exception.__cause__.__cause__) == "Disk full"

    @pytest.mark.asyncio
    async def test_exception_traceback_preservation(self, handler: ConcreteSDLHandler) -> None:
        """Test that the original exception's traceback is preserved.

        This is crucial for debugging production issues, as it allows
        developers to see where the original error occurred.
        """

        def inner_function() -> None:
            """Helper function to create a traceback."""
            raise KeyError("Missing required configuration key")

        def outer_function() -> None:
            """Helper function to add more frames to the traceback."""
            inner_function()

        try:
            outer_function()
        except KeyError as original_exc:
            # Verify the original exception has a traceback
            assert original_exc.__traceback__ is not None

            with pytest.raises(SDLHandlerError) as exc_info:
                await handler._handle_error_and_close("Configuration error", exc=original_exc)

            # Verify the cause has the original traceback
            assert exc_info.value.__cause__ is not None
            assert exc_info.value.__cause__.__traceback__ is not None
            # The traceback should contain frames from inner_function and outer_function
            assert exc_info.value.__cause__.__traceback__ is original_exc.__traceback__

    @pytest.mark.asyncio
    async def test_different_exception_types_are_preserved(
        self, handler: ConcreteSDLHandler
    ) -> None:
        """Test that various exception types are correctly preserved in the chain."""
        test_cases = [
            (ValueError("Invalid query syntax"), ValueError),
            (TypeError("Expected str, got int"), TypeError),
            (RuntimeError("Unexpected runtime error"), RuntimeError),
            (ConnectionError("Connection refused"), ConnectionError),
            (TimeoutError("Operation timed out"), TimeoutError),
        ]

        for original_exc, expected_type in test_cases:
            with pytest.raises(SDLHandlerError) as exc_info:
                await handler._handle_error_and_close("Query failed", exc=original_exc)

            assert exc_info.value.__cause__ is original_exc
            assert isinstance(exc_info.value.__cause__, expected_type)
            assert str(exc_info.value.__cause__) == str(original_exc)
