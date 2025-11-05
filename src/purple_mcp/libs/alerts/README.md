# Alerts Library

A standalone Python library for interacting with the Unified Alerts Management (UAM) GraphQL API.

## Overview

This library provides a typed, async interface to UAM, handling schema compatibility and providing robust error handling. It's designed to be completely independent and can be used outside of the MCP context.

> **📖 Read-Only Library**: This library provides read-only access to the Unified Alerts Management system. It supports retrieving alerts, notes, and history, but does not include any data modification operations.

## Installation

```bash
pip install purple-mcp
```

## Quick Start

> **Note**: This library is designed for read-only operations and works consistently across all usage contexts.

```python
import asyncio
from purple_mcp.libs.alerts import AlertsClient, AlertsConfig

async def main():
    config = AlertsConfig(
        graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
        auth_token="your-bearer-token"
    )
    
    client = AlertsClient(config)
    
    # Get a specific alert
    alert = await client.get_alert(alert_id="123")
    if alert:
        print(f"Alert: {alert.name} - Severity: {alert.severity}")
    
    # List recent alerts
    alerts = await client.list_alerts(first=10)
    print(f"Found {len(alerts.edges)} alerts")

asyncio.run(main())
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage examples and patterns
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Filter Reference](docs/FILTERS.md)** - Detailed filter format and examples
- **[Configuration](docs/CONFIG.md)** - Configuration options and schema compatibility

## Key Features

- **Read-Only Design**: Safe, read-only access to alerts data
- **Typed Interface**: Full type safety with pydantic models
- **Schema Compatibility**: Automatic handling of different UAM versions
- **Pagination Support**: Built-in cursor-based pagination
- **Error Handling**: Comprehensive exception hierarchy
- **Filtering**: Rich filter system for complex queries
- **Notes Retrieval**: Full support for reading existing alert notes
- **History**: Full support for alert audit trails

## Configuration Requirements

```python
config = AlertsConfig(
    graphql_url="https://console.example.com/web/api/v2.1/unifiedalerts/graphql",
    auth_token="your-bearer-token",
    timeout=30.0  # Optional
)
```

## Contributing

This library follows the purple-mcp project's contribution guidelines. See the main project's CONTRIBUTING.md for details.