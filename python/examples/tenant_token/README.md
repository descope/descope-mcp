# Tenant Token Example

This example demonstrates how to use tenant tokens with the MCP Descope SDK. Tenant tokens are fetched using a management key and don't require a user session, making them ideal for tenant-level operations.

## Prerequisites

- Python 3.10 or higher
- Descope project with:
  - Outbound application configured for tenant access (e.g., Slack workspace)
  - Management key configured
  - Tenant configured

## Setup

### Option 1: Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to this directory
cd examples/tenant_token

# Install dependencies
uv sync

# Run the example
uv run python fetch_tenant_token_example.py
```

### Option 2: Using pip

```bash
# Navigate to this directory
cd examples/tenant_token

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the SDK in development mode from the root directory
cd ../..
pip install -e .
cd examples/tenant_token

# Run the example
python fetch_tenant_token_example.py
```

## Configuration

Set the following environment variables before running:

```bash
export DESCOPE_MCP_WELL_KNOWN_URL="https://api.descope.com/your-project-id/.well-known/openid-configuration"
export DESCOPE_MANAGEMENT_KEY="your-management-key"
export MCP_SERVER_URL="https://your-mcp-server.com"
export TENANT_ID="your-tenant-id"
export TENANT_APP_ID="your-outbound-app-id"
```

Or create a `.env` file in this directory:

```
DESCOPE_MCP_WELL_KNOWN_URL=https://api.descope.com/your-project-id/.well-known/openid-configuration
DESCOPE_MANAGEMENT_KEY=your-management-key
MCP_SERVER_URL=https://your-mcp-server.com
TENANT_ID=your-tenant-id
TENANT_APP_ID=your-outbound-app-id
```

## What This Example Shows

1. **Tenant Token Fetching**: Fetching tenant tokens using management key
2. **No User Session Required**: Unlike user tokens, tenant tokens don't require a user session
3. **Tenant-Level Access**: Using tenant tokens for shared resources and team operations

## Key Features

- ✅ Management key authentication (no user session)
- ✅ Tenant token fetching
- ✅ Tenant-level resource access
- ✅ Scope-based token requests

## Use Cases

- **Shared Workspaces**: Access Slack workspaces, Microsoft Teams, etc.
- **Team Calendars**: Access tenant calendars
- **Shared Data**: Access tenant data stores
- **Admin Operations**: Perform administrative tasks on behalf of the tenant

## Running

```bash
python fetch_tenant_token_example.py
```

## Notes

- Management key is required for tenant token operations
- Tenant tokens are shared across all users in the tenant
- Useful for operations that don't depend on individual user sessions
- Tenant tokens are the correct Descope terminology for tenant-level access tokens