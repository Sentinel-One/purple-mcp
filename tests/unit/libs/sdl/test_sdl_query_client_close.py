"""Unit tests for SDLQueryClient close() method error handling.

These tests verify that the close() method properly handles exceptions during
cleanup and logs them appropriately, while re-raising in test environments.
"""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest

from purple_mcp.libs.sdl import SDLQueryClient, create_sdl_settings
from purple_mcp.libs.sdl.config import SDLSettings


@pytest.fixture
def base_url() -> str:
    """Base URL for SDL API."""
    return "https://test.example.test/sdl"


@pytest.fixture
def production_settings(base_url: str) -> SDLSettings:
    """Create settings for a production environment."""
    return create_sdl_settings(
        base_url=base_url,
        auth_token="Bearer test-token",
        http_timeout=10,
        max_timeout_seconds=60,
        http_max_retries=3,
        environment="production",
    )


@pytest.fixture
def test_settings(base_url: str) -> SDLSettings:
    """Create settings for a test environment."""
    return create_sdl_settings(
        base_url=base_url,
        auth_token="Bearer test-token",
        http_timeout=10,
        max_timeout_seconds=60,
        http_max_retries=3,
        environment="test",
    )


@pytest.fixture
async def production_client(
    base_url: str, production_settings: SDLSettings
) -> AsyncGenerator[SDLQueryClient, None]:
    """Yield an SDLQueryClient configured for production."""
    client = SDLQueryClient(base_url, production_settings)
    try:
        yield client
    finally:
        # Don't try to close if it's already closed or if close() is broken
        try:
            if not client.is_closed():
                await client.close()
        except Exception:
            pass  # Ignore errors in fixture cleanup


@pytest.fixture
async def test_client(
    base_url: str, test_settings: SDLSettings
) -> AsyncGenerator[SDLQueryClient, None]:
    """Yield an SDLQueryClient configured for test environment."""
    client = SDLQueryClient(base_url, test_settings)
    try:
        yield client
    finally:
        # Don't try to close if it's already closed or if close() is broken
        try:
            if not client.is_closed():
                await client.close()
        except Exception:
            pass  # Ignore errors in fixture cleanup


