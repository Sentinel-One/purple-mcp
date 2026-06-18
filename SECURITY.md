# Purple MCP Security Guide

## Purpose and Scope

This guide documents the security expectations for every contributor and operator of the Purple MCP
codebase. It covers secure development practices, deployment hardening, runtime operations, and
incident response for all tools (`src/purple_mcp/tools/`) and libraries (`src/purple_mcp/libs/`).
The guidance applies whether Purple MCP runs locally, in an enterprise environment, or as a remote
service exposed to end users.

## Security Ownership and Shared Responsibility

- **Project maintainers** provide secure-by-default libraries, tools, and configuration primitives.
- **Operators and deployers** are responsible for securing runtime environments, network
  boundaries, secrets, observability pipelines, and user access.
- **Users running Purple MCP as a remote service** must place the instance behind a reverse proxy
  (for example, Nginx, Envoy, or an API gateway) that enforces strong authentication and
  authorization. Purple MCP does not ship its own auth layer. All external-facing deployments
  require operator-managed network controls and authentication.

## Threat Model Overview

- **Data in transit**: Purple MCP communicates exclusively over HTTPS to SentinelOne APIs and
  customer-controlled backends. Interception is mitigated through TLS enforcement.
- **Data at rest**: The project does not persist long-term secrets or customer data; operators must
  ensure external storage (logs, temp files) is protected.
- **User access**: MCP tools can execute privileged actions through upstream APIs. Exposing tool
  endpoints without authentication or rate limiting invites abuse.
- **Supply chain**: Dependencies are managed through `uv` to ensure reproducible environments.
  Developers must avoid introducing unreviewed binary dependencies or side-loaded packages.

## Secure Development Lifecycle

### Architectural Principles

- Keep business logic in `libs/` and thin MCP adapters in `tools/`. Libraries must never import
  `purple_mcp.config`, read environment variables, or rely on global state.
- Every library accepts explicit configuration objects (via `_ProgrammaticSettings`) to guarantee
  testability and predictable security posture.
- Follow strict type hints and Google-style docstrings so that reviewers can reason about error
  handling, input validation, and sensitive data flows.
- Validate inputs early, prefer immutable data structures, and raise descriptive custom exceptions
  for security-relevant failures.

### Coding Standards

- Use secure defaults (HTTPS URLs, certificate verification enabled, sanitized logging).
- Reject insecure user-supplied configuration (empty tokens, non-HTTPS URLs, or skip-TLS flags in
  release contexts).
- Avoid string interpolation with untrusted data; prefer structured logging with explicit key/value
  pairs.
- Document every change that impacts security posture (new API scopes, broader permissions, new
  network endpoints).

## Secrets Management and Configuration

- Never commit secrets, tokens, or credentials. Use environment variables or secret management
  services (Vault, AWS Secrets Manager, etc.).
- Configuration surfaces should only accept explicit parameters—no implicit environment reads
  within libraries. Tools may read from `purple_mcp.config.get_settings()` and must validate that
  required values are present.
- Treat all sample configuration files as templates; mark placeholders clearly and encourage
  rotation of credentials.
- Ensure deployment pipelines scrub secrets from logs, stack traces, and crash dumps.

## Transport Security

- HTTPS is mandatory for all outbound requests. Use `field_validator` checks to enforce `https://`
  schemes and strip trailing slashes.
- TLS verification is enabled by default. The `skip_tls_verify` flag is provided solely for
  controlled testing scenarios.
- The `PURPLEMCP_ENV` environment variable controls TLS bypass protections:
  - **Unset or `release`**: TLS bypass is **forbidden**. The environment defaults to `release` when
    not explicitly set.
  - `testing`, `test`, `staging`: Allowed but emits prominent warnings.
  - `development`, `dev`: Allowed with standard warnings.
- **For local development**, explicitly set `PURPLEMCP_ENV=development` to permit TLS bypass for
  testing scenarios.
- Validation occurs at settings instantiation, client construction, and runtime operations to
  prevent accidental downgrades.
- Warn operators prominently when TLS verification is disabled, and provide remediation steps.

## Authentication, Authorization, and Access Control

### Authentication

Purple MCP uses SentinelOne Console API tokens for authentication. A single token is configured at
server startup and used for all requests:

```bash
PURPLEMCP_CONSOLE_TOKEN=YOUR_CONSOLE_TOKEN
```

**Security Characteristics:**

- Token is registered with the logging security filter and automatically redacted from logs
- Token is loaded once at startup and cached for the lifetime of the server
- All requests use the same tenant credentials
- Suitable for single-tenant deployments

### Health Check Endpoints

The following health check endpoints **bypass authentication requirements** to allow container
orchestration systems (Kubernetes, Docker, AWS ECS, etc.) to perform liveness and readiness probes
without credentials:

- `/health`
- `/ready`
- `/ping`

**Security Characteristics:**

