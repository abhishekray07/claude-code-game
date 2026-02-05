# Fix Docker Terminal — Direct ttyd Connection

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Docker terminal actually work by removing the broken auth-in-URL iframe approach and dead WebSocket proxy, replacing with a direct unauthenticated ttyd iframe connection.

**Architecture:** The sandbox container runs ttyd on port 7681, mapped to a host port (10001-10101). Currently the frontend tries to load an iframe with HTTP Basic Auth credentials embedded in the URL (`http://user:TOKEN@localhost:PORT/`), which modern browsers block. Fix: remove ttyd auth (localhost-only anyway), load iframe directly, delete the unused WebSocket proxy code.

**Tech Stack:** FastAPI (backend), React + xterm.js (frontend), Docker, ttyd

---

### Task 1: Remove ttyd Authentication from Sandbox Entrypoint

**Files:**
- Modify: `sandbox/entrypoint.sh:17`

**Step 1: Remove the `-c` auth flag from ttyd startup**

The entrypoint currently starts ttyd with HTTP Basic Auth. Since the port is only accessible on localhost (we'll enforce this in Task 4), auth is unnecessary and breaks iframe loading.

```bash
#!/bin/bash
# sandbox/entrypoint.sh
set -euo pipefail

# Copy level exercise files to workspace
LEVEL_NUM=$(printf '%02d' "${LEVEL_NUMBER:-1}")
LEVEL_DIR=$(find /home/claude/levels -maxdepth 1 -type d -name "${LEVEL_NUM}-*" 2>/dev/null | head -1 || true)

if [ -n "$LEVEL_DIR" ] && [ -d "$LEVEL_DIR/exercise" ]; then
    cp -r "$LEVEL_DIR/exercise/"* /home/claude/workspace/
fi

# Start ttyd without authentication (port only accessible on localhost via Docker port mapping)
exec ttyd -p 7681 bash -l
```

**Step 2: Verify the change looks correct**

Run: `cat sandbox/entrypoint.sh`
Expected: No `-c "user:${TTYD_TOKEN}"` flag, no `TTYD_TOKEN` reference

**Step 3: Commit**

```bash
git add sandbox/entrypoint.sh
git commit -m "fix: remove ttyd basic auth (breaks iframe, localhost-only anyway)"
```

---

### Task 2: Fix IframeTerminal URL Construction

**Files:**
- Modify: `frontend/src/components/Terminal.tsx:35-38`

**Step 1: Change the Docker-mode URL to not include credentials**

In `IframeTerminal`, the `terminalUrl` for Docker mode currently embeds credentials in the URL. Change it to a plain URL.

Replace lines 35-38:

```typescript
  const terminalUrl = ttydUrl
    ? ttydUrl
    : ttydPort
      ? `http://localhost:${ttydPort}/`
      : null;
```

This removes the `ttydToken` dependency from the URL construction. The `ttydToken` prop can stay in the interface (harmless), but it's no longer used in the URL.

**Step 2: Verify the change compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add frontend/src/components/Terminal.tsx
git commit -m "fix: remove credentials from iframe URL (browsers block auth-in-URL)"
```

---

### Task 3: Remove Dead WebSocket Proxy from Docker Terminal API

**Files:**
- Modify: `backend/app/api/docker_terminal.py`

**Step 1: Remove the WebSocket proxy endpoint and unused imports**

The `/ws/docker/terminal/{session_id}` endpoint is dead code — the frontend never calls it (Docker mode routes to IframeTerminal, not WebSocketTerminal). Remove it along with its imports.

The file should contain only the REST endpoints:

```python
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

    level_number: int = 1


class CreateSessionResponse(BaseModel):
    """Response with session details."""

    session_id: str
    port: int
    terminal_url: str
    ttyd_token: str
    level: dict


@router.post("/api/docker/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new Docker sandbox session."""
    session_id = str(uuid.uuid4())[:8]

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(
            status_code=404, detail=f"Level {request.level_number} not found"
        )

    try:
        result = await sandbox_manager.create_session(
            session_id=session_id,
            level_number=request.level_number,
        )
    except RuntimeError as e:
        logger.error(f"Sandbox runtime error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except ValueError as e:
        logger.warning(f"Invalid request parameters: {e}")
        raise HTTPException(status_code=400, detail="Invalid request parameters")
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create session")

    return CreateSessionResponse(
        session_id=session_id,
        port=result["port"],
        terminal_url=f"http://localhost:{result['port']}/",
        ttyd_token=result["ttyd_token"],
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
        "terminal_url": f"http://localhost:{session['port']}/",
        "level_number": session["level_number"],
    }
```

Removed:
- `asyncio`, `json` imports
- `WebSocket`, `WebSocketDisconnect` from fastapi
- `websockets` and `ConnectionClosed` imports
- Entire `terminal_websocket` function (lines 113-207)
- Changed `terminal_url` from `ws://` to `http://` (it's an iframe URL now, not WebSocket)

**Step 2: Verify the backend starts**

Run: `cd backend && python -c "from app.api.docker_terminal import router; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/api/docker_terminal.py
git commit -m "fix: remove dead WebSocket proxy code from Docker terminal API"
```

---

### Task 4: Bind Docker Ports to Localhost Only

**Files:**
- Modify: `backend/app/services/docker_sandbox.py:96`

**Step 1: Change port mapping to bind to 127.0.0.1**

This ensures ttyd is only reachable from the local machine, not from the network. This is the security measure that replaces ttyd auth.

Replace line 96:

```python
            ports={"7681/tcp": ("127.0.0.1", self.port)},
```

**Step 2: Verify the change**

Run: `cd backend && python -c "from app.services.docker_sandbox import DockerSandbox; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/services/docker_sandbox.py
git commit -m "fix: bind ttyd ports to localhost only for security"
```

---

### Task 5: Rebuild and Test End-to-End

**Step 1: Rebuild the sandbox Docker image**

Run: `docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .`
Expected: Build succeeds

**Step 2: Start the backend**

Run: `cd backend && SANDBOX_MODE=docker uvicorn app.main:app --port 8000 --reload`
Expected: `Running in DOCKER mode`

**Step 3: Start the frontend**

Run: `cd frontend && npm run dev`
Expected: Dev server on `http://localhost:5173`

**Step 4: Test the flow**

1. Open `http://localhost:5173`
2. Select a lesson, click "Start"
3. Click "Start Exercise"
4. Iframe should load ttyd terminal with a working bash shell
5. Type `ls` in terminal — should see workspace files

**Step 5: Commit any fixes if needed, then final commit**

```bash
git add -A
git commit -m "feat: working Docker terminal with direct ttyd iframe"
```
