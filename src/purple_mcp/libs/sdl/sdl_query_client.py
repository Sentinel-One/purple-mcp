"""SDL Query API Client."""

import asyncio
import logging
from http import HTTPStatus
from types import TracebackType
from typing import Final, Literal, cast

import httpx
import tenacity
from httpx import Headers
from httpx._types import QueryParamTypes
from pydantic import JsonValue, ValidationError
from typing_extensions import Self

from purple_mcp.libs.sdl.config import SDLSettings
from purple_mcp.libs.sdl.enums import SDLQueryPriority, SDLQueryType
from purple_mcp.libs.sdl.models import SDLPingResponse, SDLPQAttributes, SDLSubmitQueryResponse
from purple_mcp.libs.sdl.sdl_exceptions import SDLMalformedResponseError
from purple_mcp.libs.sdl.security import (
    is_development_environment,
    log_tls_bypass_initialization,
    log_tls_bypass_request,
    validate_tls_bypass_client,
)
from purple_mcp.libs.sdl.type_definitions import JsonDict
from purple_mcp.user_agent import get_user_agent

logger = logging.getLogger(__name__)

# Used for routing follow-up requests to the correct backend instance.
X_DATASET_QUERY_FORWARD_TAG_HEADER: Final = "X-Dataset-Query-Forward-Tag"

AUTHORIZATION_HEADER: Final = "Authorization"


