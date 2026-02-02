# VPS Docker Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get Docker-based sandbox working locally before deploying to Hetzner VPS.

**Architecture:** Backend creates Docker containers via Docker API. Each container runs ttyd on port 7681, mapped to a dynamic host port (10001-10100). Frontend connects directly to the container's ttyd WebSocket.

**Tech Stack:** Docker, FastAPI, ttyd, xterm.js

---

## Task 1: Create Sandbox Dockerfile

**Files:**
- Create: `sandbox/Dockerfile`
- Create: `sandbox/entrypoint.sh`

**Step 1: Create sandbox directory**

```bash
mkdir -p sandbox
```

**Step 2: Create Dockerfile**

```dockerfile
# sandbox/Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Base packages + Python + Node
RUN apt-get update && apt-get install -y \
    ttyd curl git sudo vim nano ca-certificates gnupg \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Python symlink
RUN ln -s /usr/bin/python3 /usr/bin/python

# Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Non-root user with sudo
RUN useradd -m -s /bin/bash claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Copy level files
COPY levels/ /home/claude/levels/

# Copy entrypoint
COPY sandbox/entrypoint.sh /home/claude/entrypoint.sh
RUN chmod +x /home/claude/entrypoint.sh

# Setup workspace
RUN mkdir -p /home/claude/workspace && \
    chown -R claude:claude /home/claude

USER claude
WORKDIR /home/claude/workspace

EXPOSE 7681

CMD ["/home/claude/entrypoint.sh"]
```

**Step 3: Create entrypoint script**

```bash
#!/bin/bash
# sandbox/entrypoint.sh

# Copy level exercise files to workspace
LEVEL_NUM=$(printf '%02d' ${LEVEL_NUMBER:-1})
LEVEL_DIR=$(find /home/claude/levels -maxdepth 1 -type d -name "${LEVEL_NUM}-*" 2>/dev/null | head -1)

if [ -n "$LEVEL_DIR" ] && [ -d "$LEVEL_DIR/exercise" ]; then
    cp -r "$LEVEL_DIR/exercise/"* /home/claude/workspace/
fi

# Start ttyd
exec ttyd -p 7681 bash -l
```

**Step 4: Build and test the image**

Run: `docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .`
Expected: Image builds successfully

**Step 5: Test container manually**

Run: `docker run --rm -p 10001:7681 -e LEVEL_NUMBER=1 claude-game-sandbox:latest`
Expected: ttyd starts, accessible at http://localhost:10001

**Step 6: Commit**

```bash
git add sandbox/
git commit -m "feat: add sandbox Docker image with ttyd"
```

---

## Task 2: Create DockerSandbox Service

**Files:**
- Create: `backend/app/services/docker_sandbox.py`

**Step 1: Create the DockerSandbox class**

```python
# backend/app/services/docker_sandbox.py
"""Docker-based sandbox using ttyd."""
import logging
from typing import Any

import docker
from docker.models.containers import Container

logger = logging.getLogger(__name__)


class DockerSandbox:
    """Docker sandbox with ttyd terminal access."""

    def __init__(self, session_id: str, port: int, level_number: int = 1):
        self.session_id = session_id
        self.port = port
        self.level_number = level_number
        self.container: Container | None = None
        self._docker = docker.from_env()

    async def create(self) -> str:
        """Create and start the sandbox container."""
        logger.info(f"Creating Docker sandbox for session {self.session_id} on port {self.port}")

        self.container = self._docker.containers.run(
            "claude-game-sandbox:latest",
            detach=True,
            remove=True,
            name=f"sandbox-{self.session_id}",
            environment={
                "LEVEL_NUMBER": str(self.level_number),
            },
            ports={"7681/tcp": self.port},
        )

        logger.info(f"Container started: {self.container.id[:12]}")
        return self.container.id

    async def setup_credentials(self, api_key: str) -> bool:
        """Setup Anthropic API key in container."""
        if not self.container:
            raise ValueError("Container not created")

        # Write credentials to container
        import json
        creds = json.dumps({"apiKey": api_key})
        cmd = f'''
        mkdir -p /home/claude/.claude && \
        echo '{creds}' > /home/claude/.claude/.credentials.json && \
        chmod 600 /home/claude/.claude/.credentials.json
        '''

        exit_code, output = self.container.exec_run(
            ["sh", "-c", cmd],
            user="claude"
        )

        return exit_code == 0

    async def exec_command(self, *args: str) -> tuple[str, str, int]:
        """Execute a command in the container."""
        if not self.container:
            raise ValueError("Container not created")

        exit_code, output = self.container.exec_run(
            list(args),
            user="claude",
            workdir="/home/claude/workspace"
        )

        # Docker exec_run returns combined output
        return output.decode("utf-8"), "", exit_code

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude's messages.jsonl from container."""
        if not self.container:
            return []

        import json

        # Find jsonl file
        find_cmd = "find /home/claude/.claude/projects -name '*.jsonl' -type f 2>/dev/null | head -1"
        exit_code, output = self.container.exec_run(
            ["sh", "-c", find_cmd],
            user="claude"
        )

        jsonl_path = output.decode("utf-8").strip()
        if not jsonl_path:
            return []

        # Read file
        exit_code, output = self.container.exec_run(
            ["cat", jsonl_path],
            user="claude"
        )

        messages = []
        for line in output.decode("utf-8").strip().split("\n"):
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        return messages

    async def terminate(self) -> None:
        """Stop and remove the container."""
        if self.container:
            try:
                self.container.stop(timeout=5)
                logger.info(f"Container stopped: {self.session_id}")
            except Exception as e:
                logger.error(f"Error stopping container: {e}")
            self.container = None

    def get_terminal_url(self) -> str:
        """Get the ttyd WebSocket URL for this container."""
        return f"ws://localhost:{self.port}/ws"
```

