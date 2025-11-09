# Production Setup

This guide sets up Purple MCP with authentication for production use.

## Requirements

**Docker versions:**
- Docker Engine 20.10+ (or Docker Desktop 4.0+)
- Docker Compose V2 (2.0+)

The production deployment uses security hardening features (`security_opt`, `cap_drop`) that require these minimum versions.

**Verify your versions:**
```bash
docker --version        # Should show 20.10.0+
docker compose version  # Should show v2.0.0+
```

**Note:** Use `docker compose` (V2, with space) not `docker-compose` (V1, deprecated).

## Quick Reference

Pre-built images: `ghcr.io/sentinel-one/purple-mcp:latest`

```bash
docker pull ghcr.io/sentinel-one/purple-mcp:latest
docker compose pull
```

## Quick Start

> **Note**: This quick start uses nginx for simplicity. For production deployments on AWS, GCP, or Azure, we recommend using native cloud load balancers (ALB, Cloud Load Balancing, or Application Gateway). See [Cloud Load Balancer Setup](#cloud-load-balancer-setup) for configuration details.

### 1. Generate credentials and token

```bash
# Create .env file with your SentinelOne credentials
cat > .env << EOF
PURPLEMCP_CONSOLE_TOKEN=your_service_token
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net
PURPLEMCP_AUTH_TOKEN=$(openssl rand -hex 32)
PURPLEMCP_ENV=production
EOF

chmod 600 .env
```

### 2. Generate SSL certificates

**For testing/staging only (NOT for production):**

```bash
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -days 365 -nodes \
  -subj "/CN=your-domain.com"
```

**WARNING: Self-signed certificates above are for development/testing only. Never use self-signed certificates in production deployments.**

**For production with Let's Encrypt:**

```bash
docker run --rm -v $(pwd)/ssl:/etc/letsencrypt certbot/certbot \
  certonly --standalone -d your-domain.com

# Copy certificates to expected location
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

### 3. Start the services

```bash
# Start with production profile (includes reverse proxy with auth)
docker compose --profile production up -d

# Verify services are running
docker compose ps
```

### 4. Test

```bash
# Get the auth token
TOKEN=$(grep PURPLEMCP_AUTH_TOKEN .env | cut -d= -f2)

# Test with authentication
curl -k -H "Authorization: Bearer $TOKEN" https://localhost/
```

## Architecture

This guide covers the nginx reverse proxy setup, which works well for development and self-hosted deployments. For production deployments on AWS, GCP, or Azure, we recommend using your cloud provider's native load balancer (Application Load Balancer, Cloud Load Balancing, or Application Gateway) instead. See [Cloud Load Balancer Setup](#cloud-load-balancer-setup) for details.

**Nginx architecture:**
```
Client → nginx (443) → Purple MCP (8000) → SentinelOne API
```

**Cloud load balancer architecture:**
```
Client → ALB/GCLB/App Gateway (443) → Purple MCP (8000) → SentinelOne API
```

Cloud load balancers provide managed SSL certificates, better DDoS protection, simpler horizontal scaling, and avoid the nginx rate limiting issues described below.

### How Auth Works

The nginx config uses environment variable substitution. At startup, `envsubst` replaces `${PURPLEMCP_AUTH_TOKEN}` in the template with your actual token from the environment. This means the token is never hardcoded in the config file - it's only in memory at runtime.

### Rate Limiting Limitation

The nginx configuration has a known limitation with rate limiting. Due to nginx's request processing phases, authentication failures (401/403 responses) occur before rate limiting is applied. This means an attacker can make unlimited authentication attempts without being throttled.

**Mitigation**: Use a cryptographically strong random token with sufficient entropy. A 256-bit token (32 bytes) makes brute force attacks computationally infeasible even without rate limiting:

```bash
# Recommended: Base64-encoded (URL-safe characters)
openssl rand -base64 32

# Alternative: Hexadecimal
openssl rand -hex 32
```

**Token Requirements:**
- Use only base64 or hexadecimal characters (alphanumeric + `/+=` for base64, `0-9a-f` for hex)
- Minimum 32 bytes of entropy (generates 44+ character base64 or 64 character hex string)
- It's safe to quote tokens in `.env` files (quotes will be stripped by Docker)
- Avoid special shell characters that might cause issues: `$`, backticks, `\`, `!` (in some shells)

For deployments requiring rate limiting on authentication failures, consider using a cloud load balancer with WAF rules or moving authentication to the application layer.

## Monitoring

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f purple-mcp-proxy
docker compose logs -f purple-mcp-streamable-http
```

### Check authentication

```bash
# View auth failures
docker compose logs purple-mcp-proxy | grep "Unauthorized"

# Monitor in real-time
docker compose logs -f purple-mcp-proxy | grep -E "Unauthorized|Forbidden"

# Verify token validation is working (should be rejected)
curl -k -H "Authorization: Bearer invalid-token" https://localhost/

# Verify correct token is accepted
TOKEN=$(grep PURPLEMCP_AUTH_TOKEN .env | cut -d= -f2)
curl -k -H "Authorization: Bearer $TOKEN" https://localhost/
```

### Verify token is NOT hardcoded

The nginx configuration uses environment variable substitution for security. You can verify the token is properly substituted:

```bash
# The template file should contain ${PURPLEMCP_AUTH_TOKEN} placeholder
grep "PURPLEMCP_AUTH_TOKEN" deploy/nginx/nginx.conf.template

# Verify the placeholder was substituted (check that literal string is absent)
docker exec purple-mcp-proxy grep '\${PURPLEMCP_AUTH_TOKEN}' /etc/nginx/nginx.conf
# Should return nothing (exit code 1) - confirms envsubst replaced the placeholder

# Verify the running config contains your actual token value
TOKEN=$(grep PURPLEMCP_AUTH_TOKEN .env | cut -d= -f2)
docker exec purple-mcp-proxy grep "$TOKEN" /etc/nginx/nginx.conf
# Should find matches (exit code 0) - confirms your token is active in nginx
```

### Health checks

The nginx proxy changes health endpoint behavior for security:

- **Backend `/health`** (direct): Publicly accessible, no authentication
- **Proxy `/health`**: Requires bearer token authentication
- **Proxy `/internal/health`**: IP-restricted to internal networks only (localhost IPv4 `127.0.0.1`, localhost IPv6 `::1`, and Docker bridge networks `172.16.0.0/12`)

Docker health checks use the IP-restricted `/internal/health` endpoint. For external monitoring:

```bash
TOKEN=$(grep PURPLEMCP_AUTH_TOKEN .env | cut -d= -f2)

# Authenticated health check
curl -k -H "Authorization: Bearer $TOKEN" https://localhost/health

# Or any authenticated endpoint
curl -k -H "Authorization: Bearer $TOKEN" https://localhost/
```

## Maintenance

### Update token

```bash
# Generate new token
NEW_TOKEN=$(openssl rand -hex 32)

# Update .env
sed -i "s/PURPLEMCP_AUTH_TOKEN=.*/PURPLEMCP_AUTH_TOKEN=$NEW_TOKEN/" .env

# Restart proxy
docker compose restart purple-mcp-proxy
```

### Renew Let's Encrypt certificate

```bash
# Renew (should be automatic with certbot)
docker run --rm -v $(pwd)/ssl:/etc/letsencrypt certbot/certbot renew

# Restart proxy
docker compose restart purple-mcp-proxy
```

### Renew self-signed certificate (testing only)

**WARNING: Self-signed certificates are for testing only, not production.**

```bash
openssl req -x509 -newkey rsa:4096 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -days 365 -nodes \
  -subj "/CN=your-domain.com"

docker compose restart purple-mcp-proxy
```

## Troubleshooting

### Services won't start

```bash
docker compose logs

# Validate nginx config template
export PURPLEMCP_AUTH_TOKEN=$(grep PURPLEMCP_AUTH_TOKEN .env | cut -d= -f2)
docker run --rm \
  -v $(pwd)/deploy/nginx/nginx.conf.template:/tmp/nginx.conf.template:ro \
  -e PURPLEMCP_AUTH_TOKEN \
  nginx:1.27-alpine sh -c 'envsubst "\$PURPLEMCP_AUTH_TOKEN" < /tmp/nginx.conf.template > /etc/nginx/nginx.conf && nginx -t'
```

### Certificate issues

```bash
# Check expiration
openssl x509 -in ssl/cert.pem -noout -dates

# View certificate details
openssl x509 -in ssl/cert.pem -text -noout
```

### Port already in use

Either change the port in `docker-compose.yml` or stop the conflicting service:

```bash
lsof -i :443
kill -9 <PID>
```

### Can't connect to SentinelOne

```bash
# Check logs
docker compose logs purple-mcp-streamable-http

# Verify credentials are correct
# - Token must be Account or Site level (not Global)
# - Token must not be expired
# - Base URL must be reachable from container
```

## Configuration Reference

### Environment Variables

See [docker-compose.yml](docker-compose.yml) for a complete list. Key production variables:

- `PURPLEMCP_AUTH_TOKEN` - Bearer token for proxy authentication (required)
- `PURPLEMCP_CONSOLE_TOKEN` - SentinelOne service user token
- `PURPLEMCP_CONSOLE_BASE_URL` - SentinelOne console URL
- `PURPLEMCP_ENV` - Set to `production`

### Nginx Configuration

See [deploy/nginx/nginx.conf.template](deploy/nginx/nginx.conf.template) for the reverse proxy configuration template. The template uses `envsubst` to inject `PURPLEMCP_AUTH_TOKEN` at runtime. Notable features:

- Bearer token validation (`Authorization: Bearer <token>`)
- HTTPS/TLS with modern ciphers
- Security headers (HSTS, X-Frame-Options, X-Content-Type-Options)
- Rate limiting (10 req/s)
- Streaming support for MCP
- Health check endpoint (no auth required)

### Security Hardening

The production profile (`docker compose --profile production`) includes security hardening:

- **`no-new-privileges:true`**: Prevents privilege escalation within containers
- **`cap_drop: ALL`**: Drops all Linux capabilities; services run with minimal privileges
- **Read-only volumes**: Configuration and SSL certificates mounted as read-only

These settings follow the principle of least privilege. The containers can still function normally for their intended purpose (running Python/nginx) but cannot perform privileged operations.

## Cloud Load Balancer Setup

Purple MCP uses Server-Sent Events (SSE) for streaming responses, which requires long-lived HTTP connections. The critical configuration across all cloud providers is the idle timeout - default values are typically too short and will cause connections to drop.

Purple MCP runs in stateless mode, meaning each request is independent and session state is not maintained. This simplifies deployment: you don't need sticky sessions or session affinity, and you can scale horizontally by adding more backend instances without coordination between them.

### AWS Application Load Balancer

The default ALB idle timeout of 60 seconds will cause SSE connections to fail. Increase it to at least 300 seconds (5 minutes) or higher depending on your use case:

```hcl
resource "aws_lb" "purple_mcp" {
  name               = "purple-mcp-alb"
  load_balancer_type = "application"
  subnets            = var.public_subnets
  security_groups    = [aws_security_group.alb.id]

  idle_timeout = 300  # 5 minutes for SSE
}

resource "aws_lb_target_group" "purple_mcp" {
  name     = "purple-mcp-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path     = "/health"
    interval = 30
  }

  # Sticky sessions not required - Purple MCP is stateless
  stickiness {
    enabled = false
  }
}
```

Configure your HTTPS listener to forward to this target group and attach an SSL certificate from ACM. For authentication, you can implement token validation in the application layer or use AWS WAF rules.

Reference: [AWS Guidance for Deploying MCP Servers](https://aws.amazon.com/solutions/guidance/deploying-model-context-protocol-servers-on-aws/)

### Google Cloud Load Balancing

The default 30 second backend timeout is too short for SSE connections. Set it significantly higher - 24 hours (86400 seconds) works well:
```hcl
resource "google_compute_backend_service" "purple_mcp" {
  name        = "purple-mcp-backend"
  protocol    = "HTTP"
  timeout_sec = 86400  # 24 hours for SSE

  backend {
    group = google_compute_instance_group_manager.purple_mcp.instance_group
  }

  health_checks = [google_compute_health_check.purple_mcp.id]

  # Session affinity not required - stateless mode
  session_affinity = "NONE"
}

resource "google_compute_health_check" "purple_mcp" {
  name = "purple-mcp-health"

  http_health_check {
    port         = 8000
    request_path = "/health"
  }
}
```

Session affinity is set to `NONE` since Purple MCP doesn't maintain session state. For additional security, consider using Cloud Armor for DDoS protection and WAF capabilities.

### Azure Application Gateway / Load Balancer

Azure enforces a 4 minute minimum idle timeout, which is the bare minimum for SSE. Configure a higher value if your deployment allows:
```hcl
resource "azurerm_lb" "purple_mcp" {
  name                = "purple-mcp-lb"
  location            = var.location
  resource_group_name = var.resource_group_name

  frontend_ip_configuration {
    name                 = "PublicIPAddress"
    public_ip_address_id = azurerm_public_ip.purple_mcp.id
  }
}

resource "azurerm_lb_probe" "purple_mcp" {
  loadbalancer_id     = azurerm_lb.purple_mcp.id
  name                = "purple-mcp-health"
  protocol            = "Http"
  port                = 8000
  request_path        = "/health"
}
```

Session persistence is not required since Purple MCP operates in stateless mode. If the 4 minute timeout proves insufficient, implement client-side keepalives (sending data every 3 minutes) to maintain the connection.

For enhanced security, use Azure WAF with Application Gateway or integrate Azure AD for OAuth 2.0 authentication.

### Kubernetes Deployments

If you're running Purple MCP on EKS, GKE, or AKS, configure health probes in your deployment manifest:

```yaml
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
```

Purple MCP operates in stateless mode by default, making it well-suited for Kubernetes deployments. You can enable horizontal pod autoscaling to handle varying loads, and the load balancer will distribute requests across pods without requiring session affinity.

## Pre-launch Checklist

**For cloud load balancer deployments (recommended):**
- [ ] Idle timeout configured appropriately (300+ seconds for AWS, 86400 seconds for GCP, 240+ seconds for Azure)
- [ ] Health checks configured to use `/health` endpoint
- [ ] SSL/TLS certificate configured (ACM, Google-managed certificates, or Azure certificates)
- [ ] Auto-scaling enabled for backend instances
- [ ] Sticky sessions disabled (not required for stateless mode)
- [ ] WAF or Cloud Armor configured for additional security (optional but recommended)

**For nginx reverse proxy deployments:**
- [ ] Valid SSL certificate installed (not self-signed for production)
- [ ] Token substitution verified: `docker exec purple-mcp-proxy grep '\${PURPLEMCP_AUTH_TOKEN}' /etc/nginx/nginx.conf` should return nothing (placeholder should be replaced with actual token)
- [ ] Verify actual token is present: `TOKEN=$(grep PURPLEMCP_AUTH_TOKEN .env | cut -d= -f2) && docker exec purple-mcp-proxy grep "$TOKEN" /etc/nginx/nginx.conf` should find matches
- [ ] Understanding of rate limiting limitation documented below

**Security:**
- [ ] Strong authentication token generated: `openssl rand -base64 32`
- [ ] `.env` file excluded from version control
- [ ] Firewall rules or security groups properly configured

**Operations:**
- [ ] All health checks passing
- [ ] Authentication tested with both valid and invalid tokens
- [ ] Monitoring and alerting configured
- [ ] Token rotation procedure documented and understood by team

## Next Steps

- [Docker Deployment Guide](DOCKER.md) - More deployment options
- [Troubleshooting](DOCKER.md#troubleshooting) - Common issues
- [Kubernetes Deployment](DOCKER.md#kubernetes-deployment) - Deploy to K8s