class SDLQueryClient:
    """Client for the SDL Query API.

    This client is designed to be used with a context manager (async with statement)
    to ensure proper cleanup of HTTP client resources. If not using a context manager,
    you **must** manually call the close() method to close the HTTP connection.

    State Management:
    The API uses a routing tag ("X-Dataset-Query-Forward-Tag") returned in the launch query
    response header that must be included in the request header of all subsequent ping and
    delete requests. This tag ensures the server can route follow-up requests to the correct
    backend instance maintaining your query's execution state.

    Workflow:
        1. Submit a query (submit_powerquery) → receive response and forward tag
        2. Check query status (ping_query) and gather results → include forward tag
        3. Delete query when done (delete_query) → include forward tag

    Example:
        # Recommended: using context manager
        async with SDLQueryClient(base_url) as client:
            response = await client.submit(...)

        # Alternative: manual cleanup
        client = SDLQueryClient(base_url)
        try:
            response = await client.submit(...)
        finally:
            await client.close()
    """

    def __init__(self, base_url: str, settings: SDLSettings) -> None:
        """Initialize the client.

        Args:
            base_url: The base URL for the SDL API
            settings: SDL settings configuration (required).
        """
        config = settings

        self.base_url = base_url
        self.http_timeout = config.http_timeout
        self.max_timeout_seconds = config.max_timeout_seconds
        self.http_max_retries = config.http_max_retries
        self.skip_tls_verify = config.skip_tls_verify
        self.environment = config.environment

        # Runtime security validation for TLS bypass
        self._validate_tls_security()

        self.retry_policy = tenacity.AsyncRetrying(
            retry=tenacity.retry_if_exception_type(httpx.HTTPError),
            stop=tenacity.stop_after_attempt(self.http_max_retries + 1),
            wait=tenacity.wait_exponential_jitter(initial=0.1, max=5.0, exp_base=2.0, jitter=1.0),
            reraise=True,
        )

        if self.skip_tls_verify:
            # Log each instance of TLS bypass during client initialization
            log_tls_bypass_initialization(self.base_url, self.environment)

        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=self.http_timeout,
                read=self.max_timeout_seconds,
                write=self.max_timeout_seconds,
                pool=self.http_timeout,
            ),
            verify=not self.skip_tls_verify,
            headers={"User-Agent": get_user_agent()},
        )

    def _validate_tls_security(self) -> None:
        """Validate TLS configuration with runtime security checks."""
        validate_tls_bypass_client(self.skip_tls_verify, self.base_url, self.environment)

    async def _make_request(
        self,
        method: Literal["GET", "POST", "DELETE"],
        path: str,
        auth_token: str,
        headers: Headers | None = None,
        params: QueryParamTypes | None = None,
        json_data: dict[str, JsonValue] | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with retry policy and timing.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: URL path
            auth_token: Authorization token
            headers: Additional headers
            params: Query parameters
            json_data: JSON payload

        Returns:
            httpx.Response object if successful, raises an error otherwise.

        Raises:
            httpx.HTTPError: If the request fails after retries.
        """
        final_headers = Headers()
        if headers is not None:
            final_headers.update(headers)
        final_headers.update({AUTHORIZATION_HEADER: auth_token})

        # Log TLS bypass for each request if enabled
        if self.skip_tls_verify:
            log_tls_bypass_request(str(method), path)

        async for attempt in self.retry_policy:
            with attempt:
                res = await self.http_client.request(
                    method=method,
                    url=path,
                    headers=final_headers,
                    params=params,
                    json=json_data,
                )
                res.raise_for_status()

        return res

    async def submit(
        self,
        auth_token: str,
        start_time: str,
        end_time: str,
        tenant: bool | None = None,
        account_ids: list[str] | None = None,
        query_priority: SDLQueryPriority = SDLQueryPriority.LOW,
        pq: SDLPQAttributes | None = None,
        headers: Headers | None = None,
    ) -> tuple[SDLSubmitQueryResponse, str]:
        """Create a new SDL PQ query.

        Args:
            auth_token: Authorization token
            start_time: Specifies the beginning of the time range to query. You can use:
                - Relative time: '24h', '7d', '30m', '25s'
                - Absolute timestamp: Unix epoch in seconds, milliseconds, or nanoseconds
            end_time:  Specifies the end of the time range to query. You can use:
                - Relative time: '24h', '7d', '30m', '25s'
                - Absolute timestamp: Unix epoch in seconds, milliseconds, or nanoseconds
            query: The query string to execute
            tenant: Controls the scope of the query across accessible data.

            When set to `true`:
            - Global admin users: Queries across global scope and all accounts
            - Account-level users: Queries only within the authorized account
            - Multi-account users: Queries across all authorized accounts
            - Site-level users: Queries only within the authorized site
            - Multi-site users: Queries across all authorized sites

            Tenant must be set to `false` when specifying scope via `accountIds`.
            account_ids: List of account IDs to restrict the query to.

            query_priority: Specifies the execution priority for this query; defaults to "LOW".
                Use "LOW" for background operations where a delay of a second or so is acceptable.
                LOW-priority queries have more generous rate limits.
            pq: PowerQuery attributes. Used for PQ queries
            headers: Additional headers for the request.

        Returns:
            A tuple containing the SubmitQueryResponse object and the X-Dataset-Query-Forward-Tag.

        Raises:
            httpx.HTTPError: If the request fails after retries.
            SDLMalformedResponseError: If the object could not be validated, using the Pydantic model.
        """
        payload: JsonDict = {
            "startTime": start_time,
            "endTime": end_time,
            "queryType": SDLQueryType.PQ,
            "queryPriority": query_priority,
        }

        if tenant is not None:
            payload["tenant"] = tenant
        if account_ids is not None:
            payload["accountIds"] = cast(JsonValue, account_ids)

        if pq is not None:
            payload["pq"] = pq.model_dump(mode="json", by_alias=True)
            payload["queryType"] = SDLQueryType.PQ

        res = await self._make_request(
            method="POST",
            path="/v2/api/queries",
            auth_token=auth_token,
            json_data=payload,
            headers=headers,
        )

        response_data = res.json()
        x_forward_tag = res.headers.get(X_DATASET_QUERY_FORWARD_TAG_HEADER)

        try:
            validated_response = SDLSubmitQueryResponse.model_validate(response_data)
            return validated_response, x_forward_tag
        except ValidationError as exc:
            logger.error(
                "Failed to validate SDL query response.",
                extra={"response_data": response_data},
                exc_info=exc,
            )
            raise SDLMalformedResponseError(
                "Failed to validate SDL submit query response."
            ) from exc

    async def ping_query(
        self,
        auth_token: str,
        query_id: str,
        x_dataset_query_forward_tag: str,
        last_step_seen: int = 0,
        headers: Headers | None = None,
    ) -> SDLPingResponse:
        """Get query results or status.

        Args:
            auth_token: Authorization token
            query_id: The query ID to check
            x_dataset_query_forward_tag: Forward tag for query
            last_step_seen: Last step identifier for incremental results
            headers: Additional headers for the request.

        Returns:
            A PingResponse object if successful.

        Raises:
            httpx.HTTPError: If the request fails after retries.
            SDLMalformedResponseError: If the response could not be validated, using the Pydantic model.
        """
        final_headers = Headers()
        if headers is not None:
            final_headers.update(headers)
        final_headers.update({X_DATASET_QUERY_FORWARD_TAG_HEADER: x_dataset_query_forward_tag})

        params: dict[str, int] = {"lastStepSeen": last_step_seen}

        res = await self._make_request(
            method="GET",
            path=f"/v2/api/queries/{query_id}",
            auth_token=auth_token,
            headers=final_headers,
            params=params,
        )

        response_data = res.json()

        try:
            return SDLPingResponse.model_validate(response_data)
        except ValidationError as exc:
            logger.error(
                "Failed to validate SDL query ping response.",
                extra={"response_data": response_data},
                exc_info=exc,
            )
            raise SDLMalformedResponseError("Failed to validate SDL query ping response.") from exc

    async def delete_query(
        self,
        auth_token: str,
        query_id: str,
        x_dataset_query_forward_tag: str,
        headers: Headers | None = None,
    ) -> bool:
        """Delete a query.

        Args:
            auth_token: Authorization token
            query_id: The query ID to delete
            x_dataset_query_forward_tag: Forward tag for query
            headers: Additional headers for the request.s

        Returns:
            True if successful, False otherwise

        Raises:
            httpx.HTTPError: If the request fails after retries.
        """
        final_headers = Headers()
        if headers is not None:
            final_headers.update(headers)
        final_headers.update({X_DATASET_QUERY_FORWARD_TAG_HEADER: x_dataset_query_forward_tag})

        res = await self._make_request(
            method="DELETE",
            path=f"/v2/api/queries/{query_id}",
            auth_token=auth_token,
            headers=final_headers,
        )

        if res.status_code != HTTPStatus.NO_CONTENT:
            logger.error(
                "Failed to delete SDL query.",
                extra={"query_id": query_id, "status_code": res.status_code},
            )
            return False

        return True

    async def __aenter__(self) -> Self:
        """Enter the context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the context manager and close the HTTP client."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client connection.

        This method should be called when not using the context manager
        to ensure proper cleanup of resources.

        Exceptions during cleanup are logged but not raised to prevent
        masking the original error in finally blocks. In development/test
        environments, exceptions are re-raised to ensure test failures are visible.

        Task cancellations (asyncio.CancelledError) are always re-raised
        to maintain proper cancellation semantics and prevent hanging callers.

        Raises:
            asyncio.CancelledError: Always re-raised to preserve cancellation.
            Exception: Only in development/test environments (development, dev,
                test, testing) when cleanup fails.
        """
        try:
            await self.http_client.aclose()
        except asyncio.CancelledError:
            # Always re-raise cancellations to maintain cooperative cancellation
            raise
        except Exception as exc:
            logger.warning(
                "Error during HTTP client cleanup",
                exc_info=exc,
            )
            # Re-raise in test environments for better test failure visibility
            if is_development_environment(self.environment):
                raise

    def is_closed(self) -> bool:
        """Check if the HTTP client is closed.

        Returns:
            True if the client is closed, False otherwise.
        """
        return self.http_client.is_closed
