# Docker-Only Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove Modal, Fly, and Local PTY code to simplify the codebase to Docker-only sandbox mode.

**Architecture:** The current codebase supports 4 deployment modes (local/docker/modal/fly) with conditional routing. After cleanup, only Docker mode remains with hardcoded paths and simplified components.

**Tech Stack:** FastAPI (backend), React/TypeScript (frontend), Docker (sandbox)

**Reviewed by:** Codex (2026-02-04)

**Dex Epic:** 15s5ko5p

---

## Task 1: Delete Backend Service Files

**Files:**
- Delete: `backend/app/services/local_sandbox.py`
- Delete: `backend/app/services/sandbox.py`
- Delete: `backend/app/services/fly_sandbox.py`
- Delete: `backend/app/services/session_manager.py`
- Delete: `backend/app/services/modal_config.py`
- Delete: `backend/app/services/watcher.py`

**Step 1: Delete the files**

```bash
rm backend/app/services/local_sandbox.py
rm backend/app/services/sandbox.py
rm backend/app/services/fly_sandbox.py
rm backend/app/services/session_manager.py
rm backend/app/services/modal_config.py
rm backend/app/services/watcher.py
```

**Step 2: Verify files are deleted**

```bash
ls backend/app/services/
```

Expected: Only `__init__.py`, `docker_sandbox.py`, `sandbox_manager.py`, `verification.py`, `levels.py` remain.

**Step 3: Commit**

```bash
git add -A backend/app/services/
git commit -m "chore: delete non-Docker sandbox service files"
```

---

## Task 2: Delete Backend API Files

**Files:**
- Delete: `backend/app/api/terminal.py`
- Delete: `backend/app/api/modal_terminal.py`
- Delete: `backend/app/api/fly_terminal.py`
- Delete: `backend/app/api/sessions.py`

**Step 1: Delete the files**

```bash
rm backend/app/api/terminal.py
rm backend/app/api/modal_terminal.py
rm backend/app/api/fly_terminal.py
rm backend/app/api/sessions.py
```

**Step 2: Verify files are deleted**

```bash
ls backend/app/api/
```

Expected: Only `__init__.py`, `docker_terminal.py`, `levels.py` remain.

**Step 3: Commit**

```bash
git add -A backend/app/api/
git commit -m "chore: delete non-Docker API files"
```

---

## Task 3: Delete Backend Test/Script Files

**Files:**
- Delete: `backend/test_modal_auth.py` (if exists)
- Delete: `backend/scripts/deploy.sh`
- Delete: `backend/scripts/test_ws_proxy.py`
- Delete: `backend/scripts/test_exec.py`
- Delete: `backend/scripts/setup_modal_secrets.sh`
- Delete: `backend/modal_app.py`

**Step 1: Delete the files**

```bash
rm -f backend/test_modal_auth.py
rm -f backend/scripts/deploy.sh
rm -f backend/scripts/test_ws_proxy.py
rm -f backend/scripts/test_exec.py
rm -f backend/scripts/setup_modal_secrets.sh
rm -f backend/modal_app.py
rmdir backend/scripts 2>/dev/null || true
```

**Step 2: Verify deletion**

```bash
ls backend/scripts/ 2>/dev/null || echo "scripts directory removed"
ls backend/modal_app.py 2>/dev/null || echo "modal_app.py removed"
```

**Step 3: Commit**

```bash
git add -A backend/
git commit -m "chore: delete Modal/Fly test and script files"
```

---

## Task 4: Delete Spike Directory

**Files:**
- Delete: `spike/` (entire directory)

**Step 1: Delete the directory**

```bash
rm -rf spike/
```

**Step 2: Verify deletion**

```bash
ls spike/ 2>/dev/null || echo "spike directory removed"
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: delete spike directory (Modal experiments)"
```

---

## Task 5: Delete Untracked Cloud Files

**Files:**
- Delete: `fly.toml`
- Delete: `fly-sandbox.toml`
- Delete: `fly-sandbox/` (directory)
- Delete: `fly-test/` (directory)
- Delete: `backend/Untitled`

**Step 1: Delete the files**

```bash
rm -f fly.toml
rm -f fly-sandbox.toml
rm -rf fly-sandbox/
rm -rf fly-test/
rm -f backend/Untitled
```

**Step 2: Verify deletion**

