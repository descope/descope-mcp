"""Session validation functions for Descope MCP SDK.

This module provides functions for validating MCP server access tokens
and extracting user information from validated tokens.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from descope import DescopeClient
else:  # pragma: no cover
    DescopeClient = Any  # type: ignore


class InsufficientScopeError(Exception):
    """Exception raised when token lacks required scopes.

    This exception follows the MCP spec for insufficient scope errors.
    The error response should be formatted according to RFC 6750 Section 3.1.
    """

    def __init__(
        self,
        required_scopes: List[str],
        token_scopes: List[str],
        error_description: Optional[str] = None,
    ):
        """Initialize insufficient scope error.

        Args:
            required_scopes: List of scopes required for the operation
            token_scopes: List of scopes present in the token
            error_description: Optional human-readable error description
        """
        self.required_scopes = required_scopes
        self.token_scopes = token_scopes
        self.missing_scopes = list(set(required_scopes) - set(token_scopes))

        # Recommended approach: Include existing scopes + newly required scopes
        # This prevents clients from losing previously granted permissions
        self.combined_scopes = sorted(set(token_scopes) | set(required_scopes))

        # Format scope parameter as space-separated string (per RFC 6750)
        self.scope_parameter = " ".join(self.combined_scopes)

        if error_description is None:
            missing_str = ", ".join(self.missing_scopes)
            error_description = f"Token missing required scopes: {missing_str}"

        self.error_description = error_description
        super().__init__(self.error_description)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary following MCP spec format.

        Returns:
            Dictionary with error information formatted according to MCP spec:
            - error: "insufficient_scope"
            - scope: Space-separated list of scopes (existing + required)
            - error_description: Human-readable description
            - missing_scopes: List of missing scopes
            - token_scopes: List of scopes in the token
        """
        return {
            "error": "insufficient_scope",
            "scope": self.scope_parameter,
            "error_description": self.error_description,
            "missing_scopes": self.missing_scopes,
            "token_scopes": self.token_scopes,
            "required_scopes": self.required_scopes,
        }

    def to_json(self) -> str:
        """Convert error to JSON string.

        Returns:
            JSON string representation of the error
        """
        import json

        return json.dumps(self.to_dict(), indent=2)


class TokenValidationResult(TypedDict, total=False):
    """Type definition for token validation result.

    This represents the structure returned by Descope's validate_session method.
    All fields are optional as the exact structure may vary based on token claims.
    """

    # User identification fields
    sub: str  # JWT standard subject claim (user ID)
    userId: str  # Alternative user ID field
    user_id: str  # Alternative user ID field

    # Tenant information
    tenant: str  # Tenant ID
    tenantId: str  # Alternative tenant ID field

    # Token scopes and permissions
    scopes: List[str]  # List of OAuth scopes granted to the token

    # JWT standard claims
    aud: str  # Audience claim (MCP server URL)
    iss: str  # Issuer claim
    exp: int  # Expiration time (Unix timestamp)
    iat: int  # Issued at time (Unix timestamp)

    # Additional user information (may be nested)
    user: Dict[str, Any]  # Nested user object with additional information

    # Any other JWT claims or custom fields
    # Using Dict[str, Any] for extensibility


# Import context lazily to avoid circular dependency
def _get_context():
    from .descope_mcp import _context

    return _context


logger = logging.getLogger(__name__)


