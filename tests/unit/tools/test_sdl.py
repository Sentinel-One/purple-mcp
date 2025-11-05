"""Tests for SDL tools."""

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from purple_mcp.libs.sdl import SDLHandlerError
from purple_mcp.tools.sdl import _iso_to_nanoseconds, powerquery


class TestPowerQuery:
    """Test powerquery function."""

    @pytest.mark.asyncio
    async def test_powerquery_validates_time_order(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that powerquery validates end_datetime must be after start_datetime."""
        with patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()):
            # Test with end_datetime before start_datetime
            with pytest.raises(ValueError) as exc_info:
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T10:30:00Z",
                    end_datetime="2024-01-15T09:30:00Z",  # Earlier than start
                )

            assert "end_datetime must be later than start_datetime" in str(exc_info.value)
            assert "2024-01-15T10:30:00Z" in str(exc_info.value)
            assert "2024-01-15T09:30:00Z" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_powerquery_validates_equal_times(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that powerquery validates end_datetime must not equal start_datetime."""
        with patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()):
            # Test with equal timestamps
            with pytest.raises(ValueError) as exc_info:
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T10:30:00Z",
                    end_datetime="2024-01-15T10:30:00Z",  # Same as start
                )

            assert "end_datetime must be later than start_datetime" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_powerquery_success_path(self, mock_settings: Callable[..., MagicMock]) -> None:
        """Test successful powerquery execution."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler - use MagicMock for base, AsyncMock only for async methods
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.is_result_partial.return_value = False  # Synchronous method
            mock_handler.submit_powerquery = AsyncMock()  # Async method
            mock_handler.poll_until_complete = AsyncMock()  # Async method

            # Mock successful results with proper column objects
            mock_col1 = MagicMock()
            mock_col1.name = "col1"
            mock_col2 = MagicMock()
            mock_col2.name = "col2"

            mock_results = MagicMock()
            mock_results.match_count = 42
            mock_results.columns = [mock_col1, mock_col2]
            mock_results.values = [["val1", "val2"], ["val3", "val4"]]
            mock_results.warnings = None
            mock_handler.poll_until_complete.return_value = mock_results

            result = await powerquery(
                query="test query",
                start_datetime="2024-01-15T09:30:00Z",
                end_datetime="2024-01-15T10:30:00Z",
            )

            # Verify handler was called with correct parameters
            mock_handler.submit_powerquery.assert_called_once()
            mock_handler.poll_until_complete.assert_called_once()

            # Verify result contains expected data
            assert "Match Count: 42" in result
            assert "Columns: 2" in result
            assert "Rows: 2" in result

    @pytest.mark.asyncio
    async def test_powerquery_logs_on_success_path(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that logger.info and logger.debug are called appropriately."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.logger") as mock_logger,
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler - use MagicMock for base, AsyncMock only for async methods
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.is_result_partial.return_value = False  # Synchronous method
            mock_handler.submit_powerquery = AsyncMock()  # Async method
            mock_handler.poll_until_complete = AsyncMock()  # Async method

            # Mock results
            mock_results = MagicMock()
            mock_results.match_count = 0
            mock_results.columns = []
            mock_results.values = []
            mock_results.warnings = None
            mock_handler.poll_until_complete.return_value = mock_results

            await powerquery(
                query="test query",
                start_datetime="2024-01-15T09:30:00Z",
                end_datetime="2024-01-15T10:30:00Z",
            )

            # Verify logger.info was called with only non-sensitive metadata
            mock_logger.info.assert_any_call(
                "Running PowerQuery",
                extra={
                    "token_configured": True,
                },
            )

            # Verify logger.debug was called with sanitized query metadata (not full details)
            mock_logger.debug.assert_any_call(
                "PowerQuery details",
                extra={
                    "query_length": 10,
                    "has_query": True,
                    "has_start_datetime": True,
                    "has_end_datetime": True,
                },
            )

    @pytest.mark.asyncio
    async def test_powerquery_propagates_sdl_handler_error(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that SDLHandlerError is propagated to caller instead of returning error string."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler to raise SDLHandlerError
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.submit_powerquery = AsyncMock()
            mock_handler.poll_until_complete = AsyncMock(
                side_effect=SDLHandlerError("Query execution failed")
            )

            # Verify that SDLHandlerError is raised, not returned as a string
            with pytest.raises(SDLHandlerError) as exc_info:
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T09:30:00Z",
                    end_datetime="2024-01-15T10:30:00Z",
                )

            assert "Query execution failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_powerquery_propagates_unexpected_exception(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that unexpected exceptions are propagated to caller instead of returning error string."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler to raise unexpected exception
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.submit_powerquery = AsyncMock()
            mock_handler.poll_until_complete = AsyncMock(
                side_effect=RuntimeError("Unexpected network error")
            )

            # Verify that RuntimeError is raised, not returned as a string
            with pytest.raises(RuntimeError) as exc_info:
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T09:30:00Z",
                    end_datetime="2024-01-15T10:30:00Z",
                )

            assert "Unexpected network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_powerquery_logs_sdl_handler_error(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that SDLHandlerError is logged before being propagated."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.logger") as mock_logger,
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler to raise SDLHandlerError
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.submit_powerquery = AsyncMock()
            mock_handler.poll_until_complete = AsyncMock(
                side_effect=SDLHandlerError("Query execution failed")
            )

            # Execute and catch the exception
            with pytest.raises(SDLHandlerError):
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T09:30:00Z",
                    end_datetime="2024-01-15T10:30:00Z",
                )

            # Verify that logger.exception was called
            mock_logger.exception.assert_called_once_with(
                "SDL handler error occurred during PowerQuery execution"
            )

    @pytest.mark.asyncio
    async def test_powerquery_logs_unexpected_exception(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that unexpected exceptions are logged before being propagated."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.logger") as mock_logger,
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler to raise unexpected exception
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.submit_powerquery = AsyncMock()
            mock_handler.poll_until_complete = AsyncMock(
                side_effect=RuntimeError("Unexpected network error")
            )

            # Execute and catch the exception
            with pytest.raises(RuntimeError):
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T09:30:00Z",
                    end_datetime="2024-01-15T10:30:00Z",
                )

            # Verify that logger.exception was called
            mock_logger.exception.assert_called_once_with("Unexpected error executing PowerQuery")

    @pytest.mark.asyncio
    async def test_powerquery_cleanup_on_success(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that client is closed on successful execution."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.is_result_partial.return_value = False
            mock_handler.query_submitted = True
            mock_handler.query_id = "test-query-id"
            mock_handler.is_query_completed.return_value = True
            mock_handler.submit_powerquery = AsyncMock()
            mock_handler.poll_until_complete = AsyncMock()
            mock_handler.delete_query = AsyncMock()

            # Mock the client
            mock_client = MagicMock()
            mock_client.is_closed.return_value = False
            mock_client.close = AsyncMock()
            mock_handler.sdl_query_client = mock_client

            # Mock successful results
            mock_results = MagicMock()
            mock_results.match_count = 10
            mock_results.columns = []
            mock_results.values = [["test"]]
            mock_results.warnings = None
            mock_handler.poll_until_complete.return_value = mock_results

            await powerquery(
                query="test query",
                start_datetime="2024-01-15T09:30:00Z",
                end_datetime="2024-01-15T10:30:00Z",
            )

            # Verify cleanup was called
            # On success path with completed query, delete should not be called in finally
            # (it's already handled by the handler's ping_query)
            mock_handler.delete_query.assert_not_called()
            # But close should always be called
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_powerquery_cleanup_on_error_before_submission(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that client is closed when error occurs before query submission."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler to fail during submission
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.query_submitted = False
            mock_handler.query_id = None
            mock_handler.submit_powerquery = AsyncMock(
                side_effect=SDLHandlerError("Submission failed")
            )
            mock_handler.delete_query = AsyncMock()

            # Mock the client
            mock_client = MagicMock()
            mock_client.is_closed.return_value = False
            mock_client.close = AsyncMock()
            mock_handler.sdl_query_client = mock_client

            # Execute and catch the exception
            with pytest.raises(SDLHandlerError):
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T09:30:00Z",
                    end_datetime="2024-01-15T10:30:00Z",
                )

            # Verify cleanup was attempted
            # Query was never submitted, so delete should not be called
            mock_handler.delete_query.assert_not_called()
            # But close should still be called
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_powerquery_cleanup_on_error_after_submission(
        self, mock_settings: Callable[..., MagicMock]
    ) -> None:
        """Test that client is closed and query deleted when error occurs after submission."""
        with (
            patch("purple_mcp.tools.sdl.get_settings", return_value=mock_settings()),
            patch("purple_mcp.tools.sdl.SDLPowerQueryHandler") as mock_handler_class,
        ):
            # Setup mock handler to fail during polling
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_handler.query_submitted = True
            mock_handler.query_id = "test-query-id"
            mock_handler.is_query_completed.return_value = False
            mock_handler.submit_powerquery = AsyncMock()
            mock_handler.poll_until_complete = AsyncMock(
                side_effect=SDLHandlerError("Polling failed")
            )
            mock_handler.delete_query = AsyncMock()

            # Mock the client
            mock_client = MagicMock()
            mock_client.is_closed.return_value = False
            mock_client.close = AsyncMock()
            mock_handler.sdl_query_client = mock_client

            # Execute and catch the exception
            with pytest.raises(SDLHandlerError):
                await powerquery(
                    query="test query",
                    start_datetime="2024-01-15T09:30:00Z",
                    end_datetime="2024-01-15T10:30:00Z",
                )

            # Verify cleanup was called
            # Query was submitted but not completed, so delete should be called
            mock_handler.delete_query.assert_called_once()
            # Close should also be called
            mock_client.close.assert_called_once()


class TestIsoToNanoseconds:
    """Test _iso_to_nanoseconds function."""

    def test_rejects_naive_timestamp_no_timezone(self) -> None:
        """Test that naive timestamp without timezone raises ValueError."""
        naive_timestamp = "2025-01-15T14:30:25"

        with pytest.raises(ValueError) as exc_info:
            _iso_to_nanoseconds(naive_timestamp)

        error_msg = str(exc_info.value)
        assert "explicit timezone information" in error_msg.lower()
        assert "naive timestamp" in error_msg.lower()
        assert naive_timestamp in error_msg

    def test_rejects_naive_timestamp_with_microseconds(self) -> None:
        """Test that naive timestamp with microseconds but no timezone raises ValueError."""
        naive_timestamp = "2025-01-15T14:30:25.123456"

        with pytest.raises(ValueError) as exc_info:
            _iso_to_nanoseconds(naive_timestamp)

        error_msg = str(exc_info.value)
        assert "explicit timezone information" in error_msg.lower()
        assert naive_timestamp in error_msg

    def test_accepts_utc_timestamp_with_z_suffix(self) -> None:
        """Test that UTC timestamp with 'Z' suffix is accepted."""
        utc_timestamp = "2025-01-15T14:30:25Z"
        result = _iso_to_nanoseconds(utc_timestamp)

        # Verify it returns an integer (nanoseconds)
        assert isinstance(result, int)
        assert result > 0

        # Verify it's approximately correct (Jan 15, 2025 14:30:25 UTC)
        # Expected: 1736951425 seconds * 1_000_000_000
        expected_ns = 1736951425000000000
        # Allow small tolerance for rounding
        assert abs(result - expected_ns) < 1_000_000_000

    def test_accepts_utc_timestamp_with_lowercase_z(self) -> None:
        """Test that UTC timestamp with lowercase 'z' suffix is accepted."""
        utc_timestamp = "2025-01-15T14:30:25z"
        result = _iso_to_nanoseconds(utc_timestamp)

        assert isinstance(result, int)
        assert result > 0

    def test_accepts_timestamp_with_positive_offset(self) -> None:
        """Test that timestamp with positive timezone offset is accepted."""
        offset_timestamp = "2025-01-15T14:30:25+05:00"
        result = _iso_to_nanoseconds(offset_timestamp)

        assert isinstance(result, int)
        assert result > 0

        # UTC equivalent is 14:30:25 - 05:00 = 09:30:25 UTC
        # Expected: 1736933425 seconds * 1_000_000_000
        expected_ns = 1736933425000000000
        assert abs(result - expected_ns) < 1_000_000_000

    def test_accepts_timestamp_with_negative_offset(self) -> None:
        """Test that timestamp with negative timezone offset is accepted."""
        offset_timestamp = "2025-01-15T14:30:25-08:00"
        result = _iso_to_nanoseconds(offset_timestamp)

        assert isinstance(result, int)
        assert result > 0

        # UTC equivalent is 14:30:25 + 08:00 = 22:30:25 UTC
        # Expected: 1736980225 seconds * 1_000_000_000
        expected_ns = 1736980225000000000
        assert abs(result - expected_ns) < 1_000_000_000

    def test_accepts_timestamp_with_microseconds_and_timezone(self) -> None:
        """Test that timestamp with microseconds and timezone is accepted."""
        timestamp = "2025-01-15T14:30:25.123456+02:00"
        result = _iso_to_nanoseconds(timestamp)

        assert isinstance(result, int)
        assert result > 0

        # Verify microseconds are preserved in conversion
        # UTC equivalent is 14:30:25.123456 - 02:00 = 12:30:25.123456 UTC
        expected_ns = 1736944225123456000
        assert abs(result - expected_ns) < 1_000_000_000

    def test_accepts_timestamp_with_shortened_offset(self) -> None:
        """Test that timestamp with shortened offset format is accepted."""
        offset_timestamp = "2025-01-15T14:30:25+05:30"
        result = _iso_to_nanoseconds(offset_timestamp)

        assert isinstance(result, int)
        assert result > 0

    def test_rejects_invalid_datetime_string(self) -> None:
        """Test that completely invalid datetime string raises ValueError."""
        invalid_timestamp = "not-a-valid-datetime"

        with pytest.raises(ValueError) as exc_info:
            _iso_to_nanoseconds(invalid_timestamp)

        error_msg = str(exc_info.value)
        # dateutil parser may say "Unknown string format" which is fine
        assert "unknown" in error_msg.lower() or "invalid" in error_msg.lower()

    def test_rejects_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            _iso_to_nanoseconds("")

    def test_conversion_accuracy_utc(self) -> None:
        """Test that conversion produces accurate nanosecond values for UTC timestamps."""
        # Test a known timestamp: 2024-01-15T10:30:00Z
        # Unix epoch seconds: 1705314600
        # Nanoseconds: 1705314600000000000
        utc_timestamp = "2024-01-15T10:30:00Z"
        result = _iso_to_nanoseconds(utc_timestamp)

        expected_ns = 1705314600000000000
        assert result == expected_ns

    def test_conversion_accuracy_with_offset(self) -> None:
        """Test that conversion produces accurate nanosecond values for offset timestamps."""
        # Test a known timestamp: 2024-01-15T10:30:00+05:00
        # UTC equivalent: 2024-01-15T05:30:00Z
        # Unix epoch seconds: 1705296600
        # Nanoseconds: 1705296600000000000
        offset_timestamp = "2024-01-15T10:30:00+05:00"
        result = _iso_to_nanoseconds(offset_timestamp)

        expected_ns = 1705296600000000000
        assert result == expected_ns
