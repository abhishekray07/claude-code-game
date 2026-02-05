# Modal Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy Claude Code Game to production using Modal (backend + sandboxes) and Vercel (frontend) with secure ttyd basic auth.

**Architecture:**
- Frontend on Vercel connects to Modal backend API
- Backend creates Modal sandboxes with ttyd + basic auth
- Frontend connects directly to auth'd ttyd URL for terminal
- Frontend polls backend for level completion status
- Activity-based timeout (10 min idle) + 60 min hard cap

**Tech Stack:**
- Backend: FastAPI on Modal web endpoint
- Frontend: React + Vite on Vercel
- Sandboxes: Modal with ttyd, basic auth
- Auth: Demo access code + per-session ttyd passwords

---

## Task 1: Update Config for Production Settings

**Files:**
- Modify: `backend/app/config.py`

**Step 1: Add production config settings**

```python
"""Game configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

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
    demo_access_code: str = ""  # Set via DEMO_ACCESS_CODE env var
    allowed_origins: list[str] = ["http://localhost:5173"]  # Add Vercel domain in prod

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add production config settings for sandbox timeouts and security"
```

---

## Task 2: Create Session Manager with Activity Tracking

**Files:**
- Create: `backend/app/services/session_manager.py`

**Step 1: Create session manager**

```python
"""Session manager with activity tracking and cleanup."""
import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """A game session with activity tracking."""
    session_id: str
    sandbox: Any  # Modal sandbox
    level: Any  # Level object
    level_number: int
    ttyd_url: str  # Auth'd URL for frontend
    ttyd_password: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    completed: bool = False


class SessionManager:
    """Manages game sessions with activity-based cleanup."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._cleanup_task: asyncio.Task | None = None

    def create_session_id(self) -> str:
        """Generate cryptographically secure session ID."""
        return secrets.token_urlsafe(32)

    def generate_ttyd_password(self) -> str:
        """Generate random password for ttyd basic auth."""
        return secrets.token_urlsafe(16)

    def add(self, session: Session) -> None:
        """Add a session."""
        self._sessions[session.session_id] = session
        logger.info(f"Session added: {session.session_id}")

    def get(self, session_id: str) -> Session | None:
        """Get a session and update activity timestamp."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = time.time()
        return session

    def remove(self, session_id: str) -> Session | None:
        """Remove and return a session."""
        return self._sessions.pop(session_id, None)

    def touch(self, session_id: str) -> bool:
        """Update activity timestamp. Returns False if session not found."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = time.time()
            return True
        return False

    async def cleanup_idle_sessions(self) -> None:
        """Terminate sessions that have been idle too long."""
        now = time.time()
        idle_timeout = settings.sandbox_idle_timeout_seconds

        to_remove = []
        for session_id, session in self._sessions.items():
            idle_time = now - session.last_activity
            if idle_time > idle_timeout:
                logger.info(f"Session {session_id} idle for {idle_time:.0f}s, terminating")
                to_remove.append(session_id)

        for session_id in to_remove:
            session = self._sessions.pop(session_id, None)
            if session and session.sandbox:
                try:
                    session.sandbox.terminate()
                except Exception as e:
                    logger.error(f"Error terminating sandbox: {e}")

    async def start_cleanup_loop(self) -> None:
        """Start background cleanup task."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # Check every minute
                await self.cleanup_idle_sessions()

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Session cleanup loop started")

    async def stop_cleanup_loop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session cleanup loop stopped")

    async def terminate_all(self) -> None:
        """Terminate all active sessions."""
        for session_id in list(self._sessions.keys()):
            session = self._sessions.pop(session_id, None)
            if session and session.sandbox:
                try:
                    session.sandbox.terminate()
                except Exception:
                    pass
        logger.info("All sessions terminated")


# Global instance
session_manager = SessionManager()
```

**Step 2: Commit**

```bash
git add backend/app/services/session_manager.py
git commit -m "feat: add session manager with activity tracking and cleanup"
```

---

## Task 3: Update Modal Sandbox for Production

**Files:**
- Modify: `backend/app/services/sandbox.py`

**Step 1: Rewrite sandbox.py for production Modal with ttyd auth**

