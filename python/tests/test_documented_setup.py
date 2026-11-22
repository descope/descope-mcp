"""Regression tests for the README setup (descope/etc#20545)."""

import asyncio
from unittest.mock import Mock, patch

import descope
import pytest
from mcp.server import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

import descope_mcp.descope_mcp as descope_mcp_module
from descope_mcp import (
    DescopeMCP,
    InsufficientScopeError,
    require_scopes,
    validate_token,
)
from descope_mcp.descope_mcp import _context

WELL_KNOWN_URL = "https://api.descope.com/P2abc/.well-known/openid-configuration"
SERVER_URL = "https://my-mcp-server.example.com"


@pytest.fixture(autouse=True)
def reset_context():
    _context.reset()
    yield
    _context.reset()


def test_descope_mcp_with_management_key_builds_descope_client():
    assert descope_mcp_module.DescopeClient is descope.DescopeClient
    with patch.object(descope_mcp_module, "DescopeClient") as client_cls:
        mcp = DescopeMCP(well_known_url=WELL_KNOWN_URL, management_key="mgmt-key")
    client_cls.assert_called_once_with(project_id="P2abc", management_key="mgmt-key")
    assert mcp.descope_client is client_cls.return_value


def test_descope_mcp_without_management_key_can_validate():
    mcp = DescopeMCP(well_known_url=WELL_KNOWN_URL, mcp_server_url=SERVER_URL)
    assert isinstance(mcp.descope_client, descope.DescopeClient)


def test_descope_mcp_sets_global_context_for_standalone_functions():
    mcp = DescopeMCP(well_known_url=WELL_KNOWN_URL, mcp_server_url=SERVER_URL)
    mcp._client.validate_session = Mock(return_value={"sub": "user-1"})

    assert validate_token("token") == {"sub": "user-1"}
    mcp._client.validate_session.assert_called_once_with(
        session_token="token", audience=SERVER_URL
    )


def test_instance_auth_check_uses_instance_server_url():
    mcp = DescopeMCP(well_known_url=WELL_KNOWN_URL, mcp_server_url=SERVER_URL)
    mcp._client = Mock()
    mcp._client.validate_session.return_value = {"sub": "user-1"}
    _context.reset()

    check = mcp.create_auth_check([])
    assert check(Mock(token="token")) is True
    mcp._client.validate_session.assert_called_once_with(
        session_token="token", audience=SERVER_URL
    )


def test_require_scopes_reads_space_separated_scope_claim():
    require_scopes({"scope": "calendar.read openid"}, ["calendar.read"])
    with pytest.raises(InsufficientScopeError) as exc:
        require_scopes({"scope": "openid"}, ["calendar.read"])
    assert exc.value.missing_scopes == ["calendar.read"]
    assert exc.value.token_scopes == ["openid"]


def test_missing_scope_is_a_tool_error():
    mcp = FastMCP("scope-test")

    @mcp.tool()
    def read_calendar() -> str:
        require_scopes({"scope": "openid"}, ["calendar.read"])
        return "ok"

    async def call():
        async with create_connected_server_and_client_session(
            mcp._mcp_server
        ) as session:
            return await session.call_tool("read_calendar", {})

    assert asyncio.run(call()).isError is True
