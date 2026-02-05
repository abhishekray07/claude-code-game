"""Modal sandbox with ttyd basic auth."""
import asyncio
import json
import logging
import queue
import threading
from typing import Any

import modal

from app.config import settings
from app.services.modal_config import get_game_image

logger = logging.getLogger(__name__)


class ModalSandbox:
    """Modal sandbox with secure ttyd access."""

    def __init__(self, session_id: str, ttyd_password: str):
        self.session_id = session_id
        self.ttyd_password = ttyd_password
        self.sandbox: modal.Sandbox | None = None
        self.tunnel_url: str | None = None
        self._app = modal.App.lookup(settings.modal_app_name, create_if_missing=True)
        self._image = get_game_image()
        # Interactive shell state
        self._shell_process = None
        self._shell_running = False
        self._output_queue: queue.Queue = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    async def create(self) -> str:
        """Create sandbox and start ttyd. Returns auth'd terminal URL."""
        logger.info(f"Creating Modal sandbox for session {self.session_id}")

        # Create sandbox with ttyd port exposed
        self.sandbox = modal.Sandbox.create(
            app=self._app,
            image=self._image,
            timeout=settings.sandbox_timeout_seconds,
            cpu=settings.sandbox_cpu,
            memory=settings.sandbox_memory_mb,
            encrypted_ports=[settings.ttyd_port],
        )
        logger.info(f"Sandbox created: {self.sandbox.object_id}")

        return self.sandbox.object_id

    async def setup_credentials(self, api_key: str) -> bool:
        """Setup Anthropic API key in sandbox environment."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Write credentials file
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

    async def start_ttyd(self) -> str:
        """Start ttyd. Returns terminal URL."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Start ttyd without auth for now (Modal tunnel provides isolation)
        # TODO: Add token-based auth for production
        cmd = f"ttyd -W -p {settings.ttyd_port} su - claude"
        self.sandbox.exec("sh", "-c", f"nohup {cmd} > /tmp/ttyd.log 2>&1 &")

        # Wait for ttyd to start
        await asyncio.sleep(3)

        # Get tunnel URL
        tunnels = self.sandbox.tunnels()
        if settings.ttyd_port not in tunnels:
            raise RuntimeError(f"Tunnel for port {settings.ttyd_port} not available")

        self.tunnel_url = tunnels[settings.ttyd_port].url

        logger.info(f"ttyd started, tunnel ready for session {self.session_id}")
        return self.tunnel_url

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude's messages.jsonl from sandbox."""
        if not self.sandbox:
            return []

        # Find the latest .jsonl file
        find_cmd = "find /home/claude/.claude/projects -name '*.jsonl' -type f 2>/dev/null | head -1"
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
        """Execute a command in the sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        process = self.sandbox.exec(*args)
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        process.wait()

        return stdout, stderr, process.returncode

    async def copy_exercise_files(self, source_dir: str) -> bool:
        """Copy exercise files to sandbox workspace."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        from pathlib import Path

        source = Path(source_dir)
        if not source.exists():
            logger.warning(f"Exercise directory not found: {source_dir}")
            return False

        # Skip these directories and file patterns
        skip_dirs = {"__pycache__", ".git", ".venv", "node_modules", ".pyc"}
        skip_extensions = {".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe"}

        for item in source.rglob("*"):
            # Skip unwanted directories
            if any(skip_dir in item.parts for skip_dir in skip_dirs):
                continue

            if item.is_file():
                # Skip binary files
                if item.suffix in skip_extensions:
                    continue

                rel_path = item.relative_to(source)
                dest_path = f"/home/claude/{rel_path}"

                # Create parent directory
                parent = str(Path(dest_path).parent)
                self.sandbox.exec("sh", "-c", f"mkdir -p {parent}")

                # Try to read as text, skip if binary
                try:
                    content = item.read_text(encoding="utf-8")
                    # Write file using heredoc
                    self.sandbox.exec("sh", "-c", f"cat > {dest_path} << 'EOFMARKER'\n{content}\nEOFMARKER")
                    self.sandbox.exec("chown", "claude:claude", dest_path)
                except UnicodeDecodeError:
                    logger.debug(f"Skipping binary file: {item}")
                    continue

        logger.info(f"Exercise files copied from {source_dir}")
        return True

    def terminate(self) -> None:
        """Terminate the sandbox."""
        self._shell_running = False
        self._shell_process = None
        if self.sandbox:
            try:
                self.sandbox.terminate()
                logger.info(f"Sandbox terminated for session {self.session_id}")
            except Exception as e:
                logger.error(f"Error terminating sandbox: {e}")

    def start_shell(self) -> None:
        """Start an interactive shell process with PTY-like behavior."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        if self._shell_running:
            logger.warning(f"Shell already running for session {self.session_id}")
            return

        # Use script command for PTY-like behavior
        # bufsize=-1 for unbuffered, text=False for binary mode
        self._shell_process = self.sandbox.exec(
            "script", "-q", "/dev/null", "-c", "su - claude",
            bufsize=-1,
            text=False,
        )
        self._shell_running = True

        # Start background thread to read stdout
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        logger.info(f"Interactive shell started for session {self.session_id}")

    def _read_stdout(self) -> None:
        """Background thread to read stdout into queue."""
        logger.info(f"Reader thread started for session {self.session_id}")
        try:
            # Iterate over stdout for streaming output
            for line in self._shell_process.stdout:
                if not self._shell_running:
                    break
                if line:
                    self._output_queue.put(line)
            logger.info(f"stdout iteration ended for session {self.session_id}")
        except Exception as e:
            logger.error(f"Reader thread error: {e}")
        finally:
            logger.info(f"Reader thread ended for session {self.session_id}")
            self._shell_running = False

    def write(self, data: bytes) -> None:
        """Write data to the shell's stdin."""
        if not self._shell_process or not self._shell_running:
            logger.error(f"Write failed: shell_process={self._shell_process is not None}, shell_running={self._shell_running}")
            raise ValueError("Shell not running")

        try:
            # Decode bytes to string for Modal's stdin
            text = data.decode("utf-8")
            logger.info(f"Writing to stdin: {repr(text)}")
            self._shell_process.stdin.write(text)
            # Try to flush if available
            if hasattr(self._shell_process.stdin, 'flush'):
                self._shell_process.stdin.flush()
            logger.info(f"Write successful")
        except Exception as e:
            logger.error(f"Error writing to shell: {e}")
            self._shell_running = False
            raise

    def read(self, timeout: float = 0.1) -> bytes | None:
        """Read available data from output queue."""
        if not self._shell_running:
            return None
        try:
            data = self._output_queue.get(timeout=timeout)
            if isinstance(data, str):
                return data.encode("utf-8")
            return data
        except queue.Empty:
            return None

    @property
    def shell_running(self) -> bool:
        """Check if shell is currently running."""
        return self._shell_running