```python
"""Modal sandbox with ttyd basic auth."""
import asyncio
import json
import logging
import time
from typing import Any

import modal

from app.config import settings
from app.services.modal_config import get_game_image

logger = logging.getLogger(__name__)


class ModalSandbox:
    """Modal sandbox with secure ttyd access."""

    def __init__(self, session_id: str, ttyd_password: str):
        self.session_id = session_id
        self.ttyd_password = ttyd_password
        self.sandbox: modal.Sandbox | None = None
        self.tunnel_url: str | None = None
        self._app = modal.App.lookup(settings.modal_app_name, create_if_missing=True)
        self._image = get_game_image()

    async def create(self) -> str:
        """Create sandbox and start ttyd. Returns auth'd terminal URL."""
        logger.info(f"Creating Modal sandbox for session {self.session_id}")

        # Create sandbox with ttyd port exposed
        self.sandbox = modal.Sandbox.create(
            app=self._app,
            image=self._image,
            timeout=settings.sandbox_timeout_seconds,
            cpu=settings.sandbox_cpu,
            memory=settings.sandbox_memory_mb,
            encrypted_ports=[settings.ttyd_port],
        )
        logger.info(f"Sandbox created: {self.sandbox.object_id}")

        return self.sandbox.object_id

    async def setup_credentials(self, api_key: str) -> bool:
        """Setup Anthropic API key in sandbox environment."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Write credentials file
        creds = json.dumps({"apiKey": api_key})
        setup_cmd = f"""
        mkdir -p /home/claude/.claude &&
        echo '{creds}' > /home/claude/.claude/.credentials.json &&
        chmod 600 /home/claude/.claude/.credentials.json &&
        chown claude:claude /home/claude/.claude/.credentials.json
        """

        process = self.sandbox.exec("sh", "-c", setup_cmd)
        process.wait()

        return process.returncode == 0

    async def start_ttyd(self) -> str:
        """Start ttyd with basic auth. Returns authenticated URL."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Start ttyd with basic auth
        username = "player"
        cmd = f"ttyd -W -p {settings.ttyd_port} -c {username}:{self.ttyd_password} su - claude"
        self.sandbox.exec("sh", "-c", f"nohup {cmd} > /tmp/ttyd.log 2>&1 &")

        # Wait for ttyd to start
        await asyncio.sleep(3)

        # Get tunnel URL
        tunnels = self.sandbox.tunnels()
        if settings.ttyd_port not in tunnels:
            raise RuntimeError(f"Tunnel for port {settings.ttyd_port} not available")

        base_url = tunnels[settings.ttyd_port].url
        self.tunnel_url = base_url.replace("https://", f"https://{username}:{self.ttyd_password}@")

        logger.info(f"ttyd started, tunnel ready for session {self.session_id}")
        return self.tunnel_url

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude's messages.jsonl from sandbox."""
        if not self.sandbox:
            return []

        # Find the latest .jsonl file
        find_cmd = "find /home/claude/.claude/projects -name '*.jsonl' -type f 2>/dev/null | head -1"
        process = self.sandbox.exec("sh", "-c", find_cmd)
        stdout = process.stdout.read()
        process.wait()

        jsonl_path = stdout.strip()
        if not jsonl_path:
            return []

        # Read the file
        process = self.sandbox.exec("cat", jsonl_path)
        content = process.stdout.read()
        process.wait()

        messages = []
        for line in content.strip().split("\n"):
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        return messages

    async def exec_command(self, *args: str) -> tuple[str, str, int]:
        """Execute a command in the sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        process = self.sandbox.exec(*args)
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        process.wait()

        return stdout, stderr, process.returncode

    async def copy_exercise_files(self, source_dir: str) -> bool:
        """Copy exercise files to sandbox workspace."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # For Modal, we need to copy files via exec
        # This is a simplified approach - in production you might use Modal volumes
        import os
        from pathlib import Path

        source = Path(source_dir)
        if not source.exists():
            logger.warning(f"Exercise directory not found: {source_dir}")
            return False

        for item in source.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(source)
                content = item.read_text()
                dest_path = f"/home/claude/{rel_path}"

                # Create parent directory
                parent = str(Path(dest_path).parent)
                self.sandbox.exec("sh", "-c", f"mkdir -p {parent}")

                # Write file (escape single quotes in content)
                escaped = content.replace("'", "'\"'\"'")
                self.sandbox.exec("sh", "-c", f"cat > {dest_path} << 'EOFMARKER'\n{content}\nEOFMARKER")
                self.sandbox.exec("chown", "claude:claude", dest_path)

        logger.info(f"Exercise files copied from {source_dir}")
        return True

    def terminate(self) -> None:
        """Terminate the sandbox."""
        if self.sandbox:
            try:
                self.sandbox.terminate()
                logger.info(f"Sandbox terminated for session {self.session_id}")
            except Exception as e:
                logger.error(f"Error terminating sandbox: {e}")
```

