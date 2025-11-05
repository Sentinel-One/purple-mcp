# Usage Guide

Comprehensive usage examples and patterns for the Misconfigurations library.

> **📖 Read-Only Library**: This library provides read-only access to the XSPM Misconfigurations GraphQL API. All examples show data retrieval and analysis operations.

## Basic Operations

### Getting Started

```python
import asyncio

from purple_mcp.libs.misconfigurations import (
    MisconfigurationsClient,
    MisconfigurationsConfig,
)


async def main() -> None:
    config = MisconfigurationsConfig(
        graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/misconfigurations/graphql",
        auth_token="your-bearer-token",
    )

    client = MisconfigurationsClient(config)

    # Your misconfiguration operations here


asyncio.run(main())
```

### Retrieving Misconfigurations

```python
async def get_misconfiguration_details(
    client: MisconfigurationsClient, misconfiguration_id: str
) -> None:
    misconfiguration = await client.get_misconfiguration(misconfiguration_id)
    if not misconfiguration:
        print("Misconfiguration not found")
        return

    print(f"Name: {misconfiguration.name}")
    print(f"Severity: {misconfiguration.severity}")
    print(f"Status: {misconfiguration.status}")
    if misconfiguration.asset:
        print(f"Asset: {misconfiguration.asset.name} ({misconfiguration.asset.type})")
```

### Listing Recent Misconfigurations

```python
async def list_recent_misconfigurations(client: MisconfigurationsClient) -> None:
    connection = await client.list_misconfigurations(first=10)

    print(f"Fetched {len(connection.edges)} misconfigurations")
    for edge in connection.edges:
        misc = edge.node
        print(f"- {misc.name} ({misc.severity})")
```

## Searching with Filters

The library exposes strongly-typed filter helpers. Instantiate `FilterInput` objects using the field you want to query and the appropriate value wrapper.

```python
from purple_mcp.libs.misconfigurations.models import (
    EqualFilterStringInput,
    FilterInput,
)


async def search_high_severity_misconfigurations(
    client: MisconfigurationsClient,
) -> list[str]:
    filters = [
        FilterInput(
            field_id="severity",
            string_equal=EqualFilterStringInput(value="HIGH"),
        )
    ]

    results = await client.search_misconfigurations(filters=filters, first=10)
    return [edge.node.id for edge in results.edges]
```

You can combine multiple filters:

```python
async def search_open_critical_misconfigurations(
    client: MisconfigurationsClient,
) -> list[str]:
    filters = [
        FilterInput(
            field_id="severity",
            string_equal=EqualFilterStringInput(value="CRITICAL"),
        ),
        FilterInput(
            field_id="status",
            string_equal=EqualFilterStringInput(value="OPEN"),
        ),
    ]

    results = await client.search_misconfigurations(filters=filters, first=20)
    return [edge.node.id for edge in results.edges]
```

## Dynamic Field Selection

Misconfigurations queries support custom field selection so you can reduce payload size.

### Available Fields

Key scalar fields:
- `id`, `externalId`, `name`, `severity`, `status`, `environment`
- `detectedAt`, `eventTime`, `lastSeenAt`
- `product`, `vendor`, `organization`
- `analystVerdict`, `misconfigurationType`, `mitigable`, `exposureReason`

Nested fragments (pass the simple name to receive all subfields):
- `asset` &rarr; Includes identifiers plus cloud/kubernetes metadata
- `scope` &rarr; Account, site, and group hierarchy
- `assignee` &rarr; `id`, `email`, `fullName`
- `cnapp`, `evidence`, `remediation`, `admissionRequest`, `mitreAttacks`

Custom fragments support arbitrary nesting depth. For example:
```python
fields = [
    "id",
    "severity",
    "asset { id name cloudInfo { accountId region } }",
    "scope { account { id name } site { id name } }",
]
```

### Examples

```python
# Minimal fields for pagination
connection = await client.list_misconfigurations(first=50, fields=["id"])

# Tailored selection for dashboard views
summary_fields = [
    "id",
    "name",
    "severity",
    "status",
    "environment",
    "assignee",
]
connection = await client.search_misconfigurations(
    filters=filters,
    first=25,
    fields=summary_fields,
)
```

> **Note:** When you request a subset of fields, unspecified attributes will be `None` in the resulting Pydantic models.

## Pagination Patterns

```python
async def paginate_all_misconfigurations(
    client: MisconfigurationsClient,
) -> list[str]:
    cursor = None
    ids: list[str] = []

    while True:
        connection = await client.list_misconfigurations(
            first=100,
            after=cursor,
            fields=["id"],  # minimal payload while paging
        )

        ids.extend(edge.node.id for edge in connection.edges)
        if not connection.page_info.has_next_page:
            break

        cursor = connection.page_info.end_cursor

    return ids
```

## Advanced Analysis Examples

### Severity Distribution

```python
async def analyze_by_severity(client: MisconfigurationsClient) -> dict[str, int]:
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    breakdown: dict[str, int] = {}

    for severity in severities:
        filters = [
            FilterInput(
                field_id="severity",
                string_equal=EqualFilterStringInput(value=severity),
            )
        ]

        connection = await client.search_misconfigurations(
            filters=filters,
            first=50,
            fields=["id"],
        )
        breakdown[severity] = len(connection.edges)

    return breakdown
```

### Compliance Overview

```python
async def analyze_compliance_violations(
    client: MisconfigurationsClient,
) -> dict[str, int]:
    filters = [
        FilterInput(
            field_id="status",
            string_equal=EqualFilterStringInput(value="OPEN"),
        )
    ]

    cursor = None
    frameworks: dict[str, int] = {}

    while True:
        connection = await client.search_misconfigurations(
            filters=filters,
            first=50,
            after=cursor,
            fields=["id", "complianceStandards"],
        )

        for edge in connection.edges:
            misc = edge.node
            for standard in misc.compliance_standards or []:
                frameworks[standard] = frameworks.get(standard, 0) + 1

        if not connection.page_info.has_next_page:
            break
        cursor = connection.page_info.end_cursor

    return frameworks
```

## Error Handling

```python
from purple_mcp.libs.misconfigurations.exceptions import (
    MisconfigurationsClientError,
    MisconfigurationsConfigError,
    MisconfigurationsGraphQLError,
)


async def safe_get_misconfiguration(
    client: MisconfigurationsClient, misconfiguration_id: str
) -> None:
    try:
        misc = await client.get_misconfiguration(misconfiguration_id)
        if misc:
            print(misc.name)
    except MisconfigurationsConfigError as exc:
        print(f"Configuration error: {exc}")
    except MisconfigurationsClientError as exc:
        print(f"Network error: {exc} (status={exc.status_code})")
    except MisconfigurationsGraphQLError as exc:
        print(f"GraphQL error: {exc}")
```

## Testing Helpers

```python
from unittest.mock import AsyncMock, patch

from purple_mcp.libs.misconfigurations import (
    MisconfigurationsClient,
    MisconfigurationsConfig,
)


async def test_get_misconfiguration() -> None:
    config = MisconfigurationsConfig(
        graphql_url="https://test.example.com/graphql",
        auth_token="test-token",
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = {
            "data": {
                "misconfiguration": {
                    "id": "123",
                    "name": "Test Misconfiguration",
                    "severity": "HIGH",
                    "status": "OPEN",
                }
            }
        }

        client = MisconfigurationsClient(config)
        misc = await client.get_misconfiguration("123")

        assert misc is not None
        assert misc.id == "123"
        assert misc.name == "Test Misconfiguration"
```
