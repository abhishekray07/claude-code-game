"""Tests for IP-based rate limiting."""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest

from app.services.sandbox_manager import SandboxManager


class TestCanCreateSessionForIp:
    """Test IP session tracking in SandboxManager."""

    def test_allows_first_session(self):
        mgr = SandboxManager()
        assert mgr.can_create_session_for_ip("1.2.3.4", 3) is True

    def test_blocks_at_limit(self):
        mgr = SandboxManager()
        mgr._sessions_by_ip["1.2.3.4"] = ["s1", "s2", "s3"]
        assert mgr.can_create_session_for_ip("1.2.3.4", 3) is False

    def test_allows_different_ip(self):
        mgr = SandboxManager()
        mgr._sessions_by_ip["1.2.3.4"] = ["s1", "s2", "s3"]
        assert mgr.can_create_session_for_ip("5.6.7.8", 3) is True


@pytest.mark.asyncio
class TestIpTrackingIntegration:
    """Test that create_session/destroy_session properly track IPs."""

    async def test_tracks_ip_on_create(self):
        mgr = SandboxManager()
        with patch("app.services.sandbox_manager.DockerSandbox") as MockSandbox, \
             patch("app.services.sandbox_manager.settings") as mock_settings:
            mock_settings.max_sessions = 10
            sandbox_instance = MagicMock()
            sandbox_instance.create = AsyncMock()
            sandbox_instance.get_ttyd_token = MagicMock(return_value="tok")
            MockSandbox.return_value = sandbox_instance

            await mgr.create_session("s1", level_number=1, client_ip="1.2.3.4")
            assert "1.2.3.4" in mgr._sessions_by_ip
            assert "s1" in mgr._sessions_by_ip["1.2.3.4"]

    async def test_cleans_ip_on_destroy(self):
        mgr = SandboxManager()
        with patch("app.services.sandbox_manager.DockerSandbox") as MockSandbox, \
             patch("app.services.sandbox_manager.settings") as mock_settings:
            mock_settings.max_sessions = 10
            sandbox_instance = MagicMock()
            sandbox_instance.create = AsyncMock()
            sandbox_instance.terminate = AsyncMock()
            sandbox_instance.get_ttyd_token = MagicMock(return_value="tok")
            MockSandbox.return_value = sandbox_instance

            await mgr.create_session("s1", level_number=1, client_ip="1.2.3.4")
            assert len(mgr._sessions_by_ip["1.2.3.4"]) == 1

            await mgr.destroy_session("s1")
            assert "1.2.3.4" not in mgr._sessions_by_ip

    async def test_429_returned_from_api(self, client):
        """API returns 429 when IP has too many sessions."""
        with patch("app.api.docker_terminal.settings") as mock_api_settings, \
             patch("app.api.docker_terminal.sandbox_manager") as mock_mgr:
            mock_api_settings.demo_access_code = ""
            mock_mgr.can_create_session_for_ip = MagicMock(return_value=False)

            resp = await client.post("/api/docker/sessions", json={"level_number": 1})
            assert resp.status_code == 429
            assert "Too many active sessions" in resp.json()["detail"]


class TestGetClientIp:
    """Test get_client_ip helper."""

    def test_direct_connection(self):
        from app.api.docker_terminal import get_client_ip
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"
        assert get_client_ip(mock_request) == "192.168.1.1"

    def test_forwarded_header(self):
        from app.api.docker_terminal import get_client_ip
        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-for": "10.0.0.1, 172.16.0.1"}
        assert get_client_ip(mock_request) == "10.0.0.1"

    def test_no_client(self):
        from app.api.docker_terminal import get_client_ip
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None
        assert get_client_ip(mock_request) == "unknown"