```bash
ls fly*.toml 2>/dev/null || echo "fly toml files removed"
ls -d fly-sandbox fly-test 2>/dev/null || echo "fly directories removed"
```

No commit needed - these were untracked.

---

## Task 6: Delete Planning Docs

**Files:**
- Delete: `docs/plans/2026-01-30-modal-deployment.md`
- Delete: `docs/plans/2026-01-31-modal-websocket-proxy.md`

**Step 1: Delete the files**

```bash
rm -f docs/plans/2026-01-30-modal-deployment.md
rm -f docs/plans/2026-01-31-modal-websocket-proxy.md
```

**Step 2: Commit**

```bash
git add -A docs/plans/
git commit -m "chore: delete Modal/Fly planning docs"
```

---

## Task 7: Fix Backend Services __init__.py

**Files:**
- Modify: `backend/app/services/__init__.py`

**Step 1: Replace the file contents**

Replace entire file with:

```python
"""Game services."""
from app.services.docker_sandbox import DockerSandbox
from app.services.sandbox_manager import SandboxManager, sandbox_manager
from app.services.verification import VerificationEngine
from app.services.levels import list_levels, load_level, load_level_by_number

__all__ = [
    "DockerSandbox",
    "SandboxManager",
    "sandbox_manager",
    "VerificationEngine",
    "list_levels",
    "load_level",
    "load_level_by_number",
]
```

**Step 2: Verify syntax**

```bash
cd backend && python -c "from app.services import *; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/services/__init__.py
git commit -m "fix: update services __init__.py for Docker-only"
```

---

## Task 8: Fix Backend API __init__.py

**Files:**
- Modify: `backend/app/api/__init__.py`

**Step 1: Replace the file contents**

Replace entire file with:

```python
"""API routes."""
from app.api.docker_terminal import router as docker_router

__all__ = ["docker_router"]
```

**Step 2: Verify syntax**

```bash
cd backend && python -c "from app.api import docker_router; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/api/__init__.py
git commit -m "fix: update API __init__.py for Docker-only"
```

---

## Task 9: Simplify Backend config.py

**Files:**
- Modify: `backend/app/config.py`

**Step 1: Replace the file contents**

Replace entire file with:

```python
"""Game configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory (where .env lives)
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
    )

    app_name: str = "Claude Code Game"
    debug: bool = False

    # Sandbox settings
    sandbox_timeout_seconds: int = 3600  # Hard cap: 60 minutes
    sandbox_idle_timeout_seconds: int = 600  # Soft cap: 10 min inactivity
    sandbox_cpu: float = 2.0
    sandbox_memory_mb: int = 4096
    ttyd_port: int = 7681

    # Security
    demo_access_code: str = ""  # Set via DEMO_ACCESS_CODE env var
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "https://claude-code-game.vercel.app",
        "https://*.vercel.app",  # Preview deployments
    ]


settings = Settings()
```

**Step 2: Verify syntax**

```bash
cd backend && python -c "from app.config import settings; print(settings.app_name)"
```

Expected: `Claude Code Game`

**Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "fix: remove sandbox_mode and Fly config from settings"
```

---

## Task 10: Simplify Backend main.py

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Replace the file contents**

Replace entire file with:

```python
"""Claude Code Learning Game - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.levels import list_levels as get_all_levels, load_level_by_number


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup and shutdown lifecycle."""
    from app.services.sandbox_manager import sandbox_manager

    sandbox_manager.start_cleanup_task()
    yield
    await sandbox_manager.shutdown()


