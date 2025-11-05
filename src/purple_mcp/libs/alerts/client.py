"""Alerts client implementation for interacting with the Unified Alerts Management GraphQL API.

This module provides the AlertsClient class for communicating with the UAM service
through GraphQL queries and handling responses using typed Pydantic models.
"""

import logging
from string import Template
from typing import cast

from pydantic import JsonValue

from purple_mcp.libs.alerts.config import AlertsConfig
from purple_mcp.libs.alerts.exceptions import AlertsClientError, AlertsGraphQLError
from purple_mcp.libs.alerts.models import (
    Alert,
    AlertConnection,
    AlertHistoryConnection,
    FilterInput,
    GetAlertNotesResponse,
    ViewType,
)
from purple_mcp.libs.graphql_client_base import GraphQLClientBase
from purple_mcp.libs.graphql_utils import GraphQLFieldCatalog, build_node_fields
from purple_mcp.type_defs import JsonDict

logger = logging.getLogger(__name__)


ALERT_FIELD_CATALOG = GraphQLFieldCatalog(
    default_fields=[
        "id",
        "externalId",
        "severity",
        "status",
        "name",
        "description",
        "detectedAt",
        "firstSeenAt",
        "lastSeenAt",
        "analystVerdict",
        "classification",
        "confidenceLevel",
        "detectionSource { product vendor }",
        "asset { id name type }",
        "assignee { userId email fullName }",
        "noteExists",
        "result",
        "storylineId",
        "ticketId",
    ],
    additional_allowed_fields=[
        # dataSources is valid for custom field selection but NOT in defaults because:
        # 1. It's only valid when supports_data_sources is true
        # 2. It's injected via template substitution (${data_sources_field}) in list/search queries
        # 3. Including it in defaults would cause a conflict with the template placeholder
        "dataSources",
    ],
    description="Alert field configuration for UAM GraphQL API",
)

# Legacy exports for backward compatibility
DEFAULT_ALERT_FIELDS: list[str] = ALERT_FIELD_CATALOG.default_fields
ALLOWED_ALERT_FIELDS: list[str] = ALERT_FIELD_CATALOG.get_all_allowed_fields()


GET_ALERT_QUERY_TEMPLATE = Template(
    """
query GetAlert($alertId: ID!) {
    alert(id: $alertId) {
        id
        externalId
        severity
        status
        name
        description
        detectedAt
        firstSeenAt
        lastSeenAt
        analystVerdict
        classification
        confidenceLevel
        ${data_sources_field}
        detectionSource {
            product
            vendor
        }
        asset {
            id
            name
            type
        }
        assignee {
            userId
            email
            fullName
        }
        noteExists
        result
        storylineId
        ticketId
    }
}
"""
)

LIST_ALERTS_QUERY_TEMPLATE = Template(
    """
query ListAlerts($first: Int!, $after: String${view_type_param}) {
    alerts(first: $first, after: $after${view_type_arg}) {
        edges {
            node {
${node_fields}
                ${data_sources_field}
            }
            cursor
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        totalCount
    }
}
"""
)

SEARCH_ALERTS_QUERY_TEMPLATE = Template(
    """
query SearchAlerts($filters: [FilterInput!], $first: Int!, $after: String${view_type_param}) {
    alerts(filters: $filters, first: $first, after: $after${view_type_arg}) {
        edges {
            node {
${node_fields}
                ${data_sources_field}
            }
            cursor
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        totalCount
    }
}
"""
)

GET_ALERT_NOTES_QUERY_TEMPLATE = Template(
    """
query GetAlertNotes($alertId: ID!) {
    alertNotes(alertId: $alertId) {
        data {
            id
            text
            createdAt
            author {
                userId
                email
            }
            alertId
        }
    }
}
"""
)


GET_ALERT_HISTORY_QUERY_TEMPLATE = Template(
    """
query GetAlertHistory($alertId: ID!, $first: Int!, $after: String) {
    alertHistory(alertId: $alertId, first: $first, after: $after) {
        edges {
            node {
                createdAt
                eventText
                eventType
                reportUrl
                historyItemCreator {
                    __typename
                    ... on UserHistoryItemCreator {
                        userId
                        userType
                    }
                }
            }
            cursor
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        totalCount
    }
}
"""
)


