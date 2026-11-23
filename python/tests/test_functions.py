"""End-to-end tests for SDK functions directly (no MCP server)."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from descope_mcp import (
    DescopeConfig,
    DescopeMCP,
    fetch_tenant_token,
    fetch_tenant_token_by_scopes,
    fetch_userinfo,
    get_connection_token,
    validate_token_and_get_user_id,
)


class TestDirectFunctions:
    """Test SDK functions directly without MCP server."""

    @pytest.fixture
    def mock_descope_client(self):
        """Create a mock DescopeClient."""
        client = Mock()
        client.validate_session = Mock(return_value={"sub": "user-123"})
        client.mgmt = Mock()
        client.mgmt.outbound_application = Mock()
        client.mgmt.outbound_application.fetch_token = Mock(
            return_value="connection-token-123"
        )
        client.mgmt.outbound_application.fetch_token_by_scopes = Mock(
            return_value="connection-token-123"
        )
        client.mgmt.outbound_application.fetch_tenant_token = Mock(
            return_value="tenant-token-123"
        )
        client.mgmt.outbound_application.fetch_tenant_token_by_scopes = Mock(
            return_value="tenant-token-123"
        )
        return client

    def test_validate_token_and_get_user_id(self, mock_descope_client):
        """Test token validation function."""
        DescopeMCP(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            mcp_server_url="https://test-mcp-server.com",
        )

        with patch("descope_mcp.descope_mcp._context") as mock_context:
            mock_context.get_client.return_value = mock_descope_client
            mock_context.get_mcp_server_url.return_value = "https://test-mcp-server.com"
            user_id = validate_token_and_get_user_id("test-token")
            assert user_id == "user-123"
            mock_descope_client.validate_session.assert_called_once()

    def test_get_connection_token(self, mock_descope_client):
        """Test connection token retrieval."""
        DescopeMCP(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            management_key="test-key",
        )

        with patch("descope_mcp.descope_mcp._context") as mock_context:
            mock_context.get_client.return_value = mock_descope_client

            token = get_connection_token(
                user_id="user-123",
                app_id="google-calendar",
                scopes=["calendar.readonly"],
            )

            assert token == "connection-token-123"
            mock_descope_client.mgmt.outbound_application.fetch_token_by_scopes.assert_called_once()

    def test_fetch_tenant_token(self, mock_descope_client):
        """Test tenant token fetching."""
        config = DescopeConfig(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            management_key="test-key",
        )

        with patch(
            "descope_mcp.descope_mcp._get_descope_client",
            return_value=mock_descope_client,
        ):
            import asyncio

            result = asyncio.run(
                fetch_tenant_token(
                    config=config, app_id="slack-workspace", tenant_id="tenant-123"
                )
            )

            # Result is JSON string
            import json

            token_data = json.loads(result)
            assert "token" in token_data

    def test_fetch_tenant_token_by_scopes(self, mock_descope_client):
        """Test tenant token fetching with scopes."""
        config = DescopeConfig(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            management_key="test-key",
        )

        with patch(
            "descope_mcp.descope_mcp._get_descope_client",
            return_value=mock_descope_client,
        ):
            import asyncio

            result = asyncio.run(
                fetch_tenant_token_by_scopes(
                    config=config,
                    app_id="slack-workspace",
                    tenant_id="tenant-123",
                    scopes=["channels:read"],
                )
            )

            import json

            token_data = json.loads(result)
            assert "token" in token_data

    def test_fetch_tenant_token_latest_uses_latest_endpoint_with_access_token(self):
        """Tenant latest token should call /tenant/token/latest when access_token is provided."""
        config = DescopeConfig(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            management_key=None,
        )

        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "token": {"accessToken": "tenant-access-token-xyz"}
        }
        mock_resp.raise_for_status.return_value = None
        mock_httpx.post.return_value = mock_resp

        with patch("descope_mcp.descope_mcp.httpx", mock_httpx):
            import asyncio

            result = asyncio.run(
                fetch_tenant_token(
                    config=config,
                    app_id="google-contacts",
                    tenant_id="tenant-123",
                    options={"forceRefresh": False},
                    access_token="access-token-abc",
                )
            )

        # Verify correct endpoint and auth header format
        args, kwargs = mock_httpx.post.call_args
        assert args[0].endswith("/v1/mgmt/outbound/app/tenant/token/latest")
        assert kwargs["headers"]["Authorization"] == "Bearer test:access-token-abc"

        import json

        token_data = json.loads(result)
        assert token_data["token"] == "tenant-access-token-xyz"

    def test_fetch_tenant_token_by_scopes_uses_scopes_endpoint_with_access_token(self):
        """Tenant scoped token should call /tenant/token when access_token is provided."""
        config = DescopeConfig(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            management_key=None,
        )

        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "token": {"accessToken": "tenant-access-token-scoped"}
        }
        mock_resp.raise_for_status.return_value = None
        mock_httpx.post.return_value = mock_resp

        with patch("descope_mcp.descope_mcp.httpx", mock_httpx):
            import asyncio

            result = asyncio.run(
                fetch_tenant_token_by_scopes(
                    config=config,
                    app_id="google-contacts",
                    tenant_id="tenant-123",
                    scopes=["contacts.readonly"],
                    options={"forceRefresh": False},
                    access_token="access-token-abc",
                )
            )

        args, kwargs = mock_httpx.post.call_args
        assert args[0].endswith("/v1/mgmt/outbound/app/tenant/token")
        assert kwargs["headers"]["Authorization"] == "Bearer test:access-token-abc"
        assert kwargs["json"]["scopes"] == ["contacts.readonly"]

        import json

        token_data = json.loads(result)
        assert token_data["token"] == "tenant-access-token-scoped"

    def test_descope_mcp_class_based(self, mock_descope_client):
        """Test class-based API."""
        with patch(
            "descope_mcp.descope_mcp._get_descope_client",
            return_value=mock_descope_client,
        ):
            client = DescopeMCP(
                well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
                management_key="test-key",
                mcp_server_url="https://test-mcp-server.com",
            )

            # Mock the client's _client attribute
            client._client = mock_descope_client

            user_id = client.validate_token_and_get_user_id("test-token")
            assert user_id == "user-123"

            token = client.get_connection_token(
                user_id="user-123", app_id="google-calendar"
            )
            assert token == "connection-token-123"

    def test_fetch_userinfo_requires_resolution(self):
        mock_context = MagicMock()
        mock_context.get_config.return_value = None
        with patch("descope_mcp.session._get_context", return_value=mock_context):
            with pytest.raises(ValueError, match="fetch_userinfo requires"):
                fetch_userinfo("t")

    def test_fetch_userinfo_derives_url_from_well_known(self):
        """UserInfo URL should match the OpenID well-known host."""
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"sub": "user-1", "email": "a@example.com"}
        mock_resp.raise_for_status.return_value = None
        mock_httpx.get.return_value = mock_resp

        with patch("descope_mcp.session.httpx", mock_httpx):
            info = fetch_userinfo(
                "access-token-xyz",
                well_known_url="https://api.eu.descope.com/P1/.well-known/openid-configuration",
            )

        assert info["sub"] == "user-1"
        args, kwargs = mock_httpx.get.call_args
        assert args[0] == "https://api.eu.descope.com/v1/apps/P1/userinfo"
        assert kwargs["headers"]["Authorization"] == "Bearer access-token-xyz"

    def test_fetch_userinfo_explicit_url_overrides_well_known(self):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"sub": "u2"}
        mock_resp.raise_for_status.return_value = None
        mock_httpx.get.return_value = mock_resp

        with patch("descope_mcp.session.httpx", mock_httpx):
            fetch_userinfo(
                "t",
                well_known_url="https://api.descope.com/x/.well-known/openid-configuration",
                userinfo_url="https://custom.example.com/oauth2/v1/userinfo",
            )

        args, _ = mock_httpx.get.call_args
        assert args[0] == "https://custom.example.com/oauth2/v1/userinfo"

    def test_fetch_userinfo_default_origin_without_global_config(self):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"sub": "u3"}
        mock_resp.raise_for_status.return_value = None
        mock_httpx.get.return_value = mock_resp

        mock_context = MagicMock()
        mock_context.get_config.return_value = None

        with patch("descope_mcp.session.httpx", mock_httpx):
            with patch("descope_mcp.session._get_context", return_value=mock_context):
                fetch_userinfo("t", project_id="P2v9EBlmO4XTrOwMRfsY1jeUONxU")

        args, _ = mock_httpx.get.call_args
        assert (
            args[0]
            == "https://api.descope.com/v1/apps/P2v9EBlmO4XTrOwMRfsY1jeUONxU/userinfo"
        )

    def test_descope_mcp_fetch_userinfo(self, mock_descope_client):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"sub": "from-mcp"}
        mock_resp.raise_for_status.return_value = None
        mock_httpx.get.return_value = mock_resp

        with patch(
            "descope_mcp.descope_mcp._get_descope_client",
            return_value=mock_descope_client,
        ):
            with patch("descope_mcp.session.httpx", mock_httpx):
                client = DescopeMCP(
                    well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
                    management_key="test-key",
                )
                info = client.fetch_userinfo("my-access-token")

        assert info["sub"] == "from-mcp"
        args, _ = mock_httpx.get.call_args
        assert args[0] == "https://api.descope.com/v1/apps/test/userinfo"
