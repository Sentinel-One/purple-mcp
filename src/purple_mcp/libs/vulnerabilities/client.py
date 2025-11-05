"""Vulnerabilities client implementation for interacting with the XSPM Vulnerabilities GraphQL API.

This module provides the VulnerabilitiesClient class for communicating with the
XSPM Vulnerabilities service through GraphQL queries and handling responses using
typed Pydantic models.
"""

import logging
import os

from purple_mcp.libs.graphql_client_base import GraphQLClientBase
from purple_mcp.libs.graphql_utils import build_node_fields
from purple_mcp.libs.vulnerabilities.config import VulnerabilitiesConfig
from purple_mcp.libs.vulnerabilities.exceptions import (
    VulnerabilitiesClientError,
    VulnerabilitiesGraphQLError,
)
from purple_mcp.libs.vulnerabilities.models import (
    FilterInput,
    PageInfo,
    VulnerabilityConnection,
    VulnerabilityDetail,
    VulnerabilityHistoryItemConnection,
    VulnerabilityNoteConnection,
)
from purple_mcp.libs.vulnerabilities.templates import (
    GET_VULNERABILITY_HISTORY_QUERY,
    GET_VULNERABILITY_NOTES_QUERY,
    GET_VULNERABILITY_QUERY,
    LIST_VULNERABILITIES_QUERY_TEMPLATE,
    SEARCH_VULNERABILITIES_QUERY_TEMPLATE,
    VULNERABILITY_FIELD_CATALOG,
)
from purple_mcp.type_defs import JsonDict

logger = logging.getLogger(__name__)


