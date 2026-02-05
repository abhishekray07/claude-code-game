"""Terminal endpoint with Fly.io sandbox - WebSocket proxy approach."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

try:
    import websockets
except ImportError:
    websockets = None  # Will fail gracefully if not installed

from app.config import settings
from app.services.fly_sandbox import FlySandbox
from app.services.session_manager import session_manager, Session
from app.services.levels import load_level_by_number
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_SESSIONS_PER_IP = 3


class CreateSessionRequest(BaseModel):
    """Request to create a new game session."""
    api_key: str = ""  # Optional - users can enter in terminal instead
    level_number: int = 1  # Default to Lesson 1
    access_code: str = ""


class CreateSessionResponse(BaseModel):
    """Response with session info for WebSocket terminal."""
    session_id: str
    status: str
    ttyd_url: str | None = None  # Deprecated: now using WebSocket proxy
    level: dict


def get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    # Check for forwarded headers (when behind proxy)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest, http_request: Request):
    """Create a new game session with Fly.io sandbox."""

    # Rate limiting by IP
    client_ip = get_client_ip(http_request)
    if not session_manager.can_create_session(client_ip, MAX_SESSIONS_PER_IP):
        raise HTTPException(
            status_code=429,
            detail=f"Too many active sessions. Maximum {MAX_SESSIONS_PER_IP} per IP."
        )

    # Check access code if configured
    if settings.demo_access_code:
        if request.access_code != settings.demo_access_code:
            raise HTTPException(status_code=403, detail="Invalid access code")

    # Validate API key format (basic check) - only if provided
    if request.api_key and not request.api_key.startswith("sk-ant-"):
        raise HTTPException(status_code=400, detail="Invalid API key format")

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(status_code=404, detail=f"Level {request.level_number} not found")

    # Generate session credentials
    session_id = session_manager.create_session_id()
    ttyd_password = session_manager.generate_ttyd_password()

    # Create Fly sandbox
    try:
        sandbox = await FlySandbox.create(level_number=request.level_number)
        # Note: User will enter API key directly in terminal
        # exec commands are rate-limited, so we skip setup here
    except Exception as e:
        logger.error(f"Failed to create Fly sandbox: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {e}")

    # Create session
    # Note: ttyd_url is for backward compat; frontend now uses WebSocket proxy
    session = Session(
        session_id=session_id,
        sandbox=sandbox,
        level=level,
        level_number=request.level_number,
        ttyd_url=sandbox.get_ttyd_url(),  # Stored for reference but not used
        ttyd_password=ttyd_password,
        client_ip=client_ip,
    )
    session_manager.add(session)

    return CreateSessionResponse(
        session_id=session_id,
        status="ready",
        # Note: ttyd_url is intentionally not returned
        # Frontend will use WebSocket proxy at /ws/terminal/{session_id}
        # which routes to the specific Fly machine via fly-force-instance-id header
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
        try:
            await session.sandbox.terminate()
        except Exception as e:
            logger.error(f"Error terminating Fly sandbox: {e}")
        return {"session_id": session_id, "status": "terminated"}
    raise HTTPException(status_code=404, detail="Session not found")


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

    # Check completion via verification engine
    if not session.completed:
        verification = VerificationEngine(session.sandbox)
        session.completed = await verification.check_level_complete(session.level)

    return {
        "session_id": session_id,
        "completed": session.completed,
    }


@router.get("/api/sessions/{session_id}/debug")
async def debug_session(session_id: str):
    """Debug endpoint to see verification details."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sandbox = session.sandbox
    debug_info = {
        "session_id": session_id,
        "machine_id": sandbox.machine_id,
    }

    # Test reading CLAUDE.md
    try:
        claude_md_path = "/home/claude/workspace/CLAUDE.md"
        stdout, stderr, rc = await sandbox.exec_command("cat", claude_md_path)
        debug_info["claude_md"] = {
            "path": claude_md_path,
            "content": stdout[:500] if stdout else None,
            "error": stderr if rc != 0 else None,
            "return_code": rc,
            "contains_camelCase": "camelCase" in stdout if stdout else False,
        }
    except Exception as e:
        debug_info["claude_md_error"] = str(e)

    # Test reading messages log
    try:
        messages = await sandbox.read_messages_log()
        user_messages = [m for m in messages if m.get("type") == "user"]
        debug_info["messages"] = {
            "total_count": len(messages),
            "user_message_count": len(user_messages),
            "message_types": list(set(m.get("type") for m in messages)),
        }
    except Exception as e:
        debug_info["messages_error"] = str(e)

    # Test finding .jsonl files
    try:
        stdout, stderr, rc = await sandbox.exec_command(
            "bash", "-c", "find /home/claude/.claude -name '*.jsonl' -type f 2>/dev/null || true"
        )
        debug_info["jsonl_files"] = stdout.strip().split("\n") if stdout.strip() else []
    except Exception as e:
        debug_info["jsonl_files_error"] = str(e)

    return debug_info


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket proxy to Fly machine's ttyd.

    This endpoint solves the machine routing problem:
    - Frontend connects to backend via WebSocket
    - Backend opens WebSocket to Fly with fly-force-instance-id header
    - All traffic is proxied bidirectionally

    This ensures reconnects always go to the same machine.
    """
    if websockets is None:
        logger.error("websockets library not installed")
        await websocket.close(code=1011, reason="Server misconfigured")
        return

    # Accept the frontend connection with tty subprotocol (frontend requires it)
    await websocket.accept(subprotocol="tty")

    # Look up session to get machine ID
    session = session_manager.get(session_id)
    if not session:
        logger.warning(f"WebSocket: Session not found: {session_id}")
        await websocket.close(code=1008, reason="Session not found")
        return

    machine_id = session.sandbox.machine_id
    if not machine_id:
        logger.error(f"WebSocket: No machine ID for session: {session_id}")
        await websocket.close(code=1011, reason="No machine ID")
        return

    # Connect to Fly machine's ttyd WebSocket with machine routing header
    fly_url = f"wss://{settings.fly_sandbox_app}.fly.dev/ws"
    headers = {"fly-force-instance-id": machine_id}

    logger.info(f"WebSocket proxy: {session_id} -> machine {machine_id}")
    logger.info(f"Connecting to Fly URL: {fly_url} with headers: {headers}")

    # Track connection state for cleanup
    connection_active = True

    try:
        async with websockets.connect(
            fly_url,
            extra_headers=headers,  # renamed from additional_headers in websockets 16.x
            subprotocols=["tty"],  # ttyd requires this subprotocol
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as fly_ws:
            logger.info(f"Connected to Fly machine! Subprotocol: {fly_ws.subprotocol}")

            async def forward_frontend_to_fly():
                """Forward messages from frontend to Fly machine."""
                nonlocal connection_active
                try:
                    logger.info(f"Starting forward_frontend_to_fly for {session_id}")
                    while connection_active:
                        data = await websocket.receive_text()
                        logger.debug(f"Received from frontend ({session_id}): {len(data)} bytes")
                        # Update session activity on any traffic
                        session_manager.touch(session_id)
                        await fly_ws.send(data)
                        logger.debug(f"Sent to Fly ({session_id})")
                except WebSocketDisconnect:
                    logger.info(f"Frontend disconnected: {session_id}")
                    connection_active = False
                except Exception as e:
                    logger.error(f"Frontend->Fly error ({session_id}): {type(e).__name__}: {e}")
                    connection_active = False

            async def forward_fly_to_frontend():
                """Forward messages from Fly machine to frontend."""
                nonlocal connection_active
                try:
                    logger.info(f"Starting forward_fly_to_frontend for {session_id}")
                    async for message in fly_ws:
                        if not connection_active:
                            break
                        logger.debug(f"Received from Fly ({session_id}): {type(message).__name__}, {len(message) if hasattr(message, '__len__') else 'N/A'} bytes")
                        # Update session activity on any traffic
                        session_manager.touch(session_id)
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                        logger.debug(f"Sent to frontend ({session_id})")
                except Exception as e:
                    if websockets and isinstance(e, websockets.exceptions.ConnectionClosed):
                        logger.info(f"Fly machine disconnected: {session_id}")
                    else:
                        logger.error(f"Fly->Frontend error ({session_id}): {type(e).__name__}: {e}")
                    connection_active = False

            async def keepalive_ping():
                """Send periodic pings to keep frontend connection alive."""
                nonlocal connection_active
                try:
                    while connection_active:
                        await asyncio.sleep(30)
                        if connection_active:
                            # Send a WebSocket ping to frontend
                            try:
                                await websocket.send_bytes(b"")  # Empty ping
                            except Exception:
                                pass
                except asyncio.CancelledError:
                    pass

            # Run both directions plus keepalive concurrently
            await asyncio.gather(
                forward_frontend_to_fly(),
                forward_fly_to_frontend(),
                keepalive_ping(),
                return_exceptions=True,
            )

    except Exception as e:
        import traceback
        logger.error(f"WebSocket proxy error for {session_id}: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        try:
            await websocket.close(code=1011, reason="Proxy error")
        except Exception:
            pass
