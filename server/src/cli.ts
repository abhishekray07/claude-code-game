#!/usr/bin/env node
import { startServer } from "./server.js";
import open from "open";
import fs from "fs";

const args = process.argv.slice(2);
const noOpen = args.includes("--no-open");
const portFlag = args.indexOf("--port");
const preferredPort = portFlag !== -1 ? parseInt(args[portFlag + 1], 10) : 3000;

// Detect WSL — auto-open doesn't work there
function isWSL(): boolean {
  try {
    return fs.readFileSync("/proc/version", "utf-8").toLowerCase().includes("microsoft");
  } catch {
    return false;
  }
}

async function tryStart(port: number): Promise<number> {
  try {
    return await startServer(port);
  } catch (err: any) {
    if (err.code === "EADDRINUSE") {
      throw err;
    }
    throw err;
  }
}

async function main() {
  console.log("Starting Claude Code Game...");

  let actualPort: number;
  try {
    // Try preferred port first
    actualPort = await tryStart(preferredPort);
  } catch (err: any) {
    if (err.code === "EADDRINUSE") {
      console.log(`Port ${preferredPort} is in use, finding an available port...`);
      // Let the OS assign a free port
      actualPort = await tryStart(0);
    } else {
      throw err;
    }
  }

  const url = `http://127.0.0.1:${actualPort}`;
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