- These endpoints return only basic operational status (HTTP 200 OK with `{"status": "ok"}`)
- They do NOT expose any sensitive information about the system, configuration, or data
- They do NOT provide access to any MCP tools or operations
- They are intentionally unauthenticated to support infrastructure health monitoring

**Rationale:** Container orchestration platforms require periodic health checks to determine if a
service is running and ready to accept traffic. These health checks typically run from the
orchestration layer (e.g., Kubernetes kubelet) without application credentials. Requiring
authentication for health checks would prevent proper container lifecycle management and
auto-scaling.

**Best Practices:**

1. Use network segmentation to restrict who can reach health check endpoints
2. Monitor health check access patterns for anomalies
3. Do not add sensitive information to health check responses
4. Keep health check responses minimal and standardized

## Deployment Guidance

### Local Development

- **Always explicitly set `PURPLEMCP_ENV=development`** when working locally. Without this setting,
  the environment defaults to `release` and blocks TLS bypass operations.
- Never re-use release environment credentials in development environments.
- Employ mock or sandbox SentinelOne environments whenever possible.
- Keep development logs and artifacts on encrypted storage.

### Self-Hosted Remote Service

- Place MCP behind a reverse proxy with authentication, request filtering, and TLS termination. The
  proxy must require valid user identity before forwarding MCP traffic.
- Segment the MCP host within a dedicated subnet or VPC and restrict inbound traffic to the proxy
  layer.
- Run the service under least-privilege OS accounts. Configure systemd, container runtimes, or
  orchestration platforms with read-only file systems where feasible.
- Rotate credentials frequently, monitor token usage, and store secrets in hardened secret stores.
- Ensure observability pipelines (logs, traces, metrics) comply with data handling policies.

### Containerized or Orchestrated Deployments

- Pin image digests, scan containers for vulnerabilities, and keep base images up to date.
- Leverage orchestrator features (Kubernetes NetworkPolicies, PodSecurityStandards, IAM roles for
  service accounts).
- Inject configuration via secrets and config maps—never bake secrets into container images.

## Logging and Telemetry

- Logging is sanitized by default to prevent leakage of queries, tokens, or personally identifiable
  information.
- The `PURPLEMCP_DEBUG_UNSAFE_LOGGING` flag exposes sensitive payloads for troubleshooting. Use it
  only in secured, time-boxed debugging sessions and never in release environments.
- Redact secrets before sharing logs externally. Configure log aggregation systems with tight
  access controls and retention policies.
- Instrument additional security-relevant metrics (authentication failures, rate limiting, proxy
  errors) at the reverse proxy or hosting layer.

## Dependency and Supply Chain Security

- Manage dependencies exclusively with `uv`. Do not invoke `pip install` or `uv pip`.
- Run `uv sync` to reconcile lock files and verify hashes. Commit updates only after security
  review.
- Monitor upstream advisories for critical packages (`httpx`, `pydantic`, `pytest`, etc.) and
  update promptly.
- Consider integrating software composition analysis (SCA) and container scanning into CI/CD
  pipelines.

## Testing and Verification

- Run the full security gate before every commit: `uv run ruff format`,
  `uv run ruff check . --fix`, `uv run mypy src tests`, and `uv run --group test pytest -n auto`.
- Add unit and integration tests for new tools or libraries, including negative cases (invalid
  configuration, permission errors, TLS failures).
- Ensure tests do not rely on real release environment credentials or call release environment
  APIs.
- When adding network features or parsing logic, include fuzzing or property-based tests where
  practicable.

## Handling Sensitive Data

- Treat data retrieved via Purple MCP libraries as sensitive, even when it originates from test
  systems.
- Avoid writing raw results to disk; if persistence is required, encrypt storage and enforce access
  controls.
- Anonymize or aggregate output before exporting to analytics platforms or ticketing systems.
- Document data retention expectations for every integration.

## Incident Response and Vulnerability Reporting

- If you suspect a security incident (leaked credential, unauthorized access, suspicious log
  activity), disconnect the affected MCP instance from external networks, rotate secrets, and
  notify your security response team immediately.

## Security Checklist for Releases and Deployments

- Environment variables validated; TLS verification enabled in release environment.
- Reverse proxy authentication confirmed and documented.
- Secrets sourced from approved secret stores; no hardcoded credentials.
- Logging remains sanitized; debug flags disabled.
- Dependencies scanned and synchronized.
- Tests, linters, and type checks pass without security suppressions.
- Deployment runbooks updated with latest hardening guidance.

## Additional Resources

- [`CONTRIBUTING.md`](CONTRIBUTING.md) – Development workflow and coding standards.
- [`README.md`](README.md) – Project overview and setup instructions.

Security is a continuous effort. Revisit this guide regularly, automate compliance checks where
possible, and surface improvements to the team so that Purple MCP remains secure throughout its
lifecycle.