def validate_token(
    access_token: str,
    descope_client: Optional[DescopeClient] = None,
    audience: Optional[str] = None,
) -> TokenValidationResult:
    """Validate MCP server access token and return full validation result.

    This function validates a Descope access token using the Descope Python SDK's
    validate_session method and returns the complete validation result, including
    user ID, tenant information, scopes, and other token claims.

    Args:
        access_token: MCP server access token from the request
        descope_client: Optional Descope client instance (uses global context if not provided)
        audience: Optional audience claim to validate (uses MCP server URL from context if not provided)

    Returns:
        TokenValidationResult dictionary containing the full validation result from Descope.
        Common fields include:
        - ``sub`` (str): User ID (JWT standard subject claim)
        - ``userId`` (str): Alternative user ID field
        - ``scopes`` (List[str]): List of OAuth scopes granted to the token
        - ``tenant`` (str): Tenant ID (if available)
        - ``tenantId`` (str): Alternative tenant ID field
        - ``aud`` (str): Audience claim (MCP server URL)
        - ``user`` (Dict[str, Any]): Nested user object with additional information
        - Other JWT claims (exp, iat, iss, etc.)

        Note: Not all fields may be present in every token. Use ``.get()`` with defaults
        when accessing fields.

    Raises:
        ValueError: If token is invalid or no client available
        Exception: If token validation fails

    Example:
        ```python
        from descope_mcp import DescopeMCP, validate_token

        # Initialize once
        DescopeMCP(
            well_known_url="...",
            mcp_server_url="https://your-mcp-server.com"
        )

        # Get full validation result
        result = validate_token(access_token)
        user_id = result.get('sub') or result.get('userId')
        tenant_id = result.get('tenant') or result.get('tenantId')
        scopes = result.get('scopes', [])

        # Check if user has required scope
        if 'calendar.read' in scopes:
            # User has calendar read permission
            pass
        ```
    """
    # Use provided client or global context
    if descope_client is None:
        context = _get_context()
        descope_client = context.get_client()
        if descope_client is None:
            raise ValueError(
                "No Descope client available. "
                "Either call DescopeMCP() first or pass descope_client parameter."
            )

    # Use provided audience or get from global context. If still not available,
    # skip audience validation (do not validate the JWT 'aud' claim).
    if audience is None:
        context = _get_context()
        audience = context.get_mcp_server_url()

    try:
        # Use Descope SDK's validate_session method
        # This properly validates the token signature, expiration, and audience claim
        # The audience parameter validates the 'aud' claim in the JWT token
        # This ensures tokens are only accepted if they were issued for this specific MCP server
        if audience:
            validation_result = descope_client.validate_session(
                session_token=access_token, audience=audience
            )
        else:
            validation_result = descope_client.validate_session(
                session_token=access_token
            )

        # Return the full validation result
        # This includes user ID, tenant info, scopes, and all other token claims
        return validation_result
    except Exception as e:
        # If validate_session fails, provide helpful error message
        error_msg = str(e)
        if (
            "invalid" in error_msg.lower()
            or "expired" in error_msg.lower()
            or "audience" in error_msg.lower()
        ):
            raise ValueError(f"Token validation failed: {error_msg}")
        raise Exception(f"Token validation failed: {error_msg}")


def validate_token_and_get_user_id(
    access_token: str,
    descope_client: Optional[DescopeClient] = None,
    audience: Optional[str] = None,
) -> str:
    """Validate MCP server access token and extract user ID using Descope SDK.

    This is a convenience function that validates a token and returns just the user ID.
    For full token information (including tenant, scopes, etc.), use validate_token() instead.

    Args:
        access_token: MCP server access token from the request
        descope_client: Optional Descope client instance (uses global context if not provided)
        audience: Optional audience claim to validate (uses MCP server URL from context if not provided)

    Returns:
        User ID extracted from the validated token

    Raises:
        ValueError: If token is invalid or user ID not found, or if no client available
        Exception: If token validation fails

    Example:
        ```python
        from descope_mcp import DescopeMCP, validate_token_and_get_user_id

        # Initialize once
        DescopeMCP(
            well_known_url="...",
            mcp_server_url="https://your-mcp-server.com"
        )

        # Use without passing client - audience is automatically validated
        user_id = validate_token_and_get_user_id(access_token)
        ```
    """
    # Use the full validate_token function and extract user_id
    validation_result = validate_token(access_token, descope_client, audience)

    # Extract user ID from validation result
    # Descope's validate_session returns user information
    user_id = (
        validation_result.get("sub")
        or validation_result.get("userId")
        or validation_result.get("user_id")
    )

    # If not in top-level, check nested user object
    if not user_id and "user" in validation_result:
        user_info = validation_result["user"]
        user_id = user_info.get("userId") or user_info.get("id") or user_info.get("sub")

    if not user_id:
        raise ValueError("User ID not found in token validation result")

    return user_id


