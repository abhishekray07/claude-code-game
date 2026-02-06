import * as pty from "node-pty-prebuilt-multiarch";
import os from "os";
import path from "path";
import fs from "fs";

export interface TerminalSession {
  ptyProcess: pty.IPty;
  workspaceDir: string;
}

export function spawnTerminal(workspaceDir: string): pty.IPty {
  const isWindows = process.platform === "win32";
  const shell = isWindows ? "powershell.exe" : (process.env.SHELL || "bash");
  const args = isWindows ? [] : ["--norc", "--noprofile", "-i"];

  const env: Record<string, string> = {
    ...process.env as Record<string, string>,
    TERM: "xterm-256color",
    PS1: "\\[\\033[32m\\]claude@game\\[\\033[0m\\]:\\[\\033[34m\\]\\w\\[\\033[0m\\]$ ",
    BASH_SILENCE_DEPRECATION_WARNING: "1",
  };

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
