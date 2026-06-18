"""Threat Intelligence client for querying VirusTotal API."""

import json
import logging
from enum import StrEnum

import aiohttp
import vt

from purple_mcp.libs.threat_intelligence.config import ThreatIntelligenceConfig
from purple_mcp.libs.threat_intelligence.exceptions import ThreatIntelligenceClientError

logger = logging.getLogger(__name__)


class VTErrors(StrEnum):
    """Explicit VT Errors Enum.

    VT Client does not define a symbolic reference to their errors,
    so we define this wrapper to support ease of reference to the error
    types.

    See: https://docs.virustotal.com/reference/errors
    """

    # 400 Bad Request
    BadRequestError = "BadRequestError"
    InvalidArgumentError = "InvalidArgumentError"
    NotAvailableYet = "NotAvailableYet"
    UnselectiveContentQueryError = "UnselectiveContentQueryError"
    UnsupportedContentQueryError = "UnsupportedContentQueryError"
    # 401 Unauthorized
    AuthenticationRequiredError = "AuthenticationRequiredError"
    UserNotActiveError = "UserNotActiveError"
    WrongCredentialsError = "WrongCredentialsError"
    # 403 Forbidden
    ForbiddenError = "ForbiddenError"
    # 404 Not Found
    NotFoundError = "NotFoundError"
    # 409 Conflict
    AlreadyExistsError = "AlreadyExistsError"
    # 424 Failed Dependency
    FailedDependencyError = "FailedDependencyError"
    # 429 Too Many Requests
    QuotaExceededError = "QuotaExceededError"
    TooManyRequestsError = "TooManyRequestsError"
    # 5xx Server Errors
    ServerError = "ServerError"
    TransientError = "TransientError"
    DeadlineExceededError = "DeadlineExceededError"


def _create_error_message(error_code: str, context: str) -> str:
    """Create user-friendly error message from VT API error code.

    Args:
        error_code: The VirusTotal API error code.
        context: Description of the operation that failed.

    Returns:
        User-friendly error message.
    """
    unknown_error_message = f"VirusTotal API error ({error_code}) during {context}."
    error_messages: dict[VTErrors, str] = {
        # 400 Bad Request
        VTErrors.BadRequestError: f"Bad request for {context}. The request was malformed.",
        VTErrors.InvalidArgumentError: f"Invalid request parameters for {context}. Please check your query syntax and parameters.",
        VTErrors.NotAvailableYet: f"Resource not available yet for {context}. Please try again later.",
        VTErrors.UnselectiveContentQueryError: f"Search query for {context} is too broad. Please add more specific criteria.",
        VTErrors.UnsupportedContentQueryError: f"Unsupported search query type for {context}.",
        # 401 Unauthorized
        VTErrors.AuthenticationRequiredError: "VirusTotal API authentication failed. Please check your API key.",
        VTErrors.UserNotActiveError: "VirusTotal user account is not active. Please verify your account status.",
        VTErrors.WrongCredentialsError: "Invalid VirusTotal API credentials. Please check your API key.",
        # 403 Forbidden
        VTErrors.ForbiddenError: "Access forbidden. Your API key may not have permission for this operation.",
        # 409 Conflict
        VTErrors.AlreadyExistsError: f"Resource already exists for {context}.",
        # 424 Failed Dependency
        VTErrors.FailedDependencyError: f"A dependent request failed for {context}. Please try again.",
        # 429 Too Many Requests
        VTErrors.QuotaExceededError: "VirusTotal API quota exceeded. Please wait before making more requests or upgrade your API key.",
        VTErrors.TooManyRequestsError: "Too many requests to VirusTotal. Please slow down your request rate.",
        # 5xx Server Errors
        VTErrors.ServerError: f"VirusTotal server error during {context}. Please try again later.",
        VTErrors.TransientError: f"Temporary VirusTotal server issue during {context}. Please retry.",
        VTErrors.DeadlineExceededError: f"VirusTotal request timed out during {context}. Please try again.",
    }
    # Guard against unknown error codes not in VTErrors enum
    if error_code not in VTErrors:
        return unknown_error_message
    return error_messages.get(VTErrors(error_code), unknown_error_message)


