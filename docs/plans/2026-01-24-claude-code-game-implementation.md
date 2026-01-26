# Claude Code Learning Game - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive terminal-based game that teaches Claude Code through hands-on practice in a sandboxed environment.

**Architecture:** Modal sandbox with ttyd for terminal access, FastAPI backend for game logic, React frontend with xterm.js. Verification via parsing Claude's session logs (messages.jsonl).

**Tech Stack:** Python/FastAPI, Modal, ttyd, React, xterm.js, WebSocket

---

## Phase 0: Spike - Validate Core Assumptions (DO THIS FIRST)

Before building anything substantial, we need to validate three critical assumptions:

1. Can ttyd run inside a Modal sandbox and serve terminal over WebSocket?
2. Can we read Claude's messages.jsonl from the sandbox to verify objectives?
3. Can we proxy WebSocket from browser → server → Modal sandbox?

### Task 0.1: Test ttyd in Modal Sandbox

**Files:**

- Create: `game/spike/test_ttyd_modal.py`

**Step 1: Write Modal sandbox test with ttyd**

```python
"""Spike: Test if ttyd works inside Modal sandbox."""
import modal

app = modal.App("claude-game-spike")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "build-essential", "cmake", "git", "libjson-c-dev", "libwebsockets-dev")
    .run_commands(
        # Install ttyd from source
        "git clone https://github.com/tsl0922/ttyd.git /tmp/ttyd",
        "cd /tmp/ttyd && mkdir build && cd build && cmake .. && make && make install",
        # Verify installation
        "ttyd --version",
    )
)

@app.function(image=image, timeout=300)
def test_ttyd():
    import subprocess
    import time

    # Start ttyd on port 7681
    proc = subprocess.Popen(
        ["ttyd", "-W", "-p", "7681", "bash"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)

    # Check if process is running
    if proc.poll() is None:
        print("SUCCESS: ttyd started and running")
        proc.terminate()
        return True
    else:
        stdout, stderr = proc.communicate()
        print(f"FAILED: ttyd exited with {proc.returncode}")
        print(f"stdout: {stdout.decode()}")
        print(f"stderr: {stderr.decode()}")
        return False

if __name__ == "__main__":
    with app.run():
        result = test_ttyd.remote()
        print(f"Test result: {result}")
```

**Step 2: Run the spike**

```bash
cd game/spike
python test_ttyd_modal.py
```

Expected: "SUCCESS: ttyd started and running"

**Step 3: Document result**

If FAIL: Document error, research alternatives (e.g., gotty, websocketd)
If PASS: Proceed to Task 0.2

---

### Task 0.2: Test Reading messages.jsonl from Sandbox

**Files:**

- Create: `game/spike/test_messages_read.py`

**Step 1: Write test that runs Claude and reads logs**

```python
"""Spike: Test reading Claude's messages.jsonl from sandbox."""
import modal
import json
import os

app = modal.App("claude-game-spike-messages")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("nodejs", "npm", "curl")
    .run_commands(
        "npm install -g @anthropic-ai/claude-code",
        "useradd -m -s /bin/bash claude",
        "mkdir -p /home/claude/.claude/projects",
        "chown -R claude:claude /home/claude",
    )
)

@app.function(image=image, timeout=300, secrets=[modal.Secret.from_name("anthropic-credentials")])
def test_messages_read():
    import subprocess
    import glob
    import os

    # Setup credentials
    creds = {"apiKey": os.environ.get("ANTHROPIC_API_KEY")}
    os.makedirs("/home/claude/.claude", exist_ok=True)
    with open("/home/claude/.claude/.credentials.json", "w") as f:
        json.dump(creds, f)
    os.system("chown -R claude:claude /home/claude/.claude")

    # Run a simple Claude command
    result = subprocess.run(
        ["su", "-", "claude", "-c",
         "cd /home/claude && claude -p --dangerously-skip-permissions 'say hello' </dev/null"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    print(f"Claude output: {result.stdout[:500]}")

    # Find and read messages.jsonl
    pattern = "/home/claude/.claude/projects/**/*.jsonl"
    jsonl_files = glob.glob(pattern, recursive=True)

    print(f"Found {len(jsonl_files)} .jsonl files")

    for f in jsonl_files:
        print(f"File: {f}")
        with open(f, "r") as fp:
            lines = fp.readlines()[:5]  # First 5 lines
            for line in lines:
                data = json.loads(line)
                print(f"  Type: {data.get('type')}")

    return len(jsonl_files) > 0

if __name__ == "__main__":
    with app.run():
        result = test_messages_read.remote()
        print(f"Test result: {result}")
```

**Step 2: Create Modal secret (one-time setup)**

```bash
modal secret create anthropic-credentials ANTHROPIC_API_KEY=sk-ant-xxx
```

**Step 3: Run the spike**

```bash
python test_messages_read.py
```

Expected: "Found N .jsonl files" with Type: assistant, Type: user entries

**Step 4: Document result**

If messages.jsonl not found or unreadable: Research alternative verification
If PASS: Proceed to Task 0.3

---

### Task 0.3: Test WebSocket Proxy to Modal

**Files:**

- Create: `game/spike/test_websocket_proxy.py`
- Create: `game/spike/test_ws_client.html`

**Step 1: Write WebSocket proxy server**

