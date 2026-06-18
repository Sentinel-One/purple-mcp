"""CVE client for querying cve-search.org API."""

import json
import logging
from http import HTTPStatus

import httpx
from rfc3986 import builder

from purple_mcp.libs.cve.config import CVEConfig
from purple_mcp.libs.cve.exceptions import CVEClientError

logger = logging.getLogger(__name__)


def _create_not_found_response(resource: str, resource_type: str, message: str) -> str:
    """Create a structured JSON response for not found cases.

    Args:
        resource: The resource identifier (CVE ID, vendor, vendor/product).
        resource_type: Type of resource (cve, vendor, vendor_product).
        message: User-friendly message explaining what was not found.

    Returns:
        JSON string with found=false and user-friendly message.
    """
    response = {
        "found": False,
        "resource": resource,
        "resource_type": resource_type,
        "message": message,
    }
    return json.dumps(response, indent=2)


class CVEClient:
    """Client for interacting with CVE search API."""

    def __init__(self, config: CVEConfig) -> None:
        """Initialize the CVE client.

        Args:
            config: Configuration for the CVE client.
        """
        self.config = config

    async def get_cve_by_id(self, cve_id: str) -> str:
        """Get detailed information about a specific CVE by its ID.

        Args:
            cve_id: The CVE identifier (e.g., CVE-2024-47176).

        Returns:
            JSON string containing CVE details. If the CVE is not found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "cve", "message": "..."}

        Raises:
            CVEClientError: If there's an error communicating with the API.
        """
        logger.info("Searching CVE database", extra={"cve_id": cve_id})

        url = (
            builder.URIBuilder()
            .from_uri(self.config.base_url)
            .extend_path(f"cve/{cve_id}")
            .geturl()
        )
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            logger.error(
                "Error communicating with CVE API",
                extra={"cve_id": cve_id},
                exc_info=exc,
            )
            raise CVEClientError("Error communicating with CVE API") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == HTTPStatus.NOT_FOUND:
                logger.warning("CVE not found", extra={"cve_id": cve_id})
                return _create_not_found_response(
                    resource=cve_id,
                    resource_type="cve",
                    message=f"CVE {cve_id} not found in database",
                )
            logger.error(
                "HTTP error from CVE API",
                extra={"cve_id": cve_id},
                exc_info=exc,
            )
            raise CVEClientError("HTTP error from CVE API") from exc

        cve_data = response.json()
        logger.info("Found CVE", extra={"cve_id": cve_id})
        return json.dumps(cve_data, indent=2)

    async def search_by_vendor_product(self, vendor: str, product: str | None = None) -> str:
        """Search for CVEs by vendor and optionally product.

        Args:
            vendor: The vendor name (e.g., 'microsoft', 'apache').
            product: Optional product name (e.g., 'office', 'httpd').

        Returns:
            JSON string containing CVE list or product list. If no results are found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "...", "message": "..."}

        Raises:
            CVEClientError: If there's an error communicating with the API.
        """
        if product is not None:
            url = (
                builder.URIBuilder()
                .from_uri(self.config.base_url)
                .extend_path(f"search/{vendor}/{product}")
                .geturl()
            )
            logger.info(
                "Searching CVEs for vendor and product",
                extra={"vendor": vendor, "product": product},
            )
        else:
            url = (
                builder.URIBuilder()
                .from_uri(self.config.base_url)
                .extend_path(f"browse/{vendor}")
                .geturl()
            )
            logger.info("Browsing products for vendor", extra={"vendor": vendor})

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            logger.error(
                "Error communicating with CVE API",
                extra={"vendor": vendor, "product": product},
                exc_info=exc,
            )
            raise CVEClientError("Error communicating with CVE API") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == HTTPStatus.NOT_FOUND:
                logger.warning(
                    "No results found",
                    extra={"vendor": vendor, "product": product},
                )
                resource = f"{vendor}/{product}" if product else vendor
                resource_type = "vendor_product" if product else "vendor"
                search_desc = (
                    f"vendor '{vendor}' and product '{product}'"
                    if product
                    else f"vendor '{vendor}'"
                )
                return _create_not_found_response(
                    resource=resource,
                    resource_type=resource_type,
                    message=f"No results found for {search_desc}",
                )
            logger.error(
                "HTTP error from CVE API",
                extra={"vendor": vendor, "product": product},
                exc_info=exc,
            )
            raise CVEClientError("HTTP error from CVE API") from exc

        data = response.json()
        if product is not None:
            count = len(data) if isinstance(data, list) else "unknown"
            logger.info(
                "Found CVEs for vendor/product",
                extra={"count": count, "vendor": vendor, "product": product},
            )
        else:
            logger.info("Found products for vendor", extra={"vendor": vendor})

        return json.dumps(data, indent=2)

    async def get_database_info(self) -> str:
        """Get information about the CVE database status and last update.

        Returns:
            JSON string containing database information.

        Raises:
            CVEClientError: If there's an error communicating with the API.
        """
        logger.info("Fetching CVE database information")

        url = builder.URIBuilder().from_uri(self.config.base_url).extend_path("dbInfo").geturl()
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            logger.error("Error communicating with CVE API for database info", exc_info=exc)
            raise CVEClientError("Error communicating with CVE API") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error from CVE API for database info", exc_info=exc)
            raise CVEClientError("HTTP error from CVE API") from exc

        data = response.json()
        logger.info("Retrieved CVE database information")
        return json.dumps(data, indent=2)
