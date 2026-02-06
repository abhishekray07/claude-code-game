"""Tests for container hardening options in DockerSandbox."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.docker_sandbox import DockerSandbox


@pytest.mark.asyncio
class TestContainerHardening:
    """Verify security options are passed to containers.run()."""

    async def test_resource_limits_passed(self):
        """Container should have memory, CPU, and PID limits."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_client.containers.run.return_value = mock_container

        with patch("app.services.docker_sandbox.get_docker_client", return_value=mock_client):
            sandbox = DockerSandbox("test", 10001, level_number=1)
            await sandbox.create()

        call_kwargs = mock_client.containers.run.call_args
        assert call_kwargs.kwargs["mem_limit"] == "1g"
        assert call_kwargs.kwargs["cpu_quota"] == 100000
        assert call_kwargs.kwargs["pids_limit"] == 100

    async def test_security_options_passed(self):
        """Container should have read-only rootfs, dropped caps, no-new-privileges."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_client.containers.run.return_value = mock_container

        with patch("app.services.docker_sandbox.get_docker_client", return_value=mock_client):
            sandbox = DockerSandbox("test", 10001, level_number=1)
            await sandbox.create()

        call_kwargs = mock_client.containers.run.call_args
        assert call_kwargs.kwargs["read_only"] is True
        assert call_kwargs.kwargs["security_opt"] == ["no-new-privileges:true"]
        assert call_kwargs.kwargs["cap_drop"] == ["ALL"]
        assert "CHOWN" in call_kwargs.kwargs["cap_add"]
        assert "SETUID" in call_kwargs.kwargs["cap_add"]
        assert "SETGID" in call_kwargs.kwargs["cap_add"]

    async def test_tmpfs_mounts_present(self):
        """Container should have writable tmpfs mounts for workspace, .claude, and /tmp."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_client.containers.run.return_value = mock_container

        with patch("app.services.docker_sandbox.get_docker_client", return_value=mock_client):
            sandbox = DockerSandbox("test", 10001, level_number=1)
            await sandbox.create()

        call_kwargs = mock_client.containers.run.call_args
        tmpfs = call_kwargs.kwargs["tmpfs"]
        assert "/tmp" in tmpfs
        assert "/home/claude/.claude" in tmpfs
        assert "/home/claude/workspace" in tmpfs
