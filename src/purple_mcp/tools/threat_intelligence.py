"""Threat Intelligence MCP tool implementation.

This module defines threat intelligence MCP tools that act as thin wrappers
around VirusTotal/Google Threat Intelligence, exposing it to FastMCP clients.
The tools collect configuration, perform authentication, and relay queries to
the underlying VirusTotal API before returning threat intelligence data.

Key Components:
    - threat_intel_by_hash(): Query threat intelligence by file hash.
    - threat_intel_by_url(): Query threat intelligence by URL.
    - threat_intel_by_domain(): Query threat intelligence by domain.
    - threat_intel_by_ip(): Query threat intelligence by IP address.
    - threat_intel_get_file_relationships(): Get file relationships (network IOCs).
    - threat_intel_search(): Search VirusTotal Intelligence with queries.
    - threat_intel_get_file_behavior(): Get behavioral analysis reports.

Usage:
    These tools are automatically registered when `purple_mcp.server` is
    imported but can also be called directly for unit-testing:

    ```python
    from purple_mcp.tools.threat_intelligence import threat_intel_by_hash

    result = await threat_intel_by_hash("44d88612fea8a8f36de82e1278abb02f")
    print(result)
    ```

Architecture:
    1. Resolve runtime configuration via `purple_mcp.config.get_settings()`.
    2. Build the strongly-typed config objects required by
       `purple_mcp.libs.threat_intelligence`.
    3. Delegate the API call to the client library, returning JSON results.
    4. When data is not found, methods return a structured JSON response with
       found=false instead of raising an exception.

Dependencies:
    - purple_mcp.libs.threat_intelligence: Encapsulates all VirusTotal API
      specifics.
    - fastmcp: Registers the callable as an MCP tool (handled by the server).
    - vt-py: Python SDK for VirusTotal API v3.

Raises:
    RuntimeError: When settings are missing or invalid.
    ThreatIntelligenceClientError: When the API request fails.
"""

from textwrap import dedent
from typing import Final

from purple_mcp.config import get_settings
from purple_mcp.libs.threat_intelligence import ThreatIntelligenceClient, ThreatIntelligenceConfig

THREAT_INTEL_BY_HASH_DESCRIPTION: Final = dedent(
    """
    Get threat intelligence for a file hash from VirusTotal/Google Threat Intelligence.

    This tool queries VirusTotal's database to retrieve comprehensive threat intelligence
    about a file based on its cryptographic hash. The hash can be in MD5, SHA1, or SHA256
    format.

    What this tool provides:
    - Malware detection results from 70+ antivirus engines
    - File metadata (size, type, names, creation dates)
    - Behavioral analysis results
    - YARA rule matches
    - Crowdsourced threat intelligence
    - Relationships with other files, URLs, domains, and IPs
    - Community comments and votes
    - Signature information (digital signatures, if present)

    Common Use Cases:
    - Incident response: Validate if a suspicious file is malicious
    - Threat hunting: Research known malware samples
    - Malware analysis: Get context about a file before deeper investigation
    - IOC enrichment: Add threat intelligence to indicators of compromise

    Args:
        hash_value: File hash in MD5, SHA1, or SHA256 format (case-insensitive).

    Returns:
        JSON string containing comprehensive threat intelligence data including:
        - Detection statistics (e.g., 45/70 engines detected as malicious)
        - File attributes and metadata
        - Last analysis date and statistics
        - Community reputation score
        - Related threat intelligence
        - MITRE ATT&CK techniques (if applicable)

    Examples:
        MD5:    "44d88612fea8a8f36de82e1278abb02f"
        SHA1:   "3395856ce81f2b7382dee72602f798b642f14140"
        SHA256: "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"

    Notes:
        - Requires a valid VirusTotal API key (PURPLEMCP_VT_API_KEY environment variable)
        - Results are cached by VirusTotal and may not reflect real-time scans
        - File must have been previously submitted to VirusTotal to have results
        - Private API keys have higher rate limits and additional features

    Not Found Response:
        When a hash is not found, returns a JSON response with this structure:
        {
          "found": false,
          "resource": "hash_value",
          "resource_type": "file",
          "message": "File hash 'hash_value' was not found in VirusTotal's database..."
        }

    Raises:
        ThreatIntelligenceClientError: If there's an error communicating with the API (not for not-found cases).
        RuntimeError: If the API key is not configured.
    """
).strip()

