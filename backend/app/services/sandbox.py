"""Sandbox management service."""
import json
import logging
from typing import Any

import modal

from app.services.modal_config import get_game_image, get_sandbox_config

logger = logging.getLogger(__name__)


class GameSandbox:
    """Manages a game sandbox for a user session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.sandbox: modal.Sandbox | None = None
        self.app = modal.App.lookup("claude-code-game", create_if_missing=True)
        self._image = get_game_image()

    async def create(self) -> str:
        """Create a new sandbox. Returns sandbox ID."""
        logger.info(f"Creating sandbox for session {self.session_id}")

        config = get_sandbox_config(self._image)
        self.sandbox = modal.Sandbox.create(app=self.app, **config)

        logger.info(f"Sandbox created: {self.sandbox.object_id}")
        return self.sandbox.object_id

    async def setup_credentials(self, api_key: str) -> bool:
        """Setup Claude credentials in sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        creds = json.dumps({"apiKey": api_key})
        setup_cmd = f"""
        mkdir -p /home/claude/.claude &&
        echo '{creds}' > /home/claude/.claude/.credentials.json &&
        chmod 600 /home/claude/.claude/.credentials.json &&
        chown claude:claude /home/claude/.claude/.credentials.json
        """

        process = self.sandbox.exec("sh", "-c", setup_cmd)
        process.wait()

        return process.returncode == 0

    async def start_ttyd(self, port: int = 7681) -> bool:
        """Start ttyd terminal server in sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Start ttyd in background
        cmd = f"ttyd -W -p {port} su - claude"
        self.sandbox.exec("sh", "-c", f"nohup {cmd} > /tmp/ttyd.log 2>&1 &")

        # Give it a moment to start
        import asyncio
        await asyncio.sleep(2)

        return True

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude's messages from sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Find the latest .jsonl file
        find_cmd = "find /home/claude/.claude/projects -name '*.jsonl' -type f | head -1"
        process = self.sandbox.exec("sh", "-c", find_cmd)
        stdout = process.stdout.read()
        process.wait()

        jsonl_path = stdout.strip()
        if not jsonl_path:
            return []

        # Read the file
        process = self.sandbox.exec("cat", jsonl_path)
        content = process.stdout.read()
        process.wait()

        messages = []
        for line in content.strip().split("\n"):
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        return messages

    async def exec_command(self, *args: str) -> tuple[str, str, int]:
        """Execute a command in the sandbox.

        Returns (stdout, stderr, return_code)
        """
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        process = self.sandbox.exec(*args)
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        process.wait()

        return stdout, stderr, process.returncode

    async def terminate(self):
        """Terminate the sandbox."""
        if self.sandbox:
            self.sandbox.terminate()
            logger.info(f"Sandbox terminated for session {self.session_id}")
