"""Game configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Claude Code Game"
    debug: bool = False
    modal_app_name: str = "claude-code-game"

    # Sandbox settings
    sandbox_timeout_seconds: int = 3600  # 1 hour
    sandbox_cpu: float = 2.0
    sandbox_memory_mb: int = 4096

    class Config:
        env_file = ".env"


settings = Settings()