**Step 2: Verify docker package is installed**

Run: `cd backend && uv pip list | grep docker`
If missing, run: `cd backend && uv add docker`

**Step 3: Commit**

```bash
git add backend/app/services/docker_sandbox.py
git commit -m "feat: add DockerSandbox service for container management"
```

---

## Task 3: Create SandboxManager for Port Allocation

**Files:**
- Create: `backend/app/services/sandbox_manager.py`

**Step 1: Create SandboxManager class**

```python
# backend/app/services/sandbox_manager.py
"""Manages sandbox container lifecycle and port allocation."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set

from app.services.docker_sandbox import DockerSandbox

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manages sandbox containers with port allocation and cleanup."""

    def __init__(self, port_range: tuple[int, int] = (10001, 10101)):
        self.port_range = port_range
        self.available_ports: Set[int] = set(range(port_range[0], port_range[1]))
        self.sessions: Dict[str, dict] = {}  # session_id -> {sandbox, port, last_active, level}
        self._cleanup_task: asyncio.Task | None = None

    def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cleanup task started")

    async def _cleanup_loop(self):
        """Periodically cleanup idle sessions."""
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            await self._cleanup_idle_sessions()

    async def _cleanup_idle_sessions(self, max_idle_minutes: int = 30):
        """Remove sessions idle for too long."""
        now = datetime.now()
        to_remove = []

        for session_id, session in self.sessions.items():
            idle_time = now - session["last_active"]
            if idle_time > timedelta(minutes=max_idle_minutes):
                to_remove.append(session_id)

        for session_id in to_remove:
            logger.info(f"Cleaning up idle session: {session_id}")
            await self.destroy_session(session_id)

    async def create_session(self, session_id: str, level_number: int, api_key: str) -> dict:
        """Create a new sandbox session."""
        if not self.available_ports:
            raise RuntimeError("No available ports for new session")

        port = self.available_ports.pop()

        sandbox = DockerSandbox(session_id, port, level_number)
        await sandbox.create()
        await sandbox.setup_credentials(api_key)

        # Wait for ttyd to be ready
        await asyncio.sleep(2)

        self.sessions[session_id] = {
            "sandbox": sandbox,
            "port": port,
            "last_active": datetime.now(),
            "level_number": level_number,
        }

        logger.info(f"Session created: {session_id} on port {port}")
        return {"session_id": session_id, "port": port}

    async def destroy_session(self, session_id: str) -> None:
        """Destroy a sandbox session."""
        session = self.sessions.pop(session_id, None)
        if session:
            await session["sandbox"].terminate()
            self.available_ports.add(session["port"])
            logger.info(f"Session destroyed: {session_id}")

    def get_session(self, session_id: str) -> dict | None:
        """Get session info."""
        return self.sessions.get(session_id)

    def update_activity(self, session_id: str) -> None:
        """Update last activity time for a session."""
        if session_id in self.sessions:
            self.sessions[session_id]["last_active"] = datetime.now()

    async def shutdown(self):
        """Cleanup all sessions on shutdown."""
        if self._cleanup_task:
            self._cleanup_task.cancel()

        for session_id in list(self.sessions.keys()):
            await self.destroy_session(session_id)


# Global instance
sandbox_manager = SandboxManager()
```

**Step 2: Commit**

```bash
git add backend/app/services/sandbox_manager.py
git commit -m "feat: add SandboxManager for port allocation and cleanup"
```

