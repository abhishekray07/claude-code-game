"""Claude Code Learning Game - FastAPI Application."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.terminal import router as terminal_router
from app.services.levels import list_levels as get_all_levels, load_level_by_number

app = FastAPI(
    title=settings.app_name,
    description="Interactive terminal-based game for learning Claude Code",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(terminal_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


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
