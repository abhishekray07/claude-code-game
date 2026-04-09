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
import { loadLevelByNumber, Level, WorkspaceSetup } from "./levels.js";
import { VerificationEngine } from "../verification.js";
import type { ProgressResult } from "../verification.js";
import { execFileSync } from "child_process";
import type { IPty } from "node-pty-prebuilt-multiarch";

const DATA_DIR = path.join(os.homedir(), ".claude-code-game");
const WORKSPACES_DIR = path.join(DATA_DIR, "workspaces");
const LEVELS_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../levels");

interface Session {
  sessionId: string;
  wsToken: string;
  pty: IPty;
  level: Level;
  levelNumber: number;
  workspaceDir: string;
  completed: boolean;
  lastActivity: number;
  passedRules: Set<string>;
}

const sessions = new Map<string, Session>();

export const sessionsRouter = Router();

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

function copyExerciseFiles(exerciseDir: string, workspaceDir: string) {
  const entries = fs.readdirSync(exerciseDir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isSymbolicLink()) continue;
    const src = path.join(exerciseDir, entry.name);
    const dest = path.join(workspaceDir, entry.name);
    if (entry.isDirectory()) {
      fs.cpSync(src, dest, { recursive: true });
    } else {
      fs.copyFileSync(src, dest);
    }
  }
}

function runWorkspaceSetup(workspaceDir: string, setup: WorkspaceSetup) {
  if (setup.git_init) {
    try {
      execFileSync("git", ["--version"], { timeout: 5000 });
    } catch {
      throw new Error("Git is required. Install it from https://git-scm.com");
    }
    execFileSync("git", ["init"], { cwd: workspaceDir, timeout: 10000 });
    if (setup.git_config) {
      const ALLOWED_GIT_CONFIG = new Set(["user.name", "user.email"]);
      for (const [key, value] of Object.entries(setup.git_config)) {
        if (!ALLOWED_GIT_CONFIG.has(key)) {
          throw new Error(`Disallowed git config key: ${key}`);
        }
        execFileSync("git", ["config", key, value], { cwd: workspaceDir, timeout: 5000 });
      }
    }
  }

  if (setup.files) {
    for (const file of setup.files) {
      const filePath = safePath(workspaceDir, file.path);
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, file.content);
    }
  }
}


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

process.on("exit", () => {
  for (const [, session] of sessions) {
    try { session.pty.kill(); } catch {}
  }
});

// POST /api/sessions
sessionsRouter.post("/api/sessions", (req: Request, res: Response) => {
  const { level_number = 1, workspace_dir } = req.body;

  const level = loadLevelByNumber(level_number);
  if (!level) {
    res.status(404).json({ detail: `Level ${level_number} not found` });
    return;
  }

  const sessionId = uuidv4().slice(0, 8);
  const wsToken = crypto.randomBytes(16).toString("hex");

  // Reuse existing workspace if provided (for dev testing / resuming)
  const reuseWorkspace = workspace_dir
    ? path.join(WORKSPACES_DIR, path.basename(workspace_dir))
    : null;

  const workspaceDir = reuseWorkspace && fs.existsSync(reuseWorkspace)
    ? reuseWorkspace
    : path.join(WORKSPACES_DIR, sessionId);

  if (!reuseWorkspace || !fs.existsSync(reuseWorkspace)) {
    fs.mkdirSync(workspaceDir, { recursive: true });

    const exerciseDir = getExerciseDir(level_number);
    if (exerciseDir) {
      copyExerciseFiles(exerciseDir, workspaceDir);
    }

    if (level.workspace_setup) {
      try {
        runWorkspaceSetup(workspaceDir, level.workspace_setup);
      } catch (err: any) {
        fs.rmSync(workspaceDir, { recursive: true, force: true });
        res.status(500).json({ detail: err.message });
        return;
      }
    }
  }

  let ptyProcess;
  try {
    ptyProcess = spawnTerminal(workspaceDir);
  } catch (err: any) {
    fs.rmSync(workspaceDir, { recursive: true, force: true });
    res.status(500).json({ detail: `Failed to spawn terminal: ${err.message}` });
    return;
  }

  sessions.set(sessionId, {
    sessionId,
    wsToken,
    pty: ptyProcess,
    level,
    levelNumber: level_number,
    workspaceDir,
    completed: false,
    lastActivity: Date.now(),
    passedRules: new Set(),
  });

  res.json({
    session_id: sessionId,
    ws_token: wsToken,
    status: "ready",
    level: {
      number: level.number,
      title: level.title,
      module: level.module,
      intro: level.intro,
      video: level.video ?? null,
      exercise: level.exercise ?? null,
      steps: level.steps ?? null,
    },
  });
});

// DELETE /api/sessions/:sessionId
sessionsRouter.delete("/api/sessions/:sessionId", (req: Request, res: Response) => {
  const sessionId = req.params.sessionId as string;
  const session = sessions.get(sessionId);
  if (session) {
    session.pty.kill();
    fs.rmSync(session.workspaceDir, { recursive: true, force: true });
    sessions.delete(sessionId);
  }
  res.json({ session_id: sessionId, status: "stopped" });
});