class TestCloseMethodErrorHandling:
    """Test suite for close() method exception handling."""

    async def test_close_logs_exception_on_cleanup_failure(
        self, production_client: SDLQueryClient
    ) -> None:
        """Test that exceptions during close() are logged with exc_info."""
        # Mock the http_client.aclose() to raise an exception
        error_msg = "Connection reset by peer"
        production_client.http_client.aclose = AsyncMock(side_effect=RuntimeError(error_msg))  # type: ignore[method-assign]

        # Mock the logger to capture log calls
        with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
            # close() should not raise in production environment
            await production_client.close()

            # Verify warning was logged with exception info
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Error during HTTP client cleanup" in call_args[0][0]
            assert "exc_info" in call_args[1]
            assert isinstance(call_args[1]["exc_info"], RuntimeError)
            assert error_msg in str(call_args[1]["exc_info"])

    async def test_close_reraises_exception_in_test_environment(
        self, test_client: SDLQueryClient
    ) -> None:
        """Test that exceptions during close() are re-raised in test environments."""
        # Mock the http_client.aclose() to raise an exception
        error_msg = "Test cleanup failure"
        test_client.http_client.aclose = AsyncMock(side_effect=RuntimeError(error_msg))  # type: ignore[method-assign]

        # In test environment, close() should re-raise the exception
        with pytest.raises(RuntimeError, match=error_msg):
            await test_client.close()

    async def test_close_reraises_exception_in_testing_environment(self, base_url: str) -> None:
        """Test that exceptions during close() are re-raised in 'testing' environment."""
        # Create a client with 'testing' environment
        settings = create_sdl_settings(
            base_url=base_url,
            auth_token="Bearer test-token",
            environment="testing",
        )
        client = SDLQueryClient(base_url, settings)

        # Mock the http_client.aclose() to raise an exception
        error_msg = "Testing cleanup failure"
        client.http_client.aclose = AsyncMock(side_effect=RuntimeError(error_msg))  # type: ignore[method-assign]

        # In testing environment, close() should re-raise the exception
        with pytest.raises(RuntimeError, match=error_msg):
            await client.close()

    @pytest.mark.parametrize(
        "environment",
        ["Test", "TEST", "Testing", "TESTING", "Development", "DEVELOPMENT", "Dev", "DEV"],
    )
    async def test_close_reraises_exception_in_dev_environments_case_insensitive(
        self, base_url: str, environment: str
    ) -> None:
        """Test that exceptions during close() are re-raised in dev environments regardless of case.

        This ensures that environment variables like PURPLEMCP_ENV=Test or
        PURPLEMCP_ENV=TEST are handled correctly, not just lowercase values.
        """
        # Create a client with the specified environment (mixed case)
        settings = create_sdl_settings(
            base_url=base_url,
            auth_token="Bearer test-token",
            environment=environment,
        )
        client = SDLQueryClient(base_url, settings)

        # Mock the http_client.aclose() to raise an exception
        error_msg = f"{environment} cleanup failure"
        client.http_client.aclose = AsyncMock(side_effect=RuntimeError(error_msg))  # type: ignore[method-assign]

        # In development/test environments (any case), close() should re-raise the exception
        with pytest.raises(RuntimeError, match=error_msg):
            await client.close()

    async def test_close_succeeds_normally_when_no_error(
        self, production_client: SDLQueryClient
    ) -> None:
        """Test that close() works normally when no error occurs."""
        # Mock the logger to verify it's not called
        with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
            # close() should succeed without logging
            await production_client.close()

            # Verify no warning was logged
            mock_logger.warning.assert_not_called()

        # Verify the client is closed
        assert production_client.is_closed()

    async def test_close_handles_various_exception_types(
        self, production_client: SDLQueryClient
    ) -> None:
        """Test that close() handles different exception types appropriately."""
        exception_types = [
            RuntimeError("Runtime error"),
            ConnectionError("Connection error"),
            TimeoutError("Timeout error"),
            OSError("OS error"),
            Exception("Generic exception"),
        ]

        for exc in exception_types:
            # Mock the http_client.aclose() to raise the exception
            production_client.http_client.aclose = AsyncMock(side_effect=exc)  # type: ignore[method-assign]

            # Reset mock state for clean test - note: AsyncClient doesn't have _is_closed
            # The is_closed property is managed internally by httpx

            with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
                # close() should not raise in production environment
                await production_client.close()

                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args
                assert "exc_info" in call_args[1]
                assert call_args[1]["exc_info"] == exc

    async def test_close_in_finally_block_doesnt_mask_original_error(
        self, production_client: SDLQueryClient
    ) -> None:
        """Test that close() in finally block doesn't mask the original exception."""
        # Mock the http_client.aclose() to raise an exception
        production_client.http_client.aclose = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("Cleanup error")
        )

        # Simulate using close() in a finally block after an exception
        original_error_msg = "Original operation failed"

        with (
            patch("purple_mcp.libs.sdl.sdl_query_client.logger"),
            pytest.raises(ValueError, match=original_error_msg),
        ):
            try:
                # Simulate an error in the main operation
                raise ValueError(original_error_msg)
            finally:
                # close() should not raise in production, allowing the original error to propagate
                await production_client.close()


