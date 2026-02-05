"""API endpoints for Docker-based terminal sessions."""
import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

try:
    import websockets
except ImportError:
    websockets = None

from app.services.sandbox_manager import sandbox_manager
from app.services.levels import load_level_by_number
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter()


class UpdateLevelRequest(BaseModel):
    """Request to update session level."""

    level_number: int


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    level_number: int = 1


class CreateSessionResponse(BaseModel):
    """Response with session details."""

    session_id: str
    port: int
    terminal_url: str
    ttyd_token: str
    level: dict


@router.post("/api/docker/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new Docker sandbox session."""
    session_id = str(uuid.uuid4())[:8]

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(
            status_code=404, detail=f"Level {request.level_number} not found"
        )

    try:
        result = await sandbox_manager.create_session(
            session_id=session_id,
            level_number=request.level_number,
        )
    except RuntimeError as e:
        logger.error(f"Sandbox runtime error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except ValueError as e:
        logger.warning(f"Invalid request parameters: {e}")
        raise HTTPException(status_code=400, detail="Invalid request parameters")
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create session")

    return CreateSessionResponse(
        session_id=session_id,
        port=result["port"],
        terminal_url=f"http://localhost:{result['port']}/",
        ttyd_token=result["ttyd_token"],
        level={
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
            "video": {"url": level.video.url, "duration_seconds": level.video.duration_seconds} if level.video else None,
            "exercise": {"intro": level.exercise.intro, "objective": level.exercise.objective} if level.exercise else None,
        },
    )


@router.delete("/api/docker/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a Docker sandbox session."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await sandbox_manager.destroy_session(session_id)
    return {"session_id": session_id, "status": "deleted"}


@router.patch("/api/docker/sessions/{session_id}/level")
async def update_session_level(session_id: str, request: UpdateLevelRequest):
    """Update an existing session to a new level (reuses container)."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(
            status_code=404, detail=f"Level {request.level_number} not found"
        )

    try:
        result = await sandbox_manager.update_session_level(
            session_id, request.level_number
        )
    except Exception as e:
        logger.error(f"Failed to update level: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update level")

    return {
        "session_id": session_id,
        "port": result["port"],
        "terminal_url": f"http://localhost:{result['port']}/",
        "ttyd_token": result["ttyd_token"],
        "level": {
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
            "video": {"url": level.video.url, "duration_seconds": level.video.duration_seconds} if level.video else None,
            "exercise": {"intro": level.exercise.intro, "objective": level.exercise.objective} if level.exercise else None,
        },
    }


@router.post("/api/docker/sessions/{session_id}/heartbeat")
async def heartbeat(session_id: str):
    """Update session activity timestamp."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sandbox_manager.update_activity(session_id)
    return {"session_id": session_id, "status": "active"}


@router.get("/api/docker/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "port": session["port"],
        "terminal_url": f"http://localhost:{session['port']}/",
        "level_number": session["level_number"],
    }


@router.get("/api/docker/sessions/{session_id}/progress")
async def get_progress(session_id: str):
    """Get verification progress for a session."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sandbox_manager.update_activity(session_id)

    level = load_level_by_number(session["level_number"])
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    engine = VerificationEngine(session["sandbox"])
    progress = await engine.get_progress(level)
    return {"progress": progress}


@router.get("/api/docker/sessions/{session_id}/status")
async def get_status(session_id: str):
    """Check if level is complete."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sandbox_manager.update_activity(session_id)

    level = load_level_by_number(session["level_number"])
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    engine = VerificationEngine(session["sandbox"])
    completed = await engine.check_level_complete(level)
    return {"completed": completed, "session_id": session_id}


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket proxy to local ttyd for Docker mode.

    Solves VPS deployment: frontend connects to backend, backend proxies to container.
    """
    if websockets is None:
        logger.error("websockets library not installed")
        await websocket.close(code=1011, reason="Server misconfigured")
        return

    # Accept with tty subprotocol (required by ttyd)
    await websocket.accept(subprotocol="tty")

    # Look up session to get port
    session = sandbox_manager.get_session(session_id)
    if not session:
        logger.warning(f"WebSocket: Session not found: {session_id}")
        await websocket.close(code=1008, reason="Session not found")
        return

    port = session["port"]
    target_url = f"ws://127.0.0.1:{port}/ws"
    logger.info(f"WS proxy: {session_id} -> localhost:{port}")

    connection_active = True

    try:
        async with websockets.connect(
            target_url,
            subprotocols=["tty"],
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as ttyd_ws:
            logger.info(f"Connected to ttyd for {session_id}")

            async def forward_frontend_to_ttyd():
                """Forward messages from browser to ttyd."""
                nonlocal connection_active
                try:
                    while connection_active:
                        try:
                            data = await websocket.receive_text()
                        except Exception:
                            # Try receiving bytes if text fails
                            try:
                                data = await websocket.receive_bytes()
                                await ttyd_ws.send(data)
                                sandbox_manager.update_activity(session_id)
                                continue
                            except Exception:
                                break
                        sandbox_manager.update_activity(session_id)
                        await ttyd_ws.send(data)
                except WebSocketDisconnect:
                    logger.info(f"Frontend disconnected: {session_id}")
                    connection_active = False
                except Exception as e:
                    logger.debug(f"Frontend->ttyd ended ({session_id}): {e}")
                    connection_active = False

            async def forward_ttyd_to_frontend():
                """Forward messages from ttyd to browser."""
                nonlocal connection_active
                try:
                    async for message in ttyd_ws:
                        if not connection_active:
                            break
                        sandbox_manager.update_activity(session_id)
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception as e:
                    if connection_active:
                        logger.debug(f"ttyd->Frontend ended ({session_id}): {e}")
                    connection_active = False

            async def keepalive_ping():
                """Send periodic pings to keep frontend connection alive."""
                nonlocal connection_active
                try:
                    while connection_active:
                        await asyncio.sleep(30)
                        if connection_active:
                            try:
                                await websocket.send_bytes(b"")
                            except Exception:
                                pass
                except asyncio.CancelledError:
                    pass

            # Run all three tasks concurrently
            await asyncio.gather(
                forward_frontend_to_ttyd(),
                forward_ttyd_to_frontend(),
                keepalive_ping(),
                return_exceptions=True,
            )

    except websockets.exceptions.InvalidStatusCode as e:
        logger.warning(f"ttyd connection failed for {session_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Container not ready")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WS proxy error for {session_id}: {type(e).__name__}: {e}")
        try:
            await websocket.close(code=1011, reason="Proxy error")
        except Exception:
            pass
