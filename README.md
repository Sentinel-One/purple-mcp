<picture>
  <source media="(prefers-color-scheme: dark)" type="image/svg+xml" srcset="https://www.sentinelone.com/wp-content/themes/sentinelone/assets/svg/header-logo-light.svg">
  <source media="(prefers-color-scheme: light)" type="image/svg+xml" srcset="https://www.sentinelone.com/wp-content/themes/sentinelone/assets/svg/header-logo-dark.svg">
  <img alt="SentinelOne" src="https://www.sentinelone.com/wp-content/themes/sentinelone/assets/svg/header-logo-light.svg">
</picture>

# Purple AI MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Purple AI MCP Server allows you to access SentinelOne Services with any MCP client.

## Features

This server exposes SentinelOne's platform through the Model Context Protocol:

- **Purple AI**: Ask security questions, investigate threats
- **Events**: Run PowerQueries on events in your SentinelOne data lake
- **Alerts**: Query, search, and investigate alerts
- **Vulnerabilities**: Track CVEs and security findings
- **Misconfigurations**: Analyze security posture issues
- **Inventory**: Ask questions about endpoints, cloud resources, identities, and network devices
- **CVE Search**: Query public CVE databases for vulnerability details
- **Threat Intelligence**: Get file, URL, domain, and IP analysis from VirusTotal

Purple AI MCP is a read-only service - you cannot make changes to your account or any objects
within your account from this MCP.

## Quick Start

### Using uv (Recommended for Local Development or Deployment)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set credentials
export PURPLEMCP_CONSOLE_TOKEN="your_token"
export PURPLEMCP_CONSOLE_BASE_URL="https://your-console.sentinelone.net"

# Run
uvx --from git+https://github.com/Sentinel-One/purple-mcp.git purple-mcp --mode=stdio
```

#### ⚠️ Security note ⚠️

For production or security-sensitive environments, pin to a specific commit hash instead of using
the default branch to reduce supply chain risk from the our
[releases](https://github.com/Sentinel-One/purple-mcp/releases) or our verified commits in
[main](https://github.com/Sentinel-One/purple-mcp/commits/main) branch.

```bash
# Run with pinned hash
uvx --from git+https://github.com/Sentinel-One/purple-mcp.git@<commit-hash> purple-mcp --mode=stdio
```

### Using Docker

Follow instructions for Docker Deployment [here](deploy/README.md#using-docker)

### Using Amazon Bedrock AgentCore

Follow instructions for Amazon Bedrock AgentCore Deployment
[here](deploy/README.md#using-amazon-bedrock-agentcore)

### Using Amazon Elastic Container Service (ECS)

Follow instructions for Amazon Elastic Container Service Deployment
[here](deploy/README.md#using-amazon-elastic-container-service-ecs)

### Using a Cloud Provider

For cloud deployments, see [Deployment Guide](deploy/cloud/CLOUD_SETUP.md).

**Note:** Purple AI MCP does not include built-in authentication. For network-exposed deployments,
place it behind a reverse proxy or load balancer. See [cloud Setup](deploy/cloud/CLOUD_SETUP.md)
for cloud load balancer configurations (AWS ALB, GCP Cloud Load Balancing, Azure Application
Gateway) or nginx examples for self-hosted deployments.

---

Your token needs Account or Site level permissions (not Global). Get one from Policy & Settings →
User Management → Service Users in your console. Currently, this server only supports tokens that
have access to a single Account or Site. If you need to access multiple sites, you will need to run
multiple MCP servers with Account-specific or Site-specific tokens.

## Authentication

Purple MCP uses a SentinelOne Console token configured at startup via environment variables. The
server authenticates with your SentinelOne Console using the provided token and base URL.

```bash
# Configure authentication credentials
PURPLEMCP_CONSOLE_TOKEN=YOUR_CONSOLE_TOKEN
PURPLEMCP_CONSOLE_BASE_URL=https://console.sentinelone.net
```

In addition you may define a console scope for Purple AI query operations:

```bash
PURPLEMCP_PURPLE_AI_CONSOLE_ACCOUNT_ID=1234567890123456789
```

This will scope Purple AI queries to account-scope with id `1234567890123456789`.

**Health Check Endpoints:**

The following endpoints bypass authentication to support container orchestration systems
(Kubernetes, Docker, etc.):

- `/health`, `/ready`, `/ping`

These endpoints return only basic status (`{"status": "ok"}`) and do not expose sensitive
information. See [SECURITY.md](SECURITY.md) for details.

## Clients

Purple AI MCP supports `stdio`, `sse`, and `streamable-http` protocols and should work in any
client that supports MCP. Some sample configurations are listed below.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%/Claude/claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "purple-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Sentinel-One/purple-mcp.git",
        "purple-mcp",
        "--mode",
        "stdio"
      ],
      "env": {
        "PURPLEMCP_CONSOLE_TOKEN": "your_token",
        "PURPLEMCP_CONSOLE_BASE_URL": "https://your-console.sentinelone.net"
      }
    }
  }
}
```

