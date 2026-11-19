"""Pytest configuration and shared fixtures."""

import os
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv(
        "DESCOPE_MCP_WELL_KNOWN_URL",
        "https://api.descope.com/test/.well-known/openid-configuration",
    )
    monkeypatch.setenv("DESCOPE_MANAGEMENT_KEY", "test-management-key")
    monkeypatch.setenv("MCP_SERVER_URL", "https://test-mcp-server.com")
    monkeypatch.setenv("DESCOPE_PROJECT_ID", "test-project-id")


@pytest.fixture
def mock_descope_client():
    """Create a mock DescopeClient for testing."""
    client = Mock()
    client.validate_session = Mock(
        return_value={
            "sub": "user-123",
            "scope": "read write calendar.read",
            "aud": "https://test-mcp-server.com",
        }
    )
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