```python
"""Spike: Test WebSocket proxy to Modal sandbox."""
import asyncio
import websockets
import modal

app = modal.App("claude-game-spike-ws")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "build-essential", "cmake", "git", "libjson-c-dev", "libwebsockets-dev")
    .run_commands(
        "git clone https://github.com/tsl0922/ttyd.git /tmp/ttyd",
        "cd /tmp/ttyd && mkdir build && cd build && cmake .. && make && make install",
    )
    .pip_install("websockets")
)

@app.function(image=image, timeout=600)
def run_ttyd_server():
    """Start ttyd and return sandbox info for connection."""
    import subprocess
    import time

    # Start ttyd
    proc = subprocess.Popen(
        ["ttyd", "-W", "-p", "7681", "bash"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)
    print("ttyd started, waiting...")

    # Keep alive for testing
    time.sleep(300)
    proc.terminate()

# Local test server
async def proxy_handler(websocket, path):
    """Proxy WebSocket to Modal (simplified - real impl would connect to Modal)."""
    print(f"Client connected: {path}")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            # Echo back for testing
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    print("Starting WebSocket proxy on ws://localhost:8765")
    async with websockets.serve(proxy_handler, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Write test client**

```html
<!-- test_ws_client.html -->
<!DOCTYPE html>
<html>
  <head>
    <title>WS Test</title>
  </head>
  <body>
    <h1>WebSocket Test</h1>
    <input type="text" id="msg" placeholder="Type message" />
    <button onclick="send()">Send</button>
    <pre id="log"></pre>
    <script>
      const ws = new WebSocket("ws://localhost:8765");
      const log = document.getElementById("log");
      ws.onmessage = (e) => {
        log.textContent += e.data + "\n";
      };
      ws.onopen = () => {
        log.textContent += "Connected!\n";
      };
      ws.onerror = (e) => {
        log.textContent += "Error: " + e + "\n";
      };
      function send() {
        ws.send(document.getElementById("msg").value);
      }
    </script>
  </body>
</html>
```

**Step 3: Run test**

```bash
# Terminal 1
python test_websocket_proxy.py

# Terminal 2
open test_ws_client.html  # or python -m http.server and open in browser
```

Expected: Messages echo back in browser

**Step 4: Document result**

This validates basic WebSocket flow. Real Modal integration is more complex.

---

### Task 0.4: Spike Decision Checkpoint

**After completing Tasks 0.1-0.3:**

Create: `game/spike/SPIKE_RESULTS.md`

```markdown
# Spike Results

## ttyd in Modal

- Result: PASS / FAIL
- Notes: [any issues]
- Alternative if failed: [plan B]

## messages.jsonl Reading

- Result: PASS / FAIL
- Notes: [any issues]
- Alternative if failed: [plan B]

## WebSocket Proxy

- Result: PASS / FAIL
- Notes: [any issues]
- Alternative if failed: [plan B]

## Decision

[ ] All passed - proceed with Phase 1
[ ] Some failed - need to pivot (document new approach)
```

**Commit:**

```bash
git add game/spike/
git commit -m "spike: validate core assumptions for claude code game"
```

---

## Phase 1: Core Infrastructure

**Only proceed if Phase 0 spikes passed.**

### Task 1.1: Create Game Backend Scaffold

**Files:**

- Create: `game/backend/app/__init__.py`
- Create: `game/backend/app/main.py`
- Create: `game/backend/app/config.py`
- Create: `game/backend/requirements.txt`

**Step 1: Create requirements.txt**

```txt
fastapi==0.109.0
uvicorn==0.27.0
websockets==12.0
pydantic==2.5.3
pydantic-settings==2.1.0
modal==0.66.0
pyyaml==6.0.1
```

**Step 2: Create config.py**

```python
"""Game configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Claude Code Game"
    debug: bool = False
    modal_app_name: str = "claude-code-game"

    # Sandbox settings
    sandbox_timeout_seconds: int = 3600  # 1 hour
    sandbox_cpu: float = 2.0
    sandbox_memory_mb: int = 4096

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 3: Create main.py**

```python
"""Claude Code Learning Game - FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Interactive terminal-based game for learning Claude Code",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/api/levels")
async def list_levels():
    """List all available levels."""
    # Placeholder - will be implemented in Phase 4
    return {"levels": [], "total": 0}
```

**Step 4: Create **init**.py**

```python
"""Claude Code Game backend."""
```

**Step 5: Test the scaffold**

```bash
cd game/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# In another terminal:
curl http://localhost:8000/health
```

Expected: `{"status": "healthy", "app": "Claude Code Game"}`

**Step 6: Commit**

```bash
git add game/backend/
git commit -m "feat(game): add backend scaffold with FastAPI"
```

---

### Task 1.2: Copy and Adapt Modal Services from Codient

**Files:**

- Create: `game/backend/app/services/__init__.py`
- Create: `game/backend/app/services/modal_config.py`
- Create: `game/backend/app/services/sandbox.py`

**Step 1: Create modal_config.py (adapted from Codient)**

```python
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
```

**Step 2: Create sandbox.py**

```python
"""Sandbox management service."""
import json
import logging
from typing import Any

import modal

from app.services.modal_config import get_game_image, get_sandbox_config

logger = logging.getLogger(__name__)


class GameSandbox:
    """Manages a game sandbox for a user session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.sandbox: modal.Sandbox | None = None
        self.app = modal.App.lookup("claude-code-game", create_if_missing=True)
        self._image = get_game_image()

    async def create(self) -> str:
        """Create a new sandbox. Returns sandbox ID."""
        logger.info(f"Creating sandbox for session {self.session_id}")

        config = get_sandbox_config(self._image)
        self.sandbox = modal.Sandbox.create(app=self.app, **config)

        logger.info(f"Sandbox created: {self.sandbox.object_id}")
        return self.sandbox.object_id

    async def setup_credentials(self, api_key: str) -> bool:
        """Setup Claude credentials in sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

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

    async def start_ttyd(self, port: int = 7681) -> bool:
        """Start ttyd terminal server in sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Start ttyd in background
        cmd = f"ttyd -W -p {port} su - claude"
        process = self.sandbox.exec("sh", "-c", f"nohup {cmd} &")

        # Give it a moment to start
        import asyncio
        await asyncio.sleep(2)

        return True

    async def read_messages_log(self) -> list[dict[str, Any]]:
        """Read Claude's messages from sandbox."""
        if not self.sandbox:
            raise ValueError("Sandbox not created")

        # Find the latest .jsonl file
        find_cmd = "find /home/claude/.claude/projects -name '*.jsonl' -type f | head -1"
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

    async def terminate(self):
        """Terminate the sandbox."""
        if self.sandbox:
            self.sandbox.terminate()
            logger.info(f"Sandbox terminated for session {self.session_id}")
