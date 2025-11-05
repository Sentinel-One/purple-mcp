# Usage Guide

Comprehensive usage examples and patterns for the Vulnerabilities library.

> **📖 Read-Only Library**: This library provides read-only access to the XSPM Vulnerabilities GraphQL API.

## Basic Operations

### Getting Started

```python
import asyncio

from purple_mcp.libs.vulnerabilities import (
    VulnerabilitiesClient,
    VulnerabilitiesConfig,
)


async def main() -> None:
    config = VulnerabilitiesConfig(
        graphql_url="https://console.example.com/web/api/v2.1/xspm/findings/vulnerabilities/graphql",
        auth_token="your-bearer-token",
    )

    client = VulnerabilitiesClient(config)
    # Your vulnerability operations here


asyncio.run(main())
```

### Retrieving a Vulnerability

```python
async def get_vulnerability_details(
    client: VulnerabilitiesClient, vulnerability_id: str
) -> None:
    vulnerability = await client.get_vulnerability(vulnerability_id)
    if not vulnerability:
        print("Vulnerability not found")
        return

    print(f"Name: {vulnerability.name}")
    print(f"Severity: {vulnerability.severity}")
    if vulnerability.cve:
        print(f"CVE: {vulnerability.cve.id}")
```

### Listing Recent Vulnerabilities

```python
async def list_recent_vulnerabilities(client: VulnerabilitiesClient) -> None:
    connection = await client.list_vulnerabilities(first=10)
    print(f"Found {len(connection.edges)} vulnerabilities")

    for edge in connection.edges:
        vuln = edge.node
        print(f"- {vuln.name} ({vuln.severity})")
```

## Searching with Filters

```python
from purple_mcp.libs.vulnerabilities.models import (
    EqualFilterStringInput,
    FilterInput,
)


async def search_critical_vulnerabilities(
    client: VulnerabilitiesClient,
) -> list[str]:
    filters = [
        FilterInput(
            field_id="severity",
            string_equal=EqualFilterStringInput(value="CRITICAL"),
        )
    ]

    results = await client.search_vulnerabilities(filters=filters, first=25)
    return [edge.node.id for edge in results.edges]
```

Combine multiple filters as needed:

```python
async def search_open_high_vulnerabilities(
    client: VulnerabilitiesClient,
) -> list[str]:
    filters = [
        FilterInput(
            field_id="severity",
            string_equal=EqualFilterStringInput(value="HIGH"),
        ),
        FilterInput(
            field_id="status",
            string_equal=EqualFilterStringInput(value="OPEN"),
        ),
    ]

    results = await client.search_vulnerabilities(filters=filters, first=50)
    return [edge.node.id for edge in results.edges]
```

## Dynamic Field Selection

Vulnerability queries also support custom field selection.

### Available Fields

Core scalars:
- `id`, `name`, `severity`, `status`
- `detectedAt`, `lastSeenAt`, `product`, `vendor`
- `analystVerdict`, `exclusionPolicyId`

Nested fragments:
- `asset` &rarr; Asset identifiers plus cloud/kubernetes metadata
- `scope` &rarr; Account/site/group hierarchy
- `cve` &rarr; CVE metadata, scores, maturity, timeline
- `software` &rarr; Installed software information
- `assignee` &rarr; `id`, `email`, `fullName`

You can use custom fragments with deeper nesting, e.g. `"cve { id riskScore epssScore }"` or `"asset { cloudInfo { accountId region } }"`.

### Examples

```python
# Minimal payload while paging
connection = await client.list_vulnerabilities(first=100, fields=["id"])

# Detailed view for dashboards
dashboard_fields = [
    "id",
    "name",
    "severity",
    "status",
    "detectedAt",
    "asset { id name type }",
    "cve { id riskScore exploitMaturity }",
]
connection = await client.search_vulnerabilities(
    filters=filters,
    first=25,
    fields=dashboard_fields,
)
```

> **Tip:** When you request only a subset of fields, unspecified attributes will be `None` on the resulting `Vulnerability` objects.

## Pagination Patterns

```python
async def paginate_vulnerabilities(client: VulnerabilitiesClient) -> list[str]:
    cursor = None
    ids: list[str] = []

    while True:
        connection = await client.list_vulnerabilities(
            first=100,
            after=cursor,
            fields=["id"],
        )

        ids.extend(edge.node.id for edge in connection.edges)
        if not connection.page_info.has_next_page:
            break

        cursor = connection.page_info.end_cursor

    return ids
```

## Analytical Examples

### Group by CVE

```python
async def group_vulnerabilities_by_cve(
    client: VulnerabilitiesClient,
) -> dict[str, int]:
    cursor = None
    counts: dict[str, int] = {}

    while True:
        connection = await client.list_vulnerabilities(
            first=50,
            after=cursor,
            fields=["id", "cve { id }"],
        )

        for edge in connection.edges:
            vuln = edge.node
            if vuln.cve and vuln.cve.id:
                counts[vuln.cve.id] = counts.get(vuln.cve.id, 0) + 1

        if not connection.page_info.has_next_page:
            break
        cursor = connection.page_info.end_cursor

    return counts
```

### High-Risk Findings

```python
async def find_high_risk_vulnerabilities(
    client: VulnerabilitiesClient,
) -> list[tuple[str, float]]:
    filters = [
        FilterInput(
            field_id="severity",
            string_equal=EqualFilterStringInput(value="CRITICAL"),
        )
    ]

    results = await client.search_vulnerabilities(
        filters=filters,
        first=100,
        fields=["id", "name", "cve { id riskScore }"],
    )

    high_risk: list[tuple[str, float]] = []
    for edge in results.edges:
        vuln = edge.node
        if vuln.cve and vuln.cve.risk_score:
            high_risk.append((vuln.name or vuln.id, vuln.cve.risk_score))

    return sorted(high_risk, key=lambda item: item[1], reverse=True)
```

## Error Handling

```python
from purple_mcp.libs.vulnerabilities.exceptions import (
    VulnerabilitiesClientError,
    VulnerabilitiesGraphQLError,
)


async def safe_get_vulnerability(
    client: VulnerabilitiesClient, vulnerability_id: str
) -> None:
    try:
        vuln = await client.get_vulnerability(vulnerability_id)
        if vuln:
            print(vuln.name)
    except VulnerabilitiesClientError as exc:
        print(f"Network error: {exc} (status={exc.status_code})")
    except VulnerabilitiesGraphQLError as exc:
        print(f"GraphQL error: {exc}")
```

## Testing Helpers

```python
from unittest.mock import AsyncMock, patch

from purple_mcp.libs.vulnerabilities import (
    VulnerabilitiesClient,
    VulnerabilitiesConfig,
)


async def test_get_vulnerability() -> None:
    config = VulnerabilitiesConfig(
        graphql_url="https://test.example.com/graphql",
        auth_token="test-token",
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = {
            "data": {
                "vulnerability": {
                    "id": "123",
                    "name": "Test Vulnerability",
                    "severity": "HIGH",
                    "status": "OPEN",
                }
            }
        }

        client = VulnerabilitiesClient(config)
        vuln = await client.get_vulnerability("123")

        assert vuln is not None
        assert vuln.id == "123"
        assert vuln.name == "Test Vulnerability"
```
