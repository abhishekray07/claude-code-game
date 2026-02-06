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
