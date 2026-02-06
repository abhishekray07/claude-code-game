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
import { VerificationEngine } from "../verification.js";
import type { IPty } from "node-pty-prebuilt-multiarch";

const DATA_DIR = path.join(os.homedir(), ".claude-code-game");
const WORKSPACES_DIR = path.join(DATA_DIR, "workspaces");
const LEVELS_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../../levels");

interface Session {
  sessionId: string;
  wsToken: string;
  pty: IPty;
  level: Level;
  levelNumber: number;
  workspaceDir: string;
  completed: boolean;
  lastActivity: number;
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

// Report completion to cloud (fire and forget)
function reportCompletion(levelNumber: number) {
  try {
    const authPath = path.join(os.homedir(), ".claude-code-game", "auth.json");
    if (!fs.existsSync(authPath)) return;
    const auth = JSON.parse(fs.readFileSync(authPath, "utf-8"));
    if (!auth.token) return;
    const workerUrl = process.env.WORKER_URL || "https://claude-code-game-api.YOUR_SUBDOMAIN.workers.dev";
    fetch(`${workerUrl}/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${auth.token}`,
      },
      body: JSON.stringify({ level_number: levelNumber }),
    }).catch(() => {}); // fire and forget
  } catch {}
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
  const { level_number = 1 } = req.body;

  const level = loadLevelByNumber(level_number);
  if (!level) {
    res.status(404).json({ detail: `Level ${level_number} not found` });
    return;
  }

  const sessionId = uuidv4().slice(0, 8);
  const wsToken = crypto.randomBytes(16).toString("hex");
  const workspaceDir = path.join(WORKSPACES_DIR, sessionId);
  fs.mkdirSync(workspaceDir, { recursive: true });

  const exerciseDir = getExerciseDir(level_number);
  if (exerciseDir) {
    copyExerciseFiles(exerciseDir, workspaceDir);
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
  const progress = await engine.getProgress(session.level);

  if (progress.completed) {
    session.completed = true;
    reportCompletion(session.levelNumber);
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
    const progress = await engine.getProgress(session.level);
    if (progress.completed) {
      session.completed = true;
      reportCompletion(session.levelNumber);
    }
  }
  res.json({ completed: session.completed });
});

export function getSession(sessionId: string): Session | undefined {
  return sessions.get(sessionId);
}

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
