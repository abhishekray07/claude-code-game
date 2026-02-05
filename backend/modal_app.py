"""Modal web endpoint for Claude Code Game backend."""
import modal

from app.config import settings

# Create Modal app
app = modal.App(settings.modal_app_name)

# Define image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "pyyaml>=6.0.1",
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("claude-game-secrets")],
    scaledown_window=300,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    """Return the FastAPI app for Modal to serve."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings
    from app.api.sessions import router as sessions_router
    from app.services.session_manager import session_manager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Startup and shutdown lifecycle."""
        await session_manager.start_cleanup_loop()
        yield
        await session_manager.stop_cleanup_loop()
        await session_manager.terminate_all()

    api = FastAPI(
        title=settings.app_name,
        description="Interactive game for learning Claude Code",
        lifespan=lifespan,
    )

    # CORS for frontend
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    api.include_router(sessions_router)

    @api.get("/health")
    async def health():
        return {"status": "healthy", "app": settings.app_name}

    @api.get("/api/levels")
    async def list_levels():
        from app.services.levels import list_levels
        levels = list_levels()
        return {"levels": levels, "total": len(levels)}

    @api.get("/api/levels/{number}")
    async def get_level(number: int):
        from app.services.levels import load_level_by_number
        from fastapi import HTTPException
        level = load_level_by_number(number)
        if not level:
            raise HTTPException(status_code=404, detail="Level not found")
        return level.model_dump()

    return api
