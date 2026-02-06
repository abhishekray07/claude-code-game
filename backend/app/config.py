"""Game configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory (where .env lives)
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
    )

    app_name: str = "Claude Code Game"
    debug: bool = False
    modal_app_name: str = "claude-code-game"

    # Sandbox settings
    sandbox_timeout_seconds: int = 3600  # Hard cap: 60 minutes
    sandbox_idle_timeout_seconds: int = 600  # Soft cap: 10 min inactivity
    sandbox_cpu: float = 2.0
    sandbox_memory_mb: int = 4096
    ttyd_port: int = 7681

    # Security
    max_sessions: int = 5  # Global session cap
    demo_access_code: str = ""  # Set via DEMO_ACCESS_CODE env var
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "https://claude-code-game.vercel.app",
        "https://*.vercel.app",  # Preview deployments
    ]

    # Mode: "local" for local PTY sandbox, "modal" for Modal cloud sandbox, "fly" for Fly.io
    sandbox_mode: str = "local"  # Set SANDBOX_MODE=local|modal|fly

    # Fly.io settings
    fly_api_token: str = ""  # Set via FLY_API_TOKEN env var
    fly_sandbox_app: str = "claude-game-sandbox"  # Fly app name for sandbox machines (not FLY_APP_NAME - that's reserved by Fly)
    fly_sandbox_image: str = ""  # Full image path, e.g. registry.fly.io/claude-game-sandbox:deployment-xxx
    fly_region: str = "sjc"  # Default region for machines
    fly_machine_ttl_seconds: int = 1800  # Max 30 minutes per machine


settings = Settings()
