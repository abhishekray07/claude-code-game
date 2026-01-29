"""WebSocket terminal endpoint with local PTY sandbox."""
import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.services.local_sandbox import LocalSandbox
from app.services.levels import load_level_by_number
from app.services.watcher import GameWatcher
from app.models.level import Level

logger = logging.getLogger(__name__)
router = APIRouter()

# Active sessions
active_sessions: dict[str, dict] = {}

# Path to starter app
STARTER_APP_DIR = Path(__file__).parent.parent.parent.parent / "levels" / "starter-app"


class StartSessionRequest(BaseModel):
    """Request to start a new game session."""
    api_key: str
    level_number: int = 1


@router.post("/api/sessions")
async def create_session(request: StartSessionRequest):
    """Create a new game session with local sandbox."""
    import uuid
    session_id = str(uuid.uuid4())[:8]

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(status_code=404, detail=f"Level {request.level_number} not found")

    # Create local sandbox
    sandbox = LocalSandbox(session_id)
    try:
        await sandbox.create()
        await sandbox.setup_credentials(request.api_key)

        # Copy starter app to workspace
        await _copy_starter_app(sandbox)

    except Exception as e:
        logger.error(f"Failed to create sandbox: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {e}")

    # Store session
    active_sessions[session_id] = {
        "sandbox": sandbox,
        "level": level,
        "level_number": request.level_number,
        "completed": False,
        "watcher": None,
    }

    return {
        "session_id": session_id,
        "sandbox_id": session_id,
        "status": "ready",
        "level": {
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
            "video": level.video.model_dump() if level.video else None,
            "exercise": level.exercise.model_dump() if level.exercise else None,
        },
    }


async def _copy_starter_app(sandbox: LocalSandbox):
    """Copy starter app files to sandbox workspace."""
    if not STARTER_APP_DIR.exists():
        logger.warning(f"Starter app directory not found: {STARTER_APP_DIR}")
        return

    for file_path in STARTER_APP_DIR.glob("*"):
        if file_path.is_file():
            content = file_path.read_text()
            dest_path = sandbox.workspace_dir / file_path.name
            dest_path.write_text(content)

    logger.info("Starter app copied to workspace")


@router.delete("/api/sessions/{session_id}")
async def stop_session(session_id: str):
    """Stop a game session."""
    session = active_sessions.pop(session_id, None)
    if session:
        if session.get("watcher"):
            session["watcher"].stop()
        await session["sandbox"].terminate()
    return {"session_id": session_id, "status": "stopped"}


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal access with real PTY."""
    await websocket.accept()
    logger.info(f"Terminal WebSocket connected: {session_id}")

    session = active_sessions.get(session_id)
    if not session:
        await websocket.send_text("Error: Session not found\r\n")
        await websocket.close()
        return

    sandbox: LocalSandbox = session["sandbox"]
    level: Level = session["level"]

    # Send level intro with clear formatting
    # Clear screen
    await websocket.send_text("\033[2J\033[H")
    await websocket.send_text("\r\n")
    for line in level.intro.split("\n"):
        await websocket.send_text(line + "\r\n")
    await websocket.send_text("\r\n")
    await websocket.send_text("\033[90m" + "─" * 60 + "\033[0m\r\n")
    await websocket.send_text("\r\n")

    # Start the shell with PTY
    try:
        master_fd, pid = sandbox.start_shell()
    except Exception as e:
        await websocket.send_text(f"Error starting shell: {e}\r\n")
        await websocket.close()
        return

    # Set initial terminal size
    sandbox.resize(24, 80)

    # Setup watcher callbacks
    async def on_complete():
        session["completed"] = True
        # Don't inject text into terminal - it overlaps with Claude Code output
        # Just send the completion marker for the frontend sidebar
        await websocket.send_text("__LEVEL_COMPLETE__")

    async def on_hint(text: str):
        await websocket.send_text(f"\r\n\r\n{text}\r\n")

    async def on_progress(progress: dict):
        pass

    # Start watcher
    watcher = GameWatcher(sandbox, level, on_complete, on_hint, on_progress)
    session["watcher"] = watcher
    watcher_task = asyncio.create_task(watcher.start())

    # Flag to control loops
    running = True

    async def read_from_pty():
        """Read from PTY and send to WebSocket."""
        loop = asyncio.get_event_loop()
        while running:
            try:
                # Read with small timeout to allow checking 'running' flag
                data = await loop.run_in_executor(None, lambda: sandbox.read(0.05))
                if data:
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
            except Exception as e:
                if running:
                    logger.error(f"Error reading from PTY: {e}")
                break

    async def write_to_pty():
        """Read from WebSocket and write to PTY."""
        nonlocal running
        try:
            while running:
                data = await websocket.receive_text()

                # Check for magic commands
                stripped = data.strip()
                if stripped == "/hint":
                    hint_text = level.hints[0].text if level.hints else "No hints available"
                    await websocket.send_text(f"\r\n{hint_text}\r\n")
                    continue
                elif stripped == "/skip":
                    await websocket.send_text("\r\n⏭️ Skipping level...\r\n")
                    session["completed"] = True
                    await websocket.send_text("__LEVEL_COMPLETE__\r\n")
                    continue
                elif stripped == "/objective":
                    await websocket.send_text(f"\r\n📋 Level {level.number}: {level.title}\r\n")
                    continue
                elif stripped == "/progress":
                    progress = await watcher.verification.get_progress(level)
                    await websocket.send_text(f"\r\n📊 Progress: {progress['passed_count']}/{progress['total_count']} checks passed\r\n")
                    continue

                # Write to PTY
                sandbox.write(data.encode("utf-8"))

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error writing to PTY: {e}")
        finally:
            running = False

    try:
        # Run both tasks
        await asyncio.gather(
            read_from_pty(),
            write_to_pty(),
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"Terminal error: {e}")
    finally:
        running = False
        watcher.stop()
        watcher_task.cancel()


@router.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get Claude messages from the session."""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await session["sandbox"].read_messages_log()
    return {"session_id": session_id, "messages": messages}


@router.get("/api/sessions/{session_id}/progress")
async def get_session_progress(session_id: str):
    """Get level completion progress."""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    watcher = session.get("watcher")
    if not watcher:
        return {"session_id": session_id, "progress": None}

    progress = await watcher.verification.get_progress(session["level"])
    return {
        "session_id": session_id,
        "level_number": session["level_number"],
        "completed": session["completed"],
        "progress": progress,
    }
