"""Level loading and management service."""
from pathlib import Path

import yaml

from app.models.level import (
    Level,
    VerificationRule,
    Hint,
    LevelLimits,
    VerificationType,
)

# Path to level definitions relative to this file
LEVELS_DIR = Path(__file__).parent.parent.parent.parent / "levels" / "definitions"


def load_level(level_id: str) -> Level | None:
    """Load a level by ID."""
    for yaml_file in LEVELS_DIR.glob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if data.get("id") == level_id:
            return _parse_level(data)

    return None


def load_level_by_number(number: int) -> Level | None:
    """Load a level by number."""
    for yaml_file in LEVELS_DIR.glob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if data.get("number") == number:
            return _parse_level(data)

    return None


def list_levels() -> list[dict]:
    """List all available levels."""
    levels = []

    for yaml_file in sorted(LEVELS_DIR.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

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

    return Level(
        id=data["id"],
        number=data["number"],
        title=data["title"],
        module=data["module"],
        intro=data["intro"],
        verification=verification_rules,
        hints=hints,
        success=data["success"],
        limits=limits,
    )
