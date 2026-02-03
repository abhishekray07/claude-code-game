"""Docker-based sandbox using ttyd for terminal access."""
import asyncio
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container

logger = logging.getLogger(__name__)


def get_docker_client() -> docker.DockerClient:
    """Get a Docker client with auto-detection of socket location.

    On macOS with Docker Desktop, the socket may be at a non-standard location.
    This function tries common locations if the default fails.

    Returns:
        Docker client instance.

    Raises:
        DockerException: If no Docker connection can be established.
    """
    # If DOCKER_HOST is set, use the default behavior
    if os.environ.get("DOCKER_HOST"):
        return docker.from_env()

    # Try default location first
    try:
        return docker.from_env()
    except DockerException:
        pass

    # Common macOS Docker Desktop socket locations
    socket_paths = [
        Path.home() / ".docker" / "run" / "docker.sock",
        Path("/var/run/docker.sock"),
    ]

    for socket_path in socket_paths:
        if socket_path.exists():
            try:
                base_url = f"unix://{socket_path}"
                client = docker.DockerClient(base_url=base_url)
                # Test the connection
                client.ping()
                logger.info(f"Connected to Docker at {base_url}")
                return client
            except DockerException:
                continue

    # If all else fails, raise with helpful message
    raise DockerException(
        "Could not connect to Docker. Please ensure Docker is running. "
        "On macOS, you may need to set DOCKER_HOST=unix://$HOME/.docker/run/docker.sock"
    )


