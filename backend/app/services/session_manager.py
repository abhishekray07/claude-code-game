"""Session manager with activity tracking and cleanup."""
import asyncio
import logging
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """A game session with activity tracking."""
    session_id: str
    sandbox: Any  # Modal, Local, or Fly sandbox
    level: Any  # Level object
    level_number: int
    ttyd_url: str  # Auth'd URL for frontend
    ttyd_password: str
    client_ip: str = ""  # For rate limiting
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    completed: bool = False


class SessionManager:
    """Manages game sessions with activity-based cleanup."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._sessions_by_ip: dict[str, list[str]] = defaultdict(list)  # IP -> session_ids

    def create_session_id(self) -> str:
        """Generate cryptographically secure session ID."""
        return secrets.token_urlsafe(32)

    def generate_ttyd_password(self) -> str:
        """Generate random password for ttyd basic auth."""
        return secrets.token_urlsafe(16)

    def count_sessions_by_ip(self, client_ip: str) -> int:
        """Count active sessions for a given IP."""
        # Clean up stale entries
        valid_sessions = [
            sid for sid in self._sessions_by_ip[client_ip]
            if sid in self._sessions
        ]
        self._sessions_by_ip[client_ip] = valid_sessions
        return len(valid_sessions)

    def can_create_session(self, client_ip: str, max_per_ip: int = 3) -> bool:
        """Check if IP can create a new session (rate limiting)."""
        return self.count_sessions_by_ip(client_ip) < max_per_ip

    def add(self, session: Session) -> None:
        """Add a session."""
        self._sessions[session.session_id] = session
        if session.client_ip:
            self._sessions_by_ip[session.client_ip].append(session.session_id)
        logger.info(f"Session added: {session.session_id}")

    def get(self, session_id: str) -> Session | None:
        """Get a session and update activity timestamp."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = time.time()
        return session

    def remove(self, session_id: str) -> Session | None:
        """Remove and return a session."""
        session = self._sessions.pop(session_id, None)
        if session and session.client_ip:
            try:
                self._sessions_by_ip[session.client_ip].remove(session_id)
            except ValueError:
                pass
        return session

    def touch(self, session_id: str) -> bool:
        """Update activity timestamp. Returns False if session not found."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = time.time()
            return True
        return False

    async def _terminate_sandbox(self, sandbox: Any) -> None:
        """Terminate a sandbox, handling both sync and async terminate methods."""
        try:
            if hasattr(sandbox, 'machine_id'):  # FlySandbox (async)
                await sandbox.terminate()
            else:  # Modal/Local sandbox (sync)
                sandbox.terminate()
        except Exception as e:
            logger.error(f"Error terminating sandbox: {e}")

    async def cleanup_idle_sessions(self) -> None:
        """Terminate sessions that have been idle too long or exceeded TTL."""
        now = time.time()
        idle_timeout = settings.sandbox_idle_timeout_seconds

        # For Fly, also check hard TTL
        machine_ttl = getattr(settings, 'fly_machine_ttl_seconds', 1800)

        to_remove = []
        for session_id, session in self._sessions.items():
            idle_time = now - session.last_activity
            age = now - session.created_at

            # Check idle timeout
            if idle_time > idle_timeout:
                logger.info(f"Session {session_id} idle for {idle_time:.0f}s, terminating")
                to_remove.append(session_id)
            # Check hard TTL (for Fly machines)
            elif age > machine_ttl:
                logger.info(f"Session {session_id} exceeded TTL ({age:.0f}s), terminating")
                to_remove.append(session_id)

        for session_id in to_remove:
            session = self._sessions.pop(session_id, None)
            if session:
                if session.client_ip:
                    try:
                        self._sessions_by_ip[session.client_ip].remove(session_id)
                    except ValueError:
                        pass
                if session.sandbox:
                    await self._terminate_sandbox(session.sandbox)

    async def cleanup_orphaned_fly_machines(self) -> None:
        """Clean up Fly machines that don't have corresponding sessions."""
        if settings.sandbox_mode != "fly":
            return

        try:
            import httpx
            from app.services.fly_sandbox import FLY_MACHINES_API

            app_name = settings.fly_sandbox_app
            api_token = settings.fly_api_token

            if not api_token:
                return

            headers = {"Authorization": f"Bearer {api_token}"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                # List all machines
                response = await client.get(
                    f"{FLY_MACHINES_API}/apps/{app_name}/machines",
                    headers=headers,
                )

                if response.status_code != 200:
                    return

                machines = response.json()

                # Get all machine IDs from active sessions
                active_machine_ids = set()
                for session in self._sessions.values():
                    if hasattr(session.sandbox, 'machine_id'):
                        active_machine_ids.add(session.sandbox.machine_id)

                # Find orphaned machines (running but not in sessions)
                for machine in machines:
                    machine_id = machine.get("id")
                    state = machine.get("state")

                    if state in ("started", "starting") and machine_id not in active_machine_ids:
                        logger.warning(f"Found orphaned Fly machine: {machine_id}, destroying")
                        try:
                            # Stop and delete
                            await client.post(
                                f"{FLY_MACHINES_API}/apps/{app_name}/machines/{machine_id}/stop",
                                headers=headers,
                            )
                            await client.delete(
                                f"{FLY_MACHINES_API}/apps/{app_name}/machines/{machine_id}",
                                headers=headers,
                            )
                        except Exception as e:
                            logger.error(f"Error destroying orphaned machine {machine_id}: {e}")

        except Exception as e:
            logger.error(f"Error cleaning up orphaned machines: {e}")

    async def start_cleanup_loop(self) -> None:
        """Start background cleanup task."""
        async def cleanup_loop():
            orphan_check_counter = 0
            while True:
                await asyncio.sleep(60)  # Check every minute
                await self.cleanup_idle_sessions()

                # Check for orphaned machines every 5 minutes
                orphan_check_counter += 1
                if orphan_check_counter >= 5:
                    orphan_check_counter = 0
                    await self.cleanup_orphaned_fly_machines()

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Session cleanup loop started")

    async def stop_cleanup_loop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session cleanup loop stopped")

    async def terminate_all(self) -> None:
        """Terminate all active sessions."""
        for session_id in list(self._sessions.keys()):
            session = self._sessions.pop(session_id, None)
            if session and session.sandbox:
                await self._terminate_sandbox(session.sandbox)
        self._sessions_by_ip.clear()
        logger.info("All sessions terminated")


# Global instance
session_manager = SessionManager()
