"""Misconfigurations client implementation for interacting with the XSPM Misconfigurations GraphQL API.

This module provides the MisconfigurationsClient class for communicating with the
XSPM Misconfigurations service through GraphQL queries and handling responses using
typed Pydantic models.
"""

import logging
import os
from string import Template

from purple_mcp.libs.graphql_client_base import GraphQLClientBase
from purple_mcp.libs.graphql_utils import build_node_fields
from purple_mcp.libs.misconfigurations.config import MisconfigurationsConfig
from purple_mcp.libs.misconfigurations.exceptions import (
    MisconfigurationsClientError,
    MisconfigurationsGraphQLError,
    MisconfigurationsSchemaError,
)
from purple_mcp.libs.misconfigurations.models import (
    FilterInput,
    MisconfigurationConnection,
    MisconfigurationDetail,
    MisconfigurationHistoryItemConnection,
    MisconfigurationNoteConnection,
    PageInfo,
    ViewType,
)
from purple_mcp.libs.misconfigurations.templates import (
    GET_MISCONFIGURATION_HISTORY_QUERY,
    GET_MISCONFIGURATION_NOTES_QUERY,
    GET_MISCONFIGURATION_QUERY,
    LIST_MISCONFIGURATIONS_QUERY_TEMPLATE,
    MISCONFIGURATION_FIELD_CATALOG,
    SEARCH_MISCONFIGURATIONS_QUERY_TEMPLATE,
)
from purple_mcp.type_defs import JsonDict

logger = logging.getLogger(__name__)


