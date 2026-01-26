"""Local sandbox using PTY for proper terminal support."""
import asyncio
import json
import os
import pty
import select
import signal
import subprocess
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LocalSandbox:
    """Local sandbox with real PTY support."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.master_fd: int | None = None
        self.slave_fd: int | None = None
        self.pid: int | None = None
        self.workspace_dir: Path | None = None
        self.claude_dir: Path | None = None
        self.api_key: str | None = None
        self.session_start_time: float = 0  # Unix timestamp

    async def create(self) -> str:
        """Create sandbox workspace."""
        import tempfile
        import time
        # Create a temp workspace directory
        self.workspace_dir = Path(tempfile.mkdtemp(prefix=f"claude-game-{self.session_id}-"))
        # Record session start time for message filtering
        self.session_start_time = time.time()
        logger.info(f"Created workspace: {self.workspace_dir}")
        return self.session_id

    async def setup_credentials(self, api_key: str) -> bool:
        """Setup Claude credentials."""
        # Store API key to pass as environment variable
        self.api_key = api_key

        # Use user's existing .claude directory to avoid onboarding
        # For local dev, this is fine - messages are already separated by project
        self.claude_dir = Path.home() / ".claude"

        logger.info(f"Using existing claude config: {self.claude_dir}")
        return True

    def start_shell(self) -> tuple[int, int]:
        """Start a shell with PTY. Returns (master_fd, pid)."""
        # Create PTY
        self.master_fd, self.slave_fd = pty.openpty()

        # Fork process
        self.pid = os.fork()

        if self.pid == 0:
            # Child process
            os.close(self.master_fd)

            # Create new session and set controlling terminal
            os.setsid()

            # Set slave as controlling terminal
            import fcntl
            import termios
            fcntl.ioctl(self.slave_fd, termios.TIOCSCTTY, 0)

            # Redirect stdin/stdout/stderr to slave
            os.dup2(self.slave_fd, 0)
            os.dup2(self.slave_fd, 1)
            os.dup2(self.slave_fd, 2)

            if self.slave_fd > 2:
                os.close(self.slave_fd)

            # Change to workspace directory
            os.chdir(str(self.workspace_dir))

            # Set environment
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            # Clean, short prompt with colors
            env["PS1"] = "\\[\\033[32m\\]claude@game\\[\\033[0m\\]:\\[\\033[34m\\]~\\[\\033[0m\\]$ "
            # Suppress macOS zsh message
            env["BASH_SILENCE_DEPRECATION_WARNING"] = "1"
            # Set API key so Claude Code doesn't ask for login
            if self.api_key:
                env["ANTHROPIC_API_KEY"] = self.api_key

            # Exec bash with clean startup
            os.execvpe("bash", ["bash", "--norc", "--noprofile", "-i"], env)

        else:
            # Parent process
            os.close(self.slave_fd)
            logger.info(f"Shell started with PID {self.pid}")
            return self.master_fd, self.pid

    def read(self, timeout: float = 0.1) -> bytes | None:
        """Read from PTY (non-blocking)."""
        if self.master_fd is None:
            return None

        ready, _, _ = select.select([self.master_fd], [], [], timeout)
        if ready:
            try:
                return os.read(self.master_fd, 4096)
            except OSError:
                return None
        return None

    def write(self, data: bytes) -> int:
        """Write to PTY."""
        if self.master_fd is None:
            return 0
        return os.write(self.master_fd, data)

    def resize(self, rows: int, cols: int):
        """Resize the PTY."""
        if self.master_fd is None:
            return

        import struct
        import fcntl
        import termios

        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude's messages from this session's workspace."""
        if not self.workspace_dir:
            return []

        # Claude Code stores messages in ~/.claude/projects/-path-to-workspace/
        # The path is encoded (slashes become dashes)
        projects_dir = Path.home() / ".claude" / "projects"
        if not projects_dir.exists():
            return []

        # Find the project directory for our workspace
        # Claude Code encodes the path with leading dash
        workspace_path = str(self.workspace_dir)
        encoded_path = "-" + workspace_path.replace("/", "-")

        project_dir = projects_dir / encoded_path
        if not project_dir.exists():
            # Try to find by partial match (workspace name)
            workspace_name = self.workspace_dir.name
            matching = [d for d in projects_dir.iterdir() if workspace_name in d.name]
            if matching:
                project_dir = matching[0]
            else:
                return []

        # Find .jsonl files
        jsonl_files = list(project_dir.glob("*.jsonl"))
        if not jsonl_files:
            return []

        # Get most recent
        latest = max(jsonl_files, key=lambda p: p.stat().st_mtime)

        messages = []
        for line in latest.read_text().strip().split("\n"):
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        return messages

    async def exec_command(self, *args: str) -> tuple[str, str, int]:
        """Execute a command in the workspace."""
        result = subprocess.run(
            args,
            cwd=self.workspace_dir,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode

    async def terminate(self):
        """Terminate the sandbox."""
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, 0)
            except (OSError, ChildProcessError):
                pass

        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass

        # Cleanup workspace
        if self.workspace_dir and self.workspace_dir.exists():
            import shutil
            shutil.rmtree(self.workspace_dir, ignore_errors=True)

        logger.info(f"Sandbox terminated: {self.session_id}")
