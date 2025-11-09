# Docker Deployment

This guide covers running Purple MCP in Docker for development and production.

## Requirements

**Docker versions:**
- Docker Engine 20.10+ (or Docker Desktop 4.0+)
- Docker Compose V2 (2.0+)

The production profile uses Docker Compose V2 features and security options (`security_opt`, `cap_drop`) that require these minimum versions.

**Verify your versions:**
```bash
docker --version
# Should show: Docker version 20.10.0 or higher

docker compose version
# Should show: Docker Compose version v2.0.0 or higher
```

**Note:** Docker Compose V1 (`docker-compose` with a hyphen) is deprecated and not supported. Use `docker compose` (space, not hyphen) for V2.

## Getting the Image

Pre-built images are published to `ghcr.io/sentinel-one/purple-mcp`:

```bash
# Pull the latest image
docker pull ghcr.io/sentinel-one/purple-mcp:latest

# Or a specific version
docker pull ghcr.io/sentinel-one/purple-mcp:v0.5.1
```

Images are automatically published on release tags (e.g., `v0.5.1`).

## Building Locally

```bash
# Build locally
docker build -t purple-mcp:latest .

# Build with BuildKit (faster caching)
DOCKER_BUILDKIT=1 docker build -t purple-mcp:latest .
```

## Running with Docker

All examples below assume your credentials are set:

```bash
export PURPLEMCP_CONSOLE_TOKEN="your_token"
export PURPLEMCP_CONSOLE_BASE_URL="https://your-console.sentinelone.net"
```

### Streamable-HTTP (Recommended)

```bash
docker run -p 8000:8000 \
  -e PURPLEMCP_CONSOLE_TOKEN \
  -e PURPLEMCP_CONSOLE_BASE_URL \
  purple-mcp:latest \
  --mode streamable-http
```

### SSE Mode

```bash
docker run -p 8000:8000 \
  -e PURPLEMCP_CONSOLE_TOKEN \
  -e PURPLEMCP_CONSOLE_BASE_URL \
  purple-mcp:latest \
  --mode sse
```

### STDIO Mode (Local)

```bash
docker run -it \
  -e PURPLEMCP_CONSOLE_TOKEN \
  -e PURPLEMCP_CONSOLE_BASE_URL \
  purple-mcp:latest \
  --mode stdio
```

## Docker Compose

### Quick Start

```bash
# Create .env file
cat > .env << EOF
PURPLEMCP_CONSOLE_TOKEN=your_token
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net
EOF

# Run streamable-http mode
docker compose --profile streamable-http up
```

### Available Profiles

- `streamable-http` - HTTP streaming transport (recommended)
- `sse` - Server-Sent Events transport
- `stdio` - STDIO mode (interactive, for testing)
- `proxy` - Nginx reverse proxy with authentication
- `production` - Streamable-HTTP + authenticated reverse proxy (recommended for production)
- `all` - All modes

```bash
# Run all HTTP modes
docker compose --profile all up

# Run production with authentication
docker compose --profile production up
```

## Environment Variables

**Required:**
- `PURPLEMCP_CONSOLE_TOKEN` - SentinelOne service user token
- `PURPLEMCP_CONSOLE_BASE_URL` - Console URL (e.g., `https://console.sentinelone.net`)

**Optional:**
- `PURPLEMCP_CONSOLE_GRAPHQL_ENDPOINT` - Default: `/web/api/v2.1/graphql`
- `PURPLEMCP_ALERTS_GRAPHQL_ENDPOINT` - Default: `/web/api/v2.1/unifiedalerts/graphql`
- `PURPLEMCP_MISCONFIGURATIONS_GRAPHQL_ENDPOINT` - Default: `/web/api/v2.1/xspm/findings/misconfigurations/graphql`
- `PURPLEMCP_VULNERABILITIES_GRAPHQL_ENDPOINT` - Default: `/web/api/v2.1/xspm/findings/vulnerabilities/graphql`
- `PURPLEMCP_INVENTORY_RESTAPI_ENDPOINT` - Default: `/web/api/v2.1/xdr/assets`
- `PURPLEMCP_ENV` - Environment type (default: `production`)
- `PURPLEMCP_LOGFIRE_TOKEN` - Optional observability

## Production Deployment

**Important:** Purple AI MCP has no built-in authentication. Always protect it with a reverse proxy in production.

See [Production Setup Guide](PRODUCTION_SETUP.md) for a complete example with:
- Nginx reverse proxy
- Bearer token authentication
- HTTPS/TLS configuration
- Rate limiting
- Security headers