---

## Task 4: Create Docker Terminal API

**Files:**
- Create: `backend/app/api/docker_terminal.py`

**Step 1: Create the API router**

```python
# backend/app/api/docker_terminal.py
"""API endpoints for Docker-based terminal sessions."""
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.sandbox_manager import sandbox_manager
from app.services.levels import load_level_by_number

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    api_key: str
    level_number: int = 1


class CreateSessionResponse(BaseModel):
    """Response with session details."""
    session_id: str
    port: int
    terminal_url: str
    level: dict


@router.post("/api/docker/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new Docker sandbox session."""
    session_id = str(uuid.uuid4())[:8]

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(status_code=404, detail=f"Level {request.level_number} not found")

    try:
        result = await sandbox_manager.create_session(
            session_id=session_id,
            level_number=request.level_number,
            api_key=request.api_key,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")

    return CreateSessionResponse(
        session_id=session_id,
        port=result["port"],
        terminal_url=f"ws://localhost:{result['port']}/ws",
        level={
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
        },
    )


@router.delete("/api/docker/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a Docker sandbox session."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await sandbox_manager.destroy_session(session_id)
    return {"session_id": session_id, "status": "deleted"}


@router.post("/api/docker/sessions/{session_id}/heartbeat")
async def heartbeat(session_id: str):
    """Update session activity timestamp."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sandbox_manager.update_activity(session_id)
    return {"session_id": session_id, "status": "active"}


@router.get("/api/docker/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = sandbox_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "port": session["port"],
        "terminal_url": f"ws://localhost:{session['port']}/ws",
        "level_number": session["level_number"],
    }
```

**Step 2: Register router in main.py**

Open `backend/app/main.py` and add:

```python
from app.api.docker_terminal import router as docker_terminal_router
from app.services.sandbox_manager import sandbox_manager

# Add router
app.include_router(docker_terminal_router)

# Start cleanup task on startup
@app.on_event("startup")
async def startup_event():
    sandbox_manager.start_cleanup_task()

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await sandbox_manager.shutdown()
```

**Step 3: Commit**

```bash
git add backend/app/api/docker_terminal.py backend/app/main.py
git commit -m "feat: add Docker terminal API endpoints"
```

---

## Task 5: Test Locally End-to-End

**Step 1: Build sandbox image**

Run: `docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .`
Expected: Build succeeds

**Step 2: Start backend**

Run: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
Expected: Server starts on port 8000

**Step 3: Create a session via API**

Run:
```bash
curl -X POST http://localhost:8000/api/docker/sessions \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test-key", "level_number": 1}'
```
Expected: Returns session_id and port (e.g., 10001)

**Step 4: Open terminal in browser**

Open: `http://localhost:10001` (use port from step 3)
Expected: ttyd terminal loads, shows bash prompt

**Step 5: Test Claude Code in terminal**

In the ttyd terminal, run: `claude --version`
Expected: Shows Claude Code version

**Step 6: Delete session**

Run: `curl -X DELETE http://localhost:8000/api/docker/sessions/{session_id}`
Expected: Container stops, port freed

**Step 7: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found in local testing"
```

---

## Task 6: Update Frontend to Use Docker Backend

**Files:**
- Modify: `frontend/src/components/Terminal.tsx`
- Modify: `frontend/src/config.ts`

**Step 1: Add config for terminal mode**

```typescript
// frontend/src/config.ts - add these exports
export const TERMINAL_MODE = import.meta.env.VITE_TERMINAL_MODE || 'docker';
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**Step 2: Update Terminal component to connect to ttyd**

The frontend should:
1. Call `POST /api/docker/sessions` to get session_id and port
2. Connect to `ws://localhost:{port}/ws` for the terminal
3. Use ttyd's native protocol (it handles xterm.js communication)

Note: ttyd has its own frontend, so for Docker mode we may want to use an iframe or adapt the existing Terminal component to ttyd's WebSocket protocol.

**Step 3: Test frontend connection**

Run frontend: `cd frontend && npm run dev`
Open: `http://localhost:5173`
Expected: Terminal loads and connects to Docker container

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: update frontend to support Docker terminal mode"
```

---

## Summary

After completing these tasks, you'll have:

1. ✅ Sandbox Docker image with ttyd
2. ✅ DockerSandbox service for container management
3. ✅ SandboxManager for port allocation and cleanup
4. ✅ API endpoints for session lifecycle
5. ✅ Frontend connecting to Docker containers

**Next steps (Hetzner deployment):**
- Add docker-compose.yml with nginx
- Configure nginx for routing
- Deploy to VPS