```

**Step 3: Create services/**init**.py**

```python
"""Game services."""
from app.services.sandbox import GameSandbox

__all__ = ["GameSandbox"]
```

**Step 4: Test sandbox creation (manual)**

```python
# game/backend/test_sandbox.py
import asyncio
from app.services.sandbox import GameSandbox

async def test():
    sandbox = GameSandbox("test-session")
    sandbox_id = await sandbox.create()
    print(f"Created: {sandbox_id}")
    await sandbox.terminate()

asyncio.run(test())
```

```bash
cd game/backend
python test_sandbox.py
```

Expected: Prints sandbox ID, then terminates

**Step 5: Commit**

```bash
git add game/backend/app/services/
git commit -m "feat(game): add Modal sandbox service"
```

---

### Task 1.3: Add WebSocket Terminal Endpoint

**Files:**

- Create: `game/backend/app/api/__init__.py`
- Create: `game/backend/app/api/terminal.py`
- Modify: `game/backend/app/main.py`

**Step 1: Create terminal.py**

```python
"""WebSocket terminal endpoint."""
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.sandbox import GameSandbox

logger = logging.getLogger(__name__)
router = APIRouter()

# Active sessions (in production, use Redis)
active_sessions: dict[str, GameSandbox] = {}


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal access."""
    await websocket.accept()
    logger.info(f"Terminal WebSocket connected: {session_id}")

    sandbox = active_sessions.get(session_id)
    if not sandbox or not sandbox.sandbox:
        await websocket.send_text("Error: No active sandbox for this session")
        await websocket.close()
        return

    try:
        # For now, simple echo - real impl proxies to ttyd
        while True:
            data = await websocket.receive_text()

            # Intercept magic commands
            if data.strip() == "/hint":
                await websocket.send_text("\r\n💡 Hint: Try typing 'claude' to start!\r\n")
                continue
            elif data.strip() == "/skip":
                await websocket.send_text("\r\n⏭️ Skipping level...\r\n")
                continue
            elif data.strip() == "/objective":
                await websocket.send_text("\r\n📋 Current objective: Say hello to Claude\r\n")
                continue

            # Echo back (placeholder)
            await websocket.send_text(f"[sandbox] {data}")

    except WebSocketDisconnect:
        logger.info(f"Terminal WebSocket disconnected: {session_id}")


@router.post("/api/sessions/{session_id}/start")
async def start_session(session_id: str, api_key: str):
    """Start a new game session with sandbox."""
    sandbox = GameSandbox(session_id)
    sandbox_id = await sandbox.create()
    await sandbox.setup_credentials(api_key)
    await sandbox.start_ttyd()

    active_sessions[session_id] = sandbox

    return {"session_id": session_id, "sandbox_id": sandbox_id, "status": "ready"}


@router.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a game session."""
    sandbox = active_sessions.pop(session_id, None)
    if sandbox:
        await sandbox.terminate()
    return {"session_id": session_id, "status": "stopped"}
```

**Step 2: Create api/**init**.py**

```python
"""API routes."""
from app.api.terminal import router as terminal_router