// PATCH /api/sessions/:sessionId/level
sessionsRouter.patch("/api/sessions/:sessionId/level", (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId as string);
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

  session.pty.kill();
  fs.rmSync(session.workspaceDir, { recursive: true, force: true });
  fs.mkdirSync(session.workspaceDir, { recursive: true });
  const exerciseDir = getExerciseDir(level_number);
  if (exerciseDir) {
    copyExerciseFiles(exerciseDir, session.workspaceDir);
  }

  if (level.workspace_setup) {
    try {
      runWorkspaceSetup(session.workspaceDir, level.workspace_setup);
    } catch (err: any) {
      res.status(500).json({ detail: err.message });
      return;
    }
  }

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
      steps: level.steps ?? null,
    },
  });
});

// POST /api/sessions/:sessionId/save-workspace
sessionsRouter.post("/api/sessions/:sessionId/save-workspace", (req: Request, res: Response) => {
  const session = sessions.get(req.params.sessionId as string);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }

  const baseName = "expense-tracker";
  const homeDir = os.homedir();
  let destDir = path.join(homeDir, baseName);
  let suffix = 1;
  while (fs.existsSync(destDir)) {
    suffix++;
    destDir = path.join(homeDir, `${baseName}-${suffix}`);
  }

  try {
    fs.cpSync(session.workspaceDir, destDir, { recursive: true });
    res.json({ saved: true, path: destDir });
  } catch (err: any) {
    res.status(500).json({ detail: `Failed to save workspace: ${err.message}` });
  }
});

function applyStickyProgress(progress: ProgressResult, session: Session): void {
  // For step-based lessons, make passed rules sticky per session
  if (progress.steps) {
    for (const step of progress.steps) {
      for (let i = 0; i < step.rules.length; i++) {
        const key = `${step.id}:${step.rules[i].type}:${step.rules[i].description || i}`;
        if (step.rules[i].passed) {
          session.passedRules.add(key);
        } else if (session.passedRules.has(key)) {
          step.rules[i].passed = true;
        }
      }
      step.passed_count = step.rules.filter((r) => r.passed).length;
      step.passed = step.rules.every((r) => r.passed);
    }
    // Recompute top-level fields
    const allRules = progress.steps.flatMap((s) => s.rules);
    progress.passed_count = allRules.filter((r) => r.passed).length;
    progress.completed = progress.steps.every((s) => s.passed);
    // Recompute current_step
    let currentStep = progress.steps.length;
    for (let i = 0; i < progress.steps.length; i++) {
      if (!progress.steps[i].passed) {
        currentStep = i;
        break;
      }
    }
    progress.current_step = currentStep;
  } else {
    // Flat lessons: make rules sticky too
    for (let i = 0; i < progress.rules.length; i++) {
      const key = `flat:${progress.rules[i].type}:${progress.rules[i].description || i}`;
      if (progress.rules[i].passed) {
        session.passedRules.add(key);
      } else if (session.passedRules.has(key)) {
        progress.rules[i].passed = true;
      }
    }
    progress.passed_count = progress.rules.filter((r) => r.passed).length;
    progress.completed = progress.rules.every((r) => r.passed);
  }
}

// GET /api/sessions/:sessionId/progress
sessionsRouter.get("/api/sessions/:sessionId/progress", async (req: Request, res: Response) => {
  const sessionId = req.params.sessionId as string;
  const session = sessions.get(sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }
  session.lastActivity = Date.now();
  const engine = new VerificationEngine(session.workspaceDir);

  const progress = (session.level.steps && session.level.steps.length > 0)
    ? await engine.getSteppedProgress(session.level)
    : await engine.getProgress(session.level);

  applyStickyProgress(progress, session);

  if (progress.completed && !session.completed) {
    session.completed = true;
  }

  res.json({
    session_id: session.sessionId,
    level_number: session.levelNumber,
    completed: session.completed,
    progress,
  });
});

// GET /api/sessions/:sessionId/status
sessionsRouter.get("/api/sessions/:sessionId/status", async (req: Request, res: Response) => {
  const sessionId = req.params.sessionId as string;
  const session = sessions.get(sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }
  session.lastActivity = Date.now();
  if (!session.completed) {
    const engine = new VerificationEngine(session.workspaceDir);
    const progress = (session.level.steps && session.level.steps.length > 0)
      ? await engine.getSteppedProgress(session.level)
      : await engine.getProgress(session.level);
    applyStickyProgress(progress, session);
    if (progress.completed) {
      session.completed = true;
    }
  }
  res.json({ completed: session.completed });
});

// WebSocket setup
export function setupWebSocket(server: Server) {
  const wss = new WebSocketServer({ noServer: true });

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

    const intro = session.level.intro;
    ws.send("\x1b[2J\x1b[H");
    ws.send("\r\n");
    for (const line of intro.split("\n")) {
      ws.send(line + "\r\n");
    }
    ws.send("\r\n");
    ws.send("\x1b[90m" + "\u2500".repeat(60) + "\x1b[0m\r\n");
    ws.send("\r\n");

    session.pty.onData((data: string) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    // Trigger a fresh prompt — the original was emitted before WS connected
    session.pty.write("\n");

    ws.on("message", (data: Buffer | string) => {
      const text = typeof data === "string" ? data : data.toString("utf-8");
      session.lastActivity = Date.now();

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

      session.pty.write(text);
    });

    ws.on("close", () => {
      // Session stays alive — user might reconnect
    });
  });
}