THREAT_INTEL_BY_URL_DESCRIPTION: Final = dedent(
    """
    Get threat intelligence and reputation information for a URL from VirusTotal/Google Threat Intelligence.

    This tool queries VirusTotal's database to retrieve comprehensive threat intelligence
    about a URL, including reputation scores, detection results, and historical data.

    What this tool provides:
    - URL reputation and detection status from 90+ security vendors
    - Historical analysis results
    - Associated files and malware
    - Redirection chains
    - SSL certificate information
    - WHOIS data for the domain
    - Related IPs and domains
    - Community comments and votes
    - Threat categories (phishing, malware, etc.)

    Common Use Cases:
    - Email security: Check if URLs in emails are malicious
    - Web filtering: Validate URL safety before allowing access
    - Incident response: Investigate suspicious URLs from logs
    - Phishing detection: Identify phishing sites
    - Threat hunting: Research known malicious infrastructure

    Args:
        url: The URL to query (must be a valid HTTP/HTTPS URL).

    Returns:
        JSON string containing comprehensive threat intelligence data including:
        - Detection statistics from security vendors
        - URL categories and tags
        - Last analysis timestamp
        - Reputation score
        - Related files and domains
        - SSL certificate details
        - Redirection information

    Examples:
        "https://example.com/suspicious-page"
        "http://malicious-domain.test/payload.exe"
        "https://phishing-site.example/login"

    Notes:
        - Requires a valid VirusTotal API key (PURPLEMCP_VT_API_KEY environment variable)
        - VirusTotal may scan the URL if it hasn't been analyzed recently
        - Results include historical data and may not reflect current state
        - Scanning a URL will visit the site, which may have privacy implications
        - Private API keys have higher rate limits and additional features
        - When a URL is not found, returns a structured JSON response with found=false

    Raises:
        ThreatIntelligenceClientError: If there's an error communicating with the API.
        RuntimeError: If the API key is not configured.
    """
).strip()


def _get_client() -> ThreatIntelligenceClient:
    """Create a ThreatIntelligenceClient with API key from settings.

    Returns:
        Configured ThreatIntelligenceClient instance.

    Raises:
        RuntimeError: If PURPLEMCP_VT_API_KEY environment variable is not set.
    """
    try:
        settings = get_settings()
    except Exception as e:
        raise RuntimeError(
            f"Settings not initialized. Please check your environment configuration. Error: {e}"
        ) from e

    if not settings.vt_api_key:
        raise RuntimeError(
            "PURPLEMCP_VT_API_KEY environment variable must be set. "
            "Get your API key from https://www.virustotal.com/gui/my-apikey"
        )

    config = ThreatIntelligenceConfig(
        api_key=settings.vt_api_key,
        timeout=settings.vt_timeout,
    )
    return ThreatIntelligenceClient(config)


async def threat_intel_by_hash(hash_value: str) -> str:
    """Get hash threat intel from VirusTotal/Google Threat Intelligence.

    Args:
        hash_value: The file hash (MD5, SHA1, or SHA256) to query.

    Returns:
        Threat intelligence as a JSON string. If the hash is not found, returns
        a structured response: {"found": false, "resource": "...", "message": "..."}

    Raises:
        RuntimeError: If the API key is not configured.
        ThreatIntelligenceClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_hash_threat_intel(hash_value)


async def threat_intel_by_url(url: str) -> str:
    """Get threat and reputation information for a URL from VirusTotal/Google Threat Intelligence.

    Args:
        url: The URL to query.

    Returns:
        Threat intelligence as a JSON string. If the URL is not found, returns
        a structured response: {"found": false, "resource": "...", "message": "..."}

    Raises:
        RuntimeError: If the API key is not configured.
        ThreatIntelligenceClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_url_threat_intel(url)


