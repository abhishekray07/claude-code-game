# Modal WebSocket Proxy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable frontend to connect to Modal sandboxes via backend WebSocket proxy, eliminating ttyd and direct browser-to-Modal connections.

**Architecture:** Frontend connects to backend WebSocket (`/ws/terminal/{session_id}`). Backend maintains a persistent shell process in Modal sandbox, proxying input/output between WebSocket and sandbox stdin/stdout. Same protocol as local mode - no frontend changes needed.

**Tech Stack:** FastAPI WebSocket, Modal Sandbox exec with streaming, asyncio for concurrent read/write

---

## Task 1: Add Interactive Shell Support to ModalSandbox

**Files:**
- Modify: `backend/app/services/sandbox.py`

**Step 1: Add shell process management to ModalSandbox**

Add these methods to the `ModalSandbox` class:

```python
    def start_shell(self) -> None:
        """Start an interactive shell process in the sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Start bash as the claude user with a proper PTY-like environment
        # Use script command to allocate a pseudo-terminal
        self._shell_process = self.sandbox.exec(
            "su", "-", "claude", "-c",
            "cd /home/claude && TERM=xterm-256color bash -i"
        )
        self._shell_running = True
        logger.info(f"Shell started for session {self.session_id}")

    def write(self, data: bytes) -> None:
        """Write data to the shell's stdin."""
        if not self._shell_process:
            raise ValueError("Shell not started")
        try:
            self._shell_process.stdin.write(data.decode("utf-8", errors="replace"))
        except Exception as e:
            logger.error(f"Error writing to shell: {e}")
            self._shell_running = False

    def read(self, timeout: float = 0.1) -> bytes | None:
        """Read available data from shell stdout. Non-blocking with timeout."""
        if not self._shell_process:
            return None

        try:
            # Modal's stdout.read() may block, so we use a small chunk
            # This is a simplified approach - may need adjustment
            import select
            import sys

            # Try to read available data
            data = self._shell_process.stdout.read(4096)
            if data:
                return data.encode("utf-8") if isinstance(data, str) else data
            return None
        except Exception as e:
            logger.debug(f"Read timeout or error: {e}")
            return None

    @property
    def shell_running(self) -> bool:
        """Check if shell is still running."""
        return getattr(self, '_shell_running', False)
```

**Step 2: Update __init__ to initialize shell attributes**

Add to `__init__`:
```python
        self._shell_process = None
        self._shell_running = False
```

**Step 3: Commit**

```bash
git add backend/app/services/sandbox.py
git commit -m "feat: add interactive shell support to ModalSandbox"
```

---

## Task 2: Create Modal Terminal Router

**Files:**
- Create: `backend/app/api/modal_terminal.py`

**Step 1: Create the modal terminal router**