__all__ = ["terminal_router"]
```

**Step 3: Update main.py**

```python
"""Claude Code Learning Game - FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.terminal import router as terminal_router

app = FastAPI(
    title=settings.app_name,
    description="Interactive terminal-based game for learning Claude Code",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(terminal_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}
```

**Step 4: Test WebSocket endpoint**

```bash
# Start server
uvicorn app.main:app --reload --port 8000

# Test with websocat (install: brew install websocat)
websocat ws://localhost:8000/ws/terminal/test-session
```

Expected: Connection opens (will show error about no sandbox, which is expected)

**Step 5: Commit**

```bash
git add game/backend/app/
git commit -m "feat(game): add WebSocket terminal endpoint"
```

---

## Phase 2: Terminal Experience

### Task 2.1: Create Frontend with xterm.js

**Files:**

- Create: `game/frontend/package.json`
- Create: `game/frontend/src/App.tsx`
- Create: `game/frontend/src/components/Terminal.tsx`
- Create: `game/frontend/src/main.tsx`
- Create: `game/frontend/index.html`
- Create: `game/frontend/vite.config.ts`
- Create: `game/frontend/tsconfig.json`

**Step 1: Initialize frontend**

```bash
mkdir -p game/frontend
cd game/frontend
npm create vite@latest . -- --template react-ts
npm install xterm @xterm/addon-fit
```

**Step 2: Create Terminal.tsx**

```tsx
import { useEffect, useRef } from "react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import "xterm/css/xterm.css";

interface TerminalProps {
  sessionId: string;
  onReady?: () => void;
}

export function Terminal({ sessionId, onReady }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Create terminal
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: "#1a1a2e",
        foreground: "#eee",
        cursor: "#f0f0f0",
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;

    // Connect WebSocket
    const ws = new WebSocket(`ws://localhost:8000/ws/terminal/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      term.writeln("Connected to sandbox...");
      term.writeln("");
      onReady?.();
    };

    ws.onmessage = (event) => {
      term.write(event.data);
    };

    ws.onerror = () => {
      term.writeln("\r\n\x1b[31mConnection error\x1b[0m");
    };

    ws.onclose = () => {
      term.writeln("\r\n\x1b[33mDisconnected\x1b[0m");
    };

    // Send input to WebSocket
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    // Handle resize
    const handleResize = () => fitAddon.fit();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      ws.close();
      term.dispose();
    };
  }, [sessionId, onReady]);

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

**Step 3: Update App.tsx**

```tsx
import { useState } from "react";
import { Terminal } from "./components/Terminal";
import "./App.css";

function App() {
  const [sessionId] = useState(() => `session-${Date.now()}`);

  return (
    <div
      style={{ display: "flex", height: "100vh", backgroundColor: "#0f0f1a" }}
    >
      {/* Sidebar - Level info */}
      <div
        style={{
          width: "300px",
          padding: "20px",
          color: "#fff",
          borderRight: "1px solid #333",
        }}
      >
        <h2>Level 1</h2>
        <h3>Your First Prompt</h3>
        <p style={{ color: "#aaa", marginTop: "10px" }}>
          Claude Code is an AI coding assistant that lives in your terminal.
        </p>
        <p style={{ marginTop: "20px" }}>
          👉 Type{" "}
          <code style={{ background: "#333", padding: "2px 6px" }}>claude</code>{" "}
          to start
        </p>
      </div>

      {/* Terminal */}
      <div style={{ flex: 1 }}>
        <Terminal sessionId={sessionId} />
      </div>
    </div>
  );
}

export default App;
```

**Step 4: Test frontend**

```bash
cd game/frontend
npm run dev
```

Open http://localhost:5173 - should see terminal (will show connection error until backend is running with real sandbox)

**Step 5: Commit**

```bash
git add game/frontend/
git commit -m "feat(game): add React frontend with xterm.js"
```

---

### Task 2.2: Implement Real ttyd Proxy

**Files:**

- Modify: `game/backend/app/api/terminal.py`
- Create: `game/backend/app/services/ttyd_proxy.py`

**Step 1: Create ttyd_proxy.py**

```python
"""Proxy WebSocket connections to ttyd in sandbox."""
import asyncio
import logging
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class TtydProxy:
    """Proxies WebSocket between client and ttyd in sandbox."""

    def __init__(self, sandbox_host: str, sandbox_port: int = 7681):
        self.sandbox_url = f"ws://{sandbox_host}:{sandbox_port}/ws"
        self.client_ws = None
        self.sandbox_ws = None

    async def connect_to_sandbox(self) -> bool:
        """Connect to ttyd WebSocket in sandbox."""
        try:
            self.sandbox_ws = await websockets.connect(self.sandbox_url)
            logger.info(f"Connected to sandbox ttyd at {self.sandbox_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to sandbox: {e}")
            return False

    async def proxy(self, client_ws):
        """Start bidirectional proxy."""
        self.client_ws = client_ws

        async def client_to_sandbox():
            try:
                async for message in self.client_ws:
                    if self.sandbox_ws:
                        await self.sandbox_ws.send(message)
            except ConnectionClosed:
                pass

        async def sandbox_to_client():
            try:
                async for message in self.sandbox_ws:
                    await self.client_ws.send(message)
            except ConnectionClosed:
                pass

        await asyncio.gather(
            client_to_sandbox(),
            sandbox_to_client(),
            return_exceptions=True,
        )

    async def close(self):
        """Close connections."""
        if self.sandbox_ws:
            await self.sandbox_ws.close()
```

**Note:** This requires Modal sandbox to expose a network port, which may need additional Modal configuration. If Modal doesn't support direct WebSocket to sandbox, we'll need to use Modal's exec streaming API instead.

**Step 2: Update terminal.py to use proxy (or exec-based approach)**

```python
"""WebSocket terminal endpoint - exec-based approach."""
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.sandbox import GameSandbox

logger = logging.getLogger(__name__)
router = APIRouter()

active_sessions: dict[str, GameSandbox] = {}


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal access using Modal exec."""
    await websocket.accept()
    logger.info(f"Terminal WebSocket connected: {session_id}")

    sandbox = active_sessions.get(session_id)
    if not sandbox or not sandbox.sandbox:
        await websocket.send_text("Error: No active sandbox for this session\r\n")
        await websocket.close()
        return

    # Start an interactive bash process
    process = sandbox.sandbox.exec(
        "su", "-", "claude", "-c", "cd /workspace && bash",
        pty=True,  # Request PTY if supported
    )

    async def read_from_sandbox():
        """Read stdout from sandbox and send to client."""
        try:
            for chunk in process.stdout:
                await websocket.send_text(chunk)
        except Exception as e:
            logger.error(f"Error reading from sandbox: {e}")

    async def write_to_sandbox():
        """Read from client and write to sandbox stdin."""
        try:
            while True:
                data = await websocket.receive_text()

                # Intercept magic commands
                if data.strip() in ["/hint", "/skip", "/objective"]:
                    await handle_magic_command(websocket, data.strip())
                    continue

                process.stdin.write(data)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"Error writing to sandbox: {e}")

    try:
        await asyncio.gather(
            read_from_sandbox(),
            write_to_sandbox(),
        )
    finally:
        process.terminate()


async def handle_magic_command(websocket: WebSocket, cmd: str):
    """Handle game magic commands."""
    if cmd == "/hint":
        await websocket.send_text("\r\n💡 Hint: Try typing 'claude' to start!\r\n$ ")
    elif cmd == "/skip":
        await websocket.send_text("\r\n⏭️ Skipping level...\r\n")
    elif cmd == "/objective":
        await websocket.send_text("\r\n📋 Objective: Chat with Claude about the app\r\n$ ")