THREAT_INTEL_BY_DOMAIN_DESCRIPTION: Final = dedent(
    """
    Get threat intelligence for a domain from VirusTotal/Google Threat Intelligence.

    This tool queries VirusTotal's database to retrieve comprehensive threat intelligence
    about a domain name, including reputation, detection results, WHOIS data, and relationships.

    What this tool provides:
    - Domain reputation and detection status from 90+ security vendors
    - WHOIS registration information
    - DNS resolution history
    - Associated files, URLs, and IP addresses
    - SSL certificates
    - Subdomains discovered
    - Threat categories (malware, phishing, etc.)
    - Historical analysis data
    - Community reputation scores

    Common Use Cases:
    - Investigate suspicious domains from email headers or logs
    - Research command & control infrastructure
    - Validate domain reputation before allowing access
    - Identify malicious infrastructure in incident response
    - Threat hunting for known bad actor domains

    Args:
        domain: The domain name to query (e.g., "example.com").

    Returns:
        JSON string containing comprehensive threat intelligence data including:
        - Detection statistics from security vendors
        - WHOIS registration details
        - DNS records and resolution history
        - Related malware, IPs, and URLs
        - Reputation score and categories
        - SSL certificate information

    Examples:
        "google.com"
        "malicious-c2.example.com"
        "phishing-site.test"

    Notes:
        - Requires a valid VirusTotal API key (PURPLEMCP_VT_API_KEY environment variable)
        - Results include historical data aggregated over time
        - Private API keys have higher rate limits
        - When a domain is not found, returns a structured JSON response with found=false

    Raises:
        ThreatIntelligenceClientError: If there's an error communicating with the API.
        RuntimeError: If the API key is not configured.
    """
).strip()


THREAT_INTEL_BY_IP_DESCRIPTION: Final = dedent(
    """
    Get threat intelligence for an IP address from VirusTotal/Google Threat Intelligence.

    This tool queries VirusTotal's database to retrieve comprehensive threat intelligence
    about an IP address, including reputation, geolocation, ASN data, and relationships.

    What this tool provides:
    - IP reputation and detection status from 90+ security vendors
    - Geolocation data (country, city, coordinates)
    - ASN (Autonomous System Number) and network owner
    - Associated files, URLs, and domains
    - Passive DNS data
    - Historical analysis results
    - Open ports and services (if available)
    - Threat categories and tags
    - Community reputation scores

    Common Use Cases:
    - Investigate suspicious IPs from firewall logs
    - Research malware C2 servers
    - Validate IP reputation before allowing connections
    - Identify attacker infrastructure in incident response
    - Threat hunting for known malicious IPs
    - Network forensics and attribution

    Args:
        ip_address: The IP address to query (IPv4 or IPv6).

    Returns:
        JSON string containing comprehensive threat intelligence data including:
        - Detection statistics from security vendors
        - Geolocation and network information
        - ASN and owner details
        - Related malware, domains, and URLs
        - Reputation score and categories
        - Historical connection data

    Examples:
        "8.8.8.8"
        "192.168.1.1"
        "2001:4860:4860::8888"

    Notes:
        - Requires a valid VirusTotal API key (PURPLEMCP_VT_API_KEY environment variable)
        - Results include historical data aggregated over time
        - Private/internal IPs may have limited or no data
        - Private API keys have higher rate limits
        - When an IP is not found, returns a structured JSON response with found=false

    Raises:
        ThreatIntelligenceClientError: If there's an error communicating with the API.
        RuntimeError: If the API key is not configured.
    """
).strip()


THREAT_INTEL_GET_FILE_RELATIONSHIPS_DESCRIPTION: Final = dedent(
    """
    Get relationships for a file hash from VirusTotal (network IOCs and related files).

    This tool extracts relationship data from a file's VirusTotal analysis, revealing
    network infrastructure (domains, IPs, URLs) contacted by the file, as well as
    related files. This is essential for pivoting from files to network indicators
    and building comprehensive threat intelligence profiles.

    Available relationship types:
    - contacted_domains: Domains contacted during execution
    - contacted_ips: IP addresses contacted during execution
    - contacted_urls: URLs contacted during execution
    - similar_files: Files with similar characteristics
    - execution_parents: Files that executed this file
    - bundled_files: Files bundled/dropped by this file
    - compressed_parents: Archives containing this file
    - overlay_parents: Parent files with overlays

    What this tool provides:
    - Network infrastructure IOCs (domains, IPs, URLs)
    - File lineage and relationships
    - Dropped/bundled files
    - Similar malware samples
    - Execution chain information

    Common Use Cases:
    - Extract network IOCs from malware samples
    - Build threat intelligence from file analysis
    - Pivot from files to domains/IPs for blocking
    - Identify related malware families
    - Map malware infrastructure and campaigns
    - Enrich incident response with related indicators

    Args:
        hash_value: The file hash (MD5, SHA1, or SHA256) to query.
        relationship_type: The type of relationship to retrieve (e.g., 'contacted_domains').

    Returns:
        JSON string containing:
        - relationships: Array of related objects with full details (up to 100)
        - count: Number of relationships found

    Examples:
        hash_value="275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f",
        relationship_type="contacted_domains"

        hash_value="44d88612fea8a8f36de82e1278abb02f",
        relationship_type="contacted_ips"

    Notes:
        - Requires a valid VirusTotal API key (PURPLEMCP_VT_API_KEY environment variable)
        - Returns up to 100 relationships (the API maximum)
        - Not all files have all relationship types
        - Relationship data comes from sandbox execution
        - Private API keys have access to more relationship types
        - When a hash or relationship is not found, returns a structured JSON response with found=false
        - IMPORTANT: Do NOT call this tool repeatedly with the same parameters.
          It returns the same data each time, not additional results.

    Raises:
        ThreatIntelligenceClientError: If there's an error communicating with the API.
        RuntimeError: If the API key is not configured.
    """
).strip()


