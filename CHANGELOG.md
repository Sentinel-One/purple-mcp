# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - YYYY-MM-DD

## [0.6.0] - 2025-11-25

### Added

- Amazon Bedrock AgentCore deployment support with `--stateless-http` flag
- New `PURPLEMCP_STATELESS_HTTP` environment variable for stateless HTTP mode
- New `PURPLEMCP_TRANSPORT_MODE` environment variable for transport configuration
- Comprehensive AWS Bedrock deployment guide (BEDROCK_AGENTCORE_DEPLOYMENT.md)
- IAM and trust policy templates for AWS Bedrock AgentCore

### Changed

- Updated default values for client details to be more accurate
- Transport mode now configurable via environment variable
- Improved documentation for environment variables in README

### Fixed

- Exception handling in server.py uses `Exception` instead of `BaseException`
- Type annotations for `stateless_http` field (removed unnecessary `| None`)
- Corrected `transport_mode` field description in Settings

## [0.5.1] - 2025-11-08

### Added

- Docker deployment support with multi-stage Dockerfile
- Docker Compose configurations for all MCP transport modes
- Nginx reverse proxy with bearer token authentication
- Production deployment guide (PRODUCTION_SETUP.md)
- Docker deployment documentation (DOCKER.md)
- CI/CD workflow for Docker image publishing to GHCR (on release only)
- Docker startup tests for all transport modes
- Kubernetes and cloud load balancer deployment examples
- Network allowlist guidance for `/internal/health` endpoint
- Security warning when binding to non-loopback addresses
- Bold warnings about self-signed certificates in production

### Changed

- Updated .gitignore to exclude SSL certificates and production files
- Enhanced CONTRIBUTING.md with Docker instructions
- Updated README.md with Docker deployment section
- Simplified verbose comments across Docker configuration files
- Aligned image publishing documentation (release tags only)
- Standardized nginx version references to 1.27-alpine

### Fixed

- Nginx authentication uses `map` directive instead of negated regex
- Docker healthcheck installs wget in runtime image
- Docker entrypoint uses argv form for safer execution
- Pinned nginx image to 1.27-alpine
- CI workflow healthcheck reliability with retry logic

### Security

- Nginx proxy with TLS 1.2+, strong ciphers, and security headers
- IP-restricted `/internal/health` endpoint for Docker health checks
- Docker entrypoint validates placeholder tokens and uses `set -eu`
- Conditional `--allow-remote-access` flag for non-loopback bindings
- CI workflows mask secrets and validate auth flow
- Runtime warnings for unsafe network exposure

## [0.5.0] - 2024-11-05

### Added

- Initial public release
- Purple AI tool for natural language security queries
- SDL (Singularity Data Lake) query execution and timestamp utilities
- Alerts management (list, search, get details, notes, history)
- Misconfigurations management for cloud and Kubernetes environments
- Vulnerabilities management and tracking
- Inventory management for unified asset tracking
- Purple AI utility tools (status checks, available tools listing)
- Support for three MCP transport modes: stdio, SSE, and streamable-http
- Comprehensive test suite with unit and integration tests
- Type checking with mypy (strict mode)
- Code quality enforcement with ruff
- Automated CI/CD with GitHub Actions
- Comprehensive documentation (README, CONTRIBUTING, SECURITY)

[0.6.0]: https://github.com/Sentinel-One/purple-mcp/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/Sentinel-One/purple-mcp/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Sentinel-One/purple-mcp/releases/tag/v0.5.0
