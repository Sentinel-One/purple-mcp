<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://www.sentinelone.com/wp-content/themes/sentinelone/assets/svg/header-logo-light.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://www.sentinelone.com/wp-content/themes/sentinelone/assets/svg/header-logo-dark.svg">
  <img alt="Logo description" src="light-logo.png">
</picture>

# Purple AI MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Purple AI MCP Server allows you to access SentinelOne Services with any MCP client.

**Coming Soon**: In early 2026, we will allow you to connect to this service hosted by SentinelOne.

## Features

This server exposes SentinelOne's platform through the Model Context Protocol:

- **Purple AI**: Ask security questions, investigate threats
- **Events**: Run PowerQueries on events in your SentinelOne data lake
- **Alerts**: Query, search, and investigate alerts
- **Vulnerabilities**: Track CVEs and security findings
- **Misconfigurations**: Analyze security posture issues
- **Inventory**: Ask questions about endpoints, cloud resources, identities, and network devices

Purple AI MCP is a read-only service - you cannot make changes to your account or any objects within your account from this MCP.

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

### Using Docker

```bash
# Build the image
docker build -t purple-mcp:latest .

# Run with your credentials
export PURPLEMCP_CONSOLE_TOKEN="your_token"
export PURPLEMCP_CONSOLE_BASE_URL="https://your-console.sentinelone.net"

docker run -p 8000:8000 \
  -e PURPLEMCP_CONSOLE_TOKEN \
  -e PURPLEMCP_CONSOLE_BASE_URL \
  purple-mcp:latest \
  --mode streamable-http
```

For production deployments, see [Deployment Guide](DOCKER.md).

**Note:** Purple AI MCP does not include built-in authentication. For network-exposed deployments, place it behind a reverse proxy or load balancer. See [Production Setup](PRODUCTION_SETUP.md) for cloud load balancer configurations (AWS ALB, GCP Cloud Load Balancing, Azure Application Gateway) or nginx examples for self-hosted deployments.

---

Your token needs Account or Site level permissions (not Global). Get one from Policy & Settings → User Management → Service Users in your console.  Currently, this server only supports tokens that have access to a single Account or Site.  If you need to access multiple sites, you will need to run multiple MCP servers with Account-specific or Site-specific tokens.

## Clients

Purple AI MCP supports `stdio`, `sse`, and `streamable-http` protocols and should work in any client that supports MCP.  Some sample configurations are listed below.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "purple-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Sentinel-One/purple-mcp.git", "purple-mcp", "--mode", "stdio"],
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
      "args": ["--from", "git+https://github.com/Sentinel-One/purple-mcp.git", "purple-mcp", "--mode", "stdio"],
      "env": {
        "PURPLEMCP_CONSOLE_TOKEN": "your_token",
        "PURPLEMCP_CONSOLE_BASE_URL": "https://your-console.sentinelone.net"
      }
    }
  }
}
```

### Other Clients

For debugging or to host server for multiple clients, run in streamable-http mode and connect via mcp-remote:

```bash
# Terminal 1: Start server
export PURPLEMCP_CONSOLE_TOKEN="your_token"
export PURPLEMCP_CONSOLE_BASE_URL="https://your-console.sentinelone.net"
uvx --from git+https://github.com/Sentinel-One/purple-mcp.git purple-mcp --mode streamable-http --host localhost --port 8000

# Terminal 2: Connect with any client
npx -y mcp-remote http://127.0.0.1:8000/mcp
```

We suggest you **do not** expose Purple AI MCP on a network at this time, as there is no authentication enforced and anyone could access a configured SentinelOne account.

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
- `get_inventory_item(item_id)` - Get asset details
- `list_inventory_items(limit, skip, surface)` - List assets by surface type
- `search_inventory_items(filters, limit)` - Search with advanced filters

## Environment Variables
- `PURPLEMCP_CONSOLE_TOKEN` - Service user token (Account or Site level)
- `PURPLEMCP_CONSOLE_BASE_URL` - Console URL (e.g., https://console.sentinelone.net)


## Development

We welcome your pull requests or issue submissions.

### Setup

```bash
# Install all dependencies
uv sync --group dev --group test

# Format and lint
uv run ruff format
uv run ruff check
uv run mypy
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

## Troubleshooting

  * **Authentication errors**: Check your token has Account/Site level permissions (not Global), and your token has not expired
  * **PowerQuery does not return expected results**: Check your token has Account/Site level permissions (not Global)
  * **Connection failures**: Verify your console URL and network access; use `--verbose` for debug logs

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues with this MCP server, [open an issue](https://github.com/Sentinel-One/purple-mcp/issues).

This project is open source and community-driven. Although it is not an official SentinelOne product, it is maintained by SentinelOne in partnership with the broader open source developer community.  See our [LICENSE](LICENSE) file for further information.

For SentinelOne platform support, use the appropriate [support channel](https://www.sentinelone.com/global-services/get-support-now/).
