"""Fly.io sandbox service using Machines API."""
import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FLY_MACHINES_API = "https://api.machines.dev/v1"


class FlySandbox:
    """Fly.io machine sandbox for game sessions."""

    def __init__(self, machine_id: str, machine_url: str):
        self.machine_id = machine_id
        self.machine_url = machine_url
        self.workspace_dir = None  # Not used for Fly, verification uses exec

    @classmethod
    async def create(cls, level_number: int = 1) -> "FlySandbox":
        """Create a new Fly machine for the game session."""
        app_name = settings.fly_sandbox_app
        api_token = settings.fly_api_token

        if not api_token:
            raise ValueError("FLY_API_TOKEN not configured")

        # Debug: log token info
        logger.info(f"[DEBUG] Token length: {len(api_token)}, starts with: {api_token[:30]}...")
        logger.info(f"[DEBUG] App name: {app_name}")

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        # Debug: log the full request
        url = f"{FLY_MACHINES_API}/apps/{app_name}/machines"
        logger.info(f"[DEBUG] POST URL: {url}")
        logger.info(f"[DEBUG] Auth header: Bearer {api_token[:40]}...")

        # Machine configuration - omit image to use the app's currently deployed image
        machine_config = {
            "config": {
                "env": {
                    "LEVEL_NUMBER": str(level_number),
                },
                "services": [
                    {
                        "ports": [
                            {
                                "port": 443,
                                "handlers": ["tls", "http"],
                            }
                        ],
                        "protocol": "tcp",
                        "internal_port": 7681,
                        "concurrency": {
                            "type": "connections",
                            "hard_limit": 25,
                            "soft_limit": 20,
                        },
                        # Prevent auto-stop which kills WebSocket connections
                        "autostop": "off",
                        "autostart": True,
                        "min_machines_running": 0,
                    }
                ],
                "guest": {
                    "cpu_kind": "shared",
                    "cpus": 2,
                    "memory_mb": 2048,
                },
                # Disable auto-stop to keep websocket connections alive
                "auto_destroy": False,
            },
            "region": settings.fly_region,
        }

        # If a specific image is configured, use it
        if settings.fly_sandbox_image:
            machine_config["config"]["image"] = settings.fly_sandbox_image

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create the machine
            response = await client.post(
                f"{FLY_MACHINES_API}/apps/{app_name}/machines",
                headers=headers,
                json=machine_config,
            )

            if response.status_code not in (200, 201):
                try:
                    error_text = response.text
                except Exception:
                    error_text = response.content.decode('utf-8', errors='replace')
                logger.error(f"Failed to create Fly machine: {error_text}")
                raise RuntimeError(f"Failed to create Fly machine: {error_text}")

            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse machine response: {e}, content: {response.content[:200]}")
                raise RuntimeError(f"Failed to parse machine response: {e}")

            machine_id = data["id"]

            # Wait for machine to start
            await cls._wait_for_machine(client, app_name, machine_id, headers)

            # For external access to a SPECIFIC machine, use the machine ID subdomain
            # Format: https://{machine_id}.vm.{app_name}.fly.dev
            # This ensures the connection goes to this specific machine, not load-balanced
            public_url = f"https://{machine_id}.vm.{app_name}.fly.dev"

            logger.info(f"Created Fly machine: {machine_id}, URL: {public_url}")

            return cls(machine_id=machine_id, machine_url=public_url)

    @classmethod
    async def _wait_for_machine(
        cls,
        client: httpx.AsyncClient,
        app_name: str,
        machine_id: str,
        headers: dict,
        timeout: int = 30,
    ) -> None:
        """Wait for machine to be in started state."""
        import asyncio

        for _ in range(timeout):
            response = await client.get(
                f"{FLY_MACHINES_API}/apps/{app_name}/machines/{machine_id}",
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                state = data.get("state")
                if state == "started":
                    return
                if state in ("failed", "destroyed"):
                    raise RuntimeError(f"Machine entered {state} state")
            await asyncio.sleep(1)

        raise RuntimeError("Timeout waiting for machine to start")

    async def exec_command(self, *args: str) -> tuple[str, str, int]:
        """Execute a command in the machine via Fly exec API.

        Note: Fly exec doesn't handle pipes (|) well. Avoid using them.
        """
        import shlex

        app_name = settings.fly_sandbox_app
        api_token = settings.fly_api_token

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        # Join args into a single command string - Fly exec expects a string, not array
        cmd_str = " ".join(shlex.quote(arg) for arg in args)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{FLY_MACHINES_API}/apps/{app_name}/machines/{self.machine_id}/exec",
                headers=headers,
                json={"cmd": cmd_str},
            )

            if response.status_code != 200:
                try:
                    error_text = response.text
                except Exception:
                    error_text = response.content.decode('utf-8', errors='replace')
                logger.error(f"Exec failed: {error_text}")
                return "", error_text, 1

            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse exec response: {e}")
                return "", str(e), 1

            # Fly exec API returns plain text stdout/stderr (not base64)
            stdout = data.get("stdout", "")
            stderr = data.get("stderr", "")
            exit_code = data.get("exit_code", 0)

            logger.debug(f"exec_command: {cmd_str} -> exit={exit_code}, stdout_len={len(stdout)}")

            return stdout, stderr, exit_code

    async def read_file(self, path: str) -> str | None:
        """Read a file from the machine."""
        stdout, stderr, returncode = await self.exec_command("cat", path)
        if returncode != 0:
            return None
        return stdout

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude Code messages log from the machine.

        Claude Code stores conversations at:
        ~/.claude/projects/<project-path-hash>/<conversation-id>.jsonl

        We read all conversation files (excluding subagent files) and combine messages.
        """
        # Find .jsonl files in the workspace project directory (no pipes - Fly exec doesn't handle them)
        find_stdout, _, _ = await self.exec_command(
            "find", "/home/claude/.claude/projects/-home-claude-workspace",
            "-maxdepth", "1", "-name", "*.jsonl", "-type", "f"
        )
        logger.debug(f"read_messages_log: find output: {find_stdout[:500] if find_stdout else 'none'}")

        if not find_stdout.strip():
            # Fallback: try broader search
            find_stdout, _, _ = await self.exec_command(
                "find", "/home/claude/.claude/projects",
                "-maxdepth", "2", "-name", "*.jsonl", "-type", "f"
            )
            logger.debug(f"read_messages_log: fallback find: {find_stdout[:500] if find_stdout else 'none'}")

        if not find_stdout.strip():
            logger.debug("read_messages_log: no .jsonl files found")
            return []

        # Filter to only conversation files (not subagents)
        files = [f.strip() for f in find_stdout.strip().split("\n") if f.strip()]
        conversation_files = [f for f in files if "/subagents/" not in f and f.endswith(".jsonl")]

        logger.debug(f"read_messages_log: conversation files: {conversation_files}")

        if not conversation_files:
            return []

        messages = []
        for filepath in conversation_files:
            content = await self.read_file(filepath)
            if content:
                for line in content.strip().split("\n"):
                    if line.strip():
                        try:
                            messages.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        logger.info(f"read_messages_log: parsed {len(messages)} messages from {len(conversation_files)} files")
        return messages

    async def terminate(self) -> None:
        """Stop and delete the machine."""
        app_name = settings.fly_sandbox_app
        api_token = settings.fly_api_token

        headers = {
            "Authorization": f"Bearer {api_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Stop the machine first
            await client.post(
                f"{FLY_MACHINES_API}/apps/{app_name}/machines/{self.machine_id}/stop",
                headers=headers,
            )

            # Delete the machine
            response = await client.delete(
                f"{FLY_MACHINES_API}/apps/{app_name}/machines/{self.machine_id}",
                headers=headers,
            )

            if response.status_code not in (200, 204):
                logger.warning(f"Failed to delete machine {self.machine_id}: {response.text}")
            else:
                logger.info(f"Terminated Fly machine: {self.machine_id}")

    def get_ttyd_url(self) -> str:
        """Get the public ttyd URL for this machine."""
        # Use machine-specific subdomain to route to THIS specific machine
        return self.machine_url
