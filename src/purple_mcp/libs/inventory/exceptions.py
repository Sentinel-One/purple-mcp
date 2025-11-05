"""Exceptions for inventory operations."""


class InventoryError(Exception):
    """Base exception for all inventory-related errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: The main error message.
            details: Optional additional details about the error.
        """
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        """Return a string representation of the error."""
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class InventoryConfigError(InventoryError):
    """Configuration-related errors in the inventory system."""

    pass


class InventoryClientError(InventoryError):
    """HTTP/network-related errors when communicating with the inventory API."""

    def __init__(
        self, message: str, status_code: int | None = None, details: str | None = None
    ) -> None:
        """Initialize the client error.

        Args:
            message: The main error message.
            status_code: HTTP status code if applicable.
            details: Optional additional details about the error.
        """
        self.status_code = status_code
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return a string representation of the error."""
        base_message = self.message
        if self.status_code:
            base_message = f"{base_message} (HTTP {self.status_code})"
        if self.details:
            base_message = f"{base_message}. Details: {self.details}"
        return base_message


class InventoryNotFoundError(InventoryClientError):
    """Exception raised when an inventory item is not found."""

    pass


class InventoryAuthenticationError(InventoryClientError):
    """Exception raised when authentication fails."""

    pass


class InventoryAPIError(InventoryClientError):
    """Exception raised when API returns an error."""

    pass


class InventoryNetworkError(InventoryClientError):
    """Exception raised when network/connection errors occur."""

    pass


class InventoryTransientError(InventoryClientError):
    """Exception raised for transient server errors that should be retried.

    This exception is raised for HTTP 502, 503, and 504 responses, which typically
    indicate temporary gateway or service availability issues that may succeed on retry.
    """

    pass