Quick example:

```bash
# Generate token
export PURPLEMCP_AUTH_TOKEN=$(openssl rand -hex 32)

# Generate SSL certificates (self-signed for testing ONLY)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -days 365 -nodes -subj "/CN=localhost"

# **WARNING: Self-signed certificates are for testing only, NOT for production use.**
# For production, use Let's Encrypt or your organization's certificate authority.

# Start with proxy
docker compose --profile production up

# Test with auth
curl -k -H "Authorization: Bearer $PURPLEMCP_AUTH_TOKEN" https://localhost:443/
```

See [deploy/nginx/nginx.conf.template](deploy/nginx/nginx.conf.template) for the reverse proxy configuration. The template uses environment variable substitution (`envsubst`) to inject `PURPLEMCP_AUTH_TOKEN` at container startup.

## Health Checks

### Backend Services

All HTTP-based backend services expose a health endpoint for direct access:

```bash
# SSE mode
curl http://localhost:8000/health

# Streamable-HTTP mode
curl http://localhost:8001/health
```

### Production Proxy

When using the nginx proxy, the `/health` endpoint behavior changes for security:

- **Backend `/health`** (direct): Publicly accessible, no authentication
- **Proxy `/health`**: Requires bearer token authentication
- **Proxy `/internal/health`**: IP-restricted (Docker internal networks only)

Docker health checks use the IP-restricted `/internal/health` endpoint. For external monitoring, use authenticated requests:

```bash
# Authenticated health check through proxy
curl -k -H "Authorization: Bearer $PURPLEMCP_AUTH_TOKEN" https://localhost/health

# Or use any authenticated MCP endpoint
curl -k -H "Authorization: Bearer $PURPLEMCP_AUTH_TOKEN" https://localhost/
```

## Troubleshooting

### Container won't start

```bash
docker logs <container_name>

# Run with verbose output
docker run -it \
  -e PURPLEMCP_CONSOLE_TOKEN \
  -e PURPLEMCP_CONSOLE_BASE_URL \
  purple-mcp:latest \
  --mode streamable-http --verbose
```

### Authentication errors from SentinelOne

Check your token:
- Must be Account or Site level (not Global)
- Get from: Policy & Settings → User Management → Service Users
- May have expired

### Port already in use

```bash
docker run -p 8001:8000 purple-mcp:latest --mode streamable-http
```

## Kubernetes Deployment

Example Deployment with authentication:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: purple-mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: purple-mcp
  template:
    metadata:
      labels:
        app: purple-mcp
    spec:
      containers:
      - name: purple-mcp
        image: ghcr.io/sentinel-one/purple-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: PURPLEMCP_CONSOLE_TOKEN
          valueFrom:
            secretKeyRef:
              name: purple-mcp
              key: console-token
        - name: PURPLEMCP_CONSOLE_BASE_URL
          valueFrom:
            configMapKeyRef:
              name: purple-mcp
              key: console-url
        - name: MCP_MODE
          value: "streamable-http"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: purple-mcp
spec:
  selector:
    app: purple-mcp
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: purple-mcp
data:
  console-url: https://your-console.sentinelone.net
---
apiVersion: v1
kind: Secret
metadata:
  name: purple-mcp
type: Opaque
stringData:
  console-token: "your-token-here"
```

Deploy it:

```bash
kubectl apply -f deployment.yaml
kubectl port-forward svc/purple-mcp 8000:8000
```

## Security Notes

**Authentication:** Purple AI MCP does not include authentication. You must run it behind a reverse proxy for any network-accessible deployment. See [Production Setup](PRODUCTION_SETUP.md) for a working example with Nginx.

**TLS/SSL:** The proxy is configured with modern TLS and security headers. For production, use valid certificates (not self-signed). Let's Encrypt is recommended.

**Secrets:** Never commit `.env` files or certificates to git. The project's `.gitignore` already excludes these. See [SECURITY.md](SECURITY.md) for additional security guidance.

**Rate limiting:** The proxy enforces rate limits (10 req/s) to prevent abuse.

**Token rotation:** Rotate authentication tokens regularly. See [Production Setup](PRODUCTION_SETUP.md#token-management) for procedures.

## Next Steps

- [Production Setup Guide](PRODUCTION_SETUP.md) - Complete production deployment
- [Contributing Guide](CONTRIBUTING.md) - Docker development
- [Main README](README.md) - Project overview