**Step 2: Commit**

```bash
git add backend/app/services/sandbox.py
git commit -m "feat: update Modal sandbox with ttyd basic auth"
```

---

## Task 4: Create Production API Endpoints

**Files:**
- Create: `backend/app/api/sessions.py`

**Step 1: Create new sessions API**

```python
"""Session API endpoints for production."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.session_manager import session_manager, Session
from app.services.sandbox import ModalSandbox
from app.services.levels import load_level_by_number, get_exercise_dir
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request to create a new game session."""
    api_key: str
    level_number: int = 1
    access_code: str = ""


class CreateSessionResponse(BaseModel):
    """Response with session info and terminal URL."""
    session_id: str
    terminal_url: str
    level: dict


class SessionStatusResponse(BaseModel):
    """Response with session status and completion info."""
    session_id: str
    level_number: int
    completed: bool
    progress: dict | None


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new game session with Modal sandbox."""

    # Check access code if configured
    if settings.demo_access_code:
        if request.access_code != settings.demo_access_code:
            raise HTTPException(status_code=403, detail="Invalid access code")

    # Validate API key format (basic check)
    if not request.api_key.startswith("sk-ant-"):
        raise HTTPException(status_code=400, detail="Invalid API key format")

    # Load level
    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(status_code=404, detail=f"Level {request.level_number} not found")

    # Generate session credentials
    session_id = session_manager.create_session_id()
    ttyd_password = session_manager.generate_ttyd_password()

    # Create Modal sandbox
    sandbox = ModalSandbox(session_id, ttyd_password)
    try:
        await sandbox.create()
        await sandbox.setup_credentials(request.api_key)

        # Copy exercise files
        exercise_dir = get_exercise_dir(request.level_number)
        if exercise_dir:
            await sandbox.copy_exercise_files(str(exercise_dir))

        # Start ttyd and get auth'd URL
        terminal_url = await sandbox.start_ttyd()

    except Exception as e:
        logger.error(f"Failed to create sandbox: {e}")
        if sandbox.sandbox:
            sandbox.terminate()
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {e}")

    # Create session
    session = Session(
        session_id=session_id,
        sandbox=sandbox,
        level=level,
        level_number=request.level_number,
        ttyd_url=terminal_url,
        ttyd_password=ttyd_password,
    )
    session_manager.add(session)

    return CreateSessionResponse(
        session_id=session_id,
        terminal_url=terminal_url,
        level={
            "number": level.number,
            "title": level.title,
            "module": level.module,
            "intro": level.intro,
            "video": level.video.model_dump() if level.video else None,
            "exercise": level.exercise.model_dump() if level.exercise else None,
        },
    )


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get session status and check level completion."""

    session = session_manager.get(session_id)  # Also updates activity timestamp
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check completion
    verification = VerificationEngine(session.sandbox)
    completed = await verification.check_level_complete(session.level)
    progress = await verification.get_progress(session.level)

    if completed:
        session.completed = True

    return SessionStatusResponse(
        session_id=session_id,
        level_number=session.level_number,
        completed=session.completed,
        progress=progress,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Terminate a session."""
    session = session_manager.remove(session_id)
    if session:
        session.sandbox.terminate()
        return {"session_id": session_id, "status": "terminated"}
    raise HTTPException(status_code=404, detail="Session not found")
```

**Step 2: Commit**

```bash
git add backend/app/api/sessions.py
git commit -m "feat: add production session API endpoints"
```

---

## Task 5: Create Modal Web Endpoint

**Files:**
- Create: `backend/modal_app.py`

**Step 1: Create Modal app entry point**