### Claude Code

Run this command in a terminal:

`claude mcp add --transport stdio purple-mcp --env PURPLEMCP_CONSOLE_TOKEN=your_token --env PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net -- uvx --from git+https://github.com/Sentinel-One/purple-mcp.git purple-mcp --mode stdio`

### OpenAI Codex

Run this command in a terminal:

`codex mcp add purple-mcp  --env PURPLEMCP_CONSOLE_TOKEN=your_token --env PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net -- uvx --from git+https://github.com/Sentinel-One/purple-mcp.git purple-mcp --mode stdio`

### Pydantic AI

Here is some example Python code to use Purple MCP with a Pydantic AI Agent.

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio(
    'uvx', args=["--from", "git+https://github.com/Sentinel-One/purple-mcp.git", "purple-mcp", "--mode", "stdio"], timeout=10
)
agent = Agent('anthropic:claude-haiku-4-5', toolsets=[server])
```

### Zed

Edit `~/.zed/mcp.json`:

```json
{
  "mcpServers": {
    "purple-mcp": {
      "enabled": true,
      "source": "custom",
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Sentinel-One/purple-mcp.git",
        "purple-mcp",
        "--mode",
        "stdio"
      ],
      "env": {
        "PURPLEMCP_CONSOLE_TOKEN": "your_token",
        "PURPLEMCP_CONSOLE_BASE_URL": "https://your-console.sentinelone.net"
      }
    }
  }
}
```

### Other Clients

For debugging or to host server for multiple clients, run in streamable-http mode and connect via
mcp-remote:

```bash
# Terminal 1: Start server
export PURPLEMCP_CONSOLE_TOKEN="your_token"
export PURPLEMCP_CONSOLE_BASE_URL="https://your-console.sentinelone.net"
uvx --from git+https://github.com/Sentinel-One/purple-mcp.git purple-mcp --mode streamable-http --host localhost --port 8000

# Terminal 2: Connect with any client
npx -y mcp-remote http://127.0.0.1:8000/mcp
```

We suggest you **do not** expose Purple AI MCP on a network at this time, as there is no
authentication enforced and anyone could access a configured SentinelOne account.

## Available Tools

### Purple AI

- `purple_ai(query)` - Ask security questions

### Data Lake

- `powerquery(query, start_time, end_time)` - Run PowerQuery analytics

### Alerts

- `get_alert(alert_id)` - Get alert details
- `list_alerts(first, after, view_type)` - List recent alerts
- `search_alerts(filters, first)` - Search with filters
- `get_alert_notes(alert_id)` - Get alert comments
- `get_alert_history(alert_id)` - View alert timeline

### Vulnerabilities

- `get_vulnerability(id)` - Get vulnerability details
- `list_vulnerabilities(first, after)` - List recent vulnerabilities
- `search_vulnerabilities(filters, first)` - Search CVEs and findings
- `get_vulnerability_notes(id)` - Get comments
- `get_vulnerability_history(id)` - View timeline

### Misconfigurations

- `get_misconfiguration(id)` - Get misconfiguration details
- `list_misconfigurations(first, after)` - List recent issues
- `search_misconfigurations(filters, first)` - Search by criteria
- `get_misconfiguration_notes(id)` - Get comments
- `get_misconfiguration_history(id)` - View timeline

### Asset Inventory

- `get_inventory_item(item_id, fetch_fields)` - Get asset details with field filtering
- `list_inventory_items(limit, skip, surface, fetch_fields)` - List assets by surface type
- `search_inventory_items(filters, limit, skip, fetch_fields)` - Search with advanced filters

**Field Filtering:** All inventory tools support `fetch_fields` parameter to control returned data:

- Presets: `MINIMAL` (7 fields), `STANDARD` (13 fields), `ALL` (~200+ fields)
- Custom lists: Specify exact fields in camelCase, e.g., `["id", "name", "resourceType"]`
- Use `get_inventory_item(item_id, fetch_fields="ALL")` on a single item to discover available
  field names

### CVE Search (External)

Query public CVE databases (cve-search.org) for vulnerability information:

- `cve_search_by_id(cve_id)` - Get detailed CVE information by ID
- `cve_search_by_vendor(vendor, product)` - Search CVEs by vendor/product
- `cve_database_status()` - Get database update information

**Note:** No API key required. Data sourced from CIRCL.LU's cve-search.org.

### Threat Intelligence (External)

Query VirusTotal/Google Threat Intelligence for file, URL, domain, and IP analysis:

- `threat_intel_by_hash(hash_value)` - Get threat intel for file hash (MD5/SHA1/SHA256)
- `threat_intel_by_url(url)` - Get URL reputation and analysis
- `threat_intel_by_domain(domain)` - Get domain threat intelligence
- `threat_intel_by_ip(ip_address)` - Get IP address threat intelligence
- `threat_intel_get_file_relationships(hash_value, relationship_type)` - Get file relationships
  (contacted domains/IPs, similar files)
- `threat_intel_search(query)` - Search VirusTotal Intelligence (Premium API required)
- `threat_intel_get_file_behavior(hash_value, sandbox)` - Get sandbox behavioral analysis

**Note:** Requires `PURPLEMCP_VT_API_KEY` environment variable with a valid VirusTotal API key.

## Environment Variables

### Required

- `PURPLEMCP_CONSOLE_TOKEN` - Authentication token (Service User token or Console API token)
- `PURPLEMCP_CONSOLE_BASE_URL` - Console URL (e.g., https://console.sentinelone.net)

### Optional

- `PURPLEMCP_SDL_BASE_URL` - Dedicated base URL for the SDL API
  - When set, this URL is used directly instead of `PURPLEMCP_CONSOLE_BASE_URL` + `/sdl`
  - Example: `https://your-dedicated-sdl-endpoint.sentinelone.net`
  - When not set, the SDL API is accessed at `{PURPLEMCP_CONSOLE_BASE_URL}/sdl` (default behavior)
