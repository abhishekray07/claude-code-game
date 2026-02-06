#!/usr/bin/env node
import { startServer } from "./server.js";
import open from "open";
import fs from "fs";

const args = process.argv.slice(2);
const noOpen = args.includes("--no-open");
const portFlag = args.indexOf("--port");
const requestedPort = portFlag !== -1 ? parseInt(args[portFlag + 1], 10) : 3000;

// Detect WSL — auto-open doesn't work there
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