class TestCloseMethodIntegration:
    """Integration tests for close() method with context manager."""

    async def test_context_manager_calls_close_on_exit(self, base_url: str) -> None:
        """Test that context manager properly calls close() on exit."""
        settings = create_sdl_settings(
            base_url=base_url,
            auth_token="Bearer test-token",
        )

        async with SDLQueryClient(base_url, settings) as client:
            assert not client.is_closed()

        # After exiting context manager, client should be closed
        assert client.is_closed()

    async def test_context_manager_handles_close_errors_in_production(
        self, base_url: str, production_settings: SDLSettings
    ) -> None:
        """Test that context manager handles close() errors in production without raising."""
        client = SDLQueryClient(base_url, production_settings)

        # Mock close() to raise an exception
        client.http_client.aclose = AsyncMock(side_effect=RuntimeError("Cleanup failed"))  # type: ignore[method-assign]

        with patch("purple_mcp.libs.sdl.sdl_query_client.logger"):
            # Context manager should not raise on exit in production
            async with client:
                pass

    async def test_manual_close_is_idempotent(self, production_client: SDLQueryClient) -> None:
        """Test that calling close() multiple times is safe."""
        # First close
        await production_client.close()
        assert production_client.is_closed()

        # Second close should not raise (httpx.AsyncClient.aclose() is idempotent)
        await production_client.close()
        assert production_client.is_closed()


class TestCloseMethodLogging:
    """Test suite for verifying proper logging behavior."""

    async def test_log_message_includes_exception_info(
        self, production_client: SDLQueryClient
    ) -> None:
        """Test that the log message includes the exception with traceback."""
        error_msg = "Detailed cleanup failure"
        production_client.http_client.aclose = AsyncMock(side_effect=RuntimeError(error_msg))  # type: ignore[method-assign]

        with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
            await production_client.close()

            # Verify the exact log call structure
            mock_logger.warning.assert_called_once_with(
                "Error during HTTP client cleanup",
                exc_info=production_client.http_client.aclose.side_effect,
            )

    async def test_no_logging_on_successful_close(self, production_client: SDLQueryClient) -> None:
        """Test that successful close() does not produce any log output."""
        with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
            await production_client.close()

            # No logging calls should be made
            mock_logger.debug.assert_not_called()
            mock_logger.info.assert_not_called()
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()


class TestCancelledErrorHandling:
    """Test suite for verifying proper CancelledError handling."""

    async def test_cancelled_error_is_always_reraised_in_production(
        self, production_client: SDLQueryClient
    ) -> None:
        """Test that CancelledError is re-raised in production environments.

        This ensures cooperative cancellation semantics are maintained and
        callers are not left hanging when tasks are cancelled during shutdown.
        """
        # Save original aclose to restore later for fixture cleanup
        original_aclose = production_client.http_client.aclose
        try:
            production_client.http_client.aclose = AsyncMock(side_effect=asyncio.CancelledError())  # type: ignore[method-assign]

            with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
                with pytest.raises(asyncio.CancelledError):
                    await production_client.close()

                # CancelledError should not be logged
                mock_logger.warning.assert_not_called()
        finally:
            # Restore original aclose for fixture cleanup
            production_client.http_client.aclose = original_aclose  # type: ignore[method-assign]

    async def test_cancelled_error_is_always_reraised_in_test_env(
        self, test_client: SDLQueryClient
    ) -> None:
        """Test that CancelledError is re-raised in test environments."""
        # Save original aclose to restore later for fixture cleanup
        original_aclose = test_client.http_client.aclose
        try:
            test_client.http_client.aclose = AsyncMock(side_effect=asyncio.CancelledError())  # type: ignore[method-assign]

            with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
                with pytest.raises(asyncio.CancelledError):
                    await test_client.close()

                # CancelledError should not be logged
                mock_logger.warning.assert_not_called()
        finally:
            # Restore original aclose for fixture cleanup
            test_client.http_client.aclose = original_aclose  # type: ignore[method-assign]

    async def test_cancelled_error_in_context_manager(
        self, base_url: str, production_settings: SDLSettings
    ) -> None:
        """Test that CancelledError propagates through context manager exit."""
        client = SDLQueryClient(base_url, production_settings)
        client.http_client.aclose = AsyncMock(side_effect=asyncio.CancelledError())  # type: ignore[method-assign]

        with patch("purple_mcp.libs.sdl.sdl_query_client.logger") as mock_logger:
            with pytest.raises(asyncio.CancelledError):
                async with client:
                    pass

            # CancelledError should not be logged
            mock_logger.warning.assert_not_called()