- `PURPLEMCP_VT_API_KEY` - VirusTotal API key for threat intelligence tools (get one from
  https://www.virustotal.com/gui/my-apikey)
- `PURPLEMCP_SDL_CONSOLE_ACCOUNT_IDS` - Account IDs for SDL query scoping (comma-separated or JSON
  array)
  - When specified: queries are scoped to the provided account(s)
  - When not specified: queries all accounts accessible to the token
  - Example: `"426418030212073761"` or `"123,456,789"` or `["123", "456"]`
- `PURPLEMCP_SDL_CONSOLE_SITE_IDS` - Site IDs for SDL query scoping
  - When specified: queries are scoped to the provided site
  - Requires `PURPLEMCP_SDL_CONSOLE_ACCOUNT_IDS` to also be set with exactly one account ID
  - Example: `"1234567890123456789"` or `"123,456,789"` or `"[123, 456]"`
  - **Note:** Currently, only the first site ID is used.
- `PURPLEMCP_TRANSPORT_MODE` - MCP transport mode: `stdio`, `http`, `streamable-http`, or `sse`
  (default: `stdio`)
- `PURPLEMCP_STATELESS_HTTP` - Enable stateless HTTP mode for serverless deployments (e.g., Amazon
  Bedrock AgentCore) - see [deployment guide](deploy/aws_agentcore/BEDROCK_AGENTCORE_DEPLOYMENT.md)

## Development

We welcome your pull requests or issue submissions.

### Setup

```bash
# Install all dependencies
uv sync --all-groups

# Format and lint
uv run ruff format
uv run ruff check .
uv run mypy src tests
```

### Testing

```bash
# Run unit tests
uv run pytest tests/unit/ -v

# Run integration tests (requires .env.test with real credentials)
uv run pytest tests/integration/ -v

# All tests with coverage
uv run pytest --cov=src/purple_mcp --cov-report=html
```

### Env-vars for integration-testing of Account Scopes

There are some integration tests that require additional configuration to run (if left unconfigured
they will be skipped). If you want to run
[test_sdl_scope_integration.py](tests/integration/test_sdl_scope_integration.py) you will need to
define the following env-vars in your `.env.test` file (with the dummy values replaced for your
test scenario):

    # An accessible account for your console token:
    PURPLEMCP_SDL_CONSOLE_ACCOUNT_IDS=123456789012345678
    # Another account from your console
    PURPLEMCP_SDL_INT_TEST_SECOND_ACCOUNT_ID=222333444555666
    # An Agent UUID accessible in your primary account:
    PURPLEMCP_SDL_INT_TEST_AGENT_UUID=aaabbb-1234-5678-ccdd-678e89100bb1
    # A timestamp at the middle of a 10-minute window where you expect to see events from the Agent UUID:
    PURPLEMCP_SDL_INT_TEST_AGENT_EVENT_TIMESTAMP=2025-11-18T05:25:00+00:00

## Troubleshooting

- **Authentication errors**: Check your token has Account/Site level permissions (not Global), and
  your token has not expired
- **PowerQuery does not return expected results**: Check your token has Account/Site level
  permissions (not Global)
- **Connection failures**: Verify your console URL and network access; use `--verbose` for debug
  logs

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

This project is open source and community-driven. Although it is not an official SentinelOne
product, it is maintained by SentinelOne in partnership with the broader open source developer
community. See our [LICENSE](LICENSE) file for further information.

For SentinelOne platform support, use the appropriate
[support channel](https://www.sentinelone.com/global-services/get-support-now/).
