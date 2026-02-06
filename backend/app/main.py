"""Claude Code Learning Game - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.levels import list_levels as get_all_levels, load_level_by_number


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Debug: print token info on startup
    token = settings.fly_api_token
    print(f"[DEBUG] sandbox_mode={settings.sandbox_mode}")
    print(f"[DEBUG] fly_api_token={settings.fly_api_token}")
    print(
        f"[DEBUG] fly_api_token loaded: {'yes' if token else 'NO'} (len={len(token) if token else 0})"
    )
    if settings.sandbox_mode in ("modal", "fly"):
        from app.services.session_manager import session_manager

        await session_manager.start_cleanup_loop()
    elif settings.sandbox_mode == "docker":
        from app.services.sandbox_manager import sandbox_manager

        sandbox_manager.cleanup_orphaned_containers()
        sandbox_manager.start_cleanup_task()
    yield
    if settings.sandbox_mode in ("modal", "fly"):
        from app.services.session_manager import session_manager

        await session_manager.stop_cleanup_loop()
        await session_manager.terminate_all()
    elif settings.sandbox_mode == "docker":
        from app.services.sandbox_manager import sandbox_manager

        await sandbox_manager.shutdown()


app = FastAPI(
    title=settings.app_name,
    description="Interactive terminal-based game for learning Claude Code",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers based on sandbox mode
if settings.sandbox_mode == "modal":
    from app.api.modal_terminal import router as modal_router

    app.include_router(modal_router)
    print("Running in MODAL mode - sandboxes will be created in Modal cloud")
elif settings.sandbox_mode == "fly":
    from app.api.fly_terminal import router as fly_router

    app.include_router(fly_router)
    print("Running in FLY mode - sandboxes will be created as Fly.io machines")
elif settings.sandbox_mode == "docker":
    from app.api.docker_terminal import router as docker_router

    app.include_router(docker_router)
    print("Running in DOCKER mode - sandboxes will be created as Docker containers")
else:
    from app.api.terminal import router as terminal_router

    app.include_router(terminal_router)
    print("Running in LOCAL mode - sandboxes will use local PTY")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "mode": settings.sandbox_mode,
    }


@app.get("/api/levels")
async def list_levels():
    """List all available levels."""
    levels = get_all_levels()
    return {"levels": levels, "total": len(levels)}


@app.get("/api/levels/{number}")
async def get_level(number: int):
    """Get a specific level by number."""
    level = load_level_by_number(number)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    return level.model_dump()
