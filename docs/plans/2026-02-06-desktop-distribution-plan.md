# Desktop Distribution Rewrite — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite claude-code-game as a single Node.js CLI package (`npx claude-code-game`) that runs locally with no Python, no Docker, no server infrastructure.

**Architecture:** Express server serves pre-built React frontend + API routes. Terminal uses `node-pty` for local PTY. Verification engine ports from Python to TypeScript. Cloudflare Worker handles auth (email verification) and progress tracking (D1 + KV). Asymmetric JWT for secure local token verification.

**Tech Stack:** TypeScript, Express, node-pty, ws, React (existing frontend simplified), Cloudflare Workers + D1 + KV, Resend (email)

**Design Doc:** `docs/plans/2026-02-06-desktop-distribution-design.md`

---

## Review Findings (Codex Review, 2026-02-06)

The following issues were identified during technical review and are addressed inline in the tasks below. Items marked with **[REMEDIATION]** indicate where the original plan was updated.

### Critical

1. **`execSync` in verification is an RCE vector** — `command_output` rules execute shell commands. If level YAML is tampered with, arbitrary commands run on the user's machine. **[REMEDIATION: Task 3 — allowlist commands, use `execFile` with argv, no shell expansion]**

2. **Path traversal in level handling** — Copying exercise files without validation could escape the levels directory via `..` or symlinks. **[REMEDIATION: Task 2 — validate resolved paths stay within levels root, reject symlinks]**

3. **Origin-only WebSocket guard is insufficient** — Origin headers are spoofable by non-browser clients. **[REMEDIATION: Task 2 — add per-session nonce token required in WS URL, bind to 127.0.0.1 only]**

4. **JWT verification needs audience/issuer/expiration checks** — Without these, tokens can be replayed across environments. **[REMEDIATION: Task 7/8 — enforce `aud`, `iss`, `exp`, `nbf` claims]**

5. **JSONL log path encoding is ambiguous** — Replacing `/` with `-` can collide for different paths. **[REMEDIATION: Task 3 — use sha256 hash of absolute workspace path as stable lookup key]**

### Important

6. **Two `ws.on("message")` handlers is a bug** — Both fire on every message. **[REMEDIATION: Task 2 — single handler, route by message shape]**

7. **`execSync` blocks the event loop** — Freezes server during slow verification commands. **[REMEDIATION: Task 3 — use async `execFile` with timeouts]**

8. **Port probing race condition** — Multiple instances can pick the same port. **[REMEDIATION: Task 4 — use port 0 and read assigned port from server]**

9. **Auth token file needs strict permissions** — `~/.claude-code-game/auth.json` should be 0600. **[REMEDIATION: Task 8 — set file permissions on write]**

10. **`open` package fails in WSL/headless** — **[REMEDIATION: Task 4 — detect WSL, print URL instead of auto-opening]**

### Nice-to-Have

11. **Express 5.1 ecosystem maturity** — Monitor for middleware compatibility issues.
12. **Consider `jose` over `jsonwebtoken`** — Better defaults for modern JWK handling.
13. **YAML safe schema** — Ensure `yaml.parse` uses safe schema to prevent unexpected types.

### Missing Tasks Identified

14. **Session cleanup strategy** — TTL for workspace directories and orphaned PTY processes. **[REMEDIATION: Added to Task 2]**
15. **Rate limiting on auth endpoints** — Prevent brute-force code guessing. **[REMEDIATION: Added to Task 7]**
16. **Offline mode** — Define behavior when Worker is unreachable. **[REMEDIATION: Added to Task 8 — show error, block progression, require retry]**
17. **Key rotation strategy** — Mechanism to roll JWT keys without breaking old clients. **[REMEDIATION: Added to Task 7]**
18. **Cross-platform testing should start earlier** — node-pty and path handling are high-risk. **[REMEDIATION: Task ordering note added]**

---

## Phase 1: Core Local Experience

### Task 1: Initialize Node.js Server Package

**Files:**
- Create: `server/package.json`
- Create: `server/tsconfig.json`
- Create: `server/src/server.ts`
- Create: `server/src/routes/levels.ts`

**Step 1: Create package.json**

```json
{
  "name": "claude-code-game",
  "version": "0.1.0",
  "type": "module",
  "bin": {
    "claude-code-game": "./dist/cli.js"
  },
  "engines": {
    "node": ">=20.0.0"
  },
  "scripts": {
    "build": "tsc",
    "dev": "tsx watch src/server.ts",
    "start": "node dist/server.js",
    "test": "vitest run"
  },
  "dependencies": {
    "express": "^5.1.0",
    "ws": "^8.18.0",
    "node-pty-prebuilt-multiarch": "^0.11.0",
    "yaml": "^2.7.0",
    "open": "^10.1.0",
    "jsonwebtoken": "^9.0.0",
    "uuid": "^11.1.0"
  },
  "devDependencies": {
    "@types/express": "^5.0.0",
    "@types/ws": "^8.5.0",
    "@types/jsonwebtoken": "^9.0.0",
    "@types/uuid": "^10.0.0",
    "tsx": "^4.19.0",
    "typescript": "^5.9.0",
    "vitest": "^3.1.0"
  }
}
```

