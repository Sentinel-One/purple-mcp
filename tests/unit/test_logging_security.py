"""Tests for logging security filter that redacts sensitive tokens."""

import asyncio
import logging
import threading
from io import StringIO

from purple_mcp.logging_security import REDACTED, SecretFilter, install_filter, register_secret


class TestSecretFilter:
    """Test suite for SecretFilter class."""

    def test_filter_initialization(self) -> None:
        """Test that SecretFilter initializes with empty secrets."""
        secret_filter = SecretFilter()
        assert secret_filter._secrets == set()

    def test_register_secret(self) -> None:
        """Test registering a secret value."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("my-secret-token")
        assert "my-secret-token" in secret_filter._secrets

    def test_register_empty_secret_ignored(self) -> None:
        """Test that empty secrets are ignored."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("")
        assert secret_filter._secrets == set()

    def test_filter_redacts_message(self) -> None:
        """Test that filter redacts secrets from log messages."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("secret123")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Token is secret123",
            args=(),
            exc_info=None,
        )

        secret_filter.filter(record)
        assert record.msg == f"Token is {REDACTED}"

    def test_filter_redacts_multiple_occurrences(self) -> None:
        """Test that filter redacts multiple occurrences of the same secret."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("token")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="First token, second token, third token",
            args=(),
            exc_info=None,
        )

        secret_filter.filter(record)
        assert record.msg == f"First {REDACTED}, second {REDACTED}, third {REDACTED}"

    def test_filter_redacts_multiple_secrets(self) -> None:
        """Test that filter redacts multiple different secrets."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("secret1")
        secret_filter.register_secret("secret2")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Using secret1 and secret2",
            args=(),
            exc_info=None,
        )

        secret_filter.filter(record)
        assert record.msg == f"Using {REDACTED} and {REDACTED}"

    def test_filter_redacts_exception_text(self) -> None:
        """Test that filter redacts secrets from exception tracebacks."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("secret-token")

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.exc_text = "Traceback: ValueError('Invalid token: secret-token')"

        secret_filter.filter(record)
        assert f"Invalid token: {REDACTED}" in record.exc_text

    def test_filter_returns_true(self) -> None:
        """Test that filter always returns True to allow logging."""
        secret_filter = SecretFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = secret_filter.filter(record)
        assert result is True

    def test_filter_handles_none_message(self) -> None:
        """Test that filter handles None message gracefully."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("token")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=None,
            args=(),
            exc_info=None,
        )

        # Should not raise an exception
        secret_filter.filter(record)

    def test_filter_handles_none_exc_text(self) -> None:
        """Test that filter handles None exc_text gracefully."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("token")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Should not raise an exception
        secret_filter.filter(record)


class TestGlobalFilterFunctions:
    """Test suite for global filter installation and registration functions."""

    def setup_method(self) -> None:
        """Reset global filter state before each test."""
        # Reset the global filter instance
        import purple_mcp.logging_security

        purple_mcp.logging_security._filter = None

        # Remove any existing SecretFilter instances from root logger
        root_logger = logging.getLogger()
        root_logger.filters = [f for f in root_logger.filters if not isinstance(f, SecretFilter)]

    def test_install_filter_creates_instance(self) -> None:
        """Test that install_filter creates and returns a filter instance."""
        filter_instance = install_filter()
        assert isinstance(filter_instance, SecretFilter)

    def test_install_filter_adds_to_root_logger(self) -> None:
        """Test that install_filter adds filter to root logger."""
        install_filter()
        root_logger = logging.getLogger()

        # Check that a SecretFilter was added
        secret_filters = [f for f in root_logger.filters if isinstance(f, SecretFilter)]
        assert len(secret_filters) == 1

    def test_install_filter_is_idempotent(self) -> None:
        """Test that calling install_filter multiple times doesn't create duplicates."""
        filter1 = install_filter()
        filter2 = install_filter()

        assert filter1 is filter2

        root_logger = logging.getLogger()
        secret_filters = [f for f in root_logger.filters if isinstance(f, SecretFilter)]
        assert len(secret_filters) == 1

    def test_register_secret_after_install(self) -> None:
        """Test that register_secret works after install_filter."""
        install_filter()
        register_secret("my-token")

        # Verify the secret was registered
        root_logger = logging.getLogger()
        secret_filters = [f for f in root_logger.filters if isinstance(f, SecretFilter)]
        assert "my-token" in secret_filters[0]._secrets

    def test_register_secret_before_install_queued(self) -> None:
        """Test that register_secret before install_filter queues the secret."""
        # Register secret before filter installation
        register_secret("queued-token")

        # Verify it's in the pending queue
        import purple_mcp.logging_security

        assert "queued-token" in purple_mcp.logging_security._pending_secrets

        # Now install the filter
        install_filter()

        # Verify the secret was registered and queue is cleared
        root_logger = logging.getLogger()
        secret_filters = [f for f in root_logger.filters if isinstance(f, SecretFilter)]
        assert "queued-token" in secret_filters[0]._secrets
        assert len(purple_mcp.logging_security._pending_secrets) == 0

    def test_register_secret_after_install_immediate(self) -> None:
        """Test that register_secret after install_filter registers immediately."""
        install_filter()

        # Register secret after filter installation
        register_secret("immediate-token")

        # Verify it was registered immediately (not queued)
        import purple_mcp.logging_security

        assert len(purple_mcp.logging_security._pending_secrets) == 0

        root_logger = logging.getLogger()
        secret_filters = [f for f in root_logger.filters if isinstance(f, SecretFilter)]
        assert "immediate-token" in secret_filters[0]._secrets


