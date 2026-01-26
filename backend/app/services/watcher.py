"""Game watcher - polls for level completion and stuck detection."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Awaitable, Callable

from typing import Any, Protocol

from app.models.level import Level
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)


class SandboxProtocol(Protocol):
    """Protocol for sandbox interface."""
    async def read_messages_log(self) -> list[dict]: ...
    async def exec_command(self, *args: str) -> tuple[str, str, int]: ...


class GameWatcher:
    """Watches a game session for completion and provides hints."""

    def __init__(
        self,
        sandbox: Any,  # LocalSandbox or GameSandbox
        level: Level,
        on_complete: Callable[[], Awaitable[None]],
        on_hint: Callable[[str], Awaitable[None]],
        on_progress: Callable[[dict], Awaitable[None]] | None = None,
    ):
        self.sandbox = sandbox
        self.level = level
        self.on_complete = on_complete
        self.on_hint = on_hint
        self.on_progress = on_progress
        self.verification = VerificationEngine(sandbox)

        self.started_at = datetime.utcnow()
        self.hints_shown: set[int] = set()
        self._running = False
        self._completed = False

    async def start(self):
        """Start watching."""
        self._running = True
        logger.info(f"Watcher started for level {self.level.id}")

        while self._running and not self._completed:
            try:
                # Check completion
                progress = await self.verification.get_progress(self.level)

                # Emit progress update
                if self.on_progress:
                    await self.on_progress(progress)

                if progress["completed"]:
                    logger.info(f"Level {self.level.id} completed!")
                    self._completed = True
                    await self.on_complete()
                    break

                # Check hints
                elapsed = datetime.utcnow() - self.started_at
                for hint in self.level.hints:
                    if hint.after_minutes not in self.hints_shown:
                        if elapsed > timedelta(minutes=hint.after_minutes):
                            self.hints_shown.add(hint.after_minutes)
                            await self.on_hint(hint.text)

                # Check timeout
                if elapsed > timedelta(minutes=self.level.limits.max_duration_minutes):
                    logger.warning(f"Level {self.level.id} timed out")
                    await self.on_hint(
                        f"⏰ Time's up! You've been working on this for "
                        f"{self.level.limits.max_duration_minutes} minutes. "
                        f"Type /skip to move on."
                    )

            except Exception as e:
                logger.error(f"Watcher error: {e}")

            # Poll interval
            await asyncio.sleep(3)

    def stop(self):
        """Stop watching."""
        self._running = False
        logger.info(f"Watcher stopped for level {self.level.id}")

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    @property
    def is_completed(self) -> bool:
        """Check if level is completed."""
        return self._completed

    def get_elapsed_time(self) -> timedelta:
        """Get elapsed time since start."""
        return datetime.utcnow() - self.started_at