THREAT_INTEL_SEARCH_DESCRIPTION: Final = dedent(
    """
    Search VirusTotal Intelligence with advanced queries for threat hunting.

    This tool allows searching the entire VirusTotal dataset using powerful query
    syntax to find files matching specific criteria. Essential for proactive threat
    hunting, malware research, and discovering related samples.

    Query Syntax Examples:
    - File type: type:peexe type:pdf type:apk
    - Size: size:90kb+ size:1mb-5mb
    - Detections: positives:5+ engines:kaspersky
    - Time: fs:2024-01-01+ ls:7d-
    - Behavior: behavior:"contacts C2"
    - Tags: tag:ransomware tag:trojan
    - Strings: content:"malicious string"
    - Imports: imports:CreateRemoteThread
    - Certificates: signature:"Company Name"

    What this tool provides:
    - Search results matching your criteria
    - File metadata and detection statistics
    - Comprehensive threat intelligence per result
    - Ability to hunt for specific malware characteristics
    - IOC discovery and threat research capabilities

    Common Use Cases:
    - Threat hunting: Find files with specific behaviors or characteristics
    - Malware research: Discover related samples and families
    - IOC expansion: Find files using known infrastructure
    - Campaign tracking: Identify malware from specific actors
    - Signature development: Research samples for detection rules
    - Incident response: Find similar threats in your environment

    Args:
        query: VT Intelligence search query using the VirusTotal query syntax.

    Returns:
        JSON string containing:
        - results: Array of matching files with full details (up to 10)
        - count: Number of results returned
        - query: The search query used

    Examples:
        query="type:peexe size:90kb+ positives:10+"
        query="behavior_network:C2 tag:ransomware"
        query="signature:'Microsoft Corporation' positives:0"

    Notes:
        - Requires a valid VirusTotal API key (PURPLEMCP_VT_API_KEY environment variable)
        - Intelligence search requires a VirusTotal Premium/Enterprise API key
        - Returns up to 10 results per query
        - Complex queries may take longer to execute
        - Query syntax documentation: https://docs.virustotal.com/docs/intelligence-search
        - IMPORTANT: Do NOT call this tool repeatedly with the same parameters.
          It returns the same data each time, not additional results.
          Use different search queries to find different files.

    Raises:
        ThreatIntelligenceClientError: If there's an error communicating with the API.
        RuntimeError: If the API key is not configured or lacks Intelligence access.
    """
).strip()


