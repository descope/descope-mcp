"""MCP SDK for Descope authentication."""

__version__ = "0.1.0"

from .client import DescopeMCPClient
from .connections import get_connection_token
from .descope_mcp import (
    DescopeMCP,
    add_descope_tools,
    create_auth_check,
    create_descope_fastmcp_server,
    fetch_tenant_token,
    fetch_tenant_token_by_scopes,
    fetch_user_token,
    fetch_user_token_by_scopes,
    get_descope_client,
    init_descope_mcp,
)
from .server import DescopeMCPServer
from .session import (
    InsufficientScopeError,
    TokenValidationResult,
    fetch_userinfo,
    require_scopes,
    validate_token,
    validate_token_and_get_user_id,
    validate_token_require_scopes_and_get_user_id,
)
from .types import (
    DescopeConfig,
    ErrorResponse,
    TenantTokenRequest,
    TokenRequest,
    TokenResponse,
    UserTokenRequest,
)

__all__ = [
    "DescopeMCPClient",
    "DescopeMCPServer",
    "add_descope_tools",
    "create_descope_fastmcp_server",
    "fetch_user_token",
    "fetch_user_token_by_scopes",
    "fetch_tenant_token",
    "fetch_tenant_token_by_scopes",
    "fetch_userinfo",
    "DescopeMCP",
    "get_descope_client",
    "init_descope_mcp",
    "validate_token",
    "validate_token_and_get_user_id",
    "validate_token_require_scopes_and_get_user_id",
    "TokenValidationResult",
    "require_scopes",
    "InsufficientScopeError",
    "get_connection_token",
    "create_auth_check",
    "DescopeConfig",
    "ErrorResponse",
    "TokenRequest",
    "TokenResponse",
    "UserTokenRequest",
    "TenantTokenRequest",
]
