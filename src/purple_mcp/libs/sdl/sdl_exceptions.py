"""A module for defining exceptions related to SDL client and handler operations."""


class SDLError(Exception):
    """Base exception for all SDL-related exceptions."""

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


class SDLConfigError(SDLError):
    """Configuration-related errors in the SDL system."""

    pass


class SDLHandlerError(SDLError):
    """Base exception for all SDL handler-related errors."""

    pass


class SDLClientError(SDLError):
    """Base exception for all SDL client-related errors."""

    pass


class SDLMalformedResponseError(SDLClientError):
    """Exception raised when the SDL response is malformed."""

    pass