def _create_not_found_response(
    resource: str, resource_type: str, message: str | None = None
) -> str:
    """Create a structured JSON response for not found cases.

    Args:
        resource: The resource identifier (hash, URL, domain, IP).
        resource_type: Type of resource (file, url, domain, ip).
        message: Optional custom message. If not provided, generates a default message.

    Returns:
        JSON string with found=false and user-friendly message.
    """
    if message is None:
        messages = {
            "file": f"File hash '{resource}' was not found in VirusTotal's database. This file has not been previously submitted to or analyzed by VirusTotal.",
            "url": f"URL '{resource}' was not found in VirusTotal's database. This URL has not been previously submitted to or scanned by VirusTotal.",
            "domain": f"Domain '{resource}' was not found in VirusTotal's database. This domain has no recorded threat intelligence data in VirusTotal.",
            "ip": f"IP address '{resource}' was not found in VirusTotal's database. This IP has no recorded threat intelligence data in VirusTotal.",
        }
        message = messages.get(
            resource_type, f"Resource '{resource}' was not found in VirusTotal."
        )

    response = {
        "found": False,
        "resource": resource,
        "resource_type": resource_type,
        "message": message,
    }
    return json.dumps(response, indent=2)


class ThreatIntelligenceClient:
    """Client for interacting with VirusTotal threat intelligence API."""

    def __init__(self, config: ThreatIntelligenceConfig) -> None:
        """Initialize the threat intelligence client.

        Args:
            config: Configuration for the threat intelligence client.
        """
        self.config = config

    async def get_hash_threat_intel(self, hash_value: str) -> str:
        """Get threat intelligence for a file hash (MD5, SHA1, or SHA256).

        Args:
            hash_value: The file hash to query.

        Returns:
            JSON string containing threat intelligence data. If the hash is not found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "file", "message": "..."}

        Raises:
            ThreatIntelligenceClientError: If there's an error communicating with the API.
        """
        logger.info("Searching VirusTotal for hash", extra={"hash_value": hash_value})

        try:
            async with vt.Client(self.config.api_key, timeout=self.config.timeout) as client:
                response = await client.get_json_async(f"/files/{hash_value}")
        except vt.error.APIError as exc:
            if exc.code == VTErrors.NotFoundError:
                logger.warning(
                    "Hash not found in VirusTotal",
                    extra={"hash_value": hash_value},
                )
                return _create_not_found_response(hash_value, "file")
            logger.error(
                "VirusTotal API error for hash",
                extra={"hash_value": hash_value, "error_code": exc.code},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                _create_error_message(exc.code, "file hash lookup")
            ) from exc
        except aiohttp.ClientError as exc:
            logger.error(
                "Network error querying VirusTotal for hash",
                extra={"hash_value": hash_value},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                "Network error communicating with VirusTotal"
            ) from exc
        except TimeoutError as exc:
            logger.error(
                "Request timed out querying VirusTotal for hash",
                extra={"hash_value": hash_value, "timeout": self.config.timeout},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                f"Request timed out after {self.config.timeout} seconds"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON response for hash",
                extra={"hash_value": hash_value},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError("Invalid JSON response from VirusTotal") from exc

        # Extract the 'data' field from VT API response
        # The VT API returns {"data": {...}, "links": {...}} but we only return the data
        file_data = response.get("data", response)

        logger.info("File found with hash", extra={"hash_value": hash_value})
        return json.dumps(file_data, indent=2)

    async def get_url_threat_intel(self, url: str) -> str:
        """Get threat intelligence for a URL.

        Args:
            url: The URL to query.

        Returns:
            JSON string containing threat intelligence data. If the URL is not found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "url", "message": "..."}

        Raises:
            ThreatIntelligenceClientError: If there's an error communicating with the API.
        """
        logger.info("Searching VirusTotal for URL", extra={"url": url})

        try:
            async with vt.Client(self.config.api_key, timeout=self.config.timeout) as client:
                url_id = vt.url_id(url)
                response = await client.get_json_async(f"/urls/{url_id}")
        except vt.error.APIError as exc:
            if exc.code == VTErrors.NotFoundError:
                logger.warning("URL not found in VirusTotal", extra={"url": url})
                return _create_not_found_response(url, "url")
            logger.error(
                "VirusTotal API error for URL",
                extra={"url": url, "error_code": exc.code},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                _create_error_message(exc.code, "URL lookup")
            ) from exc
        except aiohttp.ClientError as exc:
            logger.error(
                "Network error querying VirusTotal for URL",
                extra={"url": url},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                "Network error communicating with VirusTotal"
            ) from exc
        except TimeoutError as exc:
            logger.error(
                "Request timed out querying VirusTotal for URL",
                extra={"url": url, "timeout": self.config.timeout},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                f"Request timed out after {self.config.timeout} seconds"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON response for URL",
                extra={"url": url},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError("Invalid JSON response from VirusTotal") from exc

        # Extract the 'data' field from VT API response
        # The VT API returns {"data": {...}, "links": {...}} but we only return the data
        url_data = response.get("data", response)

        logger.info("URL found", extra={"url": url})
        return json.dumps(url_data, indent=2)

    async def get_domain_threat_intel(self, domain: str) -> str:
        """Get threat intelligence for a domain.

        Args:
            domain: The domain name to query.

        Returns:
            JSON string containing threat intelligence data. If the domain is not found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "domain", "message": "..."}

        Raises:
            ThreatIntelligenceClientError: If there's an error communicating with the API.
        """
        logger.info("Searching VirusTotal for domain", extra={"domain": domain})

        try:
            async with vt.Client(self.config.api_key, timeout=self.config.timeout) as client:
                response = await client.get_json_async(f"/domains/{domain}")
        except vt.error.APIError as exc:
            if exc.code == VTErrors.NotFoundError:
                logger.warning("Domain not found in VirusTotal", extra={"domain": domain})
                return _create_not_found_response(domain, "domain")
            logger.error(
                "VirusTotal API error for domain",
                extra={"domain": domain, "error_code": exc.code},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                _create_error_message(exc.code, "domain lookup")
            ) from exc
        except aiohttp.ClientError as exc:
            logger.error(
                "Network error querying VirusTotal for domain",
                extra={"domain": domain},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                "Network error communicating with VirusTotal"
            ) from exc
        except TimeoutError as exc:
            logger.error(
                "Request timed out querying VirusTotal for domain",
                extra={"domain": domain, "timeout": self.config.timeout},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                f"Request timed out after {self.config.timeout} seconds"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON response for domain",
                extra={"domain": domain},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError("Invalid JSON response from VirusTotal") from exc

        # Extract the 'data' field from VT API response
        # The VT API returns {"data": {...}, "links": {...}} but we only return the data
        domain_data = response.get("data", response)

        logger.info("Domain found", extra={"domain": domain})
        return json.dumps(domain_data, indent=2)

    async def get_ip_threat_intel(self, ip_address: str) -> str:
        """Get threat intelligence for an IP address.

        Args:
            ip_address: The IP address to query.

        Returns:
            JSON string containing threat intelligence data. If the IP is not found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "ip", "message": "..."}

        Raises:
            ThreatIntelligenceClientError: If there's an error communicating with the API.
        """
        logger.info("Searching VirusTotal for IP", extra={"ip_address": ip_address})

        try:
            async with vt.Client(self.config.api_key, timeout=self.config.timeout) as client:
                response = await client.get_json_async(f"/ip_addresses/{ip_address}")
        except vt.error.APIError as exc:
            if exc.code == VTErrors.NotFoundError:
                logger.warning(
                    "IP address not found in VirusTotal",
                    extra={"ip_address": ip_address},
                )
                return _create_not_found_response(ip_address, "ip")
            logger.error(
                "VirusTotal API error for IP",
                extra={"ip_address": ip_address, "error_code": exc.code},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                _create_error_message(exc.code, "IP address lookup")
            ) from exc
        except aiohttp.ClientError as exc:
            logger.error(
                "Network error querying VirusTotal for IP",
                extra={"ip_address": ip_address},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                "Network error communicating with VirusTotal"
            ) from exc
        except TimeoutError as exc:
            logger.error(
                "Request timed out querying VirusTotal for IP",
                extra={"ip_address": ip_address, "timeout": self.config.timeout},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                f"Request timed out after {self.config.timeout} seconds"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON response for IP",
                extra={"ip_address": ip_address},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError("Invalid JSON response from VirusTotal") from exc

        # Extract the 'data' field from VT API response
        # The VT API returns {"data": {...}, "links": {...}} but we only return the data
        ip_data = response.get("data", response)

        logger.info("IP address found", extra={"ip_address": ip_address})
        return json.dumps(ip_data, indent=2)

    async def get_file_relationships(self, hash_value: str, relationship_type: str) -> str:
        """Get relationships for a file hash.

        Args:
            hash_value: The file hash to query.
            relationship_type: Type of relationship (e.g., 'contacted_domains', 'contacted_ips',
                'contacted_urls', 'similar_files', 'execution_parents', 'bundled_files').

        Returns:
            JSON string containing relationship data. If the hash or relationship is not found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "file", "message": "..."}

        Raises:
            ThreatIntelligenceClientError: If there's an error communicating with the API.
        """
        limit = self.config.file_relationships_limit
        logger.info(
            "Getting file relationships",
            extra={
                "relationship_type": relationship_type,
                "hash_value": hash_value,
                "limit": limit,
            },
        )

        # Get relationship data
        relationship_path = f"/files/{hash_value}/{relationship_type}"
        relationships = []

        try:
            async with vt.Client(self.config.api_key, timeout=self.config.timeout) as client:
                async for item in client.iterator(relationship_path, limit=limit):
                    relationships.append(item.to_dict())
        except vt.error.APIError as exc:
            if exc.code == VTErrors.NotFoundError:
                logger.warning(
                    "Hash or relationship not found",
                    extra={"hash_value": hash_value},
                )
                message = (
                    f"File hash '{hash_value}' was not found, or it has no "
                    f"{relationship_type} relationships in VirusTotal. "
                    "The file may not have been analyzed, or no relationships "
                    "of this type were found."
                )
                return _create_not_found_response(hash_value, "file", message)
            logger.error(
                "VirusTotal API error for file relationships",
                extra={"hash_value": hash_value, "error_code": exc.code},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                _create_error_message(exc.code, f"file relationships ({relationship_type})")
            ) from exc
        except aiohttp.ClientError as exc:
            logger.error(
                "Network error querying VirusTotal for file relationships",
                extra={"hash_value": hash_value},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                "Network error communicating with VirusTotal"
            ) from exc
        except TimeoutError as exc:
            logger.error(
                "Request timed out querying VirusTotal for file relationships",
                extra={"hash_value": hash_value, "timeout": self.config.timeout},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                f"Request timed out after {self.config.timeout} seconds"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON response for file relationships",
                extra={"hash_value": hash_value},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError("Invalid JSON response from VirusTotal") from exc

        if not relationships:
            logger.warning(
                "No relationships found for hash",
                extra={"relationship_type": relationship_type, "hash_value": hash_value},
            )
            message = (
                f"No {relationship_type} relationships found for file hash '{hash_value}'. "
                "The file may not have been analyzed, or no relationships "
                "of this type were found."
            )
            return _create_not_found_response(hash_value, "file", message)

        logger.info(
            "Found file relationships",
            extra={
                "count": len(relationships),
                "relationship_type": relationship_type,
                "hash_value": hash_value,
            },
        )
        return json.dumps({"relationships": relationships, "count": len(relationships)}, indent=2)

    async def search_intelligence(self, query: str) -> str:
        """Search VirusTotal Intelligence with a query.

        Args:
            query: VT Intelligence search query (e.g., 'type:peexe size:90kb+ positives:5+').

        Returns:
            JSON string containing search results.

        Raises:
            ThreatIntelligenceClientError: If there's an error communicating with the API.
        """
        limit = self.config.intelligence_search_limit
        logger.info(
            "Searching VirusTotal Intelligence",
            extra={"query": query, "limit": limit},
        )

        results = []
        search_path = "/intelligence/search"
        try:
            async with vt.Client(self.config.api_key, timeout=self.config.timeout) as client:
                async for item in client.iterator(
                    search_path, params={"query": query}, limit=limit
                ):
                    results.append(item.to_dict())
        except vt.error.APIError as exc:
            logger.error(
                "VirusTotal API error for intelligence search",
                extra={"query": query, "error_code": exc.code},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                _create_error_message(exc.code, "intelligence search")
            ) from exc
        except aiohttp.ClientError as exc:
            logger.error(
                "Network error querying VirusTotal for intelligence search",
                extra={"query": query},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                "Network error communicating with VirusTotal"
            ) from exc
        except TimeoutError as exc:
            logger.error(
                "Request timed out querying VirusTotal for intelligence search",
                extra={"query": query, "timeout": self.config.timeout},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                f"Request timed out after {self.config.timeout} seconds"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON response for intelligence search",
                extra={"query": query},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError("Invalid JSON response from VirusTotal") from exc

        logger.info(
            "Found intelligence search results",
            extra={"count": len(results), "query": query},
        )
        return json.dumps({"results": results, "count": len(results), "query": query}, indent=2)

    async def get_file_behavior(self, hash_value: str, sandbox: str | None = None) -> str:
        """Get behavioral analysis report for a file hash.

        Args:
            hash_value: The file hash (SHA256) to query.
            sandbox: Optional specific sandbox name (e.g., 'VirusTotal Jujubox', 'C2AE').
                If None, returns the default/first available behavior report.

        Returns:
            JSON string containing behavioral analysis data. If no behavior report is found,
            returns a structured response with found=false instead of raising an exception:
            {"found": false, "resource": "...", "resource_type": "file", "message": "..."}

        Raises:
            ThreatIntelligenceClientError: If there's an error communicating with the API.
        """
        limit = self.config.file_behavior_limit
        logger.info(
            "Getting behavior report",
            extra={"hash_value": hash_value, "sandbox": sandbox, "limit": limit},
        )

        # Get all behaviors for the file
        behaviors_path = f"/files/{hash_value}/behaviours"
        behaviors = []

        try:
            async with vt.Client(self.config.api_key, timeout=self.config.timeout) as client:
                async for behavior in client.iterator(behaviors_path, limit=limit):
                    behaviors.append(behavior.to_dict())
        except vt.error.APIError as exc:
            if exc.code == VTErrors.NotFoundError:
                logger.warning(
                    "Hash not found or no behaviors available",
                    extra={"hash_value": hash_value},
                )
                return _create_not_found_response(hash_value, "file")
            logger.error(
                "VirusTotal API error for file behavior",
                extra={"hash_value": hash_value, "error_code": exc.code},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                _create_error_message(exc.code, "file behavior lookup")
            ) from exc
        except aiohttp.ClientError as exc:
            logger.error(
                "Network error querying VirusTotal for file behavior",
                extra={"hash_value": hash_value},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                "Network error communicating with VirusTotal"
            ) from exc
        except TimeoutError as exc:
            logger.error(
                "Request timed out querying VirusTotal for file behavior",
                extra={"hash_value": hash_value, "timeout": self.config.timeout},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError(
                f"Request timed out after {self.config.timeout} seconds"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON response for hash",
                extra={"hash_value": hash_value},
                exc_info=exc,
            )
            raise ThreatIntelligenceClientError("Invalid JSON response from VirusTotal") from exc

        if len(behaviors) == 0:
            logger.warning(
                "No behavior reports found",
                extra={"hash_value": hash_value},
            )
            message = (
                f"No behavioral analysis reports found for file hash '{hash_value}'. "
                "The file may not have been analyzed in a sandbox, or only SHA256 "
                "hashes are supported for behavior reports."
            )
            return _create_not_found_response(hash_value, "file", message)

        # If sandbox specified, filter for it
        if sandbox is not None:
            behaviors = [b for b in behaviors if sandbox.lower() in b.get("id", "").lower()]
            if not behaviors:
                logger.warning(
                    "No behavior report from sandbox found",
                    extra={"sandbox": sandbox, "hash_value": hash_value},
                )
                message = (
                    f"No behavioral analysis report from sandbox '{sandbox}' found "
                    f"for file hash '{hash_value}'. "
                    "The file may not have been analyzed in this specific sandbox."
                )
                return _create_not_found_response(hash_value, "file", message)

        logger.info("Found behavior report", extra={"hash_value": hash_value})
        return json.dumps(behaviors, indent=2)
