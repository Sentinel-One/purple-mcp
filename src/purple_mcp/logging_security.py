"""Simple logging filter to redact sensitive tokens from log output.

This module provides a lightweight mechanism to prevent sensitive credentials
(tokens, API keys) from appearing in application logs. It works by installing
a logging filter that performs string replacement on log records.

Usage:
    1. Call install_filter() during application startup
    2. Call register_secret() for each sensitive value to redact
    3. All subsequent logs will have secrets replaced with [REDACTED]

Thread-safety:
    This implementation is safe for multi-threaded applications as it only
    reads from the secrets set during filtering operations.

Example:
    >>> from purple_mcp.logging_security import install_filter, register_secret
    >>> install_filter()
    >>> register_secret("my-secret-token")
    >>> logging.info("Token: my-secret-token")  # Logs: Token: [REDACTED]
"""

import logging
import threading
from types import TracebackType
from typing import Final

REDACTED: Final[str] = "[REDACTED]"

# Store original methods to restore if needed
_original_get_message = logging.LogRecord.getMessage
_original_format_exception = logging.Formatter.formatException


class SecretFilter(logging.Filter):
    """Logging filter that redacts registered secrets from log messages.

    This filter intercepts LogRecord objects before they are formatted and
    replaces any occurrence of registered secrets with [REDACTED].

    The filter processes:
    - The log message itself (record.msg)
    - Exception traceback text (record.exc_text)

    Thread-safety:
        The filter uses a threading.Lock to protect the secrets set from
        concurrent modifications during iteration, ensuring safe operation
        in multi-threaded environments.
    """

    def __init__(self) -> None:
        """Initialize the secret filter with an empty secrets registry."""
        super().__init__()
        self._secrets: set[str] = set()
        self._lock = threading.Lock()

    def register_secret(self, secret: str) -> None:
        """Register a secret value to be redacted from logs.

        Args:
            secret: The secret value to redact. Empty strings are ignored.

        Thread-safety:
            This method is thread-safe and can be called concurrently.
        """
        if secret:
            with self._lock:
                self._secrets.add(secret)

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter a log record to redact registered secrets.

        Args:
            record: The log record to filter.

        Returns:
            Always returns True to allow the record to be logged.
        """
        # Redact from message
        if record.msg:
            record.msg = self._redact(str(record.msg))

        # Redact from args (used in formatted messages like logger.info("Token: %s", token))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._redact(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact(str(arg)) if isinstance(arg, str) else arg for arg in record.args
                )

        # Redact from exception text (tracebacks)
        if record.exc_text:
            record.exc_text = self._redact(record.exc_text)

        return True

    def _redact(self, text: str) -> str:
        """Replace all registered secrets in text with [REDACTED].

        Args:
            text: The text to redact secrets from.

        Returns:
            The text with all secrets replaced with [REDACTED].

        Thread-safety:
            Creates a snapshot of secrets to avoid RuntimeError if secrets
            are registered during iteration.
        """
        # Create a snapshot to avoid "Set changed size during iteration"
        with self._lock:
            secrets_snapshot = list(self._secrets)

        for secret in secrets_snapshot:
            text = text.replace(secret, REDACTED)
        return text


# Global filter instance
_filter: SecretFilter | None = None

# Queue for secrets registered before filter installation
_pending_secrets: list[str] = []


def _redacting_get_message(self: logging.LogRecord) -> str:
    """Replacement getMessage that redacts secrets after formatting.

    This method replaces the standard LogRecord.getMessage() to ensure
    secrets are redacted from the final formatted message.
    """
    # Call original getMessage to get the formatted message
    msg = _original_get_message(self)

    # Redact secrets if filter is installed
    if _filter is not None:
        msg = _filter._redact(msg)

    return msg


def _redacting_format_exception(
    self: logging.Formatter,
    ei: tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None],
) -> str:
    """Replacement formatException that redacts secrets from tracebacks.

    This method replaces the standard Formatter.formatException() to ensure
    secrets are redacted from exception tracebacks.
    """
    # Call original formatException to get the formatted traceback
    result = _original_format_exception(self, ei)

    # Redact secrets if filter is installed
    if _filter is not None:
        result = _filter._redact(result)

    return result


def install_filter() -> SecretFilter:
    """Install the secret filter on the root logger.

    This should be called once during application initialization, before
    any logging occurs. Installing the filter on the root logger ensures
    that all loggers in the application (including third-party libraries)
    will have their logs filtered.

    This also monkey-patches LogRecord.getMessage() to ensure secrets are
    redacted from formatted messages.

    If secrets were registered before the filter was installed, they will
    be registered with the filter now.

    Returns:
        The installed SecretFilter instance.

    Example:
        >>> filter_instance = install_filter()
        >>> filter_instance.register_secret("my-token")
    """
    global _filter, _pending_secrets
    if _filter is None:
        _filter = SecretFilter()
        logging.getLogger().addFilter(_filter)

        # Monkey-patch getMessage to redact secrets after formatting
        logging.LogRecord.getMessage = _redacting_get_message

        # Monkey-patch formatException to redact secrets from tracebacks
        logging.Formatter.formatException = _redacting_format_exception

        # Register any secrets that were queued before filter installation
        for secret in _pending_secrets:
            _filter.register_secret(secret)
        _pending_secrets.clear()

    return _filter


def register_secret(secret: str) -> None:
    """Register a secret value to be redacted from all logs.

    This function can be called before or after install_filter(). If called
    before the filter is installed, the secret will be queued and registered
    when install_filter() is eventually called.

    Any log messages containing the registered secret will have it replaced
    with [REDACTED].

    Args:
        secret: The secret value to redact (tokens, passwords, API keys, etc.).

    Example:
        >>> # Can be called before filter installation
        >>> register_secret("my-api-key")
        >>> install_filter()
        >>> logging.info(f"Using key: my-api-key")  # Logs: Using key: [REDACTED]
    """
    if _filter is not None:
        # Filter is installed, register immediately
        _filter.register_secret(secret)
    else:
        # Filter not yet installed, queue for later
        _pending_secrets.append(secret)
