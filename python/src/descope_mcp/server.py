"""MCP Server implementation for Descope authentication."""

import asyncio
import logging
from typing import Any, Dict
from urllib.parse import urlparse

from descope import DescopeClient
from mcp.client.session import ClientSession
from mcp.server import InitializationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
)

from .types import (
    DescopeConfig,
    ErrorResponse,
    TenantTokenRequest,
    TokenResponse,
    UserTokenRequest,
)

logger = logging.getLogger(__name__)


class DescopeMCPServer:
    """MCP Server for Descope authentication operations."""

    def __init__(self, config: DescopeConfig):
        """Initialize the Descope MCP server.

        Args:
            config: Descope configuration with well-known URL
        """
        self.config = config
        self.well_known_url = config.well_known_url
        self.management_key = config.management_key

        # If management_key is provided, we can use DescopeClient for direct API calls
        # Otherwise, we'll connect to the remote MCP server at well_known_url
        if config.management_key:
            # Try to extract project_id from well_known_url if it follows a pattern
            # For now, we'll initialize DescopeClient only when needed with management_key
            # The well_known_url might contain the project_id or we might need to parse it
            parsed_url = urlparse(config.well_known_url)
            # Common pattern: https://api.descope.com/{project_id}/...
            path_parts = [p for p in parsed_url.path.split("/") if p]
            project_id = path_parts[0] if path_parts else None

            if project_id:
                self.descope_client = DescopeClient(
                    project_id=project_id,
                    management_key=config.management_key,
                )
            else:
                # Fallback: will need to be set later or use remote MCP server
                self.descope_client = None
        else:
            self.descope_client = None

        # Initialize MCP server
        self.server = Server("descope")

        # Register tools
        self.server.list_tools = self._list_tools
        self.server.call_tool = self._call_tool

    async def _list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """List available tools."""
        tools = [
            Tool(
                name="fetch_user_token_by_scopes",
                description="Fetch user token with specific scopes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_id": {"type": "string", "description": "Application ID"},
                        "user_id": {"type": "string", "description": "User ID"},
                        "scopes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required scopes",
                        },
                        "options": {
                            "type": "object",
                            "description": "Additional options (e.g., refreshToken)",
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant ID (optional)",
                        },
                    },
                    "required": ["app_id", "user_id", "scopes"],
                },
            ),
            Tool(
                name="fetch_user_token",
                description="Fetch latest user token",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_id": {"type": "string", "description": "Application ID"},
                        "user_id": {"type": "string", "description": "User ID"},
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant ID (optional)",
                        },
                        "options": {
                            "type": "object",
                            "description": "Additional options (e.g., forceRefresh)",
                        },
                    },
                    "required": ["app_id", "user_id"],
                },
            ),
            Tool(
                name="fetch_tenant_token_by_scopes",
                description="Fetch tenant token with specific scopes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_id": {"type": "string", "description": "Application ID"},
                        "tenant_id": {"type": "string", "description": "Tenant ID"},
                        "scopes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required scopes",
                        },
                        "options": {
                            "type": "object",
                            "description": "Additional options (e.g., refreshToken)",
                        },
                    },
                    "required": ["app_id", "tenant_id", "scopes"],
                },
            ),
            Tool(
                name="fetch_tenant_token",
                description="Fetch latest tenant token",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_id": {"type": "string", "description": "Application ID"},
                        "tenant_id": {"type": "string", "description": "Tenant ID"},
                        "options": {
                            "type": "object",
                            "description": "Additional options (e.g., forceRefresh)",
                        },
                    },
                    "required": ["app_id", "tenant_id"],
                },
            ),
        ]

        return ListToolsResult(tools=tools)

    async def _call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle tool calls."""
        try:
            if request.name == "fetch_user_token_by_scopes":
                return await self._fetch_user_token_by_scopes(request.arguments)
            elif request.name == "fetch_user_token":
                return await self._fetch_user_token(request.arguments)
            elif request.name == "fetch_tenant_token_by_scopes":
                return await self._fetch_tenant_token_by_scopes(request.arguments)
            elif request.name == "fetch_tenant_token":
                return await self._fetch_tenant_token(request.arguments)
            else:
                raise ValueError(f"Unknown tool: {request.name}")
        except Exception as e:
            logger.error(f"Error calling tool {request.name}: {e}")
            error_response = ErrorResponse(error=str(e))
            return CallToolResult(
                content=[{"type": "text", "text": error_response.model_dump_json()}]
            )

    async def _fetch_user_token_by_scopes(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Fetch user token with specific scopes."""
        try:
            app_id = arguments["app_id"]
            user_id = arguments["user_id"]
            scopes = arguments["scopes"]
            options = arguments.get("options", {})
            tenant_id = arguments.get("tenant_id")

            # Use Descope Python SDK if available, otherwise connect to remote MCP server
            if self.descope_client:
                token = (
                    self.descope_client.mgmt.outbound_application.fetch_token_by_scopes(
                        app_id, user_id, scopes, options, tenant_id
                    )
                )
            else:
                # Connect to remote MCP server at well_known_url
                # This would require implementing MCP client connection
                raise NotImplementedError(
                    "Connecting to remote MCP server not yet implemented. "
                    "Please provide management_key for direct API access."
                )

            response = TokenResponse(token=token)
            return CallToolResult(
                content=[{"type": "text", "text": response.model_dump_json()}]
            )
        except Exception as e:
            logger.error(f"Error fetching user token by scopes: {e}")
            error_response = ErrorResponse(error=str(e))
            return CallToolResult(
                content=[{"type": "text", "text": error_response.model_dump_json()}]
            )

    async def _fetch_user_token(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Fetch latest user token."""
        try:
            app_id = arguments["app_id"]
            user_id = arguments["user_id"]
            tenant_id = arguments.get("tenant_id")
            options = arguments.get("options", {})

            # Use Descope Python SDK if available
            if self.descope_client:
                token = self.descope_client.mgmt.outbound_application.fetch_token(
                    app_id, user_id, tenant_id, options
                )
            else:
                raise NotImplementedError(
                    "Connecting to remote MCP server not yet implemented. "
                    "Please provide management_key for direct API access."
                )

            response = TokenResponse(token=token)
            return CallToolResult(
                content=[{"type": "text", "text": response.model_dump_json()}]
            )
        except Exception as e:
            logger.error(f"Error fetching user token: {e}")
            error_response = ErrorResponse(error=str(e))
            return CallToolResult(
                content=[{"type": "text", "text": error_response.model_dump_json()}]
            )

    async def _fetch_tenant_token_by_scopes(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Fetch tenant token with specific scopes."""
        try:
            app_id = arguments["app_id"]
            tenant_id = arguments["tenant_id"]
            scopes = arguments["scopes"]
            options = arguments.get("options", {})

            # Use Descope Python SDK if available
            if self.descope_client:
                token = self.descope_client.mgmt.outbound_application.fetch_tenant_token_by_scopes(
                    app_id, tenant_id, scopes, options
                )
            else:
                raise NotImplementedError(
                    "Connecting to remote MCP server not yet implemented. "
                    "Please provide management_key for direct API access."
                )

            response = TokenResponse(token=token)
            return CallToolResult(
                content=[{"type": "text", "text": response.model_dump_json()}]
            )
        except Exception as e:
            logger.error(f"Error fetching tenant token by scopes: {e}")
            error_response = ErrorResponse(error=str(e))
            return CallToolResult(
                content=[{"type": "text", "text": error_response.model_dump_json()}]
            )

    async def _fetch_tenant_token(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Fetch latest tenant token."""
        try:
            app_id = arguments["app_id"]
            tenant_id = arguments["tenant_id"]
            options = arguments.get("options", {})

            # Use Descope Python SDK if available
            if self.descope_client:
                token = (
                    self.descope_client.mgmt.outbound_application.fetch_tenant_token(
                        app_id, tenant_id, options
                    )
                )
            else:
                raise NotImplementedError(
                    "Connecting to remote MCP server not yet implemented. "
                    "Please provide management_key for direct API access."
                )

            response = TokenResponse(token=token)
            return CallToolResult(
                content=[{"type": "text", "text": response.model_dump_json()}]
            )
        except Exception as e:
            logger.error(f"Error fetching tenant token: {e}")
            error_response = ErrorResponse(error=str(e))
            return CallToolResult(
                content=[{"type": "text", "text": error_response.model_dump_json()}]
            )

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="descope",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )


def create_server(config: DescopeConfig) -> DescopeMCPServer:
    """Create a Descope MCP server instance.

    Args:
        config: Descope configuration

    Returns:
        Configured Descope MCP server
    """
    return DescopeMCPServer(config)


async def main():
    """Main entry point for the MCP server."""
    import os

    # Load configuration from environment variables
    well_known_url = os.getenv("DESCOPE_MCP_WELL_KNOWN_URL", "")
    management_key = os.getenv("DESCOPE_MANAGEMENT_KEY", "")

    if not well_known_url:
        raise ValueError("DESCOPE_MCP_WELL_KNOWN_URL environment variable is required")

    config = DescopeConfig(
        well_known_url=well_known_url,
        management_key=management_key if management_key else None,
    )

    server = create_server(config)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
