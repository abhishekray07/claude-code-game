"""Modal configuration for game sandboxes."""
from typing import Any

import modal


def get_game_image() -> modal.Image:
    """Get Modal image with Claude Code and ttyd installed."""
    return (
        modal.Image.debian_slim(python_version="3.11")
        .apt_install(
            "git", "curl", "openssh-client", "build-essential", "sudo",
            "nodejs", "npm", "procps",
            # ttyd dependencies
            "cmake", "libjson-c-dev", "libwebsockets-dev",
        )
        .run_commands(
            # Install ttyd
            "git clone https://github.com/tsl0922/ttyd.git /tmp/ttyd",
            "cd /tmp/ttyd && mkdir build && cd build && cmake .. && make && make install",
            # Create user
            "useradd -m -s /bin/bash -u 1000 claude",
            # Install Claude Code
            "npm install -g @anthropic-ai/claude-code",
            # Setup directories
            "mkdir -p /home/claude/.claude/projects",
            "mkdir -p /workspace",
            "chown -R claude:claude /home/claude /workspace",
        )
    )


def get_sandbox_config(image: modal.Image | None = None) -> dict[str, Any]:
    """Get sandbox configuration."""
    if image is None:
        image = get_game_image()

    return {
        "image": image,
        "timeout": 3600,
        "cpu": 2.0,
        "memory": 4096,
    }
