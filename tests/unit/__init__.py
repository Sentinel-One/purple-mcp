"""Unit tests for Purple MCP server.

This package contains unit tests that test individual components in isolation
using mocking for external dependencies. These tests do not require real
environment variables or external service connections.

Unit tests cover:
- Configuration validation and loading
- CLI argument parsing and command handling
- Server initialization and tool registration
- Purple AI client functionality with mocked API responses
- Individual component behavior and error handling

All external dependencies (APIs, file system, network) are mocked to ensure
tests are fast, deterministic, and can run in any environment.

Tests use pytest with comprehensive fixtures defined in conftest.py.
"""
