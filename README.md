# MCP Descope SDK

[![CI](https://github.com/descope/descope-mcp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/descope/descope-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/descope-mcp)](https://pypi.org/project/descope-mcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/descope-mcp)](https://pypi.org/project/descope-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

Multi-language SDK for integrating Descope authentication with MCP (Model Context Protocol) servers.

Descope serves as the **Authorization Server (AS)** for your MCP Servers, providing:
- [Full authorization and scoping](https://docs.descope.com/agentic-identity-hub/mcp-servers) - Token validation, scope enforcement, and audience validation
- [External token storage](https://docs.descope.com/agentic-identity-hub/connections) - Secure storage and retrieval of OAuth tokens for third-party services (Google Calendar, Slack, etc.)
- [Policy enforcement](https://docs.descope.com/agentic-identity-hub/policies) - Real-time authorization decisions based on user identity, roles, and scopes

## Languages

- [Python SDK](./python/README.md) - Python SDK for MCP Descope integration
- TypeScript SDK - Coming soon

## Quick Links

- [Python Documentation](./python/README.md)
- [Python Examples](./python/examples/)
- [Changelog](./CHANGELOG.md)
- [Release process](./RELEASE.md)
- [Security policy](./SECURITY.md)

## Repository Structure

```
.
├── python/          # Python SDK
│   ├── src/        # Source code
│   ├── tests/      # Tests
│   ├── examples/   # Example code
│   └── README.md   # Python SDK documentation
└── typescript/     # TypeScript SDK (coming soon)
```