class AlertsClient(GraphQLClientBase[AlertsClientError, AlertsGraphQLError]):
    """Client for interacting with the Unified Alerts Management GraphQL API."""

    def __init__(self, config: AlertsConfig) -> None:
        """Initialize the AlertsClient.

        Args:
            config: Configuration for the alerts client.
        """
        super().__init__(
            api_name="alerts API",
            client_error_class=AlertsClientError,
            graphql_error_class=AlertsGraphQLError,
        )
        self.config = config
        self._schema_info: dict[str, bool] | None = None

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
            "data_sources_field": "dataSources" if self.config.supports_data_sources else "",
            "view_type_param": ", $viewType: ViewType" if self.config.supports_view_type else "",
            "view_type_arg": ", viewType: $viewType" if self.config.supports_view_type else "",
            **template_params,
        }

        query = query_template.safe_substitute(**full_params)

        try:
            return await self.execute_query(query, variables)
        except AlertsGraphQLError as exc:
            # Check if it's a schema-related error and try fallback
            if self._is_schema_error(exc):
                logger.warning(
                    "Schema compatibility issue detected, trying fallback query",
                    exc_info=True,
                )
                return await self._execute_fallback_query(
                    query_template, variables, template_params
                )
            raise

    def _is_schema_error(self, error: AlertsGraphQLError) -> bool:
        """Check if a GraphQL error is related to schema compatibility.

        Args:
            error: The GraphQL error to check.

        Returns:
            True if the error is likely due to schema compatibility issues.
        """
        error_indicators = [
            "Cannot query field",
            "Unknown argument",
            "Field does not exist",
            "Unknown directive",
        ]

        error_text = str(error).lower()
        return any(indicator.lower() in error_text for indicator in error_indicators)

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
            "data_sources_field": "",  # Remove dataSources field
            "view_type_param": "",  # Remove viewType parameter
            "view_type_arg": "",  # Remove viewType argument
            **template_params,
        }

        # Remove viewType from variables if present
        fallback_variables = {k: v for k, v in variables.items() if k != "viewType"}

        query = query_template.safe_substitute(**fallback_params)
        return await self.execute_query(query, fallback_variables)

    def _build_alert_field_params(self, fields: list[str] | None) -> tuple[str, str]:
        """Build node fields and dataSources template parameter for alert queries.

        This helper handles the special case of dataSources field to avoid GraphQL conflicts:
        - dataSources is always added via template substitution (${data_sources_field})
        - It must never appear in the node_fields block to prevent duplicate field errors

        Args:
            fields: Optional list of field names to return. If None, uses defaults.

        Returns:
            Tuple of (node_fields_string, data_sources_field_value):
            - node_fields_string: Formatted field list for ${node_fields} substitution
            - data_sources_field_value: Either "dataSources" or "" for ${data_sources_field}
        """
        include_data_sources = False

        if fields is None:
            include_data_sources = True
            node_fields = build_node_fields(None, ALERT_FIELD_CATALOG)
        elif "dataSources" in fields:
            fields_without_data_sources = [f for f in fields if f != "dataSources"]
            include_data_sources = True
            node_fields = build_node_fields(fields_without_data_sources, ALERT_FIELD_CATALOG)
        else:
            node_fields = build_node_fields(fields, ALERT_FIELD_CATALOG)

        data_sources_field = ""
        if include_data_sources:
            data_sources_field = "dataSources" if self.config.supports_data_sources else ""

        return node_fields, data_sources_field

    async def get_alert(self, alert_id: str) -> Alert | None:
        """Get a specific alert by ID.

        Args:
            alert_id: The unique identifier of the alert.

        Returns:
            The alert if found, None otherwise.
        """
        logger.info("Fetching alert", extra={"alert_id": alert_id})

        variables: JsonDict = {"alertId": alert_id}

        data = await self.execute_compatible_query(GET_ALERT_QUERY_TEMPLATE, variables)

        alert_data = data.get("alert")
        if not alert_data:
            return None

        return Alert.model_validate(alert_data)

    async def list_alerts(
        self,
        first: int = 10,
        after: str | None = None,
        view_type: ViewType = ViewType.ALL,
        fields: list[str] | None = None,
    ) -> AlertConnection:
        """List alerts with pagination.

        Args:
            first: Number of alerts to fetch.
            after: Cursor for pagination.
            view_type: Filter alerts by view type.
            fields: Optional list of field names to return. If None, returns all default
                   fields including dataSources (if supported). If provided, dataSources
                   is only included if explicitly requested in the list.

        Returns:
            Paginated connection of alerts.
        """
        logger.info(
            "Listing alerts",
            extra={
                "first": first,
                "after": after,
                "view_type": str(view_type),
                "field_count": len(fields) if fields else len(DEFAULT_ALERT_FIELDS),
            },
        )

        variables: JsonDict = {
            "first": first,
            "after": after,
        }

        if self.config.supports_view_type:
            variables["viewType"] = view_type.value

        node_fields, data_sources_field = self._build_alert_field_params(fields)
        template_params = {"node_fields": node_fields, "data_sources_field": data_sources_field}

        data = await self.execute_compatible_query(
            LIST_ALERTS_QUERY_TEMPLATE, variables, template_params
        )

        return AlertConnection.model_validate(data["alerts"])

    async def search_alerts(
        self,
        filters: list[FilterInput] | None = None,
        first: int = 10,
        after: str | None = None,
        view_type: ViewType = ViewType.ALL,
        fields: list[str] | None = None,
    ) -> AlertConnection:
        """Search alerts with filters.

        Args:
            filters: List of filters to apply.
            first: Number of alerts to fetch.
            after: Cursor for pagination.
            view_type: Filter alerts by view type.
            fields: Optional list of field names to return. If None, returns all default
                   fields including dataSources (if supported). If provided, dataSources
                   is only included if explicitly requested in the list.

        Returns:
            Paginated connection of matching alerts.
        """
        logger.info(
            "Searching alerts",
            extra={
                "filter_count": len(filters or []),
                "first": first,
                "view_type": str(view_type),
                "field_count": len(fields) if fields else len(DEFAULT_ALERT_FIELDS),
            },
        )

        # Convert FilterInput objects to dicts for GraphQL
        filter_dicts = None
        if filters:
            filter_dicts = cast(
                list[JsonDict],
                [filter_input.model_dump(by_alias=True) for filter_input in filters],
            )

        variables: JsonDict = {
            "filters": cast(list[JsonValue], filter_dicts) if filter_dicts else None,
            "first": first,
            "after": after,
        }

        if self.config.supports_view_type:
            variables["viewType"] = view_type.value

        node_fields, data_sources_field = self._build_alert_field_params(fields)
        template_params = {"node_fields": node_fields, "data_sources_field": data_sources_field}

        data = await self.execute_compatible_query(
            SEARCH_ALERTS_QUERY_TEMPLATE, variables, template_params
        )

        return AlertConnection.model_validate(data["alerts"])

    async def get_alert_notes(self, alert_id: str) -> GetAlertNotesResponse:
        """Get notes for a specific alert.

        Args:
            alert_id: The unique identifier of the alert.

        Returns:
            Response containing list of alert notes.
        """
        logger.info("Fetching notes for alert", extra={"alert_id": alert_id})

        variables: JsonDict = {
            "alertId": alert_id,
        }

        data = await self.execute_compatible_query(GET_ALERT_NOTES_QUERY_TEMPLATE, variables)

        return GetAlertNotesResponse.model_validate(data["alertNotes"])

    async def get_alert_history(
        self, alert_id: str, first: int = 10, after: str | None = None
    ) -> AlertHistoryConnection:
        """Get history events for a specific alert.

        Args:
            alert_id: The unique identifier of the alert.
            first: Number of history events to fetch.
            after: Cursor for pagination.

        Returns:
            Paginated connection of alert history events.
        """
        logger.info("Fetching history for alert", extra={"alert_id": alert_id})

        variables: JsonDict = {
            "alertId": alert_id,
            "first": first,
            "after": after,
        }

        data = await self.execute_compatible_query(GET_ALERT_HISTORY_QUERY_TEMPLATE, variables)

        return AlertHistoryConnection.model_validate(data["alertHistory"])