class MisconfigurationsClient(
    GraphQLClientBase[MisconfigurationsClientError, MisconfigurationsGraphQLError]
):
    """Client for interacting with the XSPM Misconfigurations GraphQL API."""

    def __init__(self, config: MisconfigurationsConfig) -> None:
        """Initialize the MisconfigurationsClient.

        Args:
            config: Configuration for the misconfigurations client.
        """
        super().__init__(
            api_name="misconfigurations API",
            client_error_class=MisconfigurationsClientError,
            graphql_error_class=MisconfigurationsGraphQLError,
        )
        self.config = config

    @property
    def graphql_url(self) -> str:
        """Return the current GraphQL endpoint URL from config."""
        return self.config.graphql_url

    @property
    def auth_token(self) -> str:
        """Return the current authentication token from config."""
        return self.config.auth_token

    @property
    def timeout(self) -> float:
        """Return the current request timeout from config."""
        return self.config.timeout

    @staticmethod
    def _check_for_schema_errors(graphql_errors: list[JsonDict]) -> str | None:
        """Check if GraphQL errors contain schema compatibility issues.

        Args:
            graphql_errors: List of GraphQL error objects from the response.

        Returns:
            The field name that caused the schema error if extractable,
            empty string if schema error detected but field name not extractable,
            or None if no schema error found.
        """
        schema_error_indicators = [
            "Cannot query field",
            "Unknown argument",
            "Field does not exist",
            "Unknown directive",
        ]

        for error in graphql_errors:
            if not isinstance(error, dict):
                continue

            error_message = str(error.get("message", ""))
            error_message_lower = error_message.lower()
            for indicator in schema_error_indicators:
                if indicator.lower() in error_message_lower:
                    # Try to extract field name from error message
                    # Common patterns:
                    # - "Cannot query field 'viewType' on type 'Query'" (single quotes)
                    # - 'Cannot query field "viewType" on type "Query"' (double quotes)
                    # Try double quotes first (API standard), then single quotes
                    for quote_char in ('"', "'"):
                        parts = error_message.split(quote_char)
                        if len(parts) >= 2:
                            return parts[1]
                    # Schema error detected but field name not extractable
                    # Return empty string to still trigger fallback logic
                    return ""

        return None

    async def execute_query(self, query: str, variables: JsonDict | None = None) -> JsonDict:
        """Execute a GraphQL query against the misconfigurations API with schema error detection.

        This override adds special handling for schema compatibility errors that are unique
        to the misconfigurations API.

        Args:
            query: The GraphQL query string.
            variables: Variables for the GraphQL query.

        Returns:
            The GraphQL response data.

        Raises:
            MisconfigurationsClientError: If there's an HTTP/network error.
            MisconfigurationsGraphQLError: If there's a GraphQL error in the response.
            MisconfigurationsSchemaError: If there's a schema compatibility error.
        """
        try:
            return await super().execute_query(query, variables)
        except MisconfigurationsGraphQLError as exc:
            # Check if this is a schema compatibility error
            if exc.graphql_errors:
                field_name = self._check_for_schema_errors(exc.graphql_errors)
                if field_name is not None:
                    error_messages = [
                        str(err.get("message", "Unknown error")) for err in exc.graphql_errors
                    ]
                    details = "; ".join(error_messages)
                    raise MisconfigurationsSchemaError(
                        "Schema compatibility error in misconfigurations API response",
                        field_name=field_name,
                        details=details,
                    ) from exc
            # Re-raise if not a schema error
            raise

    async def execute_compatible_query(
        self,
        query_template: Template,
        variables: JsonDict,
        template_params: dict[str, str] | None = None,
    ) -> JsonDict:
        """Execute a query with schema compatibility fallback.

        Args:
            query_template: The GraphQL query template.
            variables: Variables for the GraphQL query.
            template_params: Parameters for template substitution.

        Returns:
            The GraphQL response data.
        """
        template_params = template_params or {}

        # Try with full schema support first
        full_params = {
            "view_type_param": ", $viewType: ViewType" if self.config.supports_view_type else "",
            "view_type_arg": ", viewType: $viewType" if self.config.supports_view_type else "",
            **template_params,
        }

        query = query_template.safe_substitute(**full_params)

        try:
            return await self.execute_query(query, variables)
        except MisconfigurationsSchemaError:
            # Schema compatibility error detected, disable future attempts and retry without optional fields
            if self.config.supports_view_type:
                logger.warning(
                    "Schema compatibility issue detected, disabling viewType support for future queries",
                    exc_info=True,
                )
                self.config.supports_view_type = False
            return await self._execute_fallback_query(query_template, variables, template_params)

    async def _execute_fallback_query(
        self,
        query_template: Template,
        variables: JsonDict,
        template_params: dict[str, str],
    ) -> JsonDict:
        """Execute a query with fallback parameters for older schemas.

        Args:
            query_template: The GraphQL query template.
            variables: Variables for the GraphQL query.
            template_params: Parameters for template substitution.

        Returns:
            The GraphQL response data.
        """
        # Use minimal schema support for fallback
        fallback_params = {
            "view_type_param": "",  # Remove viewType parameter
            "view_type_arg": "",  # Remove viewType argument
            **template_params,
        }

        # Remove viewType from variables if present.
        # This is needed because older API versions don't support viewType and will error if it's included.
        # By removing viewType from both the query template (above) and variables (here), we maintain
        # backward compatibility with older API schemas that don't have this optional field.
        fallback_variables = {k: v for k, v in variables.items() if k != "viewType"}

        query = query_template.safe_substitute(**fallback_params)
        return await self.execute_query(query, fallback_variables)

    async def get_misconfiguration(
        self, misconfiguration_id: str
    ) -> MisconfigurationDetail | None:
        """Get a specific misconfiguration by ID.

        Args:
            misconfiguration_id: The unique identifier of the misconfiguration.

        Returns:
            The misconfiguration if found, None otherwise.
        """
        logger.info(
            "Fetching misconfiguration", extra={"misconfiguration_id": misconfiguration_id}
        )

        variables: JsonDict = {"id": misconfiguration_id}

        data = await self.execute_query(GET_MISCONFIGURATION_QUERY, variables)

        misc_data = data.get("misconfiguration")
        if misc_data and isinstance(misc_data, dict):
            return MisconfigurationDetail.model_validate(misc_data)

        return None

    async def list_misconfigurations(
        self,
        first: int = 10,
        after: str | None = None,
        view_type: ViewType = ViewType.ALL,
        fields: list[str] | None = None,
    ) -> MisconfigurationConnection:
        """List misconfigurations with pagination.

        Args:
            first: Number of misconfigurations to retrieve (default: 10).
            after: Pagination cursor from previous response.
            view_type: View type filter for misconfigurations (default: ALL).
            fields: Optional list of field names to return. If None, returns all fields.

        Returns:
            Connection containing misconfigurations and pagination info.
        """
        logger.info(
            "Listing misconfigurations",
            extra={
                "first": first,
                "after": after,
                "view_type": view_type,
                "field_count": len(fields)
                if fields
                else len(MISCONFIGURATION_FIELD_CATALOG.default_fields),
            },
        )

        variables: JsonDict = {"first": first}
        if after:
            variables["after"] = after
        if self.config.supports_view_type:
            variables["viewType"] = view_type.value

        node_fields = build_node_fields(fields, MISCONFIGURATION_FIELD_CATALOG)
        template_params = {"node_fields": node_fields}

        data = await self.execute_compatible_query(
            LIST_MISCONFIGURATIONS_QUERY_TEMPLATE, variables, template_params
        )

        misconfigs_data = data.get("misconfigurations")
        if misconfigs_data and isinstance(misconfigs_data, dict):
            return MisconfigurationConnection.model_validate(misconfigs_data)

        # Return empty connection if no data
        return MisconfigurationConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )

    async def search_misconfigurations(
        self,
        filters: list[FilterInput] | None = None,
        first: int = 10,
        after: str | None = None,
        view_type: ViewType = ViewType.ALL,
        fields: list[str] | None = None,
    ) -> MisconfigurationConnection:
        """Search misconfigurations with filters and pagination.

        Args:
            filters: List of filter conditions to apply.
            first: Number of misconfigurations to retrieve (default: 10).
            after: Pagination cursor from previous response.
            view_type: View type filter for misconfigurations (default: ALL).
            fields: Optional list of field names to return. If None, returns all fields.

        Returns:
            Connection containing matching misconfigurations and pagination info.
        """
        # Only log full filters if unsafe debugging is explicitly enabled
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.info(
                "Searching misconfigurations",
                extra={
                    "filters": filters,
                    "first": first,
                    "after": after,
                    "view_type": view_type,
                    "field_count": len(fields)
                    if fields
                    else len(MISCONFIGURATION_FIELD_CATALOG.default_fields),
                },
            )
        else:
            logger.info(
                "Searching misconfigurations",
                extra={
                    "filter_count": len(filters) if filters else 0,
                    "has_filters": bool(filters),
                    "first": first,
                    "has_after": bool(after),
                    "view_type": view_type,
                    "field_count": len(fields)
                    if fields
                    else len(MISCONFIGURATION_FIELD_CATALOG.default_fields),
                },
            )

        variables: JsonDict = {"first": first}

        if filters:
            # Convert Pydantic models to dict for JSON serialization
            variables["filters"] = [
                f.model_dump(by_alias=True, exclude_none=True) for f in filters
            ]

        if after:
            variables["after"] = after

        if self.config.supports_view_type:
            variables["viewType"] = view_type.value

        node_fields = build_node_fields(fields, MISCONFIGURATION_FIELD_CATALOG)
        template_params = {"node_fields": node_fields}

        data = await self.execute_compatible_query(
            SEARCH_MISCONFIGURATIONS_QUERY_TEMPLATE, variables, template_params
        )

        misconfigs_data = data.get("misconfigurations")
        if misconfigs_data and isinstance(misconfigs_data, dict):
            return MisconfigurationConnection.model_validate(misconfigs_data)

        # Return empty connection if no data
        return MisconfigurationConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )

    async def get_misconfiguration_notes(
        self, misconfiguration_id: str
    ) -> MisconfigurationNoteConnection:
        """Get notes for a specific misconfiguration.

        Args:
            misconfiguration_id: The unique identifier of the misconfiguration.

        Returns:
            Connection containing notes and pagination info.
        """
        logger.info(
            "Fetching misconfiguration notes",
            extra={"misconfiguration_id": misconfiguration_id},
        )

        variables: JsonDict = {"misconfigurationId": misconfiguration_id}

        data = await self.execute_query(GET_MISCONFIGURATION_NOTES_QUERY, variables)

        notes_data = data.get("misconfigurationNotes")
        if notes_data and isinstance(notes_data, dict):
            return MisconfigurationNoteConnection.model_validate(notes_data)

        # Return empty connection if no data
        return MisconfigurationNoteConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )

    async def get_misconfiguration_history(
        self, misconfiguration_id: str, first: int = 10, after: str | None = None
    ) -> MisconfigurationHistoryItemConnection:
        """Get history for a specific misconfiguration.

        Args:
            misconfiguration_id: The unique identifier of the misconfiguration.
            first: Number of history items to retrieve (default: 10).
            after: Pagination cursor from previous response.

        Returns:
            Connection containing history items and pagination info.
        """
        logger.info(
            "Fetching misconfiguration history",
            extra={
                "misconfiguration_id": misconfiguration_id,
                "first": first,
                "after": after,
            },
        )

        variables: JsonDict = {
            "misconfigurationId": misconfiguration_id,
            "first": first,
        }

        if after:
            variables["after"] = after

        data = await self.execute_query(GET_MISCONFIGURATION_HISTORY_QUERY, variables)

        history_data = data.get("misconfigurationHistory")
        if history_data and isinstance(history_data, dict):
            return MisconfigurationHistoryItemConnection.model_validate(history_data)

        # Return empty connection if no data
        return MisconfigurationHistoryItemConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )
