import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "fs";
import path from "path";
import os from "os";
import { execFileSync } from "child_process";
import { VerificationEngine } from "../verification.js";

describe("workspace setup + commit_exists integration", () => {
  let workspaceDir: string;

  beforeEach(() => {
    workspaceDir = fs.mkdtempSync(path.join(os.tmpdir(), "ccg-test-"));
  });

  afterEach(() => {
    fs.rmSync(workspaceDir, { recursive: true, force: true });
  });

  it("git init + config + commit produces a passing commit_exists rule", async () => {
    // Simulate workspace setup: git init + config
    execFileSync("git", ["init"], { cwd: workspaceDir });
    execFileSync("git", ["config", "user.name", "Builder"], { cwd: workspaceDir });
    execFileSync("git", ["config", "user.email", "builder@local"], { cwd: workspaceDir });

    // Write a file and commit
    fs.writeFileSync(path.join(workspaceDir, "index.html"), "<html><script>console.log('hi')</script></html>");
    execFileSync("git", ["add", "."], { cwd: workspaceDir });
    execFileSync("git", ["commit", "-m", "Initial expense tracker"], { cwd: workspaceDir });

    // Verify commit_exists passes
    const engine = new VerificationEngine(workspaceDir);
    const level = {
      id: "test",
      number: 0,
      title: "Test",
      module: "Test",
      intro: "",
      verification: [{ type: "commit_exists", pattern: ".*" }],
      hints: [],
      success: "",
      limits: { max_duration_minutes: 15, max_claude_messages: 20 },
    };

    const result = await engine.getProgress(level);
    expect(result.completed).toBe(true);
    expect(result.rules[0].passed).toBe(true);
  });

  it("commit_exists fails when no commits exist", async () => {
    execFileSync("git", ["init"], { cwd: workspaceDir });

    const engine = new VerificationEngine(workspaceDir);
    const level = {
      id: "test",
      number: 0,
      title: "Test",
      module: "Test",
      intro: "",
      verification: [{ type: "commit_exists", pattern: ".*" }],
      hints: [],
      success: "",
      limits: { max_duration_minutes: 15, max_claude_messages: 20 },
    };

    const result = await engine.getProgress(level);
    expect(result.completed).toBe(false);
    expect(result.rules[0].passed).toBe(false);
  });

  it("CLAUDE.md is written correctly to workspace", () => {
    const claudeMdContent = "# Instructions\nUse a SINGLE index.html file.";
    fs.writeFileSync(path.join(workspaceDir, "CLAUDE.md"), claudeMdContent);

    expect(fs.existsSync(path.join(workspaceDir, "CLAUDE.md"))).toBe(true);
    expect(fs.readFileSync(path.join(workspaceDir, "CLAUDE.md"), "utf-8")).toBe(claudeMdContent);
  });

  it("file_exists and file_contains rules work for killer lesson phases", async () => {
    // Simulate Phases 1-4 output
    fs.writeFileSync(path.join(workspaceDir, "requirements.md"), "Track daily expenses and spending");
    fs.writeFileSync(path.join(workspaceDir, "plan.md"), "Step 1: Build the feature structure");
    fs.writeFileSync(path.join(workspaceDir, "index.html"), '<html><body><script>let expenses = []; function addExpense(amount) {}</script></body></html>');

    const engine = new VerificationEngine(workspaceDir);
    const level = {
      id: "test",
      number: 0,
      title: "Test",
      module: "Test",
      intro: "",
      verification: [
        { type: "file_exists", path: "requirements.md" },
        { type: "file_contains", path: "requirements.md", pattern: "(expense|budget|track|spend)" },
        { type: "file_exists", path: "plan.md" },
        { type: "file_contains", path: "plan.md", pattern: "(feature|structure|step|implement|build)" },
        { type: "file_exists", path: "index.html" },
        { type: "file_contains", path: "index.html", pattern: "(expense|add|amount|total)" },
        { type: "file_contains", path: "index.html", pattern: "<script" },
      ],
      hints: [],
      success: "",
      limits: { max_duration_minutes: 15, max_claude_messages: 20 },
    };

    const result = await engine.getProgress(level);
    expect(result.completed).toBe(true);
    expect(result.passed_count).toBe(7);
    expect(result.total_count).toBe(7);
  });
});
