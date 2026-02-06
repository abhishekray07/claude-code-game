"""Tests for startup orphan container cleanup."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.sandbox_manager import SandboxManager


class TestOrphanCleanup:
    """Test cleanup_orphaned_containers()."""

    def test_removes_orphaned_containers(self):
        """Should stop and remove all sandbox-* containers."""
        mock_container1 = MagicMock()
        mock_container1.name = "sandbox-abc123"
        mock_container2 = MagicMock()
        mock_container2.name = "sandbox-def456"

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container1, mock_container2]

        with patch("app.services.sandbox_manager.get_docker_client", return_value=mock_client):
            mgr = SandboxManager()
            mgr.cleanup_orphaned_containers()

        mock_client.containers.list.assert_called_once_with(
            filters={"name": "sandbox-"}, all=True
        )
        mock_container1.stop.assert_called_once_with(timeout=5)
        mock_container1.remove.assert_called_once_with(force=True)
        mock_container2.stop.assert_called_once_with(timeout=5)
        mock_container2.remove.assert_called_once_with(force=True)

    def test_no_orphans_is_noop(self):
        """Should handle no orphaned containers gracefully."""
        mock_client = MagicMock()
        mock_client.containers.list.return_value = []

        with patch("app.services.sandbox_manager.get_docker_client", return_value=mock_client):
            mgr = SandboxManager()
            mgr.cleanup_orphaned_containers()

        mock_client.containers.list.assert_called_once()

    def test_handles_docker_unavailable(self):
        """Should not crash if Docker is unavailable."""
        with patch("app.services.sandbox_manager.get_docker_client", side_effect=Exception("Docker not running")):
            mgr = SandboxManager()
            mgr.cleanup_orphaned_containers()  # Should not raise

    def test_continues_on_individual_failure(self):
        """Should continue removing other containers if one fails."""
        mock_container1 = MagicMock()
        mock_container1.name = "sandbox-abc123"
        mock_container1.stop.side_effect = Exception("already stopped")
        mock_container2 = MagicMock()
        mock_container2.name = "sandbox-def456"

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container1, mock_container2]

        with patch("app.services.sandbox_manager.get_docker_client", return_value=mock_client):
            mgr = SandboxManager()
            mgr.cleanup_orphaned_containers()

        # Second container should still be cleaned up despite first failing
        mock_container2.stop.assert_called_once_with(timeout=5)
        mock_container2.remove.assert_called_once_with(force=True)
