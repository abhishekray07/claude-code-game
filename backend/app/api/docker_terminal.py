"""API endpoints for Docker-based terminal sessions."""
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