```

**Step 3: Test end-to-end**

This requires a running Modal sandbox. Manual test:

1. Start backend: `uvicorn app.main:app --reload --port 8000`
2. Create session via API: `curl -X POST http://localhost:8000/api/sessions/test/start?api_key=sk-...`
3. Start frontend: `npm run dev`
4. Open browser, should connect to sandbox terminal

**Step 4: Commit**

```bash
git add game/backend/
git commit -m "feat(game): add terminal WebSocket with Modal exec"
```

---

## Phase 3: Verification System

### Task 3.1: Create Verification Engine

**Files:**

- Create: `game/backend/app/services/verification.py`
- Create: `game/backend/app/models/level.py`

**Step 1: Create level.py (Pydantic models)**

```python
"""Level definition models."""
from enum import Enum
from typing import Any
from pydantic import BaseModel


class VerificationType(str, Enum):
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


class Level(BaseModel):
    """A game level definition."""
    id: str
    number: int
    title: str
    module: str
    intro: str
    verification: list[VerificationRule]
    hints: list[Hint] = []
    success: str
    limits: LevelLimits = LevelLimits()
```

**Step 2: Create verification.py**

```python
"""Level verification engine."""
import json
import logging
import re
from typing import Any

from app.models.level import Level, VerificationRule, VerificationType
from app.services.sandbox import GameSandbox

logger = logging.getLogger(__name__)


class VerificationEngine:
    """Verifies level completion by checking sandbox state."""

    def __init__(self, sandbox: GameSandbox):
        self.sandbox = sandbox

    async def check_level_complete(self, level: Level) -> bool:
        """Check if all verification rules pass."""
        for rule in level.verification:
            if not await self._check_rule(rule):
                return False
        return True

    async def _check_rule(self, rule: VerificationRule) -> bool:
        """Check a single verification rule."""
        if rule.type == VerificationType.MESSAGE_EXISTS:
            return await self._check_message_exists()
        elif rule.type == VerificationType.TOOL_CALLED:
            return await self._check_tool_called(rule.tool_name)
        elif rule.type == VerificationType.FILE_EXISTS:
            return await self._check_file_exists(rule.path)
        elif rule.type == VerificationType.FILE_CONTAINS:
            return await self._check_file_contains(rule.path, rule.pattern)
        elif rule.type == VerificationType.FILE_CHANGED:
            return await self._check_file_changed(rule.path)
        return False

    async def _check_message_exists(self) -> bool:
        """Check if any assistant message exists."""
        messages = await self.sandbox.read_messages_log()
        return any(m.get("type") == "assistant" for m in messages)

    async def _check_tool_called(self, tool_name: str) -> bool:
        """Check if Claude called a specific tool."""
        messages = await self.sandbox.read_messages_log()

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            content = msg.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == tool_name:
                    return True

        return False

    async def _check_file_exists(self, path: str) -> bool:
        """Check if a file exists in sandbox."""
        if not self.sandbox.sandbox:
            return False

        # Resolve path relative to /workspace
        full_path = f"/workspace/{path}" if not path.startswith("/") else path

        process = self.sandbox.sandbox.exec("test", "-f", full_path)
        process.wait()

        return process.returncode == 0

    async def _check_file_contains(self, path: str, pattern: str) -> bool:
        """Check if file contains pattern."""
        if not self.sandbox.sandbox:
            return False

        full_path = f"/workspace/{path}" if not path.startswith("/") else path

        process = self.sandbox.sandbox.exec("cat", full_path)
        content = process.stdout.read()
        process.wait()

        if process.returncode != 0:
            return False

        return bool(re.search(pattern, content))

    async def _check_file_changed(self, path: str) -> bool:
        """Check if file was modified (via Edit tool in messages)."""
        messages = await self.sandbox.read_messages_log()

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            content = msg.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == "Edit":
                    tool_input = block.get("input", {})
                    if path in tool_input.get("file_path", ""):
                        return True

        return False
```

**Step 3: Commit**

```bash
git add game/backend/app/models/ game/backend/app/services/verification.py
git commit -m "feat(game): add verification engine for level completion"
```

---

### Task 3.2: Create Game Watcher Service

**Files:**

- Create: `game/backend/app/services/watcher.py`

**Step 1: Create watcher.py**

```python
"""Game watcher - polls for level completion and stuck detection."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable

from app.models.level import Level
from app.services.sandbox import GameSandbox
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)


class GameWatcher:
    """Watches a game session for completion and provides hints."""

    def __init__(
        self,
        sandbox: GameSandbox,
        level: Level,
        on_complete: Callable[[], None],
        on_hint: Callable[[str], None],
    ):
        self.sandbox = sandbox
        self.level = level
        self.on_complete = on_complete
        self.on_hint = on_hint
        self.verification = VerificationEngine(sandbox)

        self.started_at = datetime.utcnow()
        self.hints_shown: set[int] = set()
        self._running = False

    async def start(self):
        """Start watching."""
        self._running = True
        logger.info(f"Watcher started for level {self.level.id}")

        while self._running:
            # Check completion
            if await self.verification.check_level_complete(self.level):
                logger.info(f"Level {self.level.id} completed!")
                self.on_complete()
                self._running = False
                break

            # Check hints
            elapsed = datetime.utcnow() - self.started_at
            for hint in self.level.hints:
                if hint.after_minutes not in self.hints_shown:
                    if elapsed > timedelta(minutes=hint.after_minutes):
                        self.hints_shown.add(hint.after_minutes)
                        self.on_hint(hint.text)

            # Poll interval
            await asyncio.sleep(3)

    def stop(self):
        """Stop watching."""
        self._running = False
```

**Step 2: Commit**

```bash
git add game/backend/app/services/watcher.py
git commit -m "feat(game): add game watcher for completion detection"
```

