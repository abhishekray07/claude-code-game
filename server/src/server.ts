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

  app.use((_req, res, next) => {
    const origin = _req.headers.origin || "";
    if (origin.match(/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/)) {
      res.setHeader("Access-Control-Allow-Origin", origin);
      res.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS");
      res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    }
    if (_req.method === "OPTIONS") { res.sendStatus(204); return; }
    next();
  });

  app.use(levelsRouter);
  app.use(sessionsRouter);

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", mode: "local" });
  });

  const frontendDir = path.resolve(__dirname, "../frontend");
  app.use(express.static(frontendDir));
  app.get("/{*splat}", (_req, res) => {
    res.sendFile(path.join(frontendDir, "index.html"));
  });

  return app;
}

export function startServer(port: number, host = "127.0.0.1"): Promise<number> {
  const app = createApp();
  const server = createServer(app);
  setupWebSocket(server);

  return new Promise<number>((resolve, reject) => {
    server.on("error", reject);
    server.listen(port, host, () => {
      const addr = server.address();
      const actualPort = typeof addr === "object" && addr ? addr.port : port;
      resolve(actualPort);
    });
  });
}