class VulnerabilitiesClient(
    GraphQLClientBase[VulnerabilitiesClientError, VulnerabilitiesGraphQLError]
):
    """Client for interacting with the XSPM Vulnerabilities GraphQL API."""

    def __init__(self, config: VulnerabilitiesConfig) -> None:
        """Initialize the VulnerabilitiesClient.

        Args:
            config: Configuration for the vulnerabilities client.
        """
        super().__init__(
            api_name="vulnerabilities API",
            client_error_class=VulnerabilitiesClientError,
            graphql_error_class=VulnerabilitiesGraphQLError,
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

    async def get_vulnerability(self, vulnerability_id: str) -> VulnerabilityDetail | None:
        """Get a specific vulnerability by ID.

        Args:
            vulnerability_id: The unique identifier of the vulnerability.

        Returns:
            The vulnerability if found, None otherwise.
        """
        logger.info("Fetching vulnerability", extra={"vulnerability_id": vulnerability_id})

        variables: JsonDict = {"id": vulnerability_id}

        data = await self.execute_query(GET_VULNERABILITY_QUERY, variables)

        vuln_data = data.get("vulnerability")
        if vuln_data and isinstance(vuln_data, dict):
            return VulnerabilityDetail.model_validate(vuln_data)

        return None

    async def list_vulnerabilities(
        self,
        first: int = 10,
        after: str | None = None,
        fields: list[str] | None = None,
    ) -> VulnerabilityConnection:
        """List vulnerabilities with pagination.

        Args:
            first: Number of vulnerabilities to retrieve (default: 10).
            after: Pagination cursor from previous response.
            fields: Optional list of field names to return. If None, returns all fields.

        Returns:
            Connection containing vulnerabilities and pagination info.
        """
        logger.info(
            "Listing vulnerabilities",
            extra={
                "first": first,
                "after": after,
                "field_count": len(fields)
                if fields
                else len(VULNERABILITY_FIELD_CATALOG.default_fields),
            },
        )

        variables: JsonDict = {"first": first}
        if after:
            variables["after"] = after

        node_fields = build_node_fields(fields, VULNERABILITY_FIELD_CATALOG)
        template_params = {"node_fields": node_fields}

        query = LIST_VULNERABILITIES_QUERY_TEMPLATE.safe_substitute(**template_params)
        data = await self.execute_query(query, variables)

        vulns_data = data.get("vulnerabilities")
        if vulns_data and isinstance(vulns_data, dict):
            return VulnerabilityConnection.model_validate(vulns_data)

        # Return empty connection if no data
        return VulnerabilityConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )

    async def search_vulnerabilities(
        self,
        filters: list[FilterInput] | None = None,
        first: int = 10,
        after: str | None = None,
        fields: list[str] | None = None,
    ) -> VulnerabilityConnection:
        """Search vulnerabilities with filters and pagination.

        Args:
            filters: List of filter conditions to apply.
            first: Number of vulnerabilities to retrieve (default: 10).
            after: Pagination cursor from previous response.
            fields: Optional list of field names to return. If None, returns all fields.

        Returns:
            Connection containing matching vulnerabilities and pagination info.
        """
        # Only log full filters if unsafe debugging is explicitly enabled
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.info(
                "Searching vulnerabilities",
                extra={
                    "filters": filters,
                    "first": first,
                    "after": after,
                    "field_count": len(fields)
                    if fields
                    else len(VULNERABILITY_FIELD_CATALOG.default_fields),
                },
            )
        else:
            logger.info(
                "Searching vulnerabilities",
                extra={
                    "filter_count": len(filters) if filters else 0,
                    "has_filters": bool(filters),
                    "first": first,
                    "has_after": bool(after),
                    "field_count": len(fields)
                    if fields
                    else len(VULNERABILITY_FIELD_CATALOG.default_fields),
                },
            )

        variables: JsonDict = {"first": first}

        if filters:
            variables["filters"] = [
                f.model_dump(by_alias=True, exclude_none=True) for f in filters
            ]

        if after:
            variables["after"] = after

        node_fields = build_node_fields(fields, VULNERABILITY_FIELD_CATALOG)
        template_params = {"node_fields": node_fields}

        query = SEARCH_VULNERABILITIES_QUERY_TEMPLATE.safe_substitute(**template_params)
        data = await self.execute_query(query, variables)

        vulns_data = data.get("vulnerabilities")
        if vulns_data and isinstance(vulns_data, dict):
            return VulnerabilityConnection.model_validate(vulns_data)

        # Return empty connection if no data
        return VulnerabilityConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )

    async def get_vulnerability_notes(self, vulnerability_id: str) -> VulnerabilityNoteConnection:
        """Get notes for a specific vulnerability.

        Args:
            vulnerability_id: The unique identifier of the vulnerability.

        Returns:
            Connection containing notes and pagination info.
        """
        logger.info(
            "Fetching vulnerability notes",
            extra={"vulnerability_id": vulnerability_id},
        )

        variables: JsonDict = {"vulnerabilityId": vulnerability_id}

        data = await self.execute_query(GET_VULNERABILITY_NOTES_QUERY, variables)

        notes_data = data.get("vulnerabilityNotes")
        if notes_data and isinstance(notes_data, dict):
            return VulnerabilityNoteConnection.model_validate(notes_data)

        # Return empty connection if no data
        return VulnerabilityNoteConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )

    async def get_vulnerability_history(
        self, vulnerability_id: str, first: int = 10, after: str | None = None
    ) -> VulnerabilityHistoryItemConnection:
        """Get history for a specific vulnerability.

        Args:
            vulnerability_id: The unique identifier of the vulnerability.
            first: Number of history items to retrieve (default: 10).
            after: Pagination cursor from previous response.

        Returns:
            Connection containing history items and pagination info.
        """
        logger.info(
            "Fetching vulnerability history",
            extra={
                "vulnerability_id": vulnerability_id,
                "first": first,
                "after": after,
            },
        )

        variables: JsonDict = {
            "vulnerabilityId": vulnerability_id,
            "first": first,
        }

        if after:
            variables["after"] = after

        data = await self.execute_query(GET_VULNERABILITY_HISTORY_QUERY, variables)

        history_data = data.get("vulnerabilityHistory")
        if history_data and isinstance(history_data, dict):
            return VulnerabilityHistoryItemConnection.model_validate(history_data)

        # Return empty connection if no data
        return VulnerabilityHistoryItemConnection(
            edges=[],
            pageInfo=PageInfo(
                hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None
            ),
        )