---

## Phase 4: Level Content

### Task 4.1: Create Starter Todo App

**Files:**

- Create: `game/levels/starter-app/todo.py`
- Create: `game/levels/starter-app/test_todo.py`
- Create: `game/levels/starter-app/README.md`

**Step 1: Create todo.py (with intentional bug)**

```python
#!/usr/bin/env python3
"""Simple TODO CLI app - starter project for Claude Code Game."""
import json
import os
from datetime import datetime

TODO_FILE = os.path.expanduser("~/.todos.json")


def load_todos() -> list[dict]:
    """Load todos from file."""
    if not os.path.exists(TODO_FILE):
        return []
    with open(TODO_FILE, "r") as f:
        return json.load(f)


def save_todos(todos: list[dict]):
    """Save todos to file."""
    with open(TODO_FILE, "w") as f:
        json.dump(todos, f, indent=2)


def add_todo(text: str):
    """Add a new todo."""
    todos = load_todos()
    todo = {
        "id": len(todos) + 1,
        "text": text,
        "done": False,
        "created": datetime.now().isoformat(),
    }
    todos.append(todo)
    save_todos(todos)
    print(f"Added: {text}")


def list_todos():
    """List all todos."""
    todos = load_todos()
    if not todos:
        print("No todos yet!")
        return

    for todo in todos:
        status = "✓" if todo["done"] else " "
        # BUG: Should be todo["text"], not todo["title"]
        print(f"[{status}] {todo['id']}: {todo['title']}")


def complete_todo(todo_id: int):
    """Mark a todo as complete."""
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = True
            save_todos(todos)
            print(f"Completed: {todo['text']}")
            return
    print(f"Todo {todo_id} not found")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: todo.py <command> [args]")
        print("Commands: add, list, done")
        return

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: todo.py add <text>")
            return
        add_todo(" ".join(sys.argv[2:]))
    elif cmd == "list":
        list_todos()
    elif cmd == "done":
        if len(sys.argv) < 3:
            print("Usage: todo.py done <id>")
            return
        complete_todo(int(sys.argv[2]))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
```

**Step 2: Create test_todo.py**

```python
"""Tests for todo app."""
import json
import os
import tempfile
import pytest

# Set test file location before importing
TEST_FILE = tempfile.mktemp(suffix=".json")
os.environ["TODO_FILE"] = TEST_FILE

import todo


@pytest.fixture(autouse=True)
def clean_todos():
    """Clean up todos before and after each test."""
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
    yield
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


def test_add_todo():
    """Test adding a todo."""
    todo.TODO_FILE = TEST_FILE
    todo.add_todo("Test task")

    todos = todo.load_todos()
    assert len(todos) == 1
    assert todos[0]["text"] == "Test task"
    assert todos[0]["done"] is False


def test_list_todos_empty(capsys):
    """Test listing when no todos."""
    todo.TODO_FILE = TEST_FILE
    todo.list_todos()

    captured = capsys.readouterr()
    assert "No todos" in captured.out


def test_list_todos(capsys):
    """Test listing todos."""
    todo.TODO_FILE = TEST_FILE
    todo.add_todo("Task 1")
    todo.add_todo("Task 2")

    todo.list_todos()

    captured = capsys.readouterr()
    # This test will fail due to the bug!
    assert "Task 1" in captured.out


def test_complete_todo():
    """Test completing a todo."""
    todo.TODO_FILE = TEST_FILE
    todo.add_todo("Test task")
    todo.complete_todo(1)

    todos = todo.load_todos()
    assert todos[0]["done"] is True
```

**Step 3: Create README.md**

````markdown
# Todo CLI

A simple command-line todo list app.

## Usage

```bash
# Add a todo
python todo.py add "Buy groceries"

# List todos
python todo.py list

# Mark as done
python todo.py done 1
```
````

## Running Tests

```bash
pytest test_todo.py -v
```

````

**Step 4: Commit**

```bash
git add game/levels/
git commit -m "feat(game): add starter todo app with intentional bug"
````

---

### Task 4.2: Create Level Definition Files

**Files:**

- Create: `game/levels/definitions/01-first-conversation.yaml`
- Create: `game/levels/definitions/02-reading-code.yaml`
- Create: `game/levels/definitions/03-fix-bug.yaml`
- Create: `game/levels/definitions/04-run-tests.yaml`

**Step 1: Create level 1**

```yaml
# 01-first-conversation.yaml
id: "first-conversation"
number: 1
title: "Your First Conversation"
module: "Meet Claude"

intro: |
  ╔══════════════════════════════════════════════════════════════╗
  ║  LEVEL 1: Your First Conversation                            ║
  ╚══════════════════════════════════════════════════════════════╝

  Welcome! You're about to meet Claude Code, an AI coding assistant
  that lives in your terminal.

  In front of you is a simple todo app. It has a bug somewhere.
  Let's have Claude help us understand the code.

  👉 Type: claude

  Then ask Claude to explain what this app does.

  ─────────────────────────────────────────────────────────────────

verification:
  - type: message_exists

hints:
  - after_minutes: 1
    text: "💡 Hint: Just type 'claude' and press Enter to start!"
  - after_minutes: 3
    text: "💡 Hint: Try asking Claude 'what does this todo app do?'"

success: |
  ✅ Great! You just had your first conversation with Claude Code.

  Claude can explain code, answer questions, and help you understand
  any codebase - even ones you've never seen before.

  Press ENTER for Level 2...

limits:
  max_duration_minutes: 10
  max_claude_messages: 10
```

**Step 2: Create level 2**

```yaml
# 02-reading-code.yaml
id: "reading-code"
number: 2
title: "Reading Code"
module: "Meet Claude"

