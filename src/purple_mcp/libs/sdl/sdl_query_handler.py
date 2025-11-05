"""SDL query handler base class for data lake query execution.

This module defines `SDLHandler`, the abstract foundation for executing
queries against the Singularity Data Lake (SDL). Concrete subclasses
(e.g. `SDLPowerQueryHandler`) implement query-type-specific logic while
reusing shared functionality including submission, polling, cancellation,
and result aggregation.

Key Components:
    - SDLHandler: Abstract base class encapsulating common lifecycle and
      error-handling logic for **all** SDL queries.
    - SDLQueryClient: Thin HTTP client responsible for the REST / GraphQL
      interactions (imported).
    - Exceptions (`SDLHandlerError`): Domain-specific failure signalling.

Usage:
    Library consumers instantiate a concrete subclass and call
    `submit_*` followed by `poll_until_complete`:

    ```python
    handler = SDLPowerQueryHandler(token, base_url)
    await handler.submit_powerquery(
        query="filter event.type == 'DNS'",
        start_time=start_ns,
        end_time=end_ns,
    )
    results = await handler.poll_until_complete()
    ```

Architecture:
    1. Submission - Validates input, decorates headers, and delegates to
       `SDLQueryClient`.
    2. Polling - Repeatedly calls `ping_query` until progress indicates
       completion, subject to configurable timeout.
    3. Processing - Subclass hooks parse incremental responses to construct
       the final `SDLResultData` model.

    The template method pattern minimizes the public API surface while
    maximizing code reuse and ensuring consistency across query types.

Dependencies:
    asyncio: Cooperative polling without blocking the event-loop.
    httpx: Async HTTP transport used by `SDLQueryClient`.
    purple_mcp.libs.sdl.*: Internal models, config and utilities.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from timeit import default_timer
from typing import cast

from httpx import Headers

from purple_mcp.libs.sdl.config import SDLSettings
from purple_mcp.libs.sdl.enums import SDLQueryPriority
from purple_mcp.libs.sdl.models import (
    SDLPingResponse,
    SDLPQAttributes,
    SDLQueryResult,
    SDLResultData,
    SDLSubmitQueryResponse,
)
from purple_mcp.libs.sdl.sdl_exceptions import SDLHandlerError
from purple_mcp.libs.sdl.sdl_query_client import SDLQueryClient
from purple_mcp.libs.sdl.utils import parse_time_param


class SDLHandler(ABC):
    """Abstract base class for SDL Query handlers.

    Attributes:
        sdl_query_client: Client for interacting with the SDL API.
        x_dataset_query_forward_tag: Tag for forwarding dataset queries, available once the query is submitted.
        auth_token: Authentication token for the SDL API.
        total_steps: Total number of steps in the query execution.
        steps_completed: Number of steps completed in the query execution. Value is 0 until query is submitted.
        last_step_seen: Last step number that was processed. Value is 0 until query is submitted.
        poll_results_timeout_ms: Timeout in milliseconds for polling query results (default: 30000). When polling until complete, this is the max amount of time we will wait poll for results.
        poll_interval_ms: Poll interval in ms for checking query status (default: 100).
        query_submitted: Whether the query has been submitted.
        query_id: Unique identifier for the submitted query, if any.
    """

    def __init__(
        self,
        auth_token: str,
        base_url: str,
        settings: SDLSettings,
        poll_results_timeout_ms: int | None = None,
        poll_interval_ms: float | None = None,
    ) -> None:
        """Initialize the SDLHandler.

        Args:
            auth_token: The authentication token for the SDL API.
            base_url: The base URL for the SDL API.
            settings: SDL settings configuration (required).
            poll_results_timeout_ms: Timeout in milliseconds for polling query results.
                If None, uses the default from SDL configuration.
            poll_interval_ms: Poll interval in ms for checking query status.
                If None, uses the default from SDL configuration.
        """
        config = settings

        self.sdl_query_client = SDLQueryClient(base_url=base_url, settings=config)
        self.auth_token = auth_token
        self.query_submitted: bool = False
        self.query_id: str | None = None
        self.x_dataset_query_forward_tag: str | None = None
        self.total_steps: int = 0
        self.steps_completed: int = 0
        self.last_step_seen: int = 0
        self.results: SDLResultData
        self.poll_results_timeout_ms: int = (
            poll_results_timeout_ms
            if poll_results_timeout_ms is not None
            else config.default_poll_timeout_ms
        )
        self.poll_interval_ms: float = (
            poll_interval_ms if poll_interval_ms is not None else config.default_poll_interval_ms
        )

    def _ensure_client_open(self) -> None:
        """Ensure the SDL query client is not closed.

        Raises:
            SDLHandlerError: If the client is closed.
        """
        if self.sdl_query_client.is_closed():
            raise SDLHandlerError("SDL query client is closed. Cannot perform operations.")

    async def _handle_error_and_close(self, error_msg: str, exc: Exception | None = None) -> None:
        """Handle error by closing client and raising SDLHandlerError.

        Args:
            error_msg: The error message to raise.
            exc: Optional exception to raise from.

        Raises:
            SDLHandlerError: Always raises with the provided error message.
        """
        if not self.sdl_query_client.is_closed():
            await self.sdl_query_client.close()
        if exc is not None:
            raise SDLHandlerError(error_msg) from exc
        else:
            raise SDLHandlerError(error_msg)

    async def submit(
        self,
        start_time: datetime | timedelta,
        end_time: datetime | timedelta,
        tenant: bool | None = None,
        account_ids: list[str] | None = None,
        query_priority: SDLQueryPriority = SDLQueryPriority.LOW,
        pq: SDLPQAttributes | None = None,
        headers: Headers | None = None,
    ) -> None:
        """Launch SDL query.

        Args:
            start_time: The start time for the query.
            end_time: The end time for the query.
            tenant: The tenant for the query.
            account_ids: The account IDs for the query.
            query_priority: The priority for the query.
            pq: The PQ attributes for the query.
            headers: Additional headers for the request.
        """
        self._ensure_client_open()

        if self.query_submitted:
            await self._handle_error_and_close("Query already submitted.")

        try:
            (
                submit_query_response,
                x_dataset_query_forward_tag,
            ) = await self.sdl_query_client.submit(
                auth_token=self.auth_token,
                start_time=parse_time_param(start_time),
                end_time=parse_time_param(end_time),
                tenant=tenant,
                account_ids=account_ids,
                query_priority=query_priority,
                pq=pq,
                headers=headers,
            )
        except Exception as exc:
            await self.sdl_query_client.close()
            raise exc

        if x_dataset_query_forward_tag is None:
            await self._handle_error_and_close(
                "x_dataset_query_forward_tag is None. Submitting the query failed."
            )

        self.x_dataset_query_forward_tag = x_dataset_query_forward_tag
        self.query_id = submit_query_response.id
        self.query_submitted = True

        self.update_query_progress(submit_query_response)
        # Set the last_step_seen to the current step, as we have pulled the latest data
        self.last_step_seen = submit_query_response.steps_completed
        # Collect the results
        await self.process_results(response=submit_query_response)

        if self.is_query_completed():
            await self.delete_query()
            await self.sdl_query_client.close()

    async def ping_query(
        self,
        headers: Headers | None = None,
    ) -> SDLPingResponse:
        """Ping the SDL query to get results.

        NOTE: It's recommended to ping the query ever 1s, and the query time-to-live is 30s.

        Args:
            headers: Additional headers for the request.

        Returns:
            A dictionary containing the query results or None if an error occurs.
        """
        self._ensure_client_open()

        if self.query_submitted is False or self.query_id is None:
            await self._handle_error_and_close(
                "Query has not been submitted yet or submitting the query failed."
            )

        if self.x_dataset_query_forward_tag is None or len(self.x_dataset_query_forward_tag) == 0:
            await self._handle_error_and_close(
                "x_dataset_query_forward_tag is None. Query has not been submitted yet or submitting the query failed."
            )

        if self.is_query_completed() is True:
            await self._handle_error_and_close(
                "Query is already completed. Cannot ping for results."
            )

        try:
            # Mypy can not infer the types correctly here, so we cast them to str. Note the
            # above checks ensure that these are not None.
            response = await self.sdl_query_client.ping_query(
                auth_token=self.auth_token,
                query_id=cast(str, self.query_id),
                x_dataset_query_forward_tag=cast(str, self.x_dataset_query_forward_tag),
                last_step_seen=self.last_step_seen,
                headers=headers,
            )
        except Exception as exc:
            await self.sdl_query_client.close()
            raise SDLHandlerError(str(exc)) from exc

        self.update_query_progress(response)
        # Set the last_step_seen to the current step, as we have pulled the latest data
        self.last_step_seen = response.steps_completed

        # Collect the results
        await self.process_results(response=response)

        if self.is_query_completed():
            await self.delete_query()
            await self.sdl_query_client.close()
        return response

    @abstractmethod
    async def process_results(self, response: SDLQueryResult) -> None:
        """Process the results from the SDL query response.

        Args:
            response: The response from the SDL query containing results and metadata.
        """
        ...

    def is_query_completed(self) -> bool:
        """Check if the query is completed.

        Returns:
            True if the query is completed, False otherwise.
        """
        return self.last_step_seen == self.total_steps

    def get_results(self) -> SDLResultData:
        """Get the results of the SDL query.

        Returns:
            The results of the SDL query as an SDLPowerQueryHandlerResults object.
        """
        if self.query_submitted is False:
            raise SDLHandlerError("Query has not been submitted yet. Cannot get results.")

        if self.is_query_completed() is False:
            raise SDLHandlerError("Query is not completed yet. Cannot get results.")

        return self.results

    @abstractmethod
    def is_result_partial(self) -> bool:
        """Checks if the results are partial or not."""

    async def poll_until_complete(self) -> SDLResultData:
        """Get the results of the SDL query by polling until complete."""
        # Ping the query to get the next set of results
        start_time = default_timer()

        while self.is_query_completed() is False:
            await self.ping_query()

            # Small sleep to prevent tight polling
            await asyncio.sleep(self.poll_interval_ms / 1_000)

            # Convert time difference to milliseconds for comparison
            elapsed_time_ms = (default_timer() - start_time) * 1000
            if elapsed_time_ms > self.poll_results_timeout_ms:
                timeout_seconds = self.poll_results_timeout_ms / 1000
                await self._handle_error_and_close(
                    f"Query timed out after {timeout_seconds:.1f} seconds. "
                    "This usually means the time range was too long or the query was too complex. "
                    "Try reducing the time range (e.g., use 24 hours instead of multiple days) "
                    "or simplifying the query (e.g., add more specific filters)."
                )

        return self.results

    async def delete_query(
        self,
        headers: Headers | None = None,
    ) -> bool:
        """Delete the query from the SDL backend.

        Args:
            headers: Additional headers for the request.
        """
        self._ensure_client_open()

        if self.query_submitted is False or self.query_id is None:
            await self._handle_error_and_close(
                "Query has not been submitted yet or submitting the query failed."
            )

        if self.x_dataset_query_forward_tag is None or len(self.x_dataset_query_forward_tag) == 0:
            await self._handle_error_and_close(
                "x_dataset_query_forward_tag is None. Query has not been submitted yet or submitting the query failed."
            )

        try:
            # Mypy can not infer the types correctly here, so we cast them to str. Note the
            # above checks ensure that these are not None.
            return await self.sdl_query_client.delete_query(
                auth_token=self.auth_token,
                query_id=cast(str, self.query_id),
                x_dataset_query_forward_tag=cast(str, self.x_dataset_query_forward_tag),
                headers=headers,
            )
        except Exception as exc:
            await self.sdl_query_client.close()
            raise exc

    def update_query_progress(self, response: SDLSubmitQueryResponse | SDLPingResponse) -> None:
        """Update query progress based on the response.

        Args:
            response: The response from the SDL query.
        """
        self.total_steps = response.total_steps
        self.steps_completed = response.steps_completed
