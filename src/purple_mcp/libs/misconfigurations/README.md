# Misconfigurations Library

A standalone Python library for interacting with the SentinelOne Security Posture Management (XSPM) Misconfigurations GraphQL API.

## Overview

This library provides a typed, async interface to the XSPM Misconfigurations API, handling schema compatibility and providing robust error handling. It's designed to be completely independent and can be used outside of the MCP context.

> **📖 Read-Only Library**: This library provides read-only access to the misconfigurations management system. It supports retrieving misconfigurations, notes, and history, but does not include any data modification operations.

## Installation

```bash
pip install purple-mcp
```

## Quick Start

```python
import asyncio
from purple_mcp.libs.misconfigurations import MisconfigurationsClient, MisconfigurationsConfig

async def main():
    config = MisconfigurationsConfig(
        graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
        auth_token="your-bearer-token"
    )

    client = MisconfigurationsClient(config)

    # Get a specific misconfiguration
    misconfiguration = await client.get_misconfiguration(misconfiguration_id="123")
    if misconfiguration:
        print(f"Misconfiguration: {misconfiguration.name} - Severity: {misconfiguration.severity}")

    # List recent misconfigurations
    misconfigurations = await client.list_misconfigurations(first=10)
    print(f"Found {len(misconfigurations.edges)} misconfigurations")

asyncio.run(main())
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage examples and patterns
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Filter Reference](docs/FILTERS.md)** - Detailed filter format and examples
- **[Configuration](docs/CONFIG.md)** - Configuration options and schema compatibility

## Key Features

- **Read-Only Design**: Safe, read-only access to misconfigurations data
- **Typed Interface**: Full type safety with pydantic models (70+ models)
- **Schema Compatibility**: Automatic handling of different XSPM API versions
- **Pagination Support**: Built-in cursor-based pagination
- **Error Handling**: Comprehensive exception hierarchy
- **Filtering**: Rich filter system for complex queries with DoS protection
- **Notes Retrieval**: Full support for reading existing misconfiguration notes
- **History**: Full support for misconfiguration audit trails

## Configuration Requirements

```python
config = MisconfigurationsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
    auth_token="your-bearer-token",
    timeout=30.0  # Optional
)
```

## Filter System

The library includes built-in DoS protection for filters:
- Maximum 50 filters per request
- Maximum 100 values per filter

```python
# Search for high-severity open misconfigurations
filters = [
    {"fieldId": "severity", "filterType": "string_equals", "value": "HIGH"},
    {"fieldId": "status", "filterType": "string_equals", "value": "OPEN"}
]
misconfigurations = await client.search_misconfigurations(filters=filters, first=10)
```

## Available Methods

- `get_misconfiguration(misconfiguration_id: str)` - Retrieve a specific misconfiguration by ID
- `list_misconfigurations(first: int = 10, after: str | None = None, view_type: str = "ALL")` - List recent misconfigurations
- `search_misconfigurations(filters: list[FilterInput] | None = None, first: int = 10, after: str | None = None, view_type: str = "ALL")` - Search with filters
- `get_misconfiguration_notes(misconfiguration_id: str)` - Get notes for a misconfiguration
- `get_misconfiguration_history(misconfiguration_id: str, first: int = 10, after: str | None = None)` - View misconfiguration activity history

## Contributing

This library follows the purple-mcp project's contribution guidelines. See the main project's CONTRIBUTING.md for details.