> **[REMEDIATION #18]** Pin `engines.node >= 20` — node-pty is sensitive to Node ABI changes. CI should test Node 20 + 22 on macOS/Linux/Windows.

**Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

**Step 3: Create minimal Express server**

Create `server/src/server.ts`:

```typescript
import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import { levelsRouter } from "./routes/levels.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function createApp() {
  const app = express();
  app.use(express.json());

  // API routes
  app.use(levelsRouter);

  // Health check
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", mode: "local" });
  });

  // Serve frontend static files (production)
  const frontendDir = path.resolve(__dirname, "../frontend/dist");
  app.use(express.static(frontendDir));
  app.get("*", (_req, res) => {
    res.sendFile(path.join(frontendDir, "index.html"));
  });

  return app;
}
```

**Step 4: Create levels route**

Create `server/src/routes/levels.ts` — port from `backend/app/services/levels.py` and `backend/app/main.py`:

```typescript
import { Router } from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import YAML from "yaml";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LEVELS_DIR = path.resolve(__dirname, "../../levels");

export const levelsRouter = Router();

// Types matching the Python Level model
export interface VerificationRule {
  type: string;
  tool_name?: string;
  min_count?: number;
  path?: string;
  pattern?: string;
  command?: string;
  expected_output?: string;
  description?: string;
}

export interface Hint {
  after_minutes: number;
  text: string;
}

export interface Level {
  id: string;
  number: number;
  title: string;
  module: string;
  intro: string;
  video?: { url: string; duration_seconds: number };
  exercise?: { intro: string; objective: string };
  verification: VerificationRule[];
  hints: Hint[];
  success: string;
  limits: { max_duration_minutes: number; max_claude_messages: number };
}

export function loadLevelByNumber(num: number): Level | null {
  const prefix = String(num).padStart(2, "0");
  const entries = fs.readdirSync(LEVELS_DIR, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && entry.name.startsWith(`${prefix}-`)) {
      const lessonPath = path.join(LEVELS_DIR, entry.name, "lesson.yaml");
      if (fs.existsSync(lessonPath)) {
        const raw = YAML.parse(fs.readFileSync(lessonPath, "utf-8"));
        return parseLevel(raw);
      }
    }
  }
  return null;
}

export function listLevels(): Array<{ id: string; number: number; title: string; module: string }> {
  const levels: Array<{ id: string; number: number; title: string; module: string }> = [];
  const entries = fs.readdirSync(LEVELS_DIR, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && /^\d{2}-/.test(entry.name)) {
      const lessonPath = path.join(LEVELS_DIR, entry.name, "lesson.yaml");
      if (fs.existsSync(lessonPath)) {
        const raw = YAML.parse(fs.readFileSync(lessonPath, "utf-8"));
        levels.push({ id: raw.id, number: raw.number, title: raw.title, module: raw.module });
      }
    }
  }
  return levels.sort((a, b) => a.number - b.number);
}

function parseLevel(data: Record<string, any>): Level {
  return {
    id: data.id,
    number: data.number,
    title: data.title,
    module: data.module,
    intro: data.intro,
    video: data.video ? { url: data.video.url, duration_seconds: data.video.duration_seconds } : undefined,
    exercise: data.exercise ? { intro: data.exercise.intro, objective: data.exercise.objective } : undefined,
    verification: (data.verification || []).map((r: any) => ({
      type: r.type,
      tool_name: r.tool_name,
      min_count: r.min_count,
      path: r.path,
      pattern: r.pattern,
      command: r.command,
      expected_output: r.expected_output,
      description: r.description,
    })),
    hints: (data.hints || []).map((h: any) => ({ after_minutes: h.after_minutes, text: h.text })),
    success: data.success,
    limits: {
      max_duration_minutes: data.limits?.max_duration_minutes ?? 15,
      max_claude_messages: data.limits?.max_claude_messages ?? 20,
    },
  };
}

// GET /api/levels
levelsRouter.get("/api/levels", (_req, res) => {
  res.json(listLevels());
});

// GET /api/levels/:number
levelsRouter.get("/api/levels/:number", (req, res) => {
  const num = parseInt(req.params.number, 10);
  const level = loadLevelByNumber(num);
  if (!level) {
    res.status(404).json({ detail: `Level ${num} not found` });
    return;
  }
  res.json(level);
});
```

**Step 5: Install dependencies and verify it compiles**

Run: `cd server && npm install && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add server/
git commit -m "feat: initialize Node.js server with Express and level routes"
```

---

### Task 2: Terminal — node-pty + WebSocket

**Files:**
- Create: `server/src/routes/sessions.ts`
- Create: `server/src/terminal.ts`
- Modify: `server/src/server.ts` (add session + WebSocket routes)

**Step 1: Create terminal module**

Create `server/src/terminal.ts` — port from `backend/app/services/local_sandbox.py`:

```typescript
import * as pty from "node-pty-prebuilt-multiarch";
import os from "os";
import path from "path";
import fs from "fs";

export interface TerminalSession {
  ptyProcess: pty.IPty;
  workspaceDir: string;
}

export function spawnTerminal(workspaceDir: string): pty.IPty {
  // [REMEDIATION #cross-platform] Abstract shell config per OS
  const isWindows = process.platform === "win32";
  const shell = isWindows ? "powershell.exe" : (process.env.SHELL || "bash");
  const args = isWindows ? [] : ["--norc", "--noprofile", "-i"];

  const env: Record<string, string> = {
    ...process.env as Record<string, string>,
    TERM: "xterm-256color",
    PS1: "\\[\\033[32m\\]claude@game\\[\\033[0m\\]:\\[\\033[34m\\]\\w\\[\\033[0m\\]$ ",
    BASH_SILENCE_DEPRECATION_WARNING: "1",
  };

  // Pass ANTHROPIC_API_KEY if set
  if (process.env.ANTHROPIC_API_KEY) {
    env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
  }

  return pty.spawn(shell, args, {
    name: "xterm-256color",
    cols: 80,
    rows: 24,
    cwd: workspaceDir,
    env,
  });
}
```

**Step 2: Create sessions route with WebSocket**

Create `server/src/routes/sessions.ts`:

> **[REMEDIATION #2]** Path traversal protection: validate all resolved paths stay within LEVELS_DIR before copying. Reject symlinks.
>
> **[REMEDIATION #3]** WebSocket security: generate a per-session nonce token returned in the session creation response. Require it in the WS URL: `/ws/terminal/:sessionId?token=:nonce`. Validate on upgrade.
>
> **[REMEDIATION #6]** Single `ws.on("message")` handler that routes by message shape (JSON with cols/rows = resize, otherwise = PTY input).
>
> **[REMEDIATION #14]** Session cleanup: add a `lastActivity` timestamp per session. On session creation, schedule a cleanup check. Sessions idle > 30 minutes get their PTY killed and workspace cleaned up. Also clean up on process exit via `process.on("exit")`.

```typescript
import { Router, Request, Response } from "express";
import { WebSocketServer, WebSocket } from "ws";
import { v4 as uuidv4 } from "uuid";
import crypto from "crypto";
import fs from "fs";
import path from "path";
import os from "os";
import { IncomingMessage } from "http";
import { Server } from "http";
import { spawnTerminal } from "../terminal.js";
import { loadLevelByNumber, Level } from "./levels.js";
import type { IPty } from "node-pty-prebuilt-multiarch";

const DATA_DIR = path.join(os.homedir(), ".claude-code-game");
const WORKSPACES_DIR = path.join(DATA_DIR, "workspaces");
const LEVELS_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../levels");

interface Session {
  sessionId: string;
  wsToken: string; // [REMEDIATION #3] per-session nonce
  pty: IPty;
  level: Level;
  levelNumber: number;
  workspaceDir: string;
  completed: boolean;
  lastActivity: number; // [REMEDIATION #14] timestamp for cleanup
}

const sessions = new Map<string, Session>();

export const sessionsRouter = Router();

// [REMEDIATION #2] Validate path doesn't escape root
function safePath(root: string, relative: string): string {
  const resolved = path.resolve(root, relative);
  if (!resolved.startsWith(path.resolve(root) + path.sep) && resolved !== path.resolve(root)) {
    throw new Error(`Path traversal detected: ${relative}`);
  }
  return resolved;
}

function getExerciseDir(levelNumber: number): string | null {
  const prefix = String(levelNumber).padStart(2, "0");
  const entries = fs.readdirSync(LEVELS_DIR, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && entry.name.startsWith(`${prefix}-`)) {
      const exerciseDir = path.join(LEVELS_DIR, entry.name, "exercise");
      if (fs.existsSync(exerciseDir)) return exerciseDir;
    }
  }
  return null;
}

// [REMEDIATION #2] Reject symlinks during copy
function copyExerciseFiles(exerciseDir: string, workspaceDir: string) {
  const entries = fs.readdirSync(exerciseDir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isSymbolicLink()) continue; // reject symlinks
    const src = path.join(exerciseDir, entry.name);
    const dest = path.join(workspaceDir, entry.name);
    if (entry.isDirectory()) {
      fs.cpSync(src, dest, { recursive: true });
    } else {
      fs.copyFileSync(src, dest);
    }
  }
}

// [REMEDIATION #14] Session cleanup — kill idle sessions after 30 minutes
const IDLE_TIMEOUT_MS = 30 * 60 * 1000;
setInterval(() => {
  const now = Date.now();
  for (const [id, session] of sessions) {
    if (now - session.lastActivity > IDLE_TIMEOUT_MS) {
      session.pty.kill();
      fs.rmSync(session.workspaceDir, { recursive: true, force: true });
      sessions.delete(id);
    }
  }
}, 60_000);

// Clean up all sessions on process exit
process.on("exit", () => {
  for (const [, session] of sessions) {
    try { session.pty.kill(); } catch {}
  }
});

// POST /api/sessions
sessionsRouter.post("/api/sessions", (req: Request, res: Response) => {
  const { level_number = 1 } = req.body;

  const level = loadLevelByNumber(level_number);
  if (!level) {
    res.status(404).json({ detail: `Level ${level_number} not found` });
    return;
  }

  const sessionId = uuidv4().slice(0, 8);
  const wsToken = crypto.randomBytes(16).toString("hex"); // [REMEDIATION #3]
  const workspaceDir = path.join(WORKSPACES_DIR, sessionId);
  fs.mkdirSync(workspaceDir, { recursive: true });

  // Copy exercise files
  const exerciseDir = getExerciseDir(level_number);
  if (exerciseDir) {
    copyExerciseFiles(exerciseDir, workspaceDir);
  }

  // Spawn PTY
  const ptyProcess = spawnTerminal(workspaceDir);

  sessions.set(sessionId, {
    sessionId,
    wsToken,
    pty: ptyProcess,
    level,
    levelNumber: level_number,
    workspaceDir,
    completed: false,
    lastActivity: Date.now(),
  });

  res.json({
    session_id: sessionId,
    ws_token: wsToken, // [REMEDIATION #3] client uses this to connect WS
    status: "ready",
    level: {
      number: level.number,
      title: level.title,
      module: level.module,
      intro: level.intro,
      video: level.video ?? null,
      exercise: level.exercise ?? null,
    },
  });
});

// DELETE /api/sessions/:sessionId
sessionsRouter.delete("/api/sessions/:sessionId", (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId);
  if (session) {
    session.pty.kill();
    fs.rmSync(session.workspaceDir, { recursive: true, force: true });
    sessions.delete(req.params.sessionId);
  }
  res.json({ session_id: req.params.sessionId, status: "stopped" });
});

// PATCH /api/sessions/:sessionId/level — switch level without new session
sessionsRouter.patch("/api/sessions/:sessionId/level", (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }

  const { level_number } = req.body;
  const level = loadLevelByNumber(level_number);
  if (!level) {
    res.status(404).json({ detail: `Level ${level_number} not found` });
    return;
  }

  // Kill old PTY
  session.pty.kill();

  // Clean workspace and copy new exercise files
  fs.rmSync(session.workspaceDir, { recursive: true, force: true });
  fs.mkdirSync(session.workspaceDir, { recursive: true });
  const exerciseDir = getExerciseDir(level_number);
  if (exerciseDir) {
    copyExerciseFiles(exerciseDir, session.workspaceDir);
  }

  // Spawn new PTY
  session.pty = spawnTerminal(session.workspaceDir);
  session.level = level;
  session.levelNumber = level_number;
  session.completed = false;
  session.lastActivity = Date.now();

  res.json({
    level: {
      number: level.number,
      title: level.title,
      module: level.module,
      intro: level.intro,
      video: level.video ?? null,
      exercise: level.exercise ?? null,
    },
  });
});

// GET /api/sessions/:sessionId/progress (placeholder — Task 3 adds real verification)
sessionsRouter.get("/api/sessions/:sessionId/progress", (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }
  session.lastActivity = Date.now();
  res.json({ session_id: session.sessionId, progress: null });
});

// GET /api/sessions/:sessionId/status
sessionsRouter.get("/api/sessions/:sessionId/status", (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }
  session.lastActivity = Date.now();
  res.json({ completed: session.completed });
});

// Export for WebSocket setup
export function getSession(sessionId: string): Session | undefined {
  return sessions.get(sessionId);
}

// WebSocket setup — called from server.ts after HTTP server is created
export function setupWebSocket(server: Server) {
  const wss = new WebSocketServer({ noServer: true });

  // [REMEDIATION #3] Validate session + nonce token on upgrade
  server.on("upgrade", (request: IncomingMessage, socket, head) => {
    const url = new URL(request.url || "", `http://${request.headers.host}`);
    const match = url.pathname.match(/^\/ws\/terminal\/(.+)$/);

    if (!match) {
      socket.destroy();
      return;
    }

    const sessionId = match[1];
    const token = url.searchParams.get("token");
    const session = sessions.get(sessionId);

    if (!session || session.wsToken !== token) {
      socket.write("HTTP/1.1 403 Forbidden\r\n\r\n");
      socket.destroy();
      return;
    }

    // Origin check — only allow localhost
    const origin = request.headers.origin || "";
    if (origin && !origin.match(/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/)) {
      socket.write("HTTP/1.1 403 Forbidden\r\n\r\n");
      socket.destroy();
      return;
    }

    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit("connection", ws, request, sessionId);
    });
  });

  wss.on("connection", (ws: WebSocket, _req: IncomingMessage, sessionId: string) => {
    const session = sessions.get(sessionId);
    if (!session) {
      ws.close(1008, "Session not found");
      return;
    }

    session.lastActivity = Date.now();

    // Send level intro
    const intro = session.level.intro;
    ws.send("\x1b[2J\x1b[H"); // Clear screen
    ws.send("\r\n");
    for (const line of intro.split("\n")) {
      ws.send(line + "\r\n");
    }
    ws.send("\r\n");
    ws.send("\x1b[90m" + "─".repeat(60) + "\x1b[0m\r\n");
    ws.send("\r\n");

    // PTY → WebSocket
    session.pty.onData((data: string) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    // [REMEDIATION #6] Single message handler — route by message shape
    ws.on("message", (data: Buffer | string) => {
      const text = typeof data === "string" ? data : data.toString("utf-8");
      session.lastActivity = Date.now();

      // Check for resize messages (JSON with cols/rows)
      if (text.startsWith("{")) {
        try {
          const msg = JSON.parse(text);
          if (typeof msg.cols === "number" && typeof msg.rows === "number") {
            session.pty.resize(msg.cols, msg.rows);
            return;
          }
        } catch {
          // Not valid JSON, treat as PTY input
        }
      }

      // PTY input
      session.pty.write(text);
    });

    ws.on("close", () => {
      // Session stays alive — user might reconnect
    });
  });
}
```

**Step 3: Wire WebSocket into server.ts**

Update `server/src/server.ts` to add session routes and WebSocket:

```typescript
import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import { createServer } from "http";
import { levelsRouter } from "./routes/levels.js";
import { sessionsRouter, setupWebSocket } from "./routes/sessions.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function createApp() {
  const app = express();
  app.use(express.json());

  // CORS for local dev (frontend on different port)
  app.use((_req, res, next) => {
    const origin = _req.headers.origin || "";
    if (origin.match(/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/)) {
      res.setHeader("Access-Control-Allow-Origin", origin);
      res.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS");
      res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
    }
    if (_req.method === "OPTIONS") { res.sendStatus(204); return; }
    next();
  });

  app.use(levelsRouter);
  app.use(sessionsRouter);

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", mode: "local" });
  });

  // Serve frontend static files
  const frontendDir = path.resolve(__dirname, "../frontend/dist");
  app.use(express.static(frontendDir));
  app.get("*", (_req, res) => {
    res.sendFile(path.join(frontendDir, "index.html"));
  });

  return app;
}