app = FastAPI(
    title=settings.app_name,
    description="Interactive terminal-based game for learning Claude Code",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Docker terminal router
from app.api.docker_terminal import router as docker_router

app.include_router(docker_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
    }


@app.get("/api/levels")
async def list_levels():
    """List all available levels."""
    levels = get_all_levels()
    return {"levels": levels, "total": len(levels)}


@app.get("/api/levels/{number}")
async def get_level(number: int):
    """Get a specific level by number."""
    level = load_level_by_number(number)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    return level.model_dump()
```

**Step 2: Verify backend starts**

```bash
cd backend && timeout 5 uvicorn app.main:app --host 0.0.0.0 --port 8000 || true
```

Expected: Server starts without import errors.

**Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "fix: simplify main.py for Docker-only mode"
```

---

## Task 11: Update Backend .gitignore

**Files:**
- Modify: `backend/.gitignore`

**Step 1: Replace the file contents**

Replace entire file with:

```gitignore
# Python
__pycache__/
*.pyc
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/
dist/
build/

# Environment
.env

# IDE
.idea/
.vscode/

# Playwright MCP
.playwright-mcp/
```

**Step 2: Commit**

```bash
git add backend/.gitignore
git commit -m "fix: update .gitignore, add .playwright-mcp/"
```

---

## Task 12: Clean Up Backend Dependencies

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: Replace the file contents**

Replace entire file with:

```toml
[project]
name = "claude-code-game"
version = "0.1.0"
description = "Interactive terminal-based game for learning Claude Code"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "pyyaml>=6.0.1",
    "docker>=7.1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "httpx>=0.26.0",
]
```

**Step 2: Update lock file**

```bash
cd backend && uv lock
```

**Step 3: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "fix: remove modal, websockets, wsproto, httpx from dependencies"
```

---

## Task 13: Update Backend .env.example

**Files:**
- Modify: `backend/.env.example`

**Step 1: Replace the file contents**

Replace entire file with:

```bash
# Backend environment variables
DEBUG=false
DEMO_ACCESS_CODE=your-demo-code-here
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

**Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "fix: simplify .env.example for Docker-only"
```

---

## Task 14: Simplify Frontend config.ts

**Files:**
- Modify: `frontend/src/config.ts`

**Step 1: Replace the file contents**

Replace entire file with:

```typescript
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const config = {
  apiUrl: API_URL,
};
```

**Step 2: Commit**

```bash
git add frontend/src/config.ts
git commit -m "fix: remove terminalMode from frontend config"
```

---

## Task 15: Simplify Frontend App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Replace the file contents**

Replace entire file with:

```tsx
import "./App.css";

import { useCallback, useEffect, useRef, useState } from "react";

import { Terminal } from "./components/Terminal";
import { VideoPlayer } from "./components/VideoPlayer";
import { useProgress } from "./hooks/useProgress";
import {
  useVerificationProgress,
  getVerificationLabel,
} from "./hooks/useVerificationProgress";
import { config } from "./config";

const TOTAL_LESSONS = 11; // Lessons 1-11
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
  level: Level;
  port?: number;
  ttyd_token?: string;
}

