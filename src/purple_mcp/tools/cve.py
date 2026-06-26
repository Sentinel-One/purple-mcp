"""CVE MCP tool implementation.

This module defines CVE search MCP tools that act as thin wrappers
around the CVE Search API (cve-search.org), exposing vulnerability
data to FastMCP clients.

Key Components:
    - cve_search_by_id(): Query detailed CVE information by ID.
    - cve_search_by_vendor(): Search CVEs by vendor/product.
    - cve_database_status(): Get database update information.

Usage:
    These tools are automatically registered when `purple_mcp.server` is
    imported but can also be called directly for unit-testing:

    ```python
    from purple_mcp.tools.cve import cve_search_by_id

    result = await cve_search_by_id("CVE-2024-47176")
    print(result)
    ```

Architecture:
    1. Create CVEConfig with default settings (no API key required).
    2. Delegate API calls to CVEClient.
    3. Return JSON results (including structured not-found responses).
    4. When data is not found, methods return a structured JSON response with
       found=false instead of raising an exception.

Dependencies:
    - purple_mcp.libs.cve: Encapsulates all CVE API specifics.
    - fastmcp: Registers the callable as an MCP tool (handled by the server).
    - httpx: HTTP client for API requests.

Raises:
    CVEClientError: When the API request fails.
"""

from textwrap import dedent
from typing import Final

from purple_mcp.libs.cve import CVEClient, CVEConfig

CVE_SEARCH_BY_ID_DESCRIPTION: Final = dedent(
    """
    Get detailed information about a specific CVE by its identifier.

    This tool queries the CVE database to retrieve comprehensive vulnerability
    information including description, CVSS scores, affected products, references,
    and remediation guidance.

    What this tool provides:
    - CVE description and summary
    - CVSS v2 and v3 scores with vector strings
    - Affected products and versions (CPE format)
    - References to advisories, patches, and exploits
    - CWE (Common Weakness Enumeration) mappings
    - Publication and modification timestamps
    - Impact ratings and severity

    Common Use Cases:
    - Security research and vulnerability assessment
    - Incident response investigations
    - Patch management prioritization
    - Security advisory creation
    - Compliance reporting

    Args:
        cve_id: The CVE identifier in the format CVE-YYYY-NNNNN
                (e.g., CVE-2024-47176, CVE-2023-12345)

    Returns:
        JSON string containing comprehensive CVE details including:
        - id: CVE identifier
        - summary: Vulnerability description
        - cvss: CVSS v2 score
        - cvss3: CVSS v3 score with full metrics
        - vulnerable_configuration: List of affected CPEs
        - references: Links to advisories and patches
        - cwe: Common Weakness Enumeration identifier
        - Published: Publication timestamp
        - Modified: Last modification timestamp

    Examples:
        "CVE-2024-47176" - Recent vulnerability
        "CVE-2023-12345" - Search any CVE from any year
        "CVE-2021-44228" - Log4Shell vulnerability

    Notes:
        - Data sourced from cve-search.org (CIRCL.LU)
        - No API key required
        - Database updated regularly from NVD and other sources
        - Returns detailed CAPEC, CWE, and CPE expansions

    Not Found Response:
        When a CVE is not found, returns a JSON response with this structure:
        {
          "found": false,
          "resource": "CVE-YYYY-NNNNN",
          "resource_type": "cve",
          "message": "CVE-YYYY-NNNNN not found in the CVE database."
        }

    Raises:
        CVEClientError: If there's an error communicating with the API (not for not-found cases).
    """
).strip()

CVE_SEARCH_BY_VENDOR_DESCRIPTION: Final = dedent(
    """
    Search for CVEs by vendor name and optionally filter by product.

    This tool searches the CVE database for vulnerabilities affecting specific
    vendors and their products. Can be used to browse available products or
    get a comprehensive list of CVEs for a vendor/product combination.

    What this tool provides:
    - List of CVEs for a specific vendor/product
    - Available products for a vendor (when product not specified)
    - Complete CVE details for each result
    - Sorted by severity and recency

    Common Use Cases:
    - Asset vulnerability scanning
    - Vendor risk assessment
    - Product-specific security monitoring
    - Patch management planning
    - Security posture evaluation

    Args:
        vendor: The vendor name (case-insensitive, use lowercase).
                Examples: 'microsoft', 'apache', 'cisco', 'linux', 'oracle'
        product: Optional product name (case-insensitive, use lowercase).
                 Examples: 'office', 'httpd', 'ios', 'kernel', 'database'
                 If omitted, returns list of available products for the vendor.

    Returns:
        When product is specified:
        - JSON string containing array of CVE objects with full details

        When product is omitted:
        - JSON string containing array of available product names for that vendor

    Examples:
        Search CVEs: vendor="microsoft", product="windows"
        Search CVEs: vendor="apache", product="httpd"
        List products: vendor="cisco" (product omitted)
        List products: vendor="linux" (product omitted)

    Notes:
        - Vendor/product names should be lowercase
        - Use underscores or hyphens as they appear in CPE names
        - Product browsing helps discover correct product names
        - Results may include multiple product versions
        - No API key required
        - When vendor/product is not found, returns a structured JSON response with found=false

    Raises:
        CVEClientError: If there's an error communicating with the API.
    """
).strip()

CVE_DATABASE_STATUS_DESCRIPTION: Final = dedent(
    """
    Get information about the CVE database status and last update time.

    This tool provides metadata about the CVE database including when it was
    last updated and how many CVEs it contains. Useful for determining data
    freshness and database health.

    What this tool provides:
    - Last database update timestamp
    - Total CVE count in database
    - Database version information
    - Data source information

    Common Use Cases:
    - Verify data freshness
    - Check database health
    - Compliance documentation
    - Data quality assurance
    - Integration monitoring

    Returns:
        JSON string containing database metadata:
        - Last update timestamp (ISO 8601 format)
        - Total number of CVEs
        - Database version
        - Data sources

    Notes:
        - Database typically updates multiple times daily
        - Sources include NVD, vendor advisories, and community feeds
        - No API key required

    Raises:
        CVEClientError: If there's an error communicating with the API.
    """
).strip()


def _get_client() -> CVEClient:
    """Create a CVEClient with default configuration.

    Returns:
        Configured CVEClient instance.
    """
    return CVEClient(CVEConfig())


async def cve_search_by_id(cve_id: str) -> str:
    """Get detailed information about a specific CVE by its ID.

    Args:
        cve_id: The CVE identifier (e.g., CVE-2024-47176).

    Returns:
        Detailed CVE information as a JSON string. If the CVE is not found, returns
        a structured response: {"found": false, "resource": "...", "message": "..."}

    Raises:
        CVEClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_cve_by_id(cve_id)


async def cve_search_by_vendor(vendor: str, product: str | None = None) -> str:
    """Search for CVEs by vendor and optionally product name.

    Args:
        vendor: The vendor name (e.g., 'microsoft', 'apache').
        product: Optional product name (e.g., 'office', 'httpd').

    Returns:
        List of CVEs or products as a JSON string. If no results are found, returns
        a structured response: {"found": false, "resource": "...", "message": "..."}

    Raises:
        CVEClientError: If there's an error communicating with the API.
    """
    return await _get_client().search_by_vendor_product(vendor, product)


async def cve_database_status() -> str:
    """Get information about the CVE database status and last update time.

    Returns:
        Database information as a JSON string.

    Raises:
        CVEClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_database_info()