def require_scopes(
    token_result: TokenValidationResult,
    required_scopes: List[str],
    error_description: Optional[str] = None,
) -> None:
    """Validate that token has required scopes, raise InsufficientScopeError if not.

    This function implements scope validation following the MCP spec for insufficient
    scope errors. It uses the "recommended approach" which includes both existing
    scopes from the token and newly required scopes in the error response.

    Args:
        token_result: Token validation result from validate_token()
        required_scopes: List of scopes required for the operation
        error_description: Optional custom error description

    Raises:
        InsufficientScopeError: If token lacks any required scopes.
            The exception includes:
            - existing scopes from the token
            - required scopes
            - combined scope list (existing + required)
            - formatted according to MCP spec

    Example:
        ```python
        from descope_mcp import DescopeMCP, validate_token, require_scopes

        DescopeMCP(well_known_url="...", mcp_server_url="...")

        @mcp.tool()
        def my_tool(mcp_access_token: str) -> str:
            token_result = validate_token(mcp_access_token)

            # Require specific scopes - raises InsufficientScopeError if missing
            require_scopes(token_result, ["read", "write"])

            # If we get here, all scopes are present
            return "Success"
        ```

    Example with error handling:
        ```python
        from descope_mcp import validate_token, require_scopes, InsufficientScopeError
        import json

        @mcp.tool()
        def my_tool(mcp_access_token: str) -> str:
            try:
                token_result = validate_token(mcp_access_token)
                require_scopes(token_result, ["calendar.read"])
                # Tool logic here
                return "Success"
            except InsufficientScopeError as e:
                # Return error in MCP spec format
                return e.to_json()
        ```
    """
    if not required_scopes:
        # No scopes required, always pass
        return

    # Get scopes from token result
    token_scopes = token_result.get("scopes", [])

    # Check if all required scopes are present
    required_set = set(required_scopes)
    token_set = set(token_scopes)
    missing_scopes = required_set - token_set

    if missing_scopes:
        # Raise exception with MCP spec-compliant error information
        raise InsufficientScopeError(
            required_scopes=required_scopes,
            token_scopes=token_scopes,
            error_description=error_description,
        )


def validate_token_require_scopes_and_get_user_id(
    access_token: str,
    required_scopes: List[str],
    descope_client: Optional[DescopeClient] = None,
    audience: Optional[str] = None,
    error_description: Optional[str] = None,
) -> str:
    """Validate token, require scopes, and extract user ID in one call.

    This is a convenience function that combines token validation, scope checking,
    and user ID extraction into a single operation. It's useful for tools that
    need to validate authentication and authorization before proceeding.

    Args:
        access_token: MCP server access token from the request
        required_scopes: List of scopes required for the operation
        descope_client: Optional Descope client instance (uses global context if not provided)
        audience: Optional audience claim to validate (uses MCP server URL from context if not provided)
        error_description: Optional custom error description for scope errors

    Returns:
        User ID extracted from the validated token

    Raises:
        InsufficientScopeError: If token lacks any required scopes
        ValueError: If token is invalid or user ID not found, or if no client available
        Exception: If token validation fails

    Example:
        ```python
        from descope_mcp import validate_token_require_scopes_and_get_user_id, InsufficientScopeError

        @mcp.tool()
        def my_tool(mcp_access_token: str) -> str:
            try:
                # Validate token, require scopes, and get user ID in one call
                user_id = validate_token_require_scopes_and_get_user_id(
                    mcp_access_token,
                    required_scopes=["calendar.read"]
                )

                # Use user_id for further operations
                return f"User {user_id} has calendar.read access"
            except InsufficientScopeError as e:
                return e.to_json()
        ```
    """
    # Validate token
    token_result = validate_token(access_token, descope_client, audience)

    # Require scopes (raises InsufficientScopeError if missing)
    require_scopes(token_result, required_scopes, error_description)

    # Extract user ID
    user_id = (
        token_result.get("sub")
        or token_result.get("userId")
        or token_result.get("user_id")
    )

    # If not in top-level, check nested user object
    if not user_id and "user" in token_result:
        user_info = token_result["user"]
        user_id = user_info.get("userId") or user_info.get("id") or user_info.get("sub")

    if not user_id:
        raise ValueError("User ID not found in token validation result")

    return user_id