```python
"""Modal web endpoint for Claude Code Game backend."""
import modal

from app.config import settings

# Create Modal app
app = modal.App(settings.modal_app_name)

# Define image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "pyyaml>=6.0.1",
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("claude-game-secrets")],
    allow_concurrent_inputs=100,
    container_idle_timeout=300,
)
@modal.asgi_app()
def fastapi_app():
    """Return the FastAPI app for Modal to serve."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings
    from app.api.sessions import router as sessions_router
    from app.services.session_manager import session_manager

    api = FastAPI(
        title=settings.app_name,
        description="Interactive game for learning Claude Code",
    )

    # CORS for frontend
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    api.include_router(sessions_router)

    @api.get("/health")
    async def health():
        return {"status": "healthy", "app": settings.app_name}

    @api.get("/api/levels")
    async def list_levels():
        from app.services.levels import list_levels
        levels = list_levels()
        return {"levels": levels, "total": len(levels)}

    @api.get("/api/levels/{number}")
    async def get_level(number: int):
        from app.services.levels import load_level_by_number
        from fastapi import HTTPException
        level = load_level_by_number(number)
        if not level:
            raise HTTPException(status_code=404, detail="Level not found")
        return level.model_dump()

    @api.on_event("startup")
    async def startup():
        await session_manager.start_cleanup_loop()

    @api.on_event("shutdown")
    async def shutdown():
        await session_manager.stop_cleanup_loop()
        await session_manager.terminate_all()

    return api
```

**Step 2: Commit**

```bash
git add backend/modal_app.py
git commit -m "feat: add Modal web endpoint entry point"
```

---

## Task 6: Update Frontend for Direct ttyd Connection

**Files:**
- Modify: `frontend/src/components/Terminal.tsx`

**Step 1: Update Terminal component to use ttyd URL**

```tsx
import "@xterm/xterm/css/xterm.css";

import { FitAddon } from "@xterm/addon-fit";
import { Terminal as XTerm } from "@xterm/xterm";
import { AttachAddon } from "@xterm/addon-attach";
import { useEffect, useRef } from "react";

interface TerminalProps {
  terminalUrl: string; // Auth'd ttyd WebSocket URL
  onReady?: () => void;
}

export function Terminal({ terminalUrl, onReady }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  useEffect(() => {
    if (!terminalRef.current || !terminalUrl) return;

    let isActive = true;

    // Create terminal
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

    // Convert HTTPS URL to WSS for ttyd
    const wsUrl = terminalUrl.replace("https://", "wss://") + "/ws";

    const connectTimeout = setTimeout(() => {
      if (!isActive) return;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isActive) return;

        // Attach terminal to WebSocket
        const attachAddon = new AttachAddon(ws);
        term.loadAddon(attachAddon);

        // Send terminal size
        const dimensions = fitAddon.proposeDimensions();
        if (dimensions) {
          // ttyd resize protocol
          ws.send(JSON.stringify({ type: "resize", cols: dimensions.cols, rows: dimensions.rows }));
        }

        onReadyRef.current?.();
      };

      ws.onerror = () => {
        if (!isActive) return;
        term.writeln("\r\n\x1b[31mConnection error\x1b[0m");
      };

      ws.onclose = () => {
        if (!isActive) return;
        term.writeln("\r\n\x1b[33mDisconnected\x1b[0m");
      };
    }, 100);

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        const dimensions = fitAddon.proposeDimensions();
        if (dimensions) {
          ws.send(JSON.stringify({ type: "resize", cols: dimensions.cols, rows: dimensions.rows }));
        }
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      isActive = false;
      clearTimeout(connectTimeout);
      window.removeEventListener("resize", handleResize);
      if (wsRef.current) {
        wsRef.current.close();
      }
      term.dispose();
    };
  }, [terminalUrl]);

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

**Step 2: Install addon-attach**

```bash
cd frontend && npm install @xterm/addon-attach
```

**Step 3: Commit**

```bash
git add frontend/src/components/Terminal.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: update Terminal to connect directly to ttyd URL"
```

---

## Task 7: Update Frontend App for Production API

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/config.ts`

**Step 1: Create config file**

```typescript
// frontend/src/config.ts
export const config = {
  apiUrl: import.meta.env.VITE_API_URL || "http://localhost:8080",
};
```