```python
"""WebSocket terminal endpoint for Modal sandboxes."""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.sandbox import ModalSandbox
from app.services.session_manager import session_manager, Session
from app.services.levels import load_level_by_number, get_exercise_dir
from app.services.watcher import GameWatcher
from app.services.verification import VerificationEngine
from app.models.level import Level

logger = logging.getLogger(__name__)
router = APIRouter()


class StartSessionRequest(BaseModel):
    """Request to start a new game session."""
    api_key: str
    level_number: int = 1
    access_code: str = ""


@router.post("/api/sessions")
async def create_session(request: StartSessionRequest):
    """Create a new game session with Modal sandbox."""

    # Check access code if configured
    if settings.demo_access_code:
        if request.access_code != settings.demo_access_code:
            raise HTTPException(status_code=403, detail="Invalid access code")

    # Validate API key format
    if not request.api_key.startswith("sk-ant-"):
        raise HTTPException(status_code=400, detail="Invalid API key format")

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(status_code=404, detail=f"Level {request.level_number} not found")

    # Generate session credentials
    session_id = session_manager.create_session_id()
    ttyd_password = session_manager.generate_ttyd_password()  # Keep for future use

    # Create Modal sandbox
    sandbox = ModalSandbox(session_id, ttyd_password)
    try:
        await sandbox.create()
        await sandbox.setup_credentials(request.api_key)

        # Copy exercise files
        exercise_dir = get_exercise_dir(request.level_number)
        if exercise_dir:
            await sandbox.copy_exercise_files(str(exercise_dir))

    except Exception as e:
        logger.error(f"Failed to create sandbox: {e}")
        if sandbox.sandbox:
            sandbox.terminate()
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {e}")

    # Create session (no terminal_url - we use WebSocket proxy)
    session = Session(
        session_id=session_id,
        sandbox=sandbox,
        level=level,
        level_number=request.level_number,
        ttyd_url="",  # Not used in proxy mode
        ttyd_password=ttyd_password,
    )
    session_manager.add(session)

    return {
        "session_id": session_id,
        "status": "ready",
        "level": {
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
            "video": level.video.model_dump() if level.video else None,
            "exercise": level.exercise.model_dump() if level.exercise else None,
        },
    }


@router.delete("/api/sessions/{session_id}")
async def stop_session(session_id: str):
    """Stop a game session."""
    session = session_manager.remove(session_id)
    if session:
        session.sandbox.terminate()
        return {"session_id": session_id, "status": "stopped"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal access via Modal sandbox proxy."""
    await websocket.accept()
    logger.info(f"Modal terminal WebSocket connected: {session_id}")

    session = session_manager.get(session_id)
    if not session:
        await websocket.send_text("Error: Session not found\r\n")
        await websocket.close()
        return

    sandbox: ModalSandbox = session.sandbox
    level: Level = session.level

    # Send level intro
    await websocket.send_text("\033[2J\033[H")  # Clear screen
    await websocket.send_text("\r\n")
    for line in level.intro.split("\n"):
        await websocket.send_text(line + "\r\n")
    await websocket.send_text("\r\n")
    await websocket.send_text("\033[90m" + "─" * 60 + "\033[0m\r\n")
    await websocket.send_text("\r\n")

    # Start the shell in Modal sandbox
    try:
        sandbox.start_shell()
    except Exception as e:
        await websocket.send_text(f"Error starting shell: {e}\r\n")
        await websocket.close()
        return

    # Setup watcher callbacks
    async def on_complete():
        session.completed = True
        await websocket.send_text("__LEVEL_COMPLETE__")

    async def on_hint(text: str):
        await websocket.send_text(f"\r\n\r\n{text}\r\n")

    async def on_progress(progress: dict):
        pass

    # Start watcher
    watcher = GameWatcher(sandbox, level, on_complete, on_hint, on_progress)
    watcher_task = asyncio.create_task(watcher.start())

    running = True

    async def read_from_sandbox():
        """Read from Modal sandbox and send to WebSocket."""
        while running:
            try:
                data = sandbox.read(0.05)
                if data:
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
                else:
                    await asyncio.sleep(0.05)
            except Exception as e:
                if running:
                    logger.error(f"Error reading from sandbox: {e}")
                break

    async def write_to_sandbox():
        """Read from WebSocket and write to Modal sandbox."""
        nonlocal running
        try:
            while running:
                data = await websocket.receive_text()

                # Check for magic commands
                stripped = data.strip()
                if stripped == "/hint":
                    hint_text = level.hints[0].text if level.hints else "No hints available"
                    await websocket.send_text(f"\r\n{hint_text}\r\n")
                    continue
                elif stripped == "/skip":
                    await websocket.send_text("\r\n⏭️ Skipping level...\r\n")
                    session.completed = True
                    await websocket.send_text("__LEVEL_COMPLETE__\r\n")
                    continue
                elif stripped == "/objective":
                    await websocket.send_text(f"\r\n📋 Level {level.number}: {level.title}\r\n")
                    continue
                elif stripped == "/progress":
                    verification = VerificationEngine(sandbox)
                    progress = await verification.get_progress(level)
                    await websocket.send_text(f"\r\n📊 Progress: {progress['passed_count']}/{progress['total_count']} checks passed\r\n")
                    continue

                # Write to sandbox
                sandbox.write(data.encode("utf-8"))

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error writing to sandbox: {e}")
        finally:
            running = False

    try:
        await asyncio.gather(
            read_from_sandbox(),
            write_to_sandbox(),
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"Terminal error: {e}")
    finally:
        running = False
        watcher.stop()
        watcher_task.cancel()


@router.get("/api/sessions/{session_id}/progress")
async def get_session_progress(session_id: str):
    """Get level completion progress."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    verification = VerificationEngine(session.sandbox)
    progress = await verification.get_progress(session.level)

    return {
        "session_id": session_id,
        "level_number": session.level_number,
        "completed": session.completed,
        "progress": progress,
    }
```