type LessonPhase = "watch" | "exercise";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);
  const [phase, setPhase] = useState<LessonPhase>("watch");
  const [selectedLesson, setSelectedLesson] = useState(1);
  const { progress, markComplete } = useProgress();

  // Verification progress for current exercise
  const { progress: verificationProgress } = useVerificationProgress(
    phase === "exercise" ? session?.session_id ?? null : null
  );

  // Status polling
  const pollIntervalRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (sessionId: string, levelNumber: number) => {
      stopPolling();

      const poll = async () => {
        try {
          const statusUrl = `${config.apiUrl}/api/docker/sessions/${sessionId}/status`;

          const response = await fetch(statusUrl);
          if (response.ok) {
            const data = await response.json();
            if (data.completed) {
              setLevelComplete(true);
              markComplete(levelNumber);
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
    },
    [stopPolling, markComplete]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const startGame = async (levelNumber: number = 1) => {
    setLoading(true);
    setError("");
    setLevelComplete(false);
    setPhase("watch");
    stopPolling();

    try {
      const response = await fetch(`${config.apiUrl}/api/docker/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          level_number: levelNumber,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to start Docker session");
      }

      const data = await response.json();
      setSession({
        session_id: data.session_id,
        level: data.level,
        port: data.port,
        ttyd_token: data.ttyd_token,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const startExercise = () => {
    setPhase("exercise");
    if (session) {
      startPolling(session.session_id, session.level.number);
    }
  };

  const nextLevel = async () => {
    if (!session) return;

    const nextLevelNum = session.level.number + 1;
    if (nextLevelNum <= TOTAL_LESSONS) {
      setLoading(true);
      setLevelComplete(false);
      setPhase("watch");
      stopPolling();

      try {
        const response = await fetch(
          `${config.apiUrl}/api/docker/sessions/${session.session_id}/level`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ level_number: nextLevelNum }),
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to update level");
        }

        const data = await response.json();
        setSession({
          ...session,
          level: data.level,
          port: data.port,
          ttyd_token: data.ttyd_token,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    } else {
      setSession(null);
      setLevelComplete(false);
    }
  };

  const endSession = async () => {
    if (session) {
      stopPolling();
      try {
        await fetch(
          `${config.apiUrl}/api/docker/sessions/${session.session_id}`,
          {
            method: "DELETE",
          }
        );
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
                disabled={loading}
              >
                {loading ? "Starting..." : "Start"}
              </button>
            </div>
          </div>

          {error && <p className="error">{error}</p>}

          <p className="hint">
            You'll authenticate via Claude CLI in the terminal.{" "}
            <a
              href="https://console.anthropic.com/settings/keys"
              target="_blank"
              rel="noopener noreferrer"
            >
              Get an API key here
            </a>{" "}
            if you don't have one.
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
          {session.level.intro && (
            <div className="intro" style={{whiteSpace: 'pre-line', marginBottom: '1rem'}}>
              {session.level.intro}
            </div>
          )}
          {session.level.exercise && (
            <p className="objective">
              <strong>Objective:</strong> {session.level.exercise.objective}
            </p>
          )}

          {/* Verification Progress Checklist */}
          {verificationProgress && verificationProgress.rules.length > 0 && (
            <div className="verification-progress">
              <h4>Progress</h4>
              <ul className="verification-checklist">
                {verificationProgress.rules.map((rule, index) => (
                  <li key={index} className={rule.passed ? "passed" : "pending"}>
                    <span className="check-icon">
                      {rule.passed ? "\u2713" : "\u25CB"}
                    </span>
                    <span className="check-label">
                      {getVerificationLabel(rule.type, rule)}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="progress-summary">
                {verificationProgress.passed_count} of {verificationProgress.total_count} complete
              </div>
            </div>
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
          sessionId={session.session_id}
          ttydPort={session.port}
          ttydToken={session.ttyd_token}
          onReady={() => console.log("Terminal ready")}
          onLevelComplete={() => {
            setLevelComplete(true);
            markComplete(session.level.number);
          }}
        />
      </div>
    </div>
  );
}

export default App;
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors (or only unrelated errors).

**Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "fix: simplify App.tsx for Docker-only mode"
```

---

## Task 16: Simplify Frontend Terminal.tsx

**Files:**
- Modify: `frontend/src/components/Terminal.tsx`

**Step 1: Replace the file contents**

Replace entire file with:

```tsx
import { useEffect, useRef } from "react";

interface TerminalProps {
  sessionId: string;
  ttydPort?: number;
  ttydToken?: string;
  onReady?: () => void;
  onLevelComplete?: () => void;
}

export function Terminal({
  ttydPort,
  onReady,
}: TerminalProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Construct URL for Docker ttyd
  const terminalUrl = ttydPort ? `http://localhost:${ttydPort}/` : null;

  useEffect(() => {
    // Notify ready when iframe loads
    const iframe = iframeRef.current;
    if (iframe) {
      iframe.onload = () => {
        onReady?.();
      };
    }
  }, [onReady]);

  if (!terminalUrl) {
    return (
      <div style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#1a1a2e",
        color: "#eee",
      }}>
        <p>Terminal configuration missing</p>
      </div>
    );
  }

  return (
    <iframe
      ref={iframeRef}
      src={terminalUrl}
      title="Terminal"
      style={{
        width: "100%",
        height: "100%",
        border: "none",
        backgroundColor: "#1a1a2e",
      }}
      allow="clipboard-read; clipboard-write"
    />
  );
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add frontend/src/components/Terminal.tsx
git commit -m "fix: simplify Terminal.tsx to iframe-only for Docker"
```

---

## Task 17: Simplify Frontend useVerificationProgress.ts

**Files:**
- Modify: `frontend/src/hooks/useVerificationProgress.ts`

**Step 1: Replace the file contents**

Replace entire file with:

```typescript
import { useState, useEffect, useCallback, useRef } from "react";
import { config } from "../config";

interface VerificationRule {
  type: string;
  passed: boolean;
  path?: string;
  tool_name?: string;
  description?: string;
}

interface VerificationProgress {
  rules: VerificationRule[];
  completed: boolean;
  passed_count: number;
  total_count: number;
}

const POLL_INTERVAL = 3000; // 3 seconds

export function useVerificationProgress(sessionId: string | null) {
  const [progress, setProgress] = useState<VerificationProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  const fetchProgress = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${config.apiUrl}/api/docker/sessions/${sessionId}/progress`
      );
      if (response.ok) {
        const data = await response.json();
        setProgress(data.progress);
        setError(null);
      } else {
        setError("Failed to fetch progress");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      setProgress(null);
      return;
    }

    setLoading(true);
    fetchProgress();

    // Poll for progress updates
    intervalRef.current = window.setInterval(fetchProgress, POLL_INTERVAL);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [sessionId, fetchProgress]);

  return { progress, loading, error, refetch: fetchProgress };
}

// Human-readable labels for verification types
export function getVerificationLabel(type: string, rule: VerificationRule): string {
  // Use custom description if provided
  if (rule.description) return rule.description;

  switch (type) {
    case "file_contains":
      return `Edit ${rule.path || "file"}`;
    case "file_exists":
      return `Create ${rule.path || "file"}`;
    case "min_user_messages":
      return "Send messages to Claude";
    case "tool_called":
      return `Use ${rule.tool_name || "tool"}`;
    case "commit_exists":
      return "Make a git commit";
    case "command_output":
      return "Run command successfully";
    case "file_changed":
      return `Modify ${rule.path || "file"}`;
    case "glob_exists":
      return "Create required files";
    case "home_glob_exists":
      return "Configure Claude settings";
    case "tool_called_with_path":
      return `Use ${rule.tool_name || "tool"} on specific file`;
    default:
      return type.replace(/_/g, " ");
  }
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add frontend/src/hooks/useVerificationProgress.ts
git commit -m "fix: simplify useVerificationProgress for Docker-only"
```

---

## Task 18: Remove xterm Dependencies from Frontend

**Files:**
- Modify: `frontend/package.json`

**Step 1: Remove xterm packages**

```bash
cd frontend && npm uninstall @xterm/addon-fit @xterm/xterm
```

**Step 2: Delete xterm CSS import (already removed in Terminal.tsx)**

Already handled in Task 16.

**Step 3: Verify build**

```bash
cd frontend && npm run build
```

**Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "fix: remove @xterm packages (no longer needed)"
```

---

## Task 19: Update Frontend .env.example

**Files:**
- Modify: `frontend/.env.example`

**Step 1: Replace the file contents**

Replace entire file with:

```bash
# Frontend environment variables
# For production (Vercel):
# VITE_API_URL=https://your-backend-domain.com
# For local development:
VITE_API_URL=http://localhost:8000
```

**Step 2: Commit**

```bash
git add frontend/.env.example
git commit -m "fix: simplify frontend .env.example for Docker-only"
```

---

## Task 20: Test Backend Startup

**Step 1: Start the backend**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

**Step 2: Verify health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"healthy","app":"Claude Code Game"}`

**Step 3: Verify levels endpoint**

```bash
curl http://localhost:8000/api/levels | head -c 200
```

Expected: JSON with levels array.

---

## Task 21: Test Frontend Build

**Step 1: Build frontend**

```bash
cd frontend && npm run build
```

Expected: Build succeeds without errors.

**Step 2: Run frontend dev server**

```bash
cd frontend && npm run dev
```

Expected: Dev server starts on http://localhost:5173.

---

## Task 22: End-to-End Test

**Step 1: Ensure Docker sandbox image exists**

```bash
docker images | grep claude-game-sandbox
```

If not present:

```bash
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .
```

**Step 2: Start backend and frontend**

Terminal 1:
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

Terminal 2:
```bash
cd frontend && npm run dev
```

**Step 3: Test in browser**

1. Open http://localhost:5173
2. Select Lesson 1
3. Click Start
4. Verify Docker container is created
5. Verify iframe terminal loads
6. Verify you can interact with the terminal

---

## Task 23: Final Commit

**Step 1: Check for any uncommitted changes**

```bash
git status
```

**Step 2: Squash or create final summary commit if needed**

If all tasks have been committed individually, create a tag or merge commit:

```bash
git log --oneline -15
```

Verify all cleanup commits are present.

---

## Decision Log

- Keep `docker_` prefix on files for clarity about contents
- Delete planning docs rather than archive
- Hardcode Docker mode rather than keep config switching infrastructure
- Defer API path flattening (`/api/docker/sessions` → `/api/sessions`) to follow-up PR
- Remove unused dependencies to reduce bundle size
- Remove xterm packages since WebSocket terminal is no longer needed
