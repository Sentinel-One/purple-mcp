# Deployment Configurations

This directory contains deployment and infrastructure configurations.

## nginx/

Reverse proxy configuration for production deployments. See [nginx.conf.template](nginx/nginx.conf.template) for:
- Bearer token authentication
- HTTPS/TLS configuration
- Security headers
- Rate limiting
- Streaming support for MCP

Used by the `purple-mcp-proxy` service in [docker-compose.yml](../docker-compose.yml).

For production setup instructions, see [PRODUCTION_SETUP.md](../PRODUCTION_SETUP.md).