**Step 2: Commit**

```bash
git add backend/app/api/modal_terminal.py
git commit -m "feat: add Modal terminal WebSocket proxy endpoint"
```

---

## Task 3: Update Main App Routing

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Update main.py to use modal_terminal router in modal mode**

Replace the router selection logic:

```python
# Include routers based on sandbox mode
if settings.sandbox_mode == "modal":
    from app.api.modal_terminal import router as modal_router
    app.include_router(modal_router)
    print("🚀 Running in MODAL mode - sandboxes will be created in Modal cloud")
else:
    from app.api.terminal import router as terminal_router
    app.include_router(terminal_router)
    print("🖥️  Running in LOCAL mode - sandboxes will use local PTY")
```

**Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: route to modal_terminal in modal mode"
```

---

## Task 4: Simplify Frontend (Remove ttyd Mode)

**Files:**
- Modify: `frontend/src/components/Terminal.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Simplify Terminal.tsx to only use WebSocket mode**

The Terminal component can be simplified since we no longer need ttyd protocol support:

```tsx
import "@xterm/xterm/css/xterm.css";

import { FitAddon } from "@xterm/addon-fit";
import { Terminal as XTerm } from "@xterm/xterm";
import { useEffect, useRef } from "react";

import { config } from "../config";

interface TerminalProps {
  sessionId: string;
  onReady?: () => void;
  onLevelComplete?: () => void;
}

export function Terminal({
  sessionId,
  onReady,
  onLevelComplete,
}: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const onReadyRef = useRef(onReady);
  const onLevelCompleteRef = useRef(onLevelComplete);
  onReadyRef.current = onReady;
  onLevelCompleteRef.current = onLevelComplete;

  useEffect(() => {
    if (!terminalRef.current) return;

    let isActive = true;

    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: "#1a1a2e",
        foreground: "#eee",
        cursor: "#f0f0f0",
        cursorAccent: "#1a1a2e",
        selectionBackground: "#6366f1",
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;

    const connectTimeout = setTimeout(() => {
      if (!isActive) return;

      const wsUrl = `${config.apiUrl.replace("http", "ws")}/ws/terminal/${sessionId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isActive) return;
        onReadyRef.current?.();
      };

      ws.onmessage = (event) => {
        if (!isActive) return;
        const data = event.data;

        if (data.includes("__LEVEL_COMPLETE__")) {
          const cleanData = data.replace("__LEVEL_COMPLETE__", "");
          if (cleanData.trim()) {
            term.write(cleanData);
          }
          onLevelCompleteRef.current?.();
          return;
        }

        term.write(data);
      };

      ws.onerror = () => {
        if (!isActive) return;
        term.writeln("\r\n\x1b[31mConnection error\x1b[0m");
      };

      ws.onclose = () => {
        if (!isActive) return;
        term.writeln("\r\n\x1b[33mDisconnected\x1b[0m");
      };

      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(data);
        }
      });
    }, 100);

    const handleResize = () => fitAddon.fit();
    window.addEventListener("resize", handleResize);

    return () => {
      isActive = false;
      clearTimeout(connectTimeout);
      window.removeEventListener("resize", handleResize);
      if (wsRef.current) wsRef.current.close();
      term.dispose();
    };
  }, [sessionId]);

  return (
    <div
      ref={terminalRef}
      style={{
        width: "100%",
        height: "100%",
        padding: "10px",
        backgroundColor: "#1a1a2e",
      }}
    />
  );
}
```

**Step 2: Update App.tsx to remove terminal_url handling**

In `App.tsx`, update the Session interface and Terminal usage:

```tsx
interface Session {
  session_id: string;
  level: Level;
}
```

And update Terminal component usage:

```tsx
<Terminal
  sessionId={session.session_id}
  onReady={() => console.log("Terminal ready")}
  onLevelComplete={() => {
    setLevelComplete(true);
    markComplete(session.level.number);
  }}
