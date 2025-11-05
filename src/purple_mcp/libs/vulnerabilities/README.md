# Vulnerabilities Library

A standalone Python library for interacting with the SentinelOne Security Posture Management (XSPM) Vulnerabilities GraphQL API.

## Overview

This library provides a typed, async interface to the XSPM Vulnerabilities API, handling schema compatibility and providing robust error handling. It's designed to be completely independent and can be used outside of the MCP context.

> **📖 Read-Only Library**: This library provides read-only access to the vulnerabilities management system. It supports retrieving vulnerabilities, notes, and history, but does not include any data modification operations.

## Installation

```bash
pip install purple-mcp
```

## Quick Start

```python
import asyncio
from purple_mcp.libs.vulnerabilities import VulnerabilitiesClient, VulnerabilitiesConfig

async def main():
    config = VulnerabilitiesConfig(
        graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
        auth_token="your-bearer-token"
    )

    client = VulnerabilitiesClient(config)

    # Get a specific vulnerability
    vulnerability = await client.get_vulnerability(vulnerability_id="123")
    if vulnerability:
        print(f"Vulnerability: {vulnerability.name} - Severity: {vulnerability.severity}")

    # List recent vulnerabilities
    vulnerabilities = await client.list_vulnerabilities(first=10)
    print(f"Found {len(vulnerabilities.edges)} vulnerabilities")

asyncio.run(main())
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage examples and patterns
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Filter Reference](docs/FILTERS.md)** - Detailed filter format and examples
- **[Configuration](docs/CONFIG.md)** - Configuration options and schema compatibility

## Key Features

- **Read-Only Design**: Safe, read-only access to vulnerabilities data
- **Typed Interface**: Full type safety with pydantic models (70+ models)
- **Schema Compatibility**: Automatic handling of different XSPM API versions
- **Pagination Support**: Built-in cursor-based pagination
- **Error Handling**: Comprehensive exception hierarchy
- **Filtering**: Rich filter system for complex queries with DoS protection
- **Notes Retrieval**: Full support for reading existing vulnerability notes
- **History**: Full support for vulnerability audit trails

## Configuration Requirements

```python
config = VulnerabilitiesConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
    auth_token="your-bearer-token",
    timeout=30.0  # Optional
)
```

## Filter System

The library includes built-in DoS protection for filters:
- Maximum 50 filters per request
- Maximum 100 values per filter

```python
# Search for critical open vulnerabilities
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "CRITICAL"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
vulnerabilities = await client.search_vulnerabilities(filters=filters, first=10)
```

## Available Methods

- `get_vulnerability(vulnerability_id: str)` - Retrieve a specific vulnerability by ID
- `list_vulnerabilities(first: int = 10, after: str | None = None)` - List recent vulnerabilities
- `search_vulnerabilities(filters: list[FilterInput] | None = None, first: int = 10, after: str | None = None)` - Search with filters
- `get_vulnerability_notes(vulnerability_id: str)` - Get notes for a vulnerability
- `get_vulnerability_history(vulnerability_id: str, first: int = 10, after: str | None = None)` - View vulnerability activity history

## Contributing

This library follows the purple-mcp project's contribution guidelines. See the main project's CONTRIBUTING.md for details.
