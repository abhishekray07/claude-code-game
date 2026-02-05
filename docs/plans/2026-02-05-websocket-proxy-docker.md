# WebSocket Proxy for Docker Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add WebSocket proxy to Docker mode so terminals work when deployed to a VPS (not just localhost).

**Architecture:** Frontend connects to backend WebSocket endpoint, backend proxies to container's ttyd on localhost:PORT. Reuses existing WebSocketTerminal component.

**Tech Stack:** FastAPI WebSocket, websockets library, React xterm.js

---

## Task 1: Add WebSocket Proxy Endpoint to Docker Terminal API

**Files:**
- Modify: `backend/app/api/docker_terminal.py:1-12` (imports)
- Modify: `backend/app/api/docker_terminal.py:185` (add new endpoint at end)

**Step 1: Add imports for WebSocket support**

Add after line 5 in `backend/app/api/docker_terminal.py`:

```python
import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

try:
    import websockets
except ImportError:
    websockets = None

from app.services.sandbox_manager import sandbox_manager
from app.services.levels import load_level_by_number
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Step 2: Add WebSocket proxy endpoint**

Add at the end of `backend/app/api/docker_terminal.py` (after line 185):

```python
@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket proxy to local ttyd for Docker mode.

    Solves VPS deployment: frontend connects to backend, backend proxies to container.
    """
    if websockets is None:
        logger.error("websockets library not installed")
        await websocket.close(code=1011, reason="Server misconfigured")
        return

    # Accept with tty subprotocol (required by ttyd)
    await websocket.accept(subprotocol="tty")

    # Look up session to get port
    session = sandbox_manager.get_session(session_id)
    if not session:
        logger.warning(f"WebSocket: Session not found: {session_id}")
        await websocket.close(code=1008, reason="Session not found")
        return

    port = session["port"]
    target_url = f"ws://127.0.0.1:{port}/ws"
    logger.info(f"WS proxy: {session_id} -> localhost:{port}")

    connection_active = True

    try:
        async with websockets.connect(
            target_url,
            subprotocols=["tty"],
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as ttyd_ws:
            logger.info(f"Connected to ttyd for {session_id}")

            async def forward_frontend_to_ttyd():
                """Forward messages from browser to ttyd."""
                nonlocal connection_active
                try:
                    while connection_active:
                        try:
                            data = await websocket.receive_text()
                        except Exception:
                            # Try receiving bytes if text fails
                            try:
                                data = await websocket.receive_bytes()
                                await ttyd_ws.send(data)
                                sandbox_manager.update_activity(session_id)
                                continue
                            except Exception:
                                break
                        sandbox_manager.update_activity(session_id)
                        await ttyd_ws.send(data)
                except WebSocketDisconnect:
                    logger.info(f"Frontend disconnected: {session_id}")
                    connection_active = False
                except Exception as e:
                    logger.debug(f"Frontend->ttyd ended ({session_id}): {e}")
                    connection_active = False

            async def forward_ttyd_to_frontend():
                """Forward messages from ttyd to browser."""
                nonlocal connection_active
                try:
                    async for message in ttyd_ws:
                        if not connection_active:
                            break
                        sandbox_manager.update_activity(session_id)
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception as e:
                    if connection_active:
                        logger.debug(f"ttyd->Frontend ended ({session_id}): {e}")
                    connection_active = False

            async def keepalive_ping():
                """Send periodic pings to keep frontend connection alive."""
                nonlocal connection_active
                try:
                    while connection_active:
                        await asyncio.sleep(30)
                        if connection_active:
                            try:
                                await websocket.send_bytes(b"")
                            except Exception:
                                pass
                except asyncio.CancelledError:
                    pass

            # Run all three tasks concurrently
            await asyncio.gather(
                forward_frontend_to_ttyd(),
                forward_ttyd_to_frontend(),
                keepalive_ping(),
                return_exceptions=True,
            )

    except websockets.exceptions.InvalidStatusCode as e:
        logger.warning(f"ttyd connection failed for {session_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Container not ready")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WS proxy error for {session_id}: {type(e).__name__}: {e}")
        try:
            await websocket.close(code=1011, reason="Proxy error")
        except Exception:
            pass
```

**Step 3: Verify websockets is in requirements**

Run: `grep websockets backend/requirements.txt`
Expected: Should show `websockets` is listed. If not, add it.

**Step 4: Run backend to verify no import errors**

Run: `cd backend && python -c "from app.api.docker_terminal import router; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/api/docker_terminal.py
git commit -m "feat: add WebSocket proxy endpoint for Docker mode terminals"
```

---

## Task 2: Update Frontend Terminal Component to Use WebSocket for Docker

**Files:**
- Modify: `frontend/src/components/Terminal.tsx:255-265` (terminal selection logic)

**Step 1: Change Terminal component to use WebSocket for Docker mode**

The current logic at lines 255-265:
```tsx
// Use iframe for Fly.io (ttydUrl provided) or Docker mode (ttydPort + ttydToken)
if (ttydUrl || (ttydPort && ttydToken)) {
  return (
    <IframeTerminal
      ...
    />
  );
}
```

Change to only use iframe when `ttydUrl` is provided (Fly.io mode):

```tsx
export function Terminal({
  sessionId,
  ttydUrl,
  ttydPort,
  ttydToken,
  onReady,
  onLevelComplete,
}: TerminalProps) {
  // Use iframe ONLY for Fly.io (ttydUrl provided)
  // Docker mode now uses WebSocket proxy like Modal/local
  if (ttydUrl) {
    return (
      <IframeTerminal
        ttydUrl={ttydUrl}
        ttydPort={ttydPort}
        ttydToken={ttydToken}
        onReady={onReady}
      />
    );
  }

  // WebSocket mode for Docker/Modal/local
  return (
    <WebSocketTerminal
      sessionId={sessionId}
      onReady={onReady}
      onLevelComplete={onLevelComplete}
    />
  );
}
```

**Step 2: Verify frontend compiles**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

**Step 3: Commit**

```bash
git add frontend/src/components/Terminal.tsx
git commit -m "feat: use WebSocket proxy for Docker mode terminals"
```

---

## Task 3: Test WebSocket Proxy Locally

**Files:**
- No changes - manual testing

**Step 1: Build sandbox image (if not already built)**

Run: `docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .`
Expected: Image builds successfully

**Step 2: Start backend in Docker mode**

Run in terminal 1:
```bash
cd backend
SANDBOX_MODE=docker uvicorn app.main:app --reload --port 8000
```
Expected: Server starts on port 8000

**Step 3: Start frontend**

Run in terminal 2:
```bash
cd frontend
VITE_API_URL=http://localhost:8000 VITE_TERMINAL_MODE=docker npm run dev
```
Expected: Frontend starts on port 5173

**Step 4: Create a session via curl**

Run in terminal 3:
```bash
curl -X POST http://localhost:8000/api/docker/sessions \
  -H "Content-Type: application/json" \
  -d '{"level_number": 1}'
```
Expected: Returns JSON with `session_id`, `port`, `terminal_url`, `ttyd_token`

Note the `session_id` from the response.

**Step 5: Test WebSocket connection directly**

Run:
```bash
npx wscat -c "ws://localhost:8000/ws/terminal/<SESSION_ID>" -s tty
```
Expected:
- Connection opens
- You see terminal output (bash prompt or ttyd output)
- Typing sends input to the container

**Step 6: Test in browser**

1. Open http://localhost:5173
2. Click "Start" on Lesson 1
3. Wait for video phase, click "Start Exercise"
4. Terminal should connect via WebSocket and show bash prompt
5. Type `ls` and verify output appears

**Step 7: Verify WebSocket is being used (not iframe)**

Open browser DevTools → Network → WS tab
Expected: See WebSocket connection to `ws://localhost:8000/ws/terminal/<session_id>`

**Step 8: Commit test verification**

```bash
git add -A
git commit -m "test: verify WebSocket proxy works locally" --allow-empty
```

---

## Task 4: Clean Up Unused Docker Response Fields (Optional)

**Files:**
- Modify: `frontend/src/App.tsx:138-143` (Docker session data)

**Step 1: Stop storing port/ttyd_token for Docker sessions**

The frontend no longer needs `port` and `ttyd_token` for Docker mode since we use WebSocket proxy.

In `frontend/src/App.tsx`, find lines 136-143:

```tsx
const dockerData = await response.json();
// Transform Docker API response to match Session interface
data = {
  session_id: dockerData.session_id,
  level: dockerData.level,
  port: dockerData.port,
  ttyd_token: dockerData.ttyd_token,
};
```

Change to:

```tsx
const dockerData = await response.json();
// Transform Docker API response to match Session interface
// Note: port/ttyd_token not needed - Docker uses WebSocket proxy
data = {
  session_id: dockerData.session_id,
  level: dockerData.level,
};
```

**Step 2: Also update nextLevel response handling (lines 202-208)**

Find:
```tsx
setSession({
  ...session,
  level: data.level,
  port: data.port,
  ttyd_token: data.ttyd_token,
});
```

Change to:
```tsx
setSession({
  ...session,
  level: data.level,
});
```

**Step 3: Verify frontend still works**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 4: Manual test**

Repeat Task 3 Step 6 - terminal should still work.

**Step 5: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "refactor: remove unused port/ttyd_token from Docker session state"
```

---

## Summary

| Task | Description | Status |
|------|-------------|--------|
| 1 | Add WebSocket proxy endpoint to backend | |
| 2 | Update Terminal component to use WebSocket for Docker | |
| 3 | Test WebSocket proxy locally | |
| 4 | Clean up unused response fields (optional) | |

## Testing Checklist

- [ ] Backend starts without import errors
- [ ] WebSocket endpoint accepts connections with `tty` subprotocol
- [ ] Session lookup works (returns 1008 for invalid session)
- [ ] Bidirectional message forwarding works (type → see output)
- [ ] Activity updates prevent session timeout
- [ ] Frontend uses WebSocket (not iframe) for Docker mode
- [ ] Terminal displays correctly in browser
- [ ] Reconnection works if connection drops
