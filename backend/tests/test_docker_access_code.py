"""Tests for access code validation in Docker terminal API."""
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
class TestAccessCodeValidation:
    """Test access code enforcement on Docker session creation."""

    async def test_no_code_configured_allows_request(self, client):
        """When DEMO_ACCESS_CODE is empty, any request should succeed."""
        with patch("app.api.docker_terminal.settings") as mock_settings:
            mock_settings.demo_access_code = ""
            resp = await client.post("/api/docker/sessions", json={"level_number": 1})
            assert resp.status_code == 200

    async def test_valid_code_allows_request(self, client):
        """When access code matches, request should succeed."""
        with patch("app.api.docker_terminal.settings") as mock_settings:
            mock_settings.demo_access_code = "secret123"
            resp = await client.post(
                "/api/docker/sessions",
                json={"level_number": 1, "access_code": "secret123"},
            )
            assert resp.status_code == 200

    async def test_invalid_code_returns_403(self, client):
        """When access code doesn't match, request should be rejected."""
        with patch("app.api.docker_terminal.settings") as mock_settings:
            mock_settings.demo_access_code = "secret123"
            resp = await client.post(
                "/api/docker/sessions",
                json={"level_number": 1, "access_code": "wrong"},
            )
            assert resp.status_code == 403
            assert "Invalid access code" in resp.json()["detail"]

    async def test_missing_code_returns_403(self, client):
        """When code is configured but not provided, request should be rejected."""
        with patch("app.api.docker_terminal.settings") as mock_settings:
            mock_settings.demo_access_code = "secret123"
            resp = await client.post(
                "/api/docker/sessions",
                json={"level_number": 1},
            )
            assert resp.status_code == 403
