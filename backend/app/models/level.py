"""Level definition models."""
from enum import Enum
from pydantic import BaseModel


class VerificationType(str, Enum):
    """Types of verification checks."""
    MESSAGE_EXISTS = "message_exists"
    TOOL_CALLED = "tool_called"
    FILE_EXISTS = "file_exists"
    FILE_CONTAINS = "file_contains"
    FILE_CHANGED = "file_changed"


class VerificationRule(BaseModel):
    """A single verification rule."""
    type: VerificationType
    tool_name: str | None = None  # For TOOL_CALLED
    path: str | None = None  # For FILE_* checks
    pattern: str | None = None  # For FILE_CONTAINS


class Hint(BaseModel):
    """A hint shown after delay."""
    after_minutes: int
    text: str


class LevelLimits(BaseModel):
    """Resource limits for a level."""
    max_duration_minutes: int = 15
    max_claude_messages: int = 20


class Video(BaseModel):
    """Video content for a level."""
    url: str
    duration_seconds: int


class Exercise(BaseModel):
    """Exercise content for a level."""
    intro: str
    objective: str


class Level(BaseModel):
    """A game level definition."""
    id: str
    number: int
    title: str
    module: str
    intro: str
    video: Video | None = None
    exercise: Exercise | None = None
    verification: list[VerificationRule]
    hints: list[Hint] = []
    success: str
    limits: LevelLimits = LevelLimits()
