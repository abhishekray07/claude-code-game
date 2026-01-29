"""Level loading and management service."""
from pathlib import Path

import yaml

from app.models.level import (
    Level,
    VerificationRule,
    Hint,
    LevelLimits,
    VerificationType,
    Video,
    Exercise,
)

# Path to levels directory
LEVELS_DIR = Path(__file__).parent.parent.parent.parent / "levels"
DEFINITIONS_DIR = LEVELS_DIR / "definitions"


def load_level(level_id: str) -> Level | None:
    """Load a level by ID."""
    # Try new structure first: levels/01-*/lesson.yaml
    for dir_path in LEVELS_DIR.iterdir():
        if dir_path.is_dir() and not dir_path.name.startswith((".", "definitions", "starter-app")):
            lesson_file = dir_path / "lesson.yaml"
            if lesson_file.exists():
                with open(lesson_file) as f:
                    data = yaml.safe_load(f)
                if data.get("id") == level_id:
                    return _parse_level(data)

    # Fallback to old structure: levels/definitions/*.yaml
    if DEFINITIONS_DIR.exists():
        for yaml_file in DEFINITIONS_DIR.glob("*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            if data.get("id") == level_id:
                return _parse_level(data)

    return None


def load_level_by_number(number: int) -> Level | None:
    """Load a level by number."""
    # Try new structure first: levels/01-*/lesson.yaml
    for dir_path in LEVELS_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"{number:02d}-"):
            lesson_file = dir_path / "lesson.yaml"
            if lesson_file.exists():
                with open(lesson_file) as f:
                    data = yaml.safe_load(f)
                return _parse_level(data)

    # Fallback to old structure: levels/definitions/0X-*.yaml
    if DEFINITIONS_DIR.exists():
        for yaml_file in DEFINITIONS_DIR.glob(f"{number:02d}-*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            return _parse_level(data)

    return None


def get_exercise_dir(level_number: int) -> Path | None:
    """Get the exercise directory for a level."""
    # Try new structure: levels/01-*/exercise/
    for dir_path in LEVELS_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"{level_number:02d}-"):
            exercise_dir = dir_path / "exercise"
            if exercise_dir.exists():
                return exercise_dir

    # Fallback to shared starter-app
    starter_app = LEVELS_DIR / "starter-app"
    if starter_app.exists():
        return starter_app

    return None


def list_levels() -> list[dict]:
    """List all available levels."""
    levels = []
    seen_numbers = set()

    # Try new structure first: levels/01-*/lesson.yaml
    for dir_path in sorted(LEVELS_DIR.iterdir()):
        if dir_path.is_dir() and not dir_path.name.startswith((".", "definitions", "starter-app")):
            lesson_file = dir_path / "lesson.yaml"
            if lesson_file.exists():
                with open(lesson_file) as f:
                    data = yaml.safe_load(f)
                levels.append({
                    "id": data["id"],
                    "number": data["number"],
                    "title": data["title"],
                    "module": data["module"],
                })
                seen_numbers.add(data["number"])

    # Add from old structure for any missing levels
    if DEFINITIONS_DIR.exists():
        for yaml_file in sorted(DEFINITIONS_DIR.glob("*.yaml")):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            if data["number"] not in seen_numbers:
                levels.append({
                    "id": data["id"],
                    "number": data["number"],
                    "title": data["title"],
                    "module": data["module"],
                })

    return sorted(levels, key=lambda x: x["number"])


def _parse_level(data: dict) -> Level:
    """Parse YAML data into Level model."""
    verification_rules = []
    for rule in data.get("verification", []):
        verification_rules.append(VerificationRule(
            type=VerificationType(rule["type"]),
            tool_name=rule.get("tool_name"),
            path=rule.get("path"),
            pattern=rule.get("pattern"),
            command=rule.get("command"),
            expected_output=rule.get("expected_output"),
        ))

    hints = []
    for hint in data.get("hints", []):
        hints.append(Hint(
            after_minutes=hint["after_minutes"],
            text=hint["text"],
        ))

    limits_data = data.get("limits", {})
    limits = LevelLimits(
        max_duration_minutes=limits_data.get("max_duration_minutes", 15),
        max_claude_messages=limits_data.get("max_claude_messages", 20),
    )

    # Parse video if present
    video = None
    if "video" in data and data["video"]:
        video = Video(
            url=data["video"]["url"],
            duration_seconds=data["video"]["duration_seconds"],
        )

    # Parse exercise if present
    exercise = None
    if "exercise" in data and data["exercise"]:
        exercise = Exercise(
            intro=data["exercise"]["intro"],
            objective=data["exercise"]["objective"],
        )

    return Level(
        id=data["id"],
        number=data["number"],
        title=data["title"],
        module=data["module"],
        intro=data["intro"],
        video=video,
        exercise=exercise,
        verification=verification_rules,
        hints=hints,
        success=data["success"],
        limits=limits,
    )