_DEFAULT_API_ORIGIN = "https://api.descope.com"


def _extract_project_id_from_well_known(well_known_url: str) -> Optional[str]:
    """First path segment of OpenID well-known URL is the Descope project ID.

    Example: ``https://api.descope.com/P2v9E.../.well-known/openid-configuration``
    → ``P2v9E...``
    """
    try:
        parsed = urlparse(well_known_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[0]
    except Exception:
        return None
    return None


def _userinfo_url_from_well_known(
    well_known_url: str, project_id: Optional[str] = None
) -> str:
    """Build UserInfo URL: ``{origin}/v1/apps/{project_id}/userinfo``."""
    parsed = urlparse(well_known_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid well_known_url: {well_known_url!r}")
    pid = project_id or _extract_project_id_from_well_known(well_known_url)
    if not pid:
        raise ValueError(
            "Could not determine Descope project ID from well_known_url; "
            "pass project_id=... explicitly."
        )
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return f"{origin}/v1/apps/{pid}/userinfo"


def _resolve_userinfo_url(
    well_known_url: Optional[str],
    userinfo_url: Optional[str],
    project_id: Optional[str],
) -> str:
    if userinfo_url:
        return userinfo_url
    wku = well_known_url
    if wku is None:
        config = _get_context().get_config()
        if config is not None:
            wku = config.well_known_url
    if wku:
        return _userinfo_url_from_well_known(wku, project_id)
    if project_id:
        return f"{_DEFAULT_API_ORIGIN}/v1/apps/{project_id}/userinfo"
    raise ValueError(
        "fetch_userinfo requires one of: userinfo_url, well_known_url (or global "
        "DescopeMCP config with well_known_url), or project_id (uses "
        f"{_DEFAULT_API_ORIGIN} as API host)."
    )


def fetch_userinfo(
    access_token: str,
    *,
    well_known_url: Optional[str] = None,
    project_id: Optional[str] = None,
    userinfo_url: Optional[str] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Call Descope's UserInfo API with a Bearer access token.

    The endpoint is ``{api_origin}/v1/apps/{project_id}/userinfo``, for example
    ``https://api.descope.com/v1/apps/P2v9E.../userinfo``. The API host and
    project ID are taken from your OpenID well-known URL when provided.

    Descope returns profile claims plus tenant ``roles`` and ``permissions``
    when the token was issued with the appropriate scopes.

    Use this to validate or enrich authorization decisions with live roles,
    permissions, and user attributes, similar in spirit to token introspection.

    Args:
        access_token: OAuth 2.0 access token (``Authorization: Bearer``).
        well_known_url: OpenID well-known URL; used to derive API host and project ID
            (first path segment). If omitted, uses global :class:`~descope_mcp.DescopeMCP`
            config when set.
        project_id: Optional Descope project ID; overrides the ID parsed from
            ``well_known_url``. If you omit ``well_known_url`` and global config,
            pass this to use ``https://api.descope.com`` as the API host.
        userinfo_url: Optional full UserInfo URL (overrides host and project_id).
        timeout: HTTP timeout in seconds.

    Returns:
        Parsed JSON object from the UserInfo response.

    Raises:
        ImportError: If ``httpx`` is not installed.
        ValueError: If the UserInfo URL cannot be resolved or ``well_known_url`` is invalid.
        httpx.HTTPStatusError: If the UserInfo request returns a non-success status.

    Example:
        ```python
        from descope_mcp import DescopeMCP, fetch_userinfo

        DescopeMCP(well_known_url="https://api.descope.com/Pxxx/.well-known/openid-configuration")

        info = fetch_userinfo(access_token)
        tenants = info.get("tenants", {})
        ```
    """
    if not httpx:
        raise ImportError(
            "httpx is required for fetch_userinfo. Install with: pip install httpx"
        )

    url = _resolve_userinfo_url(well_known_url, userinfo_url, project_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    response = httpx.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("UserInfo response must be a JSON object")
    return data