intro: |
  ╔══════════════════════════════════════════════════════════════╗
  ║  LEVEL 2: Reading Code                                       ║
  ╚══════════════════════════════════════════════════════════════╝

  Claude can read any file in your project. Let's explore the code.

  👉 Ask Claude to read and explain the list_todos function

  You can say something like:
  "Read the list_todos function in todo.py and explain what it does"

  ─────────────────────────────────────────────────────────────────

verification:
  - type: tool_called
    tool_name: "Read"

hints:
  - after_minutes: 2
    text: "💡 Hint: Ask Claude to 'read todo.py' or 'explain the list_todos function'"
  - after_minutes: 4
    text: "💡 Hint: You can be specific: 'read the list_todos function in todo.py'"

success: |
  ✅ Nice! You just learned how Claude gathers context.

  When you ask about code, Claude uses the Read tool to look at files.
  It can read any file in your project - code, configs, docs, anything.

  Did you notice anything suspicious in list_todos? 🤔

  Press ENTER for Level 3...

limits:
  max_duration_minutes: 10
  max_claude_messages: 15
```

**Step 3: Create level 3**

```yaml
# 03-fix-bug.yaml
id: "fix-bug"
number: 3
title: "Fix a Bug"
module: "Meet Claude"

intro: |
  ╔══════════════════════════════════════════════════════════════╗
  ║  LEVEL 3: Fix a Bug                                          ║
  ╚══════════════════════════════════════════════════════════════╝

  There's a bug in the list_todos function. It's trying to access
  todo['title'] but the field is actually called 'text'.

  👉 Ask Claude to fix the bug

  You could say:
  "Fix the bug in list_todos - it should use 'text' not 'title'"

  ─────────────────────────────────────────────────────────────────

verification:
  - type: tool_called
    tool_name: "Edit"
  - type: file_contains
    path: "todo.py"
    pattern: 'todo\["text"\]'

hints:
  - after_minutes: 2
    text: "💡 Hint: Ask Claude to 'fix the bug in list_todos'"
  - after_minutes: 4
    text: "💡 Hint: The bug is on line 47 - 'title' should be 'text'"

success: |
  ✅ You fixed your first bug with Claude!

  Claude used the Edit tool to modify the file. It's careful to make
  minimal, focused changes.

  But did it actually work? Let's verify...

  Press ENTER for Level 4...

limits:
  max_duration_minutes: 10
  max_claude_messages: 15
```

**Step 4: Create level 4**

```yaml
# 04-run-tests.yaml
id: "run-tests"
number: 4
title: "Run Tests"
module: "Meet Claude"

intro: |
  ╔══════════════════════════════════════════════════════════════╗
  ║  LEVEL 4: Run Tests                                          ║
  ╚══════════════════════════════════════════════════════════════╝

  Good developers verify their changes. Let's run the tests.

  👉 Ask Claude to run the tests

  Try: "run the tests to make sure the bug is fixed"

  ─────────────────────────────────────────────────────────────────

verification:
  - type: tool_called
    tool_name: "Bash"

hints:
  - after_minutes: 2
    text: "💡 Hint: Ask Claude to 'run pytest' or 'run the tests'"
  - after_minutes: 4
    text: "💡 Hint: Claude uses the Bash tool to run commands"

success: |
  ✅ Tests passed! You've completed Module 1.

  You now know the fundamentals:
  • Chat with Claude about code
  • Read files to gather context
  • Edit files to make changes
  • Run commands to verify

  Ready to level up? Let's learn about project setup...

  Press ENTER for Module 2...

limits:
  max_duration_minutes: 10
  max_claude_messages: 15
```

**Step 5: Commit**

```bash
git add game/levels/definitions/
git commit -m "feat(game): add level definitions for Module 1"
```

---

### Task 4.3: Create Level Loader Service

**Files:**

- Create: `game/backend/app/services/levels.py`

**Step 1: Create levels.py**

```python
"""Level loading and management service."""
import os
from pathlib import Path

import yaml

from app.models.level import Level, VerificationRule, Hint, LevelLimits, VerificationType


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
```

**Step 2: Update main.py to use level loader**

```python
# Add to main.py
from app.services.levels import list_levels, load_level_by_number

@app.get("/api/levels")
async def get_levels():
    """List all available levels."""
    levels = list_levels()
    return {"levels": levels, "total": len(levels)}

@app.get("/api/levels/{number}")
async def get_level(number: int):
    """Get a specific level."""
    level = load_level_by_number(number)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    return level.model_dump()
```

**Step 3: Commit**

```bash
git add game/backend/app/services/levels.py game/backend/app/main.py
git commit -m "feat(game): add level loader service"
```

---

## Phase 5: Integration and Polish

### Task 5.1: Wire Everything Together

**Files:**

- Modify: `game/backend/app/api/terminal.py`
- Modify: `game/frontend/src/App.tsx`

This task involves connecting:

1. Level loading → Frontend display
2. Sandbox creation → Terminal connection
3. Watcher → Completion detection → Level advancement

**Step 1: Update terminal.py with full game flow**

```python
"""Complete terminal endpoint with game flow."""
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.services.sandbox import GameSandbox
from app.services.levels import load_level_by_number
from app.services.watcher import GameWatcher
from app.services.verification import VerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# Session state
sessions: dict[str, dict] = {}


class StartSessionRequest(BaseModel):
    api_key: str
    level_number: int = 1