THREAT_INTEL_GET_FILE_BEHAVIOR_DESCRIPTION: Final = dedent(
    """
    Get detailed behavioral analysis report for a file from VirusTotal sandboxes.

    This tool retrieves sandbox execution reports that show what a file does when run,
    including process activity, network connections, file operations, registry changes,
    and MITRE ATT&CK techniques. Essential for understanding malware capabilities and
    identifying detection opportunities.

    What this tool provides:
    - Process tree and execution flow
    - Network connections (IPs, domains, URLs contacted)
    - File system operations (files created, modified, deleted)
    - Registry modifications
    - MITRE ATT&CK TTPs (Tactics, Techniques, Procedures)
    - API calls and system interactions
    - Behavioral signatures matched
    - Mutex/synchronization objects
    - Memory operations

    Common Use Cases:
    - Malware analysis: Understand what a file does when executed
    - Detection engineering: Identify behavioral indicators for rules
    - Incident response: Determine malware capabilities and impact
    - Threat intelligence: Extract TTPs for threat profiling
    - IOC extraction: Get network and file system indicators
    - Attribution: Identify techniques used by specific threat actors

    Args:
        hash_value: The file hash (SHA256 preferred) to query.
        sandbox: Optional specific sandbox name (e.g., 'VirusTotal Jujubox', 'C2AE').
            If not specified, returns the default/first available report.

    Returns:
        JSON string containing detailed behavioral analysis (up to 50 reports) including:
        - Processes created and their relationships
        - Network activity (DNS, HTTP, TCP/IP)
        - File system operations
        - Registry operations
        - MITRE ATT&CK techniques
        - Behavioral signatures
        - Sandbox metadata (environment, time)

    Examples:
        hash_value="275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
        hash_value="44d88612fea8a8f36de82e1278abb02f", sandbox="VirusTotal Jujubox"

    Notes:
        - Requires a valid VirusTotal API key (PURPLEMCP_VT_API_KEY environment variable)
        - Only SHA256 hashes are supported for behavior reports
        - Returns up to 50 behavior reports
        - Not all files have behavioral analysis (requires sandbox execution)
        - Multiple sandbox environments may have analyzed the same file
        - Reports reflect behavior in a controlled sandbox environment
        - Private API keys have access to more detailed reports
        - When no behavior report is found, returns a structured JSON response with found=false
        - IMPORTANT: Do NOT call this tool repeatedly with the same parameters.
          It returns the same data each time, not additional results.

    Raises:
        ThreatIntelligenceClientError: If there's an error communicating with the API.
        RuntimeError: If the API key is not configured.
    """
).strip()


async def threat_intel_by_domain(domain: str) -> str:
    """Get threat intelligence for a domain from VirusTotal/Google Threat Intelligence.

    Args:
        domain: The domain name to query.

    Returns:
        Threat intelligence as a JSON string. If the domain is not found, returns
        a structured response: {"found": false, "resource": "...", "message": "..."}

    Raises:
        RuntimeError: If the API key is not configured.
        ThreatIntelligenceClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_domain_threat_intel(domain)


async def threat_intel_by_ip(ip_address: str) -> str:
    """Get threat intelligence for an IP address from VirusTotal/Google Threat Intelligence.

    Args:
        ip_address: The IP address to query.

    Returns:
        Threat intelligence as a JSON string. If the IP is not found, returns
        a structured response: {"found": false, "resource": "...", "message": "..."}

    Raises:
        RuntimeError: If the API key is not configured.
        ThreatIntelligenceClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_ip_threat_intel(ip_address)


async def threat_intel_get_file_relationships(hash_value: str, relationship_type: str) -> str:
    """Get relationships for a file hash (network IOCs and related files).

    Args:
        hash_value: The file hash to query.
        relationship_type: Type of relationship (e.g., 'contacted_domains', 'contacted_ips').

    Returns:
        Relationship data as a JSON string (up to 100 relationships). If the hash or
        relationship is not found, returns a structured response:
        {"found": false, "resource": "...", "message": "..."}

    Raises:
        RuntimeError: If the API key is not configured.
        ThreatIntelligenceClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_file_relationships(hash_value, relationship_type)


async def threat_intel_search(query: str) -> str:
    """Search VirusTotal Intelligence with advanced queries for threat hunting.

    Args:
        query: VT Intelligence search query.

    Returns:
        Search results as a JSON string (up to 10 results).

    Raises:
        RuntimeError: If the API key is not configured.
        ThreatIntelligenceClientError: If there's an error communicating with the API.
    """
    return await _get_client().search_intelligence(query)


async def threat_intel_get_file_behavior(hash_value: str, sandbox: str | None = None) -> str:
    """Get behavioral analysis report for a file from VirusTotal sandboxes.

    Args:
        hash_value: The file hash (SHA256 preferred) to query.
        sandbox: Optional specific sandbox name.

    Returns:
        Behavioral analysis data as a JSON string (up to 50 reports). If no behavior
        report is found, returns a structured response:
        {"found": false, "resource": "...", "message": "..."}

    Raises:
        RuntimeError: If the API key is not configured.
        ThreatIntelligenceClientError: If there's an error communicating with the API.
    """
    return await _get_client().get_file_behavior(hash_value, sandbox)
