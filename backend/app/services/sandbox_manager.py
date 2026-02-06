"""Manages sandbox container lifecycle and port allocation."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set

from app.config import settings
from app.services.docker_sandbox import DockerSandbox, get_docker_client

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manages sandbox containers with port allocation and cleanup."""

    def __init__(self, port_range: tuple[int, int] = (10001, 10101)):
        self.port_range = port_range
        self.available_ports: Set[int] = set(range(port_range[0], port_range[1]))
        self.sessions: Dict[str, dict] = {}  # session_id -> {sandbox, port, last_active, level, client_ip}
        self._sessions_by_ip: Dict[str, list[str]] = {}  # ip -> [session_ids]
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._shutting_down = False

    def cleanup_orphaned_containers(self) -> None:
        """Remove any sandbox containers left over from a previous run."""
        try:
            client = get_docker_client()
            containers = client.containers.list(
                filters={"name": "sandbox-"}, all=True
            )
            for container in containers:
                try:
                    logger.info(f"Removing orphaned container: {container.name}")
                    container.stop(timeout=5)
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove orphaned container {container.name}: {e}")
        except Exception as e:
            logger.warning(f"Orphan cleanup skipped: {e}")

    def can_create_session_for_ip(self, ip: str, max_per_ip: int) -> bool:
        """Check if an IP can create another session."""
        return len(self._sessions_by_ip.get(ip, [])) < max_per_ip

    def start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cleanup task started")

    async def _cleanup_loop(self) -> None:
        """Periodically cleanup idle sessions."""
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            await self._cleanup_idle_sessions()

    async def _cleanup_idle_sessions(self, max_idle_minutes: int = 30) -> None:
        """Remove sessions idle for too long.

        Args:
            max_idle_minutes: Maximum idle time before cleanup. Defaults to 30.
        """
        now = datetime.now()
        to_remove = []

        # Take a snapshot under lock to avoid race conditions
        async with self._lock:
            sessions_snapshot = list(self.sessions.items())

        for session_id, session in sessions_snapshot:
            idle_time = now - session["last_active"]
            if idle_time > timedelta(minutes=max_idle_minutes):
                to_remove.append(session_id)

        for session_id in to_remove:
            logger.info(f"Cleaning up idle session: {session_id}")
            await self.destroy_session(session_id)

    async def create_session(
        self, session_id: str, level_number: int, api_key: str | None = None,
        client_ip: str = "unknown",
    ) -> dict:
        """Create a new sandbox session.

        Args:
            session_id: Unique identifier for the session.
            level_number: Level number to load in the sandbox.
            api_key: Optional Anthropic API key. If not provided, user authenticates via CLI.

        Returns:
            Dict with session_id, port, and ttyd_token.

        Raises:
            RuntimeError: If no ports are available or manager is shutting down.
            ValueError: If session already exists.
        """
        async with self._lock:
            if self._shutting_down:
                raise RuntimeError("Manager is shutting down")
            if session_id in self.sessions:
                raise ValueError(f"Session {session_id} already exists")
            if len(self.sessions) >= settings.max_sessions:
                raise RuntimeError(f"Maximum sessions ({settings.max_sessions}) reached")
            if not self.available_ports:
                raise RuntimeError("No available ports for new session")
            port = self.available_ports.pop()

        try:
            sandbox = DockerSandbox(session_id, port, level_number)
            await sandbox.create()

            # Only setup credentials if API key is provided
            if api_key:
                await sandbox.setup_credentials(api_key)

            # Wait for ttyd to be ready
            await asyncio.sleep(2)

            async with self._lock:
                self.sessions[session_id] = {
                    "sandbox": sandbox,
                    "port": port,
                    "last_active": datetime.now(),
                    "level_number": level_number,
                    "client_ip": client_ip,
                }
                self._sessions_by_ip.setdefault(client_ip, []).append(session_id)

            logger.info(f"Session created: {session_id} on port {port}")
            return {
                "session_id": session_id,
                "port": port,
                "ttyd_token": sandbox.get_ttyd_token(),
            }
        except Exception:
            async with self._lock:
                self.available_ports.add(port)
            raise

    async def update_session_level(self, session_id: str, level_number: int) -> dict:
        """Update an existing session to a new level without creating a new container."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        sandbox: DockerSandbox = session["sandbox"]
        await sandbox.update_level(level_number)

        async with self._lock:
            session["level_number"] = level_number
            session["last_active"] = datetime.now()

        logger.info(f"Session {session_id} updated to level {level_number}")
        return {
            "session_id": session_id,
            "port": session["port"],
            "ttyd_token": sandbox.get_ttyd_token(),
        }

    async def destroy_session(self, session_id: str) -> None:
        """Destroy a sandbox session.

        Args:
            session_id: Session to destroy.
        """
        async with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                self.available_ports.add(session["port"])
                ip = session.get("client_ip")
                if ip and ip in self._sessions_by_ip:
                    self._sessions_by_ip[ip] = [
                        s for s in self._sessions_by_ip[ip] if s != session_id
                    ]
                    if not self._sessions_by_ip[ip]:
                        del self._sessions_by_ip[ip]

        if session:
            await session["sandbox"].terminate()
            logger.info(f"Session destroyed: {session_id}")

    def get_session(self, session_id: str) -> dict | None:
        """Get session info.

        Args:
            session_id: Session to look up.

        Returns:
            Session dict or None if not found.
        """
        return self.sessions.get(session_id)

    def update_activity(self, session_id: str) -> None:
        """Update last activity time for a session.

        Args:
            session_id: Session to update.
        """
        if session_id in self.sessions:
            self.sessions[session_id]["last_active"] = datetime.now()

    async def shutdown(self) -> None:
        """Cleanup all sessions on shutdown."""
        self._shutting_down = True

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        for session_id in list(self.sessions.keys()):
            await self.destroy_session(session_id)

        logger.info("SandboxManager shutdown complete")


# Global instance
sandbox_manager = SandboxManager()