class TestIntegration:
    """Integration tests for the logging security filter."""

    def setup_method(self) -> None:
        """Setup test environment with clean logger state."""
        import purple_mcp.logging_security

        purple_mcp.logging_security._filter = None
        purple_mcp.logging_security._pending_secrets.clear()

        # Remove existing filters and handlers
        root_logger = logging.getLogger()
        root_logger.filters = []
        root_logger.handlers = []

        # Create a string stream handler to capture log output
        self.log_stream = StringIO()
        handler = logging.StreamHandler(self.log_stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

    def teardown_method(self) -> None:
        """Clean up logger state after test."""
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.filters = []

    def test_end_to_end_secret_redaction(self) -> None:
        """Test complete flow: install filter, register secret, log message."""
        install_filter()
        register_secret("super-secret-token")

        logger = logging.getLogger("test")
        logger.info("Using token: super-secret-token")

        output = self.log_stream.getvalue()
        assert "super-secret-token" not in output
        assert REDACTED in output
        assert f"Using token: {REDACTED}" in output

    def test_register_before_install_then_log(self) -> None:
        """Test that secrets registered before filter installation are redacted.

        This simulates the real-world scenario where config.py registers secrets
        during module import, before cli.py calls install_filter().
        """
        # Register secret BEFORE installing filter (simulates config.py import)
        register_secret("early-registered-token")

        # Later, install the filter (simulates cli.py _setup_logging)
        install_filter()

        # Log a message containing the secret
        logger = logging.getLogger("test")
        logger.info("Token value: early-registered-token")

        # Verify the secret was redacted even though it was registered before installation
        output = self.log_stream.getvalue()
        assert "early-registered-token" not in output
        assert REDACTED in output
        assert f"Token value: {REDACTED}" in output

    def test_redacts_from_third_party_loggers(self) -> None:
        """Test that filter works for third-party library loggers."""
        install_filter()
        register_secret("api-key-123")

        # Simulate a third-party logger
        third_party_logger = logging.getLogger("httpx.client")
        third_party_logger.info("Sending request with Authorization: Bearer api-key-123")

        output = self.log_stream.getvalue()
        assert "api-key-123" not in output
        assert REDACTED in output

    def test_redacts_from_exception_tracebacks(self) -> None:
        """Test that secrets are redacted from exception tracebacks."""
        install_filter()
        register_secret("secret-value")

        logger = logging.getLogger("test")

        try:
            raise ValueError("Authentication failed with token: secret-value")
        except ValueError:
            logger.exception("Error occurred")

        output = self.log_stream.getvalue()
        assert "secret-value" not in output
        assert REDACTED in output

    def test_redacts_bearer_tokens_in_headers(self) -> None:
        """Test that Bearer tokens in authorization headers are redacted."""
        install_filter()
        register_secret("Bearer abc123xyz")

        logger = logging.getLogger("test")
        logger.debug("Request headers: {'Authorization': 'Bearer abc123xyz'}")

        output = self.log_stream.getvalue()
        assert "abc123xyz" not in output
        assert REDACTED in output

    def test_redacts_tokens_in_urls(self) -> None:
        """Test that tokens in URL parameters are redacted."""
        install_filter()
        register_secret("token123")

        logger = logging.getLogger("test")
        logger.info("Connecting to https://api.example.test?token=token123")

        output = self.log_stream.getvalue()
        assert "token123" not in output
        assert REDACTED in output

    def test_multiple_secrets_registration(self) -> None:
        """Test registering and redacting multiple different secrets."""
        install_filter()
        register_secret("sdl-token-abc")
        register_secret("console-token-xyz")

        logger = logging.getLogger("test")
        logger.info("SDL token: sdl-token-abc, Console token: console-token-xyz")

        output = self.log_stream.getvalue()
        assert "sdl-token-abc" not in output
        assert "console-token-xyz" not in output
        assert output.count(REDACTED) == 2

    def test_no_redaction_without_registration(self) -> None:
        """Test that tokens are not redacted if not registered."""
        install_filter()
        # Don't register any secrets

        logger = logging.getLogger("test")
        logger.info("Token: not-registered-token")

        output = self.log_stream.getvalue()
        assert "not-registered-token" in output

    def test_asyncio_safe_logging(self) -> None:
        """Test that filter works correctly with asyncio logging."""

        async def log_with_secret(secret: str, name: str) -> None:
            """Async function that logs a message with a secret."""
            logger = logging.getLogger(f"async-{name}")
            logger.info("Async task %s using %s", name, secret)

        async def main() -> None:
            """Run multiple async tasks that log secrets."""
            install_filter()
            register_secret("async-secret-123")

            # Run multiple concurrent tasks
            await asyncio.gather(
                log_with_secret("async-secret-123", "task1"),
                log_with_secret("async-secret-123", "task2"),
                log_with_secret("async-secret-123", "task3"),
            )

        asyncio.run(main())

        output = self.log_stream.getvalue()
        # Verify secret was redacted in all async task logs
        assert "async-secret-123" not in output
        assert output.count(REDACTED) == 3

    def test_concurrent_registration_and_logging(self) -> None:
        """Test that registering secrets while logging doesn't cause RuntimeError.

        This regression test verifies the fix for the "Set changed size during iteration"
        bug that occurs when secrets are registered while other threads are actively logging.
        """
        install_filter()
        register_secret("initial-secret")

        errors = []
        log_count = 100
        registration_count = 50

        def logging_worker() -> None:
            """Worker that continuously logs messages."""
            logger = logging.getLogger("concurrent-test")
            try:
                for i in range(log_count):
                    logger.info("Log message %s with initial-secret and new-secret-%s", i, i % 10)
            except Exception as e:
                errors.append(e)

        def registration_worker() -> None:
            """Worker that registers new secrets while logging is happening."""
            try:
                for i in range(registration_count):
                    register_secret(f"new-secret-{i}")
            except Exception as e:
                errors.append(e)

        # Start logging threads
        log_threads = [threading.Thread(target=logging_worker) for _ in range(5)]
        # Start registration thread
        reg_thread = threading.Thread(target=registration_worker)

        # Start all threads
        for t in log_threads:
            t.start()
        reg_thread.start()

        # Wait for completion
        for t in log_threads:
            t.join()
        reg_thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent operations raised errors: {errors}"

        # Verify secrets were registered
        output = self.log_stream.getvalue()
        assert "initial-secret" not in output
        assert REDACTED in output


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self) -> None:
        """Setup for edge case tests."""
        import purple_mcp.logging_security

        purple_mcp.logging_security._filter = None

        root_logger = logging.getLogger()
        root_logger.filters = []
        root_logger.handlers = []

    def test_empty_string_secret(self) -> None:
        """Test that empty string secrets are ignored."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("")
        assert len(secret_filter._secrets) == 0

    def test_whitespace_only_secret(self) -> None:
        """Test handling of whitespace-only secrets."""
        secret_filter = SecretFilter()
        secret_filter.register_secret("   ")

        # Should register it (whitespace is a valid secret)
        assert "   " in secret_filter._secrets

    def test_very_long_secret(self) -> None:
        """Test redaction of very long secrets."""
        secret_filter = SecretFilter()
        long_secret = "x" * 10000
        secret_filter.register_secret(long_secret)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Token: {long_secret}",
            args=(),
            exc_info=None,
        )

        secret_filter.filter(record)
        assert long_secret not in record.msg
        assert REDACTED in record.msg

    def test_special_characters_in_secret(self) -> None:
        """Test redaction of secrets with special characters."""
        secret_filter = SecretFilter()
        special_secret = "token!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        secret_filter.register_secret(special_secret)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Using: {special_secret}",
            args=(),
            exc_info=None,
        )

        secret_filter.filter(record)
        assert special_secret not in record.msg
        assert REDACTED in record.msg

    def test_unicode_secret(self) -> None:
        """Test redaction of secrets with unicode characters."""
        secret_filter = SecretFilter()
        unicode_secret = "토큰-🔑-密钥"
        secret_filter.register_secret(unicode_secret)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Secret: {unicode_secret}",
            args=(),
            exc_info=None,
        )

        secret_filter.filter(record)
        assert unicode_secret not in record.msg
        assert REDACTED in record.msg