// [REMEDIATION #3] Bind to 127.0.0.1 only — never expose to network
export function startServer(port: number, host = "127.0.0.1") {
  const app = createApp();
  const server = createServer(app);
  setupWebSocket(server);

  return new Promise<void>((resolve) => {
    server.listen(port, host, () => {
      console.log(`Server running at http://${host}:${port}`);
      resolve();
    });
  });
}
```

**Step 4: Verify compilation**

Run: `cd server && npx tsc --noEmit`
Expected: No errors

**Step 5: Quick cross-platform smoke test**

> **[REMEDIATION #18]** Test node-pty spawning early. Run `cd server && npx tsx -e "import * as pty from 'node-pty-prebuilt-multiarch'; const p = pty.spawn('echo', ['hello'], { name: 'xterm' }); p.onData(d => { console.log(d); p.kill(); });"` on macOS/Linux. If it fails, investigate now rather than at Task 11.

**Step 6: Commit**

```bash
git add server/src/routes/sessions.ts server/src/terminal.ts server/src/server.ts
git commit -m "feat: add terminal sessions with node-pty and WebSocket"
```

---

### Task 3: Verification Engine

**Files:**
- Create: `server/src/verification.ts`
- Modify: `server/src/routes/sessions.ts` (wire up real progress endpoint)

> **[REMEDIATION #1]** `command_output` rules now use `execFile` (no shell) with an allowlist of safe commands. Only `git`, `node`, `npx`, `cat`, `ls`, `wc`, `grep`, `test` are permitted. Commands are parsed into argv and executed without shell expansion.
>
> **[REMEDIATION #5]** Log lookup uses sha256 hash of absolute workspace path as the primary lookup key, with the existing path-encoding as a fallback.
>
> **[REMEDIATION #7]** All `execSync` calls replaced with async `execFile` wrapped in `Promise` with 10s timeout.

**Step 1: Create verification engine**

Create `server/src/verification.ts` — port from `backend/app/services/verification.py`:

```typescript
import fs from "fs";
import path from "path";
import os from "os";
import crypto from "crypto";
import { execFile } from "child_process";
import { promisify } from "util";
import type { VerificationRule, Level } from "./routes/levels.js";

