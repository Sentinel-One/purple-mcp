"""PowerQuery handler for Singularity Data Lake.

This module implements `SDLPowerQueryHandler`, the concrete subclass of
`SDLHandler` responsible for executing PowerQuery requests (SDL's SQL-like
language).  Beyond the base functionality it adds query-specific
validation, convenience helpers and result post-processing.

Key Components:
    - SDLPowerQueryHandler: Concrete handler implementing the PowerQuery
      workflow.
    - submit_powerquery(): User-facing helper that maps the high-level
      arguments onto the generic `submit()` template.

Usage:
    ```python
    from purple_mcp.libs.sdl.sdl_powerquery_handler import SDLPowerQueryHandler

    handler = SDLPowerQueryHandler(token, "https://sdl.example.com")
    await handler.submit_powerquery(
        start_time=timedelta(hours=1),
        end_time=timedelta(),
        query="filter event.category == 'DNS' | summarize count()",
    )
    results = await handler.poll_until_complete()
    print(results.match_count)
    ```

Architecture:
    The class leverages the template-method hooks of `SDLHandler`:

    1. `submit_powerquery` - prepares `SDLPQAttributes` before delegating to
       the protected `submit()` defined in the base class.
    2. `process_results` - merges incremental table rows and maintains
       column metadata.

    Additional helpers like `is_result_partial` encapsulate domain rules so
    callers can reason about result completeness without duplicating logic.

Dependencies:
    math: Numeric helpers for floating-point comparison.
    purple_mcp.libs.sdl.enums: Enumerations for PowerQuery arguments.
    purple_mcp.libs.sdl.models: Pydantic models for wire-format parsing.
"""

import logging
import math
from datetime import datetime, timedelta

from httpx import Headers
from typing_extensions import override

from purple_mcp.libs.sdl.config import SDLSettings
from purple_mcp.libs.sdl.enums import SDLPQFrequency, SDLPQResultType, SDLQueryPriority
from purple_mcp.libs.sdl.models import SDLPQAttributes, SDLQueryResult, SDLTableResultData
from purple_mcp.libs.sdl.sdl_exceptions import SDLHandlerError
from purple_mcp.libs.sdl.sdl_query_handler import SDLHandler

logger = logging.getLogger(__name__)


class SDLPowerQueryHandler(SDLHandler):
    """A helper class to handle SDL queries."""

    def __init__(
        self,
        auth_token: str,
        base_url: str,
        settings: SDLSettings,
        poll_results_timeout_ms: int | None = None,
        poll_interval_ms: float | None = None,
    ) -> None:
        """Initialize class.

        Args:
            auth_token: The raw authentication token that will be passed directly to the
            Authorization header when making SDL API requests. It should be in the format
            "Bearer <token>".
            base_url: The base URL for the SDL API.
            settings: SDL settings configuration (required).
            poll_results_timeout_ms: Timeout in milliseconds for polling
                query results. If None, uses the default from SDL configuration.
            poll_interval_ms: Poll interval in ms for checking query status.
                If None, uses the default from SDL configuration.
        """
        super().__init__(auth_token, base_url, settings, poll_results_timeout_ms, poll_interval_ms)

        self.settings = settings
        self.results = SDLTableResultData(match_count=0, values=[], columns=[])

    async def submit_powerquery(
        self,
        start_time: datetime | timedelta,
        end_time: datetime | timedelta,
        query: str,
        result_type: SDLPQResultType = SDLPQResultType.TABLE,
        frequency: SDLPQFrequency = SDLPQFrequency.LOW,
        tenant: bool | None = None,
        account_ids: list[str] | None = None,
        query_priority: SDLQueryPriority = SDLQueryPriority.LOW,
        headers: Headers | None = None,
    ) -> None:
        """Launch a SDL powerquery.

        Args:
            start_time: The start time for the query.
            end_time: The end time for the query.
            query: The SDL query to be executed.
            result_type: The result type for the query.
            frequency: The frequency for the query.
            tenant: The tenant for the query.
            account_ids: The account IDs for the query.
            query_priority: The priority for the query.
            headers: The headers for the query.

        Raises:
            SDLHandlerError: If the x_dataset_query_forward_tag is None, indicating that the query submission failed.
        """
        if result_type != SDLPQResultType.TABLE:
            raise SDLHandlerError(
                f"PowerQuery result type: {result_type} not currently supported."
            )
        await self.submit(
            start_time=start_time,
            end_time=end_time,
            tenant=tenant,
            account_ids=account_ids,
            query_priority=query_priority,
            pq=SDLPQAttributes(
                query=query,
                result_type=result_type,
                frequency=frequency,
            ),
            headers=headers,
        )

    @override
    def is_result_partial(self) -> bool:
        """Checks if the results are partial or not."""
        if self.results is None:
            raise SDLHandlerError("Cannot check if results are partial when results are None.")

        if self.is_query_completed() is False:
            raise SDLHandlerError(
                "Cannot check if results are partial when the query is not completed."
            )

        return (
            self.results.partial_results_due_to_time_limit is True
            or self.results.discarded_array_items != 0
            or (
                self.results.omitted_events is not None
                and math.isclose(self.results.omitted_events, 0.0, abs_tol=1e-9) is False
            )
            or self.results.truncated_at_limit is True
        )

    @override
    async def process_results(self, response: SDLQueryResult) -> None:
        """Process the results from the SDL query response.

        This method accumulates results from paginated query responses while enforcing
        the max_query_results limit. If the limit is reached, results are truncated
        and a warning is logged.

        Args:
            response: The response from the SDL query containing the data.

        Raises:
            SDLHandlerError: If the results are None.
        """
        # The columns are the same for all steps.
        if response.data is None:
            return

        if self.results is None:
            raise SDLHandlerError("Cannot process results when results are None.")

        self.results.columns = response.data.columns

        # Must happen before early return to capture authoritative values from this page
        self.results.warnings = response.data.warnings
        self.results.match_count = response.data.match_count

        if response.data.key_columns is not None:
            self.results.key_columns = response.data.key_columns

        if response.data.partial_results_due_to_time_limit is not None:
            self.results.partial_results_due_to_time_limit = (
                response.data.partial_results_due_to_time_limit
            )

        if response.data.discarded_array_items is not None:
            self.results.discarded_array_items = response.data.discarded_array_items

        if response.data.omitted_events is not None:
            self.results.omitted_events = response.data.omitted_events

        current_count = len(self.results.values)
        new_count = len(response.data.values)
        max_results = self.settings.max_query_results

        if current_count >= max_results:
            if not self.results.truncated_at_limit:
                logger.warning(
                    "Query result limit reached, skipping additional results",
                    extra={
                        "current_count": current_count,
                        "limit": max_results,
                        "truncated": True,
                    },
                )
                self.results.truncated_at_limit = True
            return

        if current_count + new_count > max_results:
            remaining = max_results - current_count
            logger.warning(
                "Query result limit reached, truncating results",
                extra={
                    "current_count": current_count,
                    "new_count": new_count,
                    "limit": max_results,
                    "truncating_to": remaining,
                    "truncated": True,
                },
            )
            self.results.values.extend(response.data.values[:remaining])
            self.results.truncated_at_limit = True
        else:
            self.results.values.extend(response.data.values)
