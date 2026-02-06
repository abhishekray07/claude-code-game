import { Router, Request, Response } from "express";
import fs from "fs";
import path from "path";
import os from "os";
import jwt from "jsonwebtoken";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(os.homedir(), ".claude-code-game");
const AUTH_FILE = path.join(DATA_DIR, "auth.json");
const KEYS_DIR = path.resolve(__dirname, "../../keys");

// Worker URL — configurable via env
const WORKER_URL = process.env.WORKER_URL || "https://claude-code-game-api.YOUR_SUBDOMAIN.workers.dev";

export const authRouter = Router();

function readAuthFile(): { token: string; email: string; name: string } | null {
  try {
    if (!fs.existsSync(AUTH_FILE)) return null;
    const data = JSON.parse(fs.readFileSync(AUTH_FILE, "utf-8"));
    return data;
  } catch {
    return null;
  }
}

function writeAuthFile(data: { token: string; email: string; name: string }) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  // Write with 0600 permissions on Unix
  fs.writeFileSync(AUTH_FILE, JSON.stringify(data), { mode: 0o600 });
}

function verifyToken(token: string): { valid: boolean; payload?: any } {
  try {
    // Try all public keys in keys/ directory
    if (!fs.existsSync(KEYS_DIR)) return { valid: false };
    const keyFiles = fs.readdirSync(KEYS_DIR).filter(f => f.endsWith(".pem"));
    for (const keyFile of keyFiles) {
      try {
        const publicKey = fs.readFileSync(path.join(KEYS_DIR, keyFile), "utf-8");
        const payload = jwt.verify(token, publicKey, {
          algorithms: ["RS256"],
          issuer: "claude-code-game-worker",
          audience: "claude-code-game-local",
        });
        return { valid: true, payload };
      } catch {
        continue;
      }
    }
    return { valid: false };
  } catch {
    return { valid: false };
  }
}

// GET /api/auth/status — check if user has valid local token
authRouter.get("/api/auth/status", (_req: Request, res: Response) => {
  const auth = readAuthFile();
  if (!auth) {
    res.json({ authenticated: false });
    return;
  }
  const { valid, payload } = verifyToken(auth.token);
  if (!valid) {
    res.json({ authenticated: false });
    return;
  }
  res.json({ authenticated: true, token: auth.token, email: payload.sub, name: payload.name });
});

// POST /api/auth/request — proxy to Worker
authRouter.post("/api/auth/request", async (req: Request, res: Response) => {
  try {
    const workerRes = await fetch(`${WORKER_URL}/verify/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await workerRes.json() as Record<string, any>;
    res.status(workerRes.status).json(data);
  } catch (err: any) {
    res.status(503).json({ error: "Auth service unavailable. Try guest mode." });
  }
});

// POST /api/auth/confirm — proxy to Worker, store token locally
authRouter.post("/api/auth/confirm", async (req: Request, res: Response) => {
  try {
    const workerRes = await fetch(`${WORKER_URL}/verify/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await workerRes.json() as Record<string, any>;
    if (workerRes.ok && data.token) {
      writeAuthFile({ token: data.token, email: data.email, name: data.name });
    }
    res.status(workerRes.status).json(data);
  } catch (err: any) {
    res.status(503).json({ error: "Auth service unavailable. Try guest mode." });
  }
});

// POST /api/auth/logout — delete local auth file
authRouter.post("/api/auth/logout", (_req: Request, res: Response) => {
  try {
    if (fs.existsSync(AUTH_FILE)) fs.unlinkSync(AUTH_FILE);
  } catch {}
  res.json({ ok: true });
});

// GET /api/leaderboard — proxy to Worker
authRouter.get("/api/leaderboard", async (_req: Request, res: Response) => {
  try {
    const workerRes = await fetch(`${WORKER_URL}/leaderboard`);
    const data = await workerRes.json();
    res.status(workerRes.status).json(data);
  } catch {
    res.json([]); // Return empty if Worker is unreachable
  }
});