**Step 2: Update App.tsx for new API and status polling**

```tsx
import "./App.css";

import { useCallback, useEffect, useRef, useState } from "react";

import { Terminal } from "./components/Terminal";
import { VideoPlayer } from "./components/VideoPlayer";
import { useProgress } from "./hooks/useProgress";
import { config } from "./config";

const TOTAL_LESSONS = 9;
const STATUS_POLL_INTERVAL = 5000; // 5 seconds

interface Video {
  url: string;
  duration_seconds: number;
}

interface Exercise {
  intro: string;
  objective: string;
}

interface Level {
  number: number;
  title: string;
  module: string;
  intro?: string;
  video?: Video;
  exercise?: Exercise;
}

interface Session {
  session_id: string;
  terminal_url: string;
  level: Level;
}

type LessonPhase = "watch" | "exercise";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [apiKey, setApiKey] = useState(import.meta.env.VITE_ANTHROPIC_API_KEY || "");
  const [accessCode, setAccessCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);
  const [phase, setPhase] = useState<LessonPhase>("watch");
  const [selectedLesson, setSelectedLesson] = useState(1);
  const { progress, markComplete } = useProgress();

  // Status polling
  const pollIntervalRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback((sessionId: string) => {
    stopPolling();

    const poll = async () => {
      try {
        const response = await fetch(`${config.apiUrl}/api/sessions/${sessionId}/status`);
        if (response.ok) {
          const data = await response.json();
          if (data.completed) {
            setLevelComplete(true);
            stopPolling();
          }
        }
      } catch (e) {
        console.error("Status poll error:", e);
      }
    };

    // Poll immediately, then every 5 seconds
    poll();
    pollIntervalRef.current = window.setInterval(poll, STATUS_POLL_INTERVAL);
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const startGame = async (levelNumber: number = 1) => {
    if (!apiKey.trim()) {
      setError("Please enter your API key");
      return;
    }

    setLoading(true);
    setError("");
    setLevelComplete(false);
    setPhase("watch");
    stopPolling();

    try {
      const response = await fetch(`${config.apiUrl}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: apiKey,
          level_number: levelNumber,
          access_code: accessCode,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to start session");
      }

      const data: Session = await response.json();
      setSession(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleLevelComplete = useCallback(() => {
    setLevelComplete(true);
    stopPolling();
    if (session) {
      markComplete(session.level.number);
    }
  }, [session, markComplete, stopPolling]);

  const startExercise = () => {
    setPhase("exercise");
    if (session) {
      startPolling(session.session_id);
    }
  };

  const nextLevel = () => {
    if (session) {
      const nextLevelNum = session.level.number + 1;
      if (nextLevelNum <= TOTAL_LESSONS) {
        startGame(nextLevelNum);
      } else {
        setSession(null);
        setLevelComplete(false);
      }
    }
  };

  const endSession = async () => {
    if (session) {
      stopPolling();
      try {
        await fetch(`${config.apiUrl}/api/sessions/${session.session_id}`, {
          method: "DELETE",
        });
      } catch (e) {
        console.error("Error ending session:", e);
      }
      setSession(null);
      setLevelComplete(false);
    }
  };

  // Start screen
  if (!session) {
    return (
      <div className="start-screen">
        <div className="start-content">
          <h1>Claude Code Game</h1>
          <p className="subtitle">
            Learn Claude Code through interactive challenges
          </p>

          <div className="input-group">
            <input
              type="password"
              placeholder="Enter your Anthropic API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <input
              type="text"
              placeholder="Access code (if required)"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && startGame(selectedLesson)}
            />
            <div className="lesson-select-row">
              <select
                value={selectedLesson}
                onChange={(e) => setSelectedLesson(Number(e.target.value))}
                className="lesson-select"
              >
                {Array.from({ length: TOTAL_LESSONS }, (_, i) => i + 1).map(
                  (n) => (
                    <option key={n} value={n}>
                      Lesson {n}
                    </option>
                  )
                )}
              </select>
              <button
                onClick={() => startGame(selectedLesson)}
                disabled={loading || !apiKey.trim()}
              >
                {loading ? "Starting..." : "Start"}
              </button>
            </div>
          </div>

          {error && <p className="error">{error}</p>}

          <p className="hint">
            Don't have an API key?{" "}
            <a
              href="https://console.anthropic.com/settings/keys"
              target="_blank"
              rel="noopener noreferrer"
            >
              Get one here
            </a>
          </p>

          <div className="progress-indicator">
            <span>
              {progress.completedLessons.length} of {TOTAL_LESSONS} lessons
              complete
            </span>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${(progress.completedLessons.length / TOTAL_LESSONS) * 100}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Watch Phase
  if (phase === "watch") {
    const hasVideo = session.level.video?.url;

    return (
      <div className="lesson-screen">
        <div className="lesson-header">
          <span className="module-badge">{session.level.module}</span>
          <h1>
            Lesson {session.level.number}: {session.level.title}
          </h1>
        </div>

        <div className="lesson-content">
          {hasVideo ? (
            <>
              <VideoPlayer url={session.level.video!.url} onEnded={() => {}} />
              <button className="start-exercise-btn" onClick={startExercise}>
                Start Exercise →
              </button>
            </>
          ) : (
            <>
              <div className="no-video-message">
                <p>This lesson doesn't have a video yet.</p>
                <p>Proceed directly to the exercise.</p>
              </div>
              <button className="start-exercise-btn" onClick={startExercise}>
                Start Exercise →
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  // Exercise Phase
  return (
    <div className="game-screen">
      <div className="sidebar">
        <div className="level-info">
          <span className="module-badge">{session.level.module}</span>
          <span className="level-badge">Lesson {session.level.number}</span>
          <h2>{session.level.title}</h2>
        </div>

        <div className="instructions">
          {session.level.exercise ? (
            <>
              <p>{session.level.exercise.intro}</p>
              <p className="objective">
                <strong>Objective:</strong> {session.level.exercise.objective}
              </p>
            </>
          ) : (
            <>
              <p>
                Claude Code is an AI coding assistant that lives in your
                terminal.
              </p>
              <p className="action">
                👉 Type <code>claude</code> to start
              </p>
            </>
          )}
          {levelComplete && (
            <div className="completion-message">
              <p>Nice work! You've completed this lesson's objective.</p>
            </div>
          )}
        </div>

        {session.level.video && (
          <button className="rewatch-btn" onClick={() => setPhase("watch")}>
            ↺ Rewatch Video
          </button>
        )}

        <button className="end-session-btn" onClick={endSession}>
          End Session
        </button>

        {levelComplete && (
          <div className="level-complete">
            <p>🎉 Lesson Complete!</p>
            <p className="exit-hint">
              Press <code>Ctrl+C</code> twice to exit Claude
            </p>
            {session.level.number < TOTAL_LESSONS ? (
              <button onClick={nextLevel}>Next Lesson →</button>
            ) : (
              <button onClick={() => setSession(null)}>
                🏆 Course Complete!
              </button>
            )}
          </div>
        )}
      </div>

      <div className="terminal-container">
        <Terminal
          terminalUrl={session.terminal_url}
          onReady={() => console.log("Terminal ready")}
        />
      </div>
    </div>
  );
}

export default App;
```

**Step 3: Commit**

```bash
git add frontend/src/App.tsx frontend/src/config.ts
git commit -m "feat: update App for production API with status polling"
```

---

## Task 8: Create Modal Secrets

**Files:**
- Create: `backend/scripts/setup_modal_secrets.sh`

**Step 1: Create setup script**

```bash
#!/bin/bash
# Setup Modal secrets for Claude Code Game

echo "Setting up Modal secrets..."

# Prompt for values
read -p "Enter demo access code (leave blank to disable): " DEMO_ACCESS_CODE
read -p "Enter allowed origin (e.g., https://your-app.vercel.app): " ALLOWED_ORIGIN

# Create secret
modal secret create claude-game-secrets \
    DEMO_ACCESS_CODE="$DEMO_ACCESS_CODE" \
    ALLOWED_ORIGINS="$ALLOWED_ORIGIN,http://localhost:5173"

echo "Modal secrets created successfully!"
echo ""
echo "To update secrets later, run:"
echo "  modal secret update claude-game-secrets KEY=VALUE"
```

**Step 2: Make executable and commit**

```bash
chmod +x backend/scripts/setup_modal_secrets.sh
git add backend/scripts/setup_modal_secrets.sh
git commit -m "feat: add Modal secrets setup script"
```

---

## Task 9: Create Deployment Scripts

**Files:**
- Create: `backend/scripts/deploy.sh`
- Create: `frontend/vercel.json`

**Step 1: Create backend deploy script**

```bash
#!/bin/bash
# Deploy backend to Modal

set -e

echo "Deploying Claude Code Game backend to Modal..."

cd "$(dirname "$0")/.."

# Deploy
modal deploy modal_app.py

echo ""
echo "Backend deployed successfully!"
echo ""
echo "Your backend URL will be shown above."
echo "Update your frontend VITE_API_URL with this URL."
```

**Step 2: Create Vercel config**

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**Step 3: Commit**

```bash
chmod +x backend/scripts/deploy.sh
git add backend/scripts/deploy.sh frontend/vercel.json
git commit -m "feat: add deployment scripts for Modal and Vercel"
```

---

## Task 10: Update .gitignore and Environment Templates

**Files:**
- Modify: `backend/.gitignore` (create if not exists)
- Create: `backend/.env.example`
- Create: `frontend/.env.example`

**Step 1: Update backend .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/

# Environment
.env

# Test files
test_modal_auth.py

# IDE
.idea/
.vscode/
```

**Step 2: Create backend .env.example**

```bash
# Backend environment variables
DEBUG=false
DEMO_ACCESS_CODE=your-demo-code-here
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

**Step 3: Create frontend .env.example**

```bash
# Frontend environment variables
VITE_API_URL=https://your-modal-app--fastapi-app.modal.run
VITE_ANTHROPIC_API_KEY=  # Optional: pre-fill API key for development
```

**Step 4: Commit**

```bash
git add backend/.gitignore backend/.env.example frontend/.env.example
git commit -m "chore: add gitignore and env templates"
```

---

## Task 11: Test Local Development Flow

**Step 1: Start backend locally for testing**

```bash
cd backend
cp .env.example .env
# Edit .env if needed
uv run uvicorn app.main:app --reload --port 8080
```

**Step 2: Start frontend locally**

```bash
cd frontend
cp .env.example .env
# Edit .env: VITE_API_URL=http://localhost:8080
npm run dev
```

**Step 3: Test the flow**

1. Open http://localhost:5173
2. Enter API key and start a session
3. Verify Modal sandbox is created
4. Verify terminal connects to ttyd
5. Verify status polling works
6. Verify level completion detection works

---

## Task 12: Deploy to Production

**Step 1: Setup Modal secrets**

```bash
cd backend
./scripts/setup_modal_secrets.sh
```

**Step 2: Deploy backend to Modal**

```bash
cd backend
./scripts/deploy.sh
```

**Step 3: Deploy frontend to Vercel**

```bash
cd frontend
# Set environment variable in Vercel dashboard or CLI:
# VITE_API_URL=https://your-modal-app--fastapi-app.modal.run

vercel --prod
```

**Step 4: Test production deployment**

1. Open Vercel URL
2. Enter access code (if configured)
3. Enter API key
4. Verify end-to-end flow works

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Update config | `config.py` |
| 2 | Session manager | `session_manager.py` |
| 3 | Modal sandbox | `sandbox.py` |
| 4 | Session API | `api/sessions.py` |
| 5 | Modal web endpoint | `modal_app.py` |
| 6 | Terminal component | `Terminal.tsx` |
| 7 | Frontend App | `App.tsx`, `config.ts` |
| 8 | Modal secrets | `setup_modal_secrets.sh` |
| 9 | Deploy scripts | `deploy.sh`, `vercel.json` |
| 10 | Env templates | `.gitignore`, `.env.example` |
| 11 | Test locally | Manual testing |
| 12 | Deploy to prod | Manual deployment |

**Security controls implemented:**
- ✅ ttyd basic auth with random password per session
- ✅ Cryptographically secure session IDs
- ✅ Demo access code gate
- ✅ API key format validation
- ✅ CORS locked to frontend domain
- ✅ Activity-based timeout (10 min)
- ✅ Hard timeout cap (60 min)
- ✅ Session cleanup on idle
