"""Tests for global session cap."""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest

from app.services.sandbox_manager import SandboxManager


@pytest.mark.asyncio
class TestSessionCap:
    """Test global session cap enforcement."""

    async def test_allows_session_under_cap(self):
        """Sessions under the cap should be allowed."""
        mgr = SandboxManager()
        with patch("app.services.sandbox_manager.DockerSandbox") as MockSandbox, \
             patch("app.services.sandbox_manager.settings") as mock_settings:
            mock_settings.max_sessions = 5
            sandbox_instance = MagicMock()
            sandbox_instance.create = AsyncMock()
            sandbox_instance.get_ttyd_token = MagicMock(return_value="tok")
            MockSandbox.return_value = sandbox_instance

            result = await mgr.create_session("s1", level_number=1)
            assert result["session_id"] == "s1"

    async def test_rejects_session_at_cap(self):
        """Sessions at the cap should be rejected with RuntimeError."""
        mgr = SandboxManager()
        with patch("app.services.sandbox_manager.settings") as mock_settings:
            mock_settings.max_sessions = 2
            # Pre-fill sessions to reach the cap
            mgr.sessions = {
                "a": {"port": 10001, "last_active": datetime.now()},
                "b": {"port": 10002, "last_active": datetime.now()},
            }
            with pytest.raises(RuntimeError, match="Maximum sessions"):
                await mgr.create_session("c", level_number=1)

    async def test_cap_frees_after_destroy(self):
        """After destroying a session, a new one should be allowed."""
        mgr = SandboxManager()
        with patch("app.services.sandbox_manager.settings") as mock_settings, \
             patch("app.services.sandbox_manager.DockerSandbox") as MockSandbox:
            mock_settings.max_sessions = 1
            sandbox_instance = MagicMock()
            sandbox_instance.create = AsyncMock()
            sandbox_instance.terminate = AsyncMock()
            sandbox_instance.get_ttyd_token = MagicMock(return_value="tok")
            MockSandbox.return_value = sandbox_instance

            # Create one session to fill the cap
            mgr.sessions = {}
            await mgr.create_session("s1", level_number=1)
            assert len(mgr.sessions) == 1

            # Should fail at cap
            with pytest.raises(RuntimeError, match="Maximum sessions"):
                await mgr.create_session("s2", level_number=1)

            # Destroy and try again
            await mgr.destroy_session("s1")
            result = await mgr.create_session("s3", level_number=1)
            assert result["session_id"] == "s3"

    async def test_503_returned_from_api(self, client):
        """API should return 503 when session cap is reached."""
        with patch("app.api.docker_terminal.settings") as mock_api_settings, \
             patch("app.api.docker_terminal.sandbox_manager") as mock_mgr:
            mock_api_settings.demo_access_code = ""
            mock_mgr.create_session = AsyncMock(
                side_effect=RuntimeError("Maximum sessions (5) reached")
            )
            resp = await client.post("/api/docker/sessions", json={"level_number": 1})
            assert resp.status_code == 503
