"""Vulnerability-specific exceptions for the vulnerabilities library."""

from purple_mcp.type_defs import JsonDict


class VulnerabilitiesError(Exception):
    """Base exception for all vulnerabilities-related errors."""

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


class VulnerabilitiesConfigError(VulnerabilitiesError):
    """Configuration-related errors in the vulnerabilities system."""

    pass


class VulnerabilitiesClientError(VulnerabilitiesError):
    """HTTP/network-related errors when communicating with the vulnerabilities API."""

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


class VulnerabilitiesGraphQLError(VulnerabilitiesError):
    """GraphQL-specific errors from the vulnerabilities API."""

    def __init__(self, message: str, graphql_errors: list[JsonDict] | None = None) -> None:
        """Initialize the GraphQL error.

        Args:
            message: The main error message.
            graphql_errors: List of GraphQL error objects from the response.
        """
        self.graphql_errors = graphql_errors or []
        details = None
        if self.graphql_errors:
            error_messages = [
                str(err.get("message", "Unknown error")) for err in self.graphql_errors
            ]
            details = "; ".join(error_messages)
        super().__init__(message, details)


class VulnerabilitiesSchemaError(VulnerabilitiesError):
    """Schema compatibility errors in the vulnerabilities system."""

    def __init__(
        self, message: str, field_name: str | None = None, details: str | None = None
    ) -> None:
        """Initialize the schema error.

        Args:
            message: The main error message.
            field_name: The name of the field that caused the schema error.
            details: Optional additional details about the error.
        """
        self.field_name = field_name
        if field_name and not details:
            details = f"Field '{field_name}' is not supported in the current schema version"
        super().__init__(message, details)
