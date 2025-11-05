"""REST client for Unified Asset Inventory API."""

import logging
import os
from collections.abc import Mapping
from http import HTTPStatus

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from purple_mcp.libs.inventory.config import InventoryConfig
from purple_mcp.libs.inventory.exceptions import (
    InventoryAPIError,
    InventoryAuthenticationError,
    InventoryClientError,
    InventoryNetworkError,
    InventoryNotFoundError,
    InventoryTransientError,
)
from purple_mcp.libs.inventory.models import (
    InventoryItem,
    InventoryResponse,
    PaginationInfo,
    Surface,
)
from purple_mcp.user_agent import get_user_agent

logger = logging.getLogger(__name__)


class InventoryClient:
    """Client for interacting with the Unified Asset Inventory REST API.

    This client provides read-only access to inventory data using the REST API.
    It uses httpx AsyncClient for asynchronous HTTP operations.
    """

    def __init__(self, config: InventoryConfig):
        """Initialize the inventory client.

        Args:
            config: Configuration for the inventory API
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None
        logger.debug(
            "Initialized inventory client",
            extra={"base_url": config.base_url, "api_endpoint": config.api_endpoint},
        )

    async def __aenter__(self) -> "InventoryClient":
        """Enter async context manager."""
        logger.debug("Opening HTTP client connection")
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.config.api_token}",
                "Content-Type": "application/json",
                "User-Agent": get_user_agent(),
            },
            timeout=httpx.Timeout(30.0),
        )
        logger.debug("HTTP client connection established")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        logger.debug("Closing HTTP client connection")
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("HTTP client connection closed")

    def _get_surface_endpoint(self, surface: Surface | None) -> str:
        """Get the endpoint URL for a specific surface.

        Args:
            surface: The surface type (ENDPOINT, CLOUD, IDENTITY, NETWORK_DISCOVERY)

        Returns:
            The full API endpoint URL
        """
        base = self.config.full_url
        if surface:
            # Convert enum to lowercase for API endpoint
            surface_str = surface.value.lower()
            endpoint = f"{base}/surface/{surface_str}"
            logger.debug(
                "Using surface-specific endpoint",
                extra={"surface": surface.value, "endpoint": endpoint},
            )
            return endpoint
        logger.debug("Using base endpoint", extra={"endpoint": base})
        return base

    async def get_inventory_item(self, item_id: str) -> InventoryItem | None:
        """Get a single inventory item by ID.

        Args:
            item_id: The ID of the inventory item

        Returns:
            The inventory item if found, None otherwise

        Raises:
            InventoryAuthenticationError: If authentication fails
            InventoryAPIError: If the API returns an error
            InventoryNetworkError: If a network error occurs
        """
        if not self._client:
            logger.error("Client not initialized")
            raise InventoryAPIError("Client not initialized. Use async context manager.")

        logger.debug("Getting inventory item by ID", extra={"item_id": item_id})

        try:
            # Use id__in filter for exact ID match
            filters = {"id__in": [item_id]}
            # Only log filter details if unsafe debugging is explicitly enabled
            if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
                logger.debug("Searching for item using id__in filter", extra={"filters": filters})
            else:
                logger.debug(
                    "Searching for item using id__in filter",
                    extra={"filter_keys": list(filters.keys())},
                )
            response = await self.search_inventory(filters=filters, limit=1, skip=0)

            if response.data:
                logger.debug("Found inventory item", extra={"item_id": item_id})
                return response.data[0]
            logger.debug("Inventory item not found", extra={"item_id": item_id})
            return None

        except InventoryNotFoundError:
            logger.debug(
                "Inventory item not found (InventoryNotFoundError)", extra={"item_id": item_id}
            )
            return None
        except Exception as e:
            logger.exception(
                "Failed to get inventory item",
                extra={"item_id": item_id, "error": str(e)},
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, InventoryTransientError)
        ),
    )
    async def _list_inventory_http(self, endpoint: str, limit: int, skip: int) -> httpx.Response:
        """Execute the HTTP GET request with automatic retry on transient failures.

        This internal method allows httpx exceptions to bubble up so tenacity can retry them.
        Also checks for transient 5xx errors (502, 503, 504) and raises InventoryTransientError
        to trigger a retry.

        Args:
            endpoint: The API endpoint to call.
            limit: Maximum number of items to return.
            skip: Number of items to skip for pagination.

        Returns:
            The httpx Response object.

        Raises:
            httpx.TimeoutException: If the request times out (retried automatically).
            httpx.NetworkError: If a network error occurs (retried automatically).
            InventoryTransientError: If a transient 5xx error occurs (retried automatically).
        """
        if not self._client:
            raise InventoryAPIError("Client not initialized. Use async context manager.")

        response = await self._client.get(
            endpoint,
            params={"limit": limit, "skip": skip},
        )

        # Check for transient 5xx errors that should be retried
        if response.status_code in (502, 503, 504):
            error_message = f"Transient server error {response.status_code}"
            try:
                error_data = response.json()
                error_message = (
                    error_data.get("message")
                    or error_data.get("error")
                    or error_data.get("detail")
                    or error_message
                )
            except Exception:
                pass  # Use default error message if JSON parsing fails

            logger.warning(
                "Transient server error, will retry",
                extra={"status_code": response.status_code, "endpoint": endpoint},
            )
            raise InventoryTransientError(f"{error_message}")

        return response

    async def list_inventory(
        self, limit: int = 50, skip: int = 0, surface: Surface | None = None
    ) -> InventoryResponse:
        """List inventory items with pagination and automatic retry on transient failures.

        Args:
            limit: Maximum number of items to return (1-1000, default 50)
            skip: Number of items to skip for pagination (default 0)
            surface: Optional surface filter (ENDPOINT, CLOUD, IDENTITY, NETWORK_DISCOVERY)

        Returns:
            InventoryResponse containing items and pagination info

        Raises:
            InventoryAuthenticationError: If authentication fails
            InventoryAPIError: If the API returns an error
            InventoryNetworkError: If a network error occurs
        """
        if not self._client:
            raise InventoryAPIError("Client not initialized. Use async context manager.")

        endpoint = self._get_surface_endpoint(surface)

        logger.debug(
            "Listing inventory items",
            extra={"limit": limit, "skip": skip, "surface": surface, "endpoint": endpoint},
        )

        try:
            response = await self._list_inventory_http(endpoint, limit, skip)
        except RetryError as e:
            # Unwrap the retry error to get the original exception
            original_exception = e.last_attempt.exception()
            if isinstance(original_exception, httpx.TimeoutException):
                logger.exception(
                    "Timeout listing inventory items after retries",
                    extra={"endpoint": endpoint, "limit": limit, "skip": skip},
                )
                raise InventoryNetworkError(
                    f"Request timeout: {original_exception}"
                ) from original_exception
            elif isinstance(original_exception, (httpx.NetworkError, httpx.RequestError)):
                logger.exception(
                    "Network error listing inventory items after retries",
                    extra={"endpoint": endpoint, "limit": limit, "skip": skip},
                )
                raise InventoryNetworkError(
                    f"Network error: {original_exception}"
                ) from original_exception
            elif isinstance(original_exception, InventoryTransientError):
                logger.exception(
                    "Transient server error persisted after retries",
                    extra={"endpoint": endpoint, "limit": limit, "skip": skip},
                )
                raise InventoryAPIError(
                    f"Server returned transient error after multiple retries: {original_exception}"
                ) from original_exception
            else:
                # Re-raise if it's not a known exception
                raise
        except httpx.TimeoutException as e:
            logger.exception(
                "Timeout listing inventory items",
                extra={"endpoint": endpoint, "limit": limit, "skip": skip},
            )
            raise InventoryNetworkError(f"Request timeout: {e}") from e
        except (httpx.NetworkError, httpx.RequestError) as e:
            logger.exception(
                "Network error listing inventory items",
                extra={"endpoint": endpoint, "limit": limit, "skip": skip},
            )
            raise InventoryNetworkError(f"Network error: {e}") from e

        logger.debug(
            "Received response for list_inventory",
            extra={"status_code": response.status_code, "url": str(response.url)},
        )

        try:
            return self._handle_response(response)
        except InventoryClientError:
            # Re-raise our typed exceptions unchanged so they remain observable
            raise
        except Exception as e:
            logger.exception(
                "Unexpected error listing inventory items",
                extra={"endpoint": endpoint, "limit": limit, "skip": skip},
            )
            raise InventoryAPIError(f"Unexpected error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, InventoryTransientError)
        ),
    )
    async def _search_inventory_http(
        self, endpoint: str, payload: dict[str, object]
    ) -> httpx.Response:
        """Execute the HTTP POST request with automatic retry on transient failures.

        This internal method allows httpx exceptions to bubble up so tenacity can retry them.
        Also checks for transient 5xx errors (502, 503, 504) and raises InventoryTransientError
        to trigger a retry.

        Args:
            endpoint: The API endpoint to call.
            payload: The JSON payload to send in the POST request.

        Returns:
            The httpx Response object.

        Raises:
            httpx.TimeoutException: If the request times out (retried automatically).
            httpx.NetworkError: If a network error occurs (retried automatically).
            InventoryTransientError: If a transient 5xx error occurs (retried automatically).
        """
        if not self._client:
            raise InventoryAPIError("Client not initialized. Use async context manager.")

        response = await self._client.post(
            endpoint,
            json=payload,
        )

        # Check for transient 5xx errors that should be retried
        if response.status_code in (502, 503, 504):
            error_message = f"Transient server error {response.status_code}"
            try:
                error_data = response.json()
                error_message = (
                    error_data.get("message")
                    or error_data.get("error")
                    or error_data.get("detail")
                    or error_message
                )
            except Exception:
                pass  # Use default error message if JSON parsing fails

            logger.warning(
                "Transient server error, will retry",
                extra={"status_code": response.status_code, "endpoint": endpoint},
            )
            raise InventoryTransientError(f"{error_message}")

        return response

    async def search_inventory(  # noqa: C901
        self,
        filters: Mapping[str, object],
        limit: int = 50,
        skip: int = 0,
    ) -> InventoryResponse:
        """Search inventory items with complex filters and automatic retry on transient failures.

        Note: This method does not support surface filtering. Surface-specific endpoints
        only support GET (list) operations, not POST (search) operations. Use list_inventory()
        with the surface parameter for surface-specific queries.

        Args:
            filters: Filter dictionary in REST API format (NOT GraphQL format).
                Examples: {"resourceType": ["Windows Server"]}, {"name__contains": ["prod"]},
                {"lastActiveDt__between": {"from": "2024-01-01", "to": "2024-12-31"}},
                {"id__in": ["id1", "id2"]}
            limit: Maximum number of items to return (1-1000, default 50)
            skip: Number of items to skip for pagination (default 0)

        Returns:
            InventoryResponse containing filtered items and pagination info

        Raises:
            InventoryAuthenticationError: If authentication fails
            InventoryAPIError: If the API returns an error
            InventoryNetworkError: If a network error occurs
        """
        if not self._client:
            raise InventoryAPIError("Client not initialized. Use async context manager.")

        endpoint = self.config.full_url

        # Construct the request payload
        # The API expects both filters and pagination params in the body
        payload: dict[str, object] = {
            "filter": {
                **filters,
                "limit": limit,
                "skip": skip,
            },
        }

        # Only log full payload if unsafe debugging is explicitly enabled
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.debug(
                "Searching inventory items",
                extra={
                    "filters": filters,
                    "limit": limit,
                    "skip": skip,
                    "endpoint": endpoint,
                    "payload": payload,
                },
            )
        else:
            logger.debug(
                "Searching inventory items",
                extra={
                    "filter_count": len(filters),
                    "filter_keys": list(filters.keys()),
                    "limit": limit,
                    "skip": skip,
                    "endpoint": endpoint,
                },
            )

        # Log the sanitized request details for debugging
        if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
            logger.debug(
                "Sending POST request to inventory API",
                extra={
                    "url": f"{self.config.base_url}{endpoint}",
                    "payload_json": payload,
                },
            )
        else:
            logger.debug(
                "Sending POST request to inventory API",
                extra={
                    "url": f"{self.config.base_url}{endpoint}",
                    "has_payload": bool(payload),
                },
            )

        try:
            response = await self._search_inventory_http(endpoint, payload)
        except RetryError as e:
            # Unwrap the retry error to get the original exception
            original_exception = e.last_attempt.exception()

            # Prepare sanitized logging extra dict
            if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
                log_extra = {
                    "endpoint": endpoint,
                    "filters": filters,
                    "limit": limit,
                    "skip": skip,
                }
            else:
                log_extra = {
                    "endpoint": endpoint,
                    "filter_count": len(filters),
                    "filter_keys": list(filters.keys()),
                    "limit": limit,
                    "skip": skip,
                }

            if isinstance(original_exception, httpx.TimeoutException):
                logger.exception(
                    "Timeout searching inventory items after retries",
                    extra=log_extra,
                )
                raise InventoryNetworkError(
                    f"Request timeout: {original_exception}"
                ) from original_exception
            elif isinstance(original_exception, (httpx.NetworkError, httpx.RequestError)):
                logger.exception(
                    "Network error searching inventory items after retries",
                    extra=log_extra,
                )
                raise InventoryNetworkError(
                    f"Network error: {original_exception}"
                ) from original_exception
            elif isinstance(original_exception, InventoryTransientError):
                logger.exception(
                    "Transient server error persisted after retries",
                    extra=log_extra,
                )
                raise InventoryAPIError(
                    f"Server returned transient error after multiple retries: {original_exception}"
                ) from original_exception
            else:
                # Re-raise if it's not a known exception
                raise
        except httpx.TimeoutException as e:
            # Use same sanitized log_extra as above
            if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
                log_extra = {
                    "endpoint": endpoint,
                    "filters": filters,
                    "limit": limit,
                    "skip": skip,
                }
            else:
                log_extra = {
                    "endpoint": endpoint,
                    "filter_count": len(filters),
                    "filter_keys": list(filters.keys()),
                    "limit": limit,
                    "skip": skip,
                }
            logger.exception(
                "Timeout searching inventory items",
                extra=log_extra,
            )
            raise InventoryNetworkError(f"Request timeout: {e}") from e
        except (httpx.NetworkError, httpx.RequestError) as e:
            # Use same sanitized log_extra as above
            if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
                log_extra = {
                    "endpoint": endpoint,
                    "filters": filters,
                    "limit": limit,
                    "skip": skip,
                }
            else:
                log_extra = {
                    "endpoint": endpoint,
                    "filter_count": len(filters),
                    "filter_keys": list(filters.keys()),
                    "limit": limit,
                    "skip": skip,
                }
            logger.exception(
                "Network error searching inventory items",
                extra=log_extra,
            )
            raise InventoryNetworkError(f"Network error: {e}") from e

        logger.debug(
            "Received response for search_inventory",
            extra={"status_code": response.status_code, "url": str(response.url)},
        )

        try:
            return self._handle_response(response)
        except InventoryClientError:
            # Re-raise our typed exceptions unchanged so they remain observable
            raise
        except Exception as e:
            # Use sanitized logging for unexpected errors too
            if os.environ.get("PURPLEMCP_DEBUG_UNSAFE_LOGGING") == "1":
                log_extra = {
                    "endpoint": endpoint,
                    "filters": filters,
                    "limit": limit,
                    "skip": skip,
                }
            else:
                log_extra = {
                    "endpoint": endpoint,
                    "filter_count": len(filters),
                    "filter_keys": list(filters.keys()),
                    "limit": limit,
                    "skip": skip,
                }
            logger.exception(
                "Unexpected error searching inventory items",
                extra=log_extra,
            )
            raise InventoryAPIError(f"Unexpected error: {e}") from e

    def _handle_response(self, response: httpx.Response) -> InventoryResponse:
        """Handle the HTTP response and convert to InventoryResponse.

        Args:
            response: The httpx Response object

        Returns:
            Parsed InventoryResponse

        Raises:
            InventoryAuthenticationError: If authentication fails (401/403)
            InventoryNotFoundError: If resource not found (404)
            InventoryAPIError: For other API errors
        """
        logger.debug(
            "Handling response",
            extra={
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
            },
        )

        # Handle authentication errors
        if response.status_code in (401, 403):
            logger.error(
                "Authentication failed",
                extra={"status_code": response.status_code, "url": str(response.url)},
            )
            raise InventoryAuthenticationError(
                f"Authentication failed with status {response.status_code}"
            )

        # Handle not found
        if response.status_code == HTTPStatus.NOT_FOUND:
            logger.warning("Resource not found", extra={"url": str(response.url)})
            raise InventoryNotFoundError("Inventory resource not found")

        # Handle other client/server errors
        if response.status_code >= 400:
            # Log the raw response body for debugging
            raw_body = response.text
            logger.debug(
                "Received error response - raw body",
                extra={
                    "status_code": response.status_code,
                    "raw_body": raw_body,
                    "content_length": len(raw_body),
                },
            )

            try:
                error_data = response.json()
                logger.debug("Parsed error response as JSON", extra={"error_data": error_data})

                # Try multiple possible error message fields
                error_message = (
                    error_data.get("message")
                    or error_data.get("error")
                    or error_data.get("errors")
                    or error_data.get("detail")
                    or error_data.get("description")
                    or "Unknown error"
                )
            except Exception as parse_error:
                error_message = raw_body
                logger.debug(
                    "Could not parse error response as JSON",
                    extra={"text": raw_body[:200], "parse_error": str(parse_error)},
                )

            logger.error(
                "API error",
                extra={
                    "status_code": response.status_code,
                    "url": str(response.url),
                    "error": error_message,
                },
            )
            raise InventoryAPIError(f"API error {response.status_code}: {error_message}")

        # Parse successful response
        try:
            logger.debug("Parsing successful response")
            data = response.json()

            # Extract items and pagination
            items_data = data.get("data", [])
            pagination_data = data.get("pagination", {})

            logger.debug(
                "Extracted response components",
                extra={
                    "items_count": len(items_data),
                    "has_pagination": bool(pagination_data),
                },
            )

            items = [InventoryItem.model_validate(item) for item in items_data]

            pagination = (
                PaginationInfo.model_validate(pagination_data) if pagination_data else None
            )

            logger.debug(
                "Successfully parsed inventory response",
                extra={
                    "item_count": len(items),
                    "total_count": pagination.total_count if pagination else None,
                },
            )

            return InventoryResponse(data=items, pagination=pagination)

        except Exception as e:
            logger.exception(
                "Failed to parse inventory response",
                extra={"error": str(e), "response": response.text[:500]},
            )
            raise InventoryAPIError(f"Failed to parse response: {e}") from e
