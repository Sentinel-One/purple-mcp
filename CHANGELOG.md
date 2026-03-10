# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0]

### Added

- Field filtering support for inventory tools via `fetch_fields` parameter
  - Three presets: MINIMAL (7 fields), STANDARD (13 fields), ALL (~200+ fields)
  - Custom field lists support using camelCase field names (e.g., `["id", "resourceType"]`)
  - Significant performance improvement for list/search operations using MINIMAL preset
  - Field filtering applies to `get_inventory_item`, `list_inventory_items`, and
    `search_inventory_items`
- Comprehensive documentation for field filtering in tool descriptions and docstrings
- Field preset validation with clear error messages for invalid field names
- `InventoryFetchFieldsPreset` enum in `libs.inventory.field_presets` module
- Built-in `CVE` and `VT` tools
- Tool for retrieving Agentic Investigation reports

### Changed

- Inventory tools now default to MINIMAL fields for list/search operations (was ALL)
- `get_inventory_item` defaults to ALL fields for backward compatibility
- Inventory tool return values now use camelCase field names (`by_alias=True`)
- Fields without values are now excluded from inventory responses (`exclude_unset=True`)
- Updated README with inventory tool signatures including `fetch_fields` parameter
- Purple AI query request scope can now be configured via console scope selector environment
  variables (optional). These are named:
  - `PURPLEMCP_PURPLE_AI_CONSOLE_TENANT_ID`
  - `PURPLEMCP_PURPLE_AI_CONSOLE_ACCOUNT_ID`
  - `PURPLEMCP_PURPLE_AI_CONSOLE_SITE_ID`
- Dropped Python 3.10 support
- Structural reorganization of documentation, files, and wording

## [0.6.0]

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

## [0.5.1]

### Added

- Docker deployment support with multi-stage Dockerfile
- Docker Compose configurations for all MCP transport modes
- Nginx reverse proxy with bearer token authentication
- Release deployment guide (CLOUD_SETUP.md)
- Docker deployment documentation (DOCKER.md)
- CI/CD workflow for Docker image publishing to GHCR (on release only)
- Docker startup tests for all transport modes
- Kubernetes and cloud load balancer deployment examples
- Network allowlist guidance for `/internal/health` endpoint
- Security warning when binding to non-loopback addresses
- Bold warnings about self-signed certificates in release environments

### Changed

- Updated .gitignore to exclude SSL certificates and release environment files
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

## [0.5.0]

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

[Unreleased]: https://github.com/Sentinel-One/purple-mcp/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/Sentinel-One/purple-mcp/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Sentinel-One/purple-mcp/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/Sentinel-One/purple-mcp/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Sentinel-One/purple-mcp/releases/tag/v0.5.0
