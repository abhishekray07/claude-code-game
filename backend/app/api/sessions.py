"""Session API endpoints for production."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.session_manager import session_manager, Session
from app.services.sandbox import ModalSandbox
from app.services.levels import load_level_by_number, get_exercise_dir
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request to create a new game session."""
    api_key: str
    level_number: int = 1
    access_code: str = ""


class CreateSessionResponse(BaseModel):
    """Response with session info and terminal URL."""
    session_id: str
    terminal_url: str
    level: dict


class SessionStatusResponse(BaseModel):
    """Response with session status and completion info."""
    session_id: str
    level_number: int
    completed: bool
    progress: dict | None


@router.post("/sessions", response_model=CreateSessionResponse)
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

        # Start ttyd and get auth'd URL
        terminal_url = await sandbox.start_ttyd()

    except Exception as e:
        logger.error(f"Failed to create sandbox: {e}")
        if sandbox.sandbox:
            sandbox.terminate()
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {e}")

    # Create session
    session = Session(
        session_id=session_id,
        sandbox=sandbox,
        level=level,
        level_number=request.level_number,
        ttyd_url=terminal_url,
        ttyd_password=ttyd_password,
    )
    session_manager.add(session)

    return CreateSessionResponse(
        session_id=session_id,
        terminal_url=terminal_url,
        level={
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
            "video": level.video.model_dump() if level.video else None,
            "exercise": level.exercise.model_dump() if level.exercise else None,
        },
    )


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get session status and check level completion."""

    session = session_manager.get(session_id)  # Also updates activity timestamp
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check completion
    verification = VerificationEngine(session.sandbox)
    completed = await verification.check_level_complete(session.level)
    progress = await verification.get_progress(session.level)

    if completed:
        session.completed = True

    return SessionStatusResponse(
        session_id=session_id,
        level_number=session.level_number,
        completed=session.completed,
        progress=progress,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Terminate a session."""
    session = session_manager.remove(session_id)
    if session:
        session.sandbox.terminate()
        return {"session_id": session_id, "status": "terminated"}
    raise HTTPException(status_code=404, detail="Session not found")