@router.post("/api/sessions")
async def create_session(request: StartSessionRequest):
    """Create a new game session."""
    import uuid
    session_id = str(uuid.uuid4())[:8]

    level = load_level_by_number(request.level_number)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    # Create sandbox
    sandbox = GameSandbox(session_id)
    await sandbox.create()
    await sandbox.setup_credentials(request.api_key)

    # Store session
    sessions[session_id] = {
        "sandbox": sandbox,
        "level": level,
        "completed": False,
    }

    return {
        "session_id": session_id,
        "level": {
            "number": level.number,
            "title": level.title,
            "intro": level.intro,
        },
    }


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket terminal with game integration."""
    await websocket.accept()

    session = sessions.get(session_id)
    if not session:
        await websocket.send_text("Error: Session not found\r\n")
        await websocket.close()
        return

    sandbox = session["sandbox"]
    level = session["level"]

    # Print level intro
    await websocket.send_text(level.intro)
    await websocket.send_text("\r\n$ ")

    # Start watcher
    async def on_complete():
        session["completed"] = True
        await websocket.send_text(f"\r\n\r\n{level.success}")

    async def on_hint(text: str):
        await websocket.send_text(f"\r\n\r\n{text}\r\n\r\n$ ")

    watcher = GameWatcher(sandbox, level, on_complete, on_hint)
    watcher_task = asyncio.create_task(watcher.start())

    try:
        # Main terminal loop (simplified)
        while not session["completed"]:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0,
                )

                # Handle magic commands
                if data.strip().startswith("/"):
                    await handle_magic_command(websocket, data.strip(), level)
                else:
                    # Echo for now (real impl: send to sandbox)
                    await websocket.send_text(data)

            except asyncio.TimeoutError:
                continue

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    finally:
        watcher.stop()
        watcher_task.cancel()


async def handle_magic_command(websocket: WebSocket, cmd: str, level):
    """Handle magic commands."""
    if cmd == "/hint":
        hints = level.hints
        if hints:
            await websocket.send_text(f"\r\n{hints[0].text}\r\n$ ")
    elif cmd == "/objective":
        await websocket.send_text(f"\r\n📋 {level.title}\r\n$ ")
    elif cmd == "/skip":
        await websocket.send_text("\r\n⏭️ Skipping...\r\n")
```

**Step 2: Update frontend App.tsx**

```tsx
import { useState, useEffect } from "react";
import { Terminal } from "./components/Terminal";
import "./App.css";

interface Level {
  number: number;
  title: string;
  intro: string;
}

interface Session {
  session_id: string;
  level: Level;
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const startGame = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, level_number: 1 }),
      });

      if (!response.ok) throw new Error("Failed to start session");

      const data = await response.json();
      setSession(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  if (!session) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          backgroundColor: "#0f0f1a",
          color: "#fff",
        }}
      >
        <h1>Claude Code Game</h1>
        <p style={{ color: "#aaa", marginBottom: "20px" }}>
          Learn Claude Code through interactive challenges
        </p>

        <input
          type="password"
          placeholder="Enter your Anthropic API key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          style={{
            padding: "10px 15px",
            width: "300px",
            marginBottom: "10px",
            borderRadius: "5px",
            border: "1px solid #333",
            backgroundColor: "#1a1a2e",
            color: "#fff",
          }}
        />

        <button
          onClick={startGame}
          disabled={loading || !apiKey}
          style={{
            padding: "10px 30px",
            borderRadius: "5px",
            border: "none",
            backgroundColor: "#6366f1",
            color: "#fff",
            cursor: loading || !apiKey ? "not-allowed" : "pointer",
            opacity: loading || !apiKey ? 0.5 : 1,
          }}
        >
          {loading ? "Starting..." : "Start Game"}
        </button>

        {error && (
          <p style={{ color: "#f87171", marginTop: "10px" }}>{error}</p>
        )}
      </div>
    );
  }

  return (
    <div
      style={{ display: "flex", height: "100vh", backgroundColor: "#0f0f1a" }}
    >
      <div
        style={{
          width: "300px",
          padding: "20px",
          color: "#fff",
          borderRight: "1px solid #333",
        }}
      >
        <h2>Level {session.level.number}</h2>
        <h3>{session.level.title}</h3>
        <p style={{ color: "#666", fontSize: "12px", marginTop: "20px" }}>
          Type /hint for help • /skip to skip
        </p>
      </div>

      <div style={{ flex: 1 }}>
        <Terminal sessionId={session.session_id} />
      </div>
    </div>
  );
}

export default App;
```

**Step 3: Commit**

```bash
git add game/
git commit -m "feat(game): wire together full game flow"
```

---

### Task 5.2: End-to-End Test

**Manual testing checklist:**

1. Start backend: `cd game/backend && uvicorn app.main:app --reload`
2. Start frontend: `cd game/frontend && npm run dev`
3. Open http://localhost:5173
4. Enter API key, click Start
5. Verify terminal loads with Level 1 intro
6. Type `claude` and have a conversation
7. Verify level completes when assistant message detected
8. Verify hints appear after timeout

**Commit:**

```bash
git add .
git commit -m "chore(game): complete MVP integration"
```

---

## Summary: Phase Checklist

| Phase | Description    | Validates                                                   |
| ----- | -------------- | ----------------------------------------------------------- |
| 0     | Spike          | ttyd in Modal, messages.jsonl reading, WebSocket proxy      |
| 1     | Infrastructure | Backend scaffold, Modal sandbox service, WebSocket endpoint |
| 2     | Terminal       | xterm.js frontend, PTY passthrough                          |
| 3     | Verification   | Verification engine, game watcher                           |
| 4     | Content        | Starter app, level definitions, level loader                |
| 5     | Integration    | Full game flow, end-to-end test                             |

**Total tasks:** 15 tasks across 5 phases

**Key decision points:**

- After Phase 0: Go/no-go based on spike results
- After Phase 2: Verify terminal experience works before building game logic
- After Phase 4: Verify levels load correctly before integration

---

_Plan created 2026-01-24_