class DockerSandbox:
    """Docker sandbox with ttyd terminal access."""

    def __init__(self, session_id: str, port: int, level_number: int = 1):
        self.session_id = session_id
        self.port = port
        self.level_number = level_number
        self.container: Container | None = None
        self.ttyd_token: str | None = None
        self._docker = get_docker_client()

    async def create(self) -> str:
        """Create and start the sandbox container.

        Returns:
            Container ID.
        """
        logger.info(f"Creating Docker sandbox for session {self.session_id} on port {self.port}")

        # Generate secure token for ttyd authentication
        self.ttyd_token = secrets.token_urlsafe(32)

        self.container = await asyncio.to_thread(
            self._docker.containers.run,
            "claude-game-sandbox:latest",
            detach=True,
            remove=True,
            name=f"sandbox-{self.session_id}",
            environment={
                "LEVEL_NUMBER": str(self.level_number),
                "TTYD_TOKEN": self.ttyd_token,
            },
            ports={"7681/tcp": ("127.0.0.1", self.port)},
        )

        container_id = self.container.id
        if container_id is None:
            raise RuntimeError("Container created but has no ID")
        logger.info(f"Container started: {container_id[:12]}")
        return container_id

    async def setup_credentials(self, api_key: str) -> bool:
        """Setup Anthropic API key in container.

        Args:
            api_key: Anthropic API key.

        Returns:
            True if credentials were set up successfully.
        """
        if not self.container:
            raise ValueError("Container not created")

        # Write credentials to container
        creds = json.dumps({"apiKey": api_key})
        # Escape single quotes in credentials JSON for shell safety
        escaped_creds = creds.replace("'", "'\"'\"'")
        cmd = f'''
        mkdir -p /home/claude/.claude && \
        echo '{escaped_creds}' > /home/claude/.claude/.credentials.json && \
        chown claude:claude /home/claude/.claude/.credentials.json && \
        chmod 600 /home/claude/.claude/.credentials.json
        '''

        exit_code, output = await asyncio.to_thread(
            self.container.exec_run,
            ["sh", "-c", cmd],
            user="root"  # Use root to ensure directory creation works
        )

        if exit_code != 0:
            logger.error(f"Failed to setup credentials: {output.decode('utf-8')}")
            return False

        logger.info(f"Credentials configured for session {self.session_id}")
        return True

    async def exec_command(self, *args: str) -> tuple[str, str, int]:
        """Execute a command in the container.

        Args:
            *args: Command and arguments to execute.

        Returns:
            Tuple of (stdout, stderr, exit_code).
        """
        if not self.container:
            raise ValueError("Container not created")

        exit_code, output = await asyncio.to_thread(
            self.container.exec_run,
            list(args),
            user="claude",
            workdir="/home/claude/workspace"
        )

        # Docker exec_run returns combined output
        return output.decode("utf-8"), "", exit_code

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude's messages.jsonl from container.

        Returns:
            List of message dictionaries from the JSONL log.
        """
        if not self.container:
            return []

        # Find jsonl file - Claude Code stores logs in ~/.claude/projects/
        find_cmd = "find /home/claude/.claude/projects -name '*.jsonl' -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1"
        exit_code, output = await asyncio.to_thread(
            self.container.exec_run,
            ["sh", "-c", find_cmd],
            user="claude"
        )

        jsonl_path = output.decode("utf-8").strip()
        if not jsonl_path:
            logger.debug(f"No JSONL log found for session {self.session_id}")
            return []

        # Read file contents
        exit_code, output = await asyncio.to_thread(
            self.container.exec_run,
            ["cat", jsonl_path],
            user="claude"
        )

        if exit_code != 0:
            logger.warning(f"Failed to read JSONL log: {output.decode('utf-8')}")
            return []

        messages = []
        for line in output.decode("utf-8").strip().split("\n"):
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.debug(f"Skipping invalid JSON line: {line[:50]}...")

        logger.debug(f"Read {len(messages)} messages from log for session {self.session_id}")
        return messages

    async def update_level(self, level_number: int) -> None:
        """Swap exercise files for a new level in the running container."""
        if not self.container:
            raise ValueError("Container not created")

        self.level_number = level_number
        level_num = f"{level_number:02d}"

        cmd = f'''
        LEVEL_DIR=$(find /home/claude/levels -maxdepth 1 -type d -name "{level_num}-*" 2>/dev/null | head -1)
        if [ -n "$LEVEL_DIR" ] && [ -d "$LEVEL_DIR/exercise" ]; then
            rm -rf /home/claude/workspace/*
            rm -rf /home/claude/workspace/.claude 2>/dev/null || true
            rm -rf /home/claude/workspace/.git 2>/dev/null || true
            find /home/claude/.claude/projects -name '*.jsonl' -type f -delete 2>/dev/null || true
            cp -r "$LEVEL_DIR/exercise/"* /home/claude/workspace/
            cp -r "$LEVEL_DIR/exercise/".* /home/claude/workspace/ 2>/dev/null || true
            chown -R claude:claude /home/claude/workspace
        fi
        '''

        exit_code, output = await asyncio.to_thread(
            self.container.exec_run,
            ["sh", "-c", cmd],
            user="root"
        )

        if exit_code != 0:
            logger.error(f"Failed to update level files: {output.decode('utf-8')}")
            raise RuntimeError(f"Failed to update level to {level_number}")

        logger.info(f"Updated container {self.session_id} to level {level_number}")

    async def terminate(self) -> None:
        """Stop and remove the container."""
        if self.container:
            try:
                await asyncio.to_thread(self.container.stop, timeout=5)
                logger.info(f"Container stopped: {self.session_id}")
            except NotFound:
                logger.debug(f"Container already removed: {self.session_id}")
            except Exception as e:
                logger.error(f"Error stopping container {self.session_id}: {e}")
            finally:
                self.container = None
                self.ttyd_token = None

    def get_terminal_url(self) -> str:
        """Get the ttyd WebSocket URL for this container.

        Returns:
            WebSocket URL for terminal connection.
        """
        return f"ws://localhost:{self.port}/ws"

    def get_ttyd_token(self) -> str | None:
        """Get the ttyd authentication token.

        Returns:
            The token required to authenticate with ttyd, or None if not created.
        """
        return self.ttyd_token

