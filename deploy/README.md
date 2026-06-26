# Deployment Configurations

This directory contains deployment and infrastructure configurations.

## Using nginx

Reverse proxy configuration for release deployments. See
[nginx.conf.template](nginx/nginx.conf.template) for:

- Bearer token authentication
- HTTPS/TLS configuration
- Security headers
- Rate limiting
- Streaming support for MCP

Used by the `purple-mcp-proxy` service in [docker-compose.yml](../docker-compose.yml).

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
  -e MCP_MODE=streamable-http \
  purple-mcp:latest
```

Follow more detailed instructions Docker Deployment [here](docker/DOCKER.md)

## Using Amazon Bedrock AgentCore

```bash
# Subscribe to Purple AI MCP Server via AWS Marketplace

#Prepare Environment Variables
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net
PURPLEMCP_CONSOLE_TOKEN=your-token
MCP_MODE=streamable-http
PURPLEMCP_STATELESS_HTTP=True
```

Follow mode detailed instructions for Amazon Bedrock AgentCore Deployment
[here](aws_agentcore/BEDROCK_AGENTCORE_DEPLOYMENT.md)

### Using Amazon Elastic Container Service (ECS)

```bash
# Subscribe to Purple AI MCP Server via AWS Marketplace

#Prepare Environment Variables
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net
PURPLEMCP_CONSOLE_TOKEN=your-token
MCP_MODE=streamable-http
PURPLEMCP_STATELESS_HTTP=True
```

Follow more detailed instructions for Amazon Elastic Container Service Deployment
[here](aws_ecs/AMAZON_ECS_DEPLOYMENT.md)

### Cloud Native Setup

For more detailed cloud setup instructions, see [CLOUD_SETUP.md](cloud/CLOUD_SETUP.md).