const execFileAsync = promisify(execFile);

// [REMEDIATION #1] Allowlist of safe commands for command_output verification
const ALLOWED_COMMANDS = new Set(["git", "node", "npx", "cat", "ls", "wc", "grep", "test", "head", "tail"]);

export interface ProgressResult {
  rules: Array<{
    type: string;
    passed: boolean;
    tool_name?: string;
    path?: string;
    description?: string;
  }>;
  completed: boolean;
  passed_count: number;
  total_count: number;
}

export class VerificationEngine {
  constructor(private workspaceDir: string) {}

  async getProgress(level: Level): Promise<ProgressResult> {
    const results = [];
    for (const rule of level.verification) {
      const passed = await this.checkRule(rule);
      results.push({
        type: rule.type,
        passed,
        tool_name: rule.tool_name,
        path: rule.path,
        description: rule.description,
      });
    }
    return {
      rules: results,
      completed: results.every((r) => r.passed),
      passed_count: results.filter((r) => r.passed).length,
      total_count: results.length,
    };
  }

  private async checkRule(rule: VerificationRule): Promise<boolean> {
    try {
      switch (rule.type) {
        case "message_exists": return this.checkMessageExists();
        case "tool_called": return this.checkToolCalled(rule.tool_name, rule.min_count);
        case "file_exists": return this.checkFileExists(rule.path);
        case "file_contains": return this.checkFileContains(rule.path, rule.pattern);
        case "file_changed": return this.checkFileChanged(rule.path);
        case "commit_exists": return this.checkCommitExists(rule.pattern);
        case "command_output": return await this.checkCommandOutput(rule.command, rule.expected_output);
        case "min_user_messages": return this.checkMinUserMessages(rule.min_count);
        case "glob_exists": return this.checkGlobExists(rule.pattern);
        case "home_glob_exists": return this.checkHomeGlobExists(rule.pattern);
        case "tool_called_with_path": return this.checkToolCalledWithPath(rule.tool_name, rule.pattern);
        default: return false;
      }
    } catch {
      return false;
    }
  }

  // --- Message log reading ---
  // [REMEDIATION #5] Use sha256 hash of absolute workspace path as primary lookup

