"""WebSocket terminal endpoint with Modal sandbox proxy."""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.sandbox import ModalSandbox
from app.services.session_manager import session_manager, Session
from app.services.levels import load_level_by_number, get_exercise_dir
from app.services.watcher import GameWatcher
from app.services.verification import VerificationEngine
from app.models.level import Level

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateSessionRequest(BaseModel):
    """Request to create a new game session."""
    api_key: str
    level_number: int = 1
    access_code: str = ""


class CreateSessionResponse(BaseModel):
    """Response with session info (no terminal_url - use WebSocket)."""
    session_id: str
    status: str
    level: dict


@router.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new game session with Modal sandbox."""

    # Check access code if configured
    if settings.demo_access_code:
        if request.access_code != settings.demo_access_code:
            raise HTTPException(status_code=403, detail="Invalid access code")

    # Validate API key format (basic check)
    if not request.api_key.startswith("sk-ant-"):
        raise HTTPException(status_code=400, detail="Invalid API key format")

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(status_code=404, detail=f"Level {request.level_number} not found")

    # Generate session credentials
    session_id = session_manager.create_session_id()
    ttyd_password = session_manager.generate_ttyd_password()

    # Create Modal sandbox
    sandbox = ModalSandbox(session_id, ttyd_password)
    try:
        await sandbox.create()
        await sandbox.setup_credentials(request.api_key)

        # Copy exercise files
        exercise_dir = get_exercise_dir(request.level_number)
        if exercise_dir:
            await sandbox.copy_exercise_files(str(exercise_dir))

    except Exception as e:
        logger.error(f"Failed to create sandbox: {e}")
        if sandbox.sandbox:
            sandbox.terminate()
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {e}")

    # Create session (no ttyd_url - we use WebSocket proxy)
    session = Session(
        session_id=session_id,
        sandbox=sandbox,
        level=level,
        level_number=request.level_number,
        ttyd_url="",  # Not using ttyd, using WebSocket proxy
        ttyd_password=ttyd_password,
    )
    session_manager.add(session)

    return CreateSessionResponse(
        session_id=session_id,
        status="ready",
        level={
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
            "video": level.video.model_dump() if level.video else None,
            "exercise": level.exercise.model_dump() if level.exercise else None,
        },
    )


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Terminate a session."""
    session = session_manager.remove(session_id)
    if session:
        session.sandbox.terminate()
        return {"session_id": session_id, "status": "terminated"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal access - proxies to Modal sandbox."""
    await websocket.accept()
    logger.info(f"Modal terminal WebSocket connected: {session_id}")

    session = session_manager.get(session_id)
    if not session:
        await websocket.send_text("Error: Session not found\r\n")
        await websocket.close()
        return

    sandbox: ModalSandbox = session.sandbox
    level: Level = session.level

    # Send level intro with clear formatting
    # Clear screen
    await websocket.send_text("\033[2J\033[H")
    await websocket.send_text("\r\n")
    for line in level.intro.split("\n"):
        await websocket.send_text(line + "\r\n")
    await websocket.send_text("\r\n")
    await websocket.send_text("\033[90m" + "-" * 60 + "\033[0m\r\n")
    await websocket.send_text("\r\n")

    # Start the shell
    try:
        sandbox.start_shell()
    except Exception as e:
        await websocket.send_text(f"Error starting shell: {e}\r\n")
        await websocket.close()
        return

    # Setup watcher callbacks
    async def on_complete():
        session.completed = True
        # Send completion marker for the frontend sidebar
        await websocket.send_text("__LEVEL_COMPLETE__")

    async def on_hint(text: str):
        await websocket.send_text(f"\r\n\r\n{text}\r\n")

    async def on_progress(progress: dict):
        _ = progress  # Progress updates handled via /progress endpoint

    # Start watcher
    watcher = GameWatcher(sandbox, level, on_complete, on_hint, on_progress)
    watcher_task = asyncio.create_task(watcher.start())

    # Flag to control loops
    running = True

    async def read_from_sandbox():
        """Read from sandbox shell and send to WebSocket."""
        loop = asyncio.get_event_loop()
        while running:
            try:
                # Read with small timeout to allow checking 'running' flag
                data = await loop.run_in_executor(None, lambda: sandbox.read(0.05))
                if data:
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
            except Exception as e:
                if running:
                    logger.error(f"Error reading from sandbox: {e}")
                break

    async def write_to_sandbox():
        """Read from WebSocket and write to sandbox shell."""
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
                    await websocket.send_text("\r\nSkipping level...\r\n")
                    session.completed = True
                    await websocket.send_text("__LEVEL_COMPLETE__\r\n")
                    continue
                elif stripped == "/objective":
                    await websocket.send_text(f"\r\nLevel {level.number}: {level.title}\r\n")
                    continue
                elif stripped == "/progress":
                    progress = await watcher.verification.get_progress(level)
                    await websocket.send_text(
                        f"\r\nProgress: {progress['passed_count']}/{progress['total_count']} checks passed\r\n"
                    )
                    continue

                # Write to sandbox shell
                logger.info(f"Received from WebSocket: {repr(data)}")
                sandbox.write(data.encode("utf-8"))
                logger.info(f"Wrote to sandbox stdin")

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error writing to sandbox: {e}")
        finally:
            running = False

    try:
        # Run both tasks
        await asyncio.gather(
            read_from_sandbox(),
            write_to_sandbox(),
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"Terminal error: {e}")
    finally:
        running = False
        watcher.stop()
        watcher_task.cancel()


@router.get("/api/sessions/{session_id}/progress")
async def get_session_progress(session_id: str):
    """Get level completion progress."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    verification = VerificationEngine(session.sandbox)
    progress = await verification.get_progress(session.level)

    return {
        "session_id": session_id,
        "level_number": session.level_number,
        "completed": session.completed,
        "progress": progress,
    }


@router.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session completion status (polled by frontend)."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "completed": session.completed,
    }
