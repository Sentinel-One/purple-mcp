"""Purple AI-specific exceptions for the purple_ai library."""

from purple_mcp.type_defs import JsonDict


class PurpleAIError(Exception):
    """Base exception for all purple AI-related errors."""

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


class PurpleAIConfigError(PurpleAIError):
    """Configuration-related errors in the purple AI system."""

    pass


class PurpleAIClientError(Exception):
    """Base exception for Purple AI client errors."""

    def __init__(self, message: str, details: str | None = None, status_code: int | None = None):
        """Initialize the exception.

        Args:
            message: The error message.
            details: Additional error details.
            status_code: HTTP status code if applicable.
        """
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with optional details."""
        parts = [self.message]
        if self.status_code:
            parts.append(f"(status {self.status_code})")
        if self.details:
            parts.append(f": {self.details}")
        return " ".join(parts)


class PurpleAIGraphQLError(Exception):
    """Exception for GraphQL errors in Purple AI responses."""

    def __init__(self, message: str, graphql_errors: list[JsonDict] | None = None):
        """Initialize the exception.

        Args:
            message: The error message.
            graphql_errors: List of GraphQL error objects from the response.
        """
        self.message = message
        self.graphql_errors = graphql_errors or []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with GraphQL errors."""
        if not self.graphql_errors:
            return self.message
        error_messages = [str(err.get("message", "Unknown error")) for err in self.graphql_errors]
        return f"{self.message}: {'; '.join(error_messages)}"


class PurpleAISchemaError(PurpleAIError):
    """Schema compatibility errors in the purple AI system."""

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