/>
```

**Step 3: Commit**

```bash
git add frontend/src/components/Terminal.tsx frontend/src/App.tsx
git commit -m "feat: simplify frontend to use WebSocket proxy only"
```

---

## Task 5: Fix Modal Sandbox Read/Write for Streaming

**Files:**
- Modify: `backend/app/services/sandbox.py`

The initial `read()` implementation may not work well with Modal's streaming. Here's a more robust approach using threading:

**Step 1: Update ModalSandbox with thread-based I/O**

```python
import queue
import threading

class ModalSandbox:
    # ... existing code ...

    def __init__(self, session_id: str, ttyd_password: str):
        # ... existing init ...
        self._shell_process = None
        self._shell_running = False
        self._output_queue: queue.Queue = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def start_shell(self) -> None:
        """Start an interactive shell process in the sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        self._shell_process = self.sandbox.exec(
            "su", "-", "claude", "-c",
            "cd /home/claude && TERM=xterm-256color bash -i"
        )
        self._shell_running = True

        # Start background thread to read stdout
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        logger.info(f"Shell started for session {self.session_id}")

    def _read_stdout(self) -> None:
        """Background thread to read stdout into queue."""
        try:
            while self._shell_running and self._shell_process:
                chunk = self._shell_process.stdout.read(1024)
                if chunk:
                    self._output_queue.put(chunk)
                else:
                    break
        except Exception as e:
            logger.debug(f"Reader thread ended: {e}")
        finally:
            self._shell_running = False

    def write(self, data: bytes) -> None:
        """Write data to the shell's stdin."""
        if not self._shell_process:
            raise ValueError("Shell not started")
        try:
            text = data.decode("utf-8", errors="replace")
            self._shell_process.stdin.write(text)
        except Exception as e:
            logger.error(f"Error writing to shell: {e}")
            self._shell_running = False

    def read(self, timeout: float = 0.1) -> bytes | None:
        """Read available data from output queue."""
        try:
            data = self._output_queue.get(timeout=timeout)
            if isinstance(data, str):
                return data.encode("utf-8")
            return data
        except queue.Empty:
            return None

    @property
    def shell_running(self) -> bool:
        return self._shell_running
```

**Step 2: Commit**

```bash
git add backend/app/services/sandbox.py
git commit -m "feat: add thread-based I/O for Modal shell streaming"
```

---

## Task 6: Test End-to-End

**Step 1: Restart backend in modal mode**

```bash
pkill -f "uvicorn app.main" 2>/dev/null
SANDBOX_MODE=modal uv run uvicorn app.main:app --port 8080 --reload
```

**Step 2: Start frontend**

```bash
cd frontend && npm run dev
```

**Step 3: Test flow**

1. Open http://localhost:5174
2. Enter API key
3. Start Lesson 1
4. Verify terminal connects via WebSocket
5. Type `claude` to start Claude Code
6. Verify interactive shell works

**Step 4: Commit test verification**

```bash
git add -A
git commit -m "test: verify modal websocket proxy works end-to-end"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add shell support to ModalSandbox | `sandbox.py` |
| 2 | Create Modal terminal router | `modal_terminal.py` |
| 3 | Update main.py routing | `main.py` |
| 4 | Simplify frontend | `Terminal.tsx`, `App.tsx` |
| 5 | Fix streaming I/O | `sandbox.py` |
| 6 | Test end-to-end | Manual testing |

**Key benefits of this approach:**
- No ttyd complexity
- Same protocol as local mode - minimal frontend changes
- Full control over authentication at backend level
- Works with existing GameWatcher for level completion detection