  private readMessagesLog(): Array<Record<string, any>> {
    const projectsDir = path.join(os.homedir(), ".claude", "projects");
    if (!fs.existsSync(projectsDir)) return [];

    const absWorkspace = path.resolve(this.workspaceDir);

    // Primary: sha256 hash lookup
    const hash = crypto.createHash("sha256").update(absWorkspace).digest("hex").slice(0, 16);
    let projectDir = "";
    const dirs = fs.readdirSync(projectsDir);

    // Try hash match first, then encoded path, then partial name match
    const encoded = "-" + absWorkspace.replace(/\//g, "-");
    const workspaceName = path.basename(absWorkspace);

    for (const d of dirs) {
      if (d.includes(hash)) { projectDir = path.join(projectsDir, d); break; }
    }
    if (!projectDir) {
      const encodedMatch = dirs.find((d) => d === encoded);
      if (encodedMatch) projectDir = path.join(projectsDir, encodedMatch);
    }
    if (!projectDir) {
      const partialMatch = dirs.find((d) => d.includes(workspaceName));
      if (partialMatch) projectDir = path.join(projectsDir, partialMatch);
    }
    if (!projectDir || !fs.existsSync(projectDir)) return [];

    // Find latest .jsonl
    const jsonlFiles = fs.readdirSync(projectDir).filter((f) => f.endsWith(".jsonl"));
    if (jsonlFiles.length === 0) return [];

    const latest = jsonlFiles
      .map((f) => ({ name: f, mtime: fs.statSync(path.join(projectDir, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime)[0];

    const content = fs.readFileSync(path.join(projectDir, latest.name), "utf-8");
    const messages: Array<Record<string, any>> = [];
    for (const line of content.split("\n")) {
      if (!line.trim()) continue;
      try { messages.push(JSON.parse(line)); } catch { /* skip */ }
    }
    return messages;
  }

  // --- Rule implementations ---

  private checkMessageExists(): boolean {
    const messages = this.readMessagesLog();
    return messages.some((m) => m.type === "assistant");
  }

  private checkToolCalled(toolName?: string, minCount?: number): boolean {
    if (!toolName) return false;
    const messages = this.readMessagesLog();
    let count = 0;
    for (const msg of messages) {
      if (msg.type !== "assistant") continue;
      const content = msg.message?.content || [];
      for (const block of content) {
        if (block.type === "tool_use" && block.name === toolName) {
          count++;
          if (minCount == null) return true;
        }
      }
    }
    return minCount != null ? count >= minCount : false;
  }

  private checkFileExists(filePath?: string): boolean {
    if (!filePath) return false;
    return fs.existsSync(path.join(this.workspaceDir, filePath));
  }

  private checkFileContains(filePath?: string, pattern?: string): boolean {
    if (!filePath || !pattern) return false;
    const fullPath = path.join(this.workspaceDir, filePath);
    if (!fs.existsSync(fullPath)) return false;
    const content = fs.readFileSync(fullPath, "utf-8");
    return new RegExp(pattern).test(content);
  }

  private checkFileChanged(filePath?: string): boolean {
    if (!filePath) return false;
    const messages = this.readMessagesLog();
    for (const msg of messages) {
      if (msg.type !== "assistant") continue;
      const content = msg.message?.content || [];
      for (const block of content) {
        if (block.type === "tool_use" && block.name === "Edit") {
          if ((block.input?.file_path || "").includes(filePath)) return true;
        }
      }
    }
    return false;
  }

  private async checkCommitExists(pattern?: string): Promise<boolean> {
    try {
      // [REMEDIATION #1, #7] Use execFile (no shell) with async
      const { stdout } = await execFileAsync("git", ["log", "--oneline", "-n", "10"], {
        cwd: this.workspaceDir,
        timeout: 10000,
      });
      if (pattern) return new RegExp(pattern, "i").test(stdout);
      return stdout.trim().length > 0;
    } catch {
      return false;
    }
  }

  // [REMEDIATION #1] Allowlisted async command execution
  private async checkCommandOutput(command?: string, expected?: string): Promise<boolean> {
    if (!command) return false;
    try {
      // Parse command into argv
      const parts = command.split(/\s+/);
      const cmd = parts[0];
      const args = parts.slice(1);

      // Allowlist check
      if (!ALLOWED_COMMANDS.has(cmd)) {
        console.warn(`Verification: blocked disallowed command "${cmd}"`);
        return false;
      }

      const { stdout, stderr } = await execFileAsync(cmd, args, {
        cwd: this.workspaceDir,
        timeout: 10000,
      });
      if (expected) return new RegExp(expected).test(stdout + stderr);
      return true;
    } catch (err: any) {
      if (expected && (err.stdout || err.stderr)) {
        return new RegExp(expected).test((err.stdout || "") + (err.stderr || ""));
      }
      return false;
    }
  }

  private checkMinUserMessages(minCount?: number): boolean {
    if (!minCount) return true;
    const messages = this.readMessagesLog();
    const count = messages.filter((m) => m.type === "user").length;
    return count >= minCount;
  }

  private checkGlobExists(pattern?: string): boolean {
    if (!pattern) return false;
    const fullPattern = path.join(this.workspaceDir, pattern);
    const { globSync } = require("glob");
    const matches = globSync(fullPattern);
    return matches.length > 0;
  }

  private checkHomeGlobExists(pattern?: string): boolean {
    if (!pattern) return false;
    const fullPattern = path.join(os.homedir(), ".claude", pattern);
    const { globSync } = require("glob");
    const matches = globSync(fullPattern);
    return matches.length > 0;
  }

  private checkToolCalledWithPath(toolName?: string, pathPattern?: string): boolean {
    if (!toolName || !pathPattern) return false;
    const messages = this.readMessagesLog();
    for (const msg of messages) {
      if (msg.type !== "assistant") continue;
      const content = msg.message?.content || [];
      for (const block of content) {
        if (block.type === "tool_use" && block.name === toolName) {
          const fp = block.input?.file_path || "";
          if (new RegExp(pathPattern).test(fp)) return true;
        }
      }
    }
    return false;
  }
}
```

**Step 2: Add `glob` dependency**

Run: `cd server && npm install glob && npm install -D @types/glob`

**Step 3: Wire verification into sessions route**

Update the `/api/sessions/:sessionId/progress` handler in `server/src/routes/sessions.ts`:

```typescript
// Replace the placeholder progress endpoint with:
import { VerificationEngine } from "../verification.js";

// GET /api/sessions/:sessionId/progress
sessionsRouter.get("/api/sessions/:sessionId/progress", async (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }
  session.lastActivity = Date.now();
  const engine = new VerificationEngine(session.workspaceDir);
  const progress = await engine.getProgress(session.level);

  // Update session completion state
  if (progress.completed) session.completed = true;

  res.json({
    session_id: session.sessionId,
    level_number: session.levelNumber,
    completed: session.completed,
    progress,
  });
});
```

Also update the status endpoint to do a real check:

```typescript
sessionsRouter.get("/api/sessions/:sessionId/status", async (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }
  session.lastActivity = Date.now();
  if (!session.completed) {
    const engine = new VerificationEngine(session.workspaceDir);
    const progress = await engine.getProgress(session.level);
    if (progress.completed) session.completed = true;
  }
  res.json({ completed: session.completed });
});
```

**Step 4: Verify compilation**

Run: `cd server && npx tsc --noEmit`
Expected: No errors

**Step 5: Commit**

```bash
git add server/src/verification.ts server/src/routes/sessions.ts
git commit -m "feat: port verification engine from Python to TypeScript"
```

---

### Task 4: CLI Wrapper

**Files:**
- Create: `server/src/cli.ts`

> **[REMEDIATION #8]** Use port 0 (OS-assigned) as default, read actual port from server.
>
> **[REMEDIATION #10]** Detect WSL and print URL instead of auto-opening browser.

**Step 1: Create CLI entry point**

Create `server/src/cli.ts`:

```typescript
#!/usr/bin/env node
import { startServer } from "./server.js";
import open from "open";
import fs from "fs";

const args = process.argv.slice(2);
const noOpen = args.includes("--no-open");
const portFlag = args.indexOf("--port");
const requestedPort = portFlag !== -1 ? parseInt(args[portFlag + 1], 10) : 3000;

// [REMEDIATION #10] Detect WSL — auto-open doesn't work there
function isWSL(): boolean {
  try {
    return fs.readFileSync("/proc/version", "utf-8").toLowerCase().includes("microsoft");
  } catch {
    return false;
  }
}

async function main() {
  const port = requestedPort;
  const url = `http://127.0.0.1:${port}`;

  console.log("Starting Claude Code Game...");
  await startServer(port);
  console.log(`Running at ${url}`);

  if (!noOpen && !isWSL()) {
    await open(url);
  } else if (isWSL()) {
    console.log("WSL detected — open the URL above in your browser manually.");
  }
}

main().catch((err) => {
  console.error("Failed to start:", err);
  process.exit(1);
});
```

**Step 2: Verify compilation**

Run: `cd server && npx tsc --noEmit`
Expected: No errors

**Step 3: Test locally**

Run: `cd server && npx tsx src/cli.ts --no-open`
Expected: Prints "Running at http://127.0.0.1:3000"

Kill the process (Ctrl+C).

**Step 4: Commit**

```bash
git add server/src/cli.ts
git commit -m "feat: add CLI entry point with WSL detection and browser open"
```

---

### Task 5: Simplify Frontend

**Files:**
- Modify: `frontend/src/config.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Terminal.tsx`
- Modify: `frontend/src/hooks/useVerificationProgress.ts`

The frontend currently has conditional logic for Docker, Fly, Modal, and local modes. We strip all of that down to a single mode: direct WebSocket to the local Express server. No ttyd protocol, no iframe mode, no subprotocol — just plain WebSocket carrying raw PTY data.

**Step 1: Simplify config.ts**

Replace `frontend/src/config.ts` with:

```typescript
export const config = {
  apiUrl: import.meta.env.VITE_API_URL || "",
};
```

The empty string `""` means "same origin" — when the frontend is served by the Express server, all API calls go to the same host. During dev, set `VITE_API_URL=http://localhost:3000`.

**Step 2: Simplify App.tsx**

Remove all `isDockerMode` branching. All API calls use the same paths (`/api/sessions`, not `/api/docker/sessions`). Remove `ttyd_url`, `port`, `ttyd_token` from Session interface. Remove access code input (auth will be added in Phase 2). The PATCH `/api/sessions/:id/level` endpoint is now available for all modes.

Key changes:
- Remove `isDockerMode` variable and all its conditionals
- Session interface becomes: `{ session_id: string; ws_token: string; level: Level }`
- `startGame()` always POSTs to `${config.apiUrl}/api/sessions`
- `nextLevel()` always PATCHes `${config.apiUrl}/api/sessions/${id}/level`
- Remove access code input field (Phase 2 adds email auth)
- Remove API key hints text

**Step 3: Simplify Terminal.tsx**

Remove `IframeTerminal` entirely. Remove ttyd protocol handling (no more `{"AuthToken":""}`, no type-prefix parsing). The WebSocket now carries plain text (PTY output directly).

Replace `WebSocketTerminal` connection logic:

```typescript
// [REMEDIATION #3] Include ws_token in WebSocket URL
const wsUrl = `${config.apiUrl.replace("http", "ws")}/ws/terminal/${sessionId}?token=${wsToken}`;
const ws = new WebSocket(wsUrl);

ws.onmessage = (event) => {
  const data = event.data;
  if (typeof data === "string") {
    if (data.includes("__LEVEL_COMPLETE__")) {
      term.write(data.replace("__LEVEL_COMPLETE__", ""));
      onLevelCompleteRef.current?.();
      return;
    }
    term.write(data);
  }
};

// Input — plain text, no type prefix
term.onData((data) => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(data);
  }
});

// Resize — send as JSON
const handleResize = () => {
  fitAddon.fit();
  if (ws.readyState === WebSocket.OPEN) {
    const dims = fitAddon.proposeDimensions();
    if (dims) ws.send(JSON.stringify({ cols: dims.cols, rows: dims.rows }));
  }
};
```

Remove: `ws.binaryType = "arraybuffer"`, ArrayBuffer parsing, ttyd auth handshake, ttyd resize prefix.

**Step 4: Simplify useVerificationProgress.ts**

Remove Docker mode endpoint branching — always use `/api/sessions/${sessionId}/progress`.

**Step 5: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/config.ts frontend/src/App.tsx frontend/src/components/Terminal.tsx frontend/src/hooks/useVerificationProgress.ts
git commit -m "feat: simplify frontend to single local mode (no Docker/Fly/Modal)"
```

---

### Task 6: End-to-End Integration Test

**Files:** None created — manual verification

**Step 1: Build frontend**

Run: `cd frontend && npm run build`
Expected: Build succeeds, creates `frontend/dist/`

**Step 2: Copy or symlink frontend dist into server**

Run: `ln -s ../../frontend/dist server/frontend` (or adjust server.ts to point to `../frontend/dist`)

**Step 3: Start server**

Run: `cd server && npx tsx src/cli.ts --no-open`
Expected: Server starts on port 3000

**Step 4: Open browser manually**

Navigate to `http://127.0.0.1:3000`
Expected: See start screen with lesson selector

**Step 5: Start a session**

Click "Start" on Lesson 1. Verify:
- Watch phase shows video player
- Click "Start Exercise" transitions to exercise phase
- Terminal connects and shows level intro + bash prompt
- Typing in terminal works
- Verification progress checklist appears and updates

**Step 6: Commit integration fix-ups**

```bash
git add -A
git commit -m "fix: wire up frontend build with Express server"
```

---

## Phase 2: Auth + Cloud Features

### Task 7: Cloudflare Worker — Auth Endpoints

**Files:**
- Create: `worker/package.json`
- Create: `worker/wrangler.toml`
- Create: `worker/src/index.ts`
- Create: `worker/src/auth.ts`
- Create: `worker/schema.sql`

> **[REMEDIATION #4]** JWT tokens include and enforce: `iss: "claude-code-game-worker"`, `aud: "claude-code-game-local"`, `exp` (24h), `nbf`, `iat`. Local server validates all claims.
>
> **[REMEDIATION #15]** Rate limiting: KV-based counter per email, max 5 code requests per hour. Return 429 on excess.
>
> **[REMEDIATION #17]** Key rotation: Include `kid` (key ID) in JWT header. Public key shipped as `keys/{kid}.pem`. Worker can have multiple active private keys. Local server tries all public keys matching the `kid`.

**Step 1: Initialize worker project**

```json
// worker/package.json
{
  "name": "claude-code-game-worker",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy"
  },
  "devDependencies": {
    "wrangler": "^4.0.0",
    "@cloudflare/workers-types": "^4.0.0",
    "typescript": "^5.9.0"
  }
}
```

```toml
# worker/wrangler.toml
name = "claude-code-game-api"
main = "src/index.ts"
compatibility_date = "2025-01-01"

[vars]
ADMIN_TOKEN = "change-me"

[[kv_namespaces]]
binding = "KV"
id = "placeholder"  # Replace after creating

[[d1_databases]]
binding = "DB"
database_name = "claude-code-game"
database_id = "placeholder"  # Replace after creating
```

```sql
-- worker/schema.sql
CREATE TABLE IF NOT EXISTS enrolled (
  email TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS progress (
  email TEXT NOT NULL,
  level_number INTEGER NOT NULL,
  completed_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (email, level_number),
  FOREIGN KEY (email) REFERENCES enrolled(email)
);
```

**Step 2: Create worker with auth routes**

Create `worker/src/index.ts`:

```typescript
export interface Env {
  KV: KVNamespace;
  DB: D1Database;
  JWT_PRIVATE_KEY: string;  // Secret: PEM-encoded RSA private key
  JWT_KEY_ID: string;       // [REMEDIATION #17] Key ID for rotation
  ADMIN_TOKEN: string;
  RESEND_API_KEY: string;  // Secret
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      let response: Response;
      switch (`${request.method} ${url.pathname}`) {
        case "POST /verify/request":
          response = await handleVerifyRequest(request, env);
          break;
        case "POST /verify/confirm":
          response = await handleVerifyConfirm(request, env);
          break;
        case "POST /events":
          response = await handleEvent(request, env);
          break;
        case "GET /leaderboard":
          response = await handleLeaderboard(request, env);
          break;
        case "GET /admin/stats":
          response = await handleAdminStats(request, env);
          break;
        default:
          response = new Response("Not found", { status: 404 });
      }
      // Add CORS to response
      for (const [k, v] of Object.entries(corsHeaders)) {
        response.headers.set(k, v);
      }
      return response;
    } catch (err: any) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      });
    }
  },
};
```

Handler functions implement:
- `handleVerifyRequest`: Check enrollment in D1, generate 6-digit code, store in KV with 5min TTL, send via Resend. **[REMEDIATION #15]** Check rate limit counter in KV (`rate:{email}`, increment, 1h TTL, max 5).
- `handleVerifyConfirm`: Validate code from KV, sign JWT with private key. **[REMEDIATION #4]** JWT payload includes `iss`, `aud`, `exp` (24h), `nbf`, `iat`. **[REMEDIATION #17]** JWT header includes `kid`.
- `handleEvent`: Validate JWT, record progress in D1.
- `handleLeaderboard`: Query D1 for progress counts, return ranked list.
- `handleAdminStats`: Require ADMIN_TOKEN, return enrollment + progress stats.

**Step 3: Generate RSA key pair**

Run:
```bash
openssl genrsa -out worker/private.pem 2048
openssl rsa -in worker/private.pem -pubout -out server/keys/v1.pem
```

> **[REMEDIATION #17]** Key file named by key ID (`v1`). Worker secret `JWT_KEY_ID` set to `v1`.

Store `private.pem` content as a Cloudflare Worker secret (never committed).
`v1.pem` ships with the npm package for local JWT verification.

**Step 4: Deploy and test**

Run: `cd worker && npm install && wrangler d1 create claude-code-game && wrangler kv:namespace create KV`

Update `wrangler.toml` with real IDs.

Run: `wrangler d1 execute claude-code-game --file schema.sql`
Run: `wrangler secret put JWT_PRIVATE_KEY` (paste private key)
Run: `wrangler secret put JWT_KEY_ID` (enter `v1`)
Run: `wrangler secret put RESEND_API_KEY` (paste Resend key)
Run: `wrangler deploy`

**Step 5: Commit**

```bash
git add worker/ server/keys/v1.pem
git commit -m "feat: add Cloudflare Worker for auth, progress, and leaderboard"
```

---

### Task 8: Auth Flow in Frontend

**Files:**
- Modify: `frontend/src/App.tsx` (add auth screen)
- Create: `frontend/src/hooks/useAuth.ts`
- Modify: `server/src/routes/sessions.ts` (add auth proxy routes)

> **[REMEDIATION #9]** Auth token file written with mode 0600 on Unix.
>
> **[REMEDIATION #16]** Offline mode: If Worker is unreachable during auth, show an error message and block progression until auth succeeds. No guest bypass.

**Step 1: Create useAuth hook**

Create `frontend/src/hooks/useAuth.ts`:

```typescript
import { useState, useEffect } from "react";
import { config } from "../config";

interface AuthState {
  token: string | null;
  email: string | null;
  name: string | null;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>({ token: null, email: null, name: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token via server endpoint
    fetch(`${config.apiUrl}/api/auth/status`)
      .then((r) => r.json())
      .then((data) => {
        if (data.authenticated) {
          setAuth({ token: data.token, email: data.email, name: data.name });
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function requestCode(email: string) {
    const res = await fetch(`${config.apiUrl}/api/auth/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) throw new Error((await res.json()).error);
  }

  async function confirmCode(email: string, code: string) {
    const res = await fetch(`${config.apiUrl}/api/auth/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    if (!res.ok) throw new Error((await res.json()).error);
    const data = await res.json();
    setAuth({ token: data.token, email: data.email, name: data.name });
  }

  function logout() {
    fetch(`${config.apiUrl}/api/auth/logout`, { method: "POST" });
    setAuth({ token: null, email: null, name: null });
  }

  return { auth, loading, requestCode, confirmCode, logout };
}
```

**Step 2: Add auth proxy routes to server**

The local Express server proxies auth requests to the Cloudflare Worker and manages the local JWT file at `~/.claude-code-game/auth.json`.

Create `server/src/routes/auth.ts` with:
- `POST /api/auth/request` → forwards to Worker `POST /verify/request`
- `POST /api/auth/confirm` → forwards to Worker `POST /verify/confirm`, stores JWT locally
- `GET /api/auth/status` → reads local JWT, verifies with public key (checking `iss`, `aud`, `exp`), returns auth state
- `POST /api/auth/logout` → deletes local auth file

> **[REMEDIATION #9]** When writing `auth.json`, set file permissions:
> ```typescript
> fs.writeFileSync(authPath, JSON.stringify(data), { mode: 0o600 });
> ```

> **[REMEDIATION #4]** JWT verification with full claim validation:
> ```typescript
> jwt.verify(token, publicKey, {
>   algorithms: ["RS256"],
>   issuer: "claude-code-game-worker",
>   audience: "claude-code-game-local",
> });
> ```

**Step 3: Add auth screen to App.tsx**

Before the lesson list, check `auth.token`. If falsy, show:
1. Email input → "Send Code" button
2. Code input → "Verify" button
3. On success, proceed to lesson list
4. If Worker unreachable, show error and require retry (no bypass)

**Step 4: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 5: Commit**

```bash
git add frontend/src/hooks/useAuth.ts frontend/src/App.tsx server/src/routes/auth.ts
git commit -m "feat: add email verification auth flow"
```

---

### Task 9: Progress Reporting + Leaderboard

**Files:**
- Modify: `server/src/routes/sessions.ts` (report completion to Worker)
- Create: `frontend/src/components/Leaderboard.tsx`
- Modify: `frontend/src/App.tsx` (add leaderboard tab)

**Step 1: Report completion events**

When a session is marked completed (in the progress/status endpoints), fire a POST to the Worker's `/events` endpoint with the user's JWT + level number.

**Step 2: Create Leaderboard component**

```typescript
// frontend/src/components/Leaderboard.tsx
// Fetches GET /api/leaderboard (proxied through Express → Worker)
// Renders simple table: rank, name, levels completed out of 11
```

**Step 3: Add leaderboard to App.tsx start screen**

Show a "Leaderboard" tab/section on the start screen below the lesson selector.

**Step 4: Commit**

```bash
git add frontend/src/components/Leaderboard.tsx frontend/src/App.tsx server/src/routes/sessions.ts
git commit -m "feat: add progress reporting and leaderboard"
```

---

## Phase 3: Ship

### Task 10: Packaging

**Files:**
- Modify: `server/package.json` (add `files`, `bin`, `prepublishOnly`)
- Symlink or copy `levels/` and `frontend/dist/` into server package

**Step 1: Configure package.json for npm publish**

```json
{
  "files": ["dist/", "frontend/", "levels/", "keys/"],
  "bin": { "claude-code-game": "./dist/cli.js" },
  "scripts": {
    "prepublishOnly": "npm run build && cd ../frontend && npm run build && cp -r dist ../server/frontend"
  }
}
```

**Step 2: Build and check package size**

Run: `cd server && npm pack --dry-run`
Expected: Under 10MB

**Step 3: Commit**

```bash
git add server/package.json
git commit -m "feat: configure npm packaging with bin entry and bundled assets"
```

---

### Task 11: Cross-Platform Testing

> **[REMEDIATION #18]** This should be started as early as Task 2, with full matrix testing here.

**Step 1: Test on macOS**

Run: `cd server && npm pack && npx ./claude-code-game-0.1.0.tgz`
Expected: Server starts, browser opens, terminal works, verification works.

**Step 2: Test on Linux (or CI)**

Same as above in a Linux environment.

**Step 3: Test on Windows/WSL**

Same as above in WSL. Verify:
- node-pty spawns correctly with ConPTY
- WSL detection prints URL instead of opening browser
- File paths use correct separators

**Step 4: Fix any platform issues found**

Commit fixes as needed.

---

### Task 12: npm Publish

**Step 1: Test with npx from registry**

Run: `npm publish --dry-run` to verify contents.

**Step 2: Publish**

Run: `npm publish`

**Step 3: Verify**

Run (from a clean machine): `npx claude-code-game`
Expected: Full flow works — auth, lessons, terminal, verification, leaderboard.

---

### Task 13: Delete Old Code

**Files:**
- Delete: `backend/` (entire directory)
- Delete: `sandbox/` (entire directory)
- Modify: `CLAUDE.md` (update for new architecture)

**Step 1: Remove old directories**

```bash
rm -rf backend/ sandbox/
```

**Step 2: Update CLAUDE.md**

Rewrite to reflect new architecture: Node.js server, no Docker, no Python.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove Python backend and Docker sandbox (replaced by Node.js CLI)"
```

---

## Verification Log

### Phase 1: Core Local Experience — VERIFIED
- Tasks 1–6 completed in prior sessions
- TypeScript compiles clean (`npx tsc --noEmit` passes for server, frontend, worker)

### Phase 2: Auth + Cloud Features — VERIFIED (2026-02-06)

**Level 2 (API tests via curl) — 11/11 PASS:**
- `GET /health` → `{"status":"ok","mode":"local"}`
- `GET /api/auth/status` → `{"authenticated":false}`
- `POST /api/auth/request` (no Worker) → graceful error: "Auth service unavailable. Please try again later."
- `POST /api/auth/confirm` (no Worker) → graceful error
- `GET /api/leaderboard` (no Worker) → `[]` (graceful empty)
- `POST /api/auth/logout` → `{"ok":true}`
- `GET /api/levels` → all 11 levels returned
- `POST /api/sessions` → session created with `ws_token`
- `GET /api/sessions/:id/progress` → verification rules returned
- `GET /api/sessions/:id/status` → `{"completed":false}`
- `GET /api/sessions/nonexistent/status` → 404

**Level 3 (Browser E2E via Playwright) — 5/5 PASS (after fixes):**
- Auth screen loads with email input, Send Code button
- Send Code shows "Auth service unavailable" error (no Worker), blocks progression
- Start lesson shows watch phase with YouTube player
- Start Exercise shows terminal with lesson intro + bash prompt
- `echo hello` → `hello` — terminal is fully interactive

**Bugs found and fixed (commit 295818a):**
1. **Stale frontend build** — `server/frontend/` was built before auth code was committed. Auth screen was missing. Fix: rebuilt and re-copied.
2. **Shell was zsh, not bash** (`terminal.ts`) — macOS `$SHELL` is zsh but PS1/args were bash-only. Prompt was invisible. Fix: hardcode `bash`.
3. **PTY prompt lost before WS connects** (`sessions.ts`) — PTY spawned at session creation, WS connects at exercise phase. Initial prompt lost. Fix: `pty.write("\n")` after attaching `onData`.

### Cloudflare Worker Deployment — VERIFIED (2026-02-07)

**Infrastructure provisioned:**
- D1 database `claude-code-game` (ID: `1f3a3b8f-ac62-41ee-9d0d-0926ce8e74eb`) — schema applied (enrolled + progress tables)
- KV namespace (ID: `9867a634a9864f8d8d1981044c5207b2`) — rate limiting + verification codes
- Worker deployed at `https://claude-code-game-api.abhishekray07.workers.dev`
- Secrets set: `JWT_PRIVATE_KEY` (PKCS8 RSA 2048), `RESEND_API_KEY`
- RSA public key regenerated at `server/keys/v1.pem`
- Default Worker URL hardcoded in `auth.ts` + `sessions.ts` (no env config needed)
- Resend sender: `noreply@opslane.com`

**Auth endpoint tests — 4/4 PASS:**
- Unenrolled email → `403 Not enrolled`
- Invalid email format → `400 Invalid email format`
- Missing email → `400 Email required`
- Wrong verification code → `401 Invalid or expired code`

**Full auth flow — VERIFIED:**
- Enrolled test user `abhishek@opslane.com` in D1
- `POST /verify/request` → email sent via Resend
- `POST /verify/confirm` with 6-digit code → JWT issued (RS256, kid=v1, iss/aud/exp claims)
- Browser flow: email → code → authenticated → lesson list

**Bug found and fixed (commit ab69351):**
1. **Resend API key invalid in Worker** — `echo` piped a trailing newline into `wrangler secret put`. Fix: re-set with `printf '%s'`. Also added error detail logging to the Worker for Resend failures.

### Phase 3: Ship — NOT YET STARTED (Tasks 10–13)

---

## Execution Notes

**TDD Trade-off:** This plan ports an existing working system (Python/Docker → Node.js). Most tasks prioritize "compile and verify" over strict TDD because the behavior is already well-defined by the existing backend. Where tests add value (verification engine edge cases, auth flow), they should be added alongside the implementation.

**Cross-Platform Risk:** Tasks 2 (node-pty) and 3 (verification engine) are the highest-risk for cross-platform issues. Run the smoke test in Task 2 Step 5 on all target platforms early.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-02-06-desktop-distribution-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Uses `superpowers:subagent-driven-development`.

**2. Parallel Session (separate)** — Open a new session in this worktree and invoke `superpowers:executing-plans` to batch-execute with checkpoints.

Which approach?
