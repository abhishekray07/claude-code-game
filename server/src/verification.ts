import fs from "fs";
import path from "path";
import os from "os";
import crypto from "crypto";
import { execFile } from "child_process";
import { promisify } from "util";
import type { VerificationRule, Level, Step } from "./routes/levels.js";

const execFileAsync = promisify(execFile);

// Allowlist of safe commands for command_output verification
const ALLOWED_COMMANDS = new Set(["git", "node", "npx", "cat", "ls", "wc", "grep", "test", "head", "tail"]);

export interface StepProgress {
  id: string;
  name: string;
  subtitle: string;
  passed: boolean;
  rules: Array<{
    type: string;
    passed: boolean;
    description?: string;
  }>;
  passed_count: number;
  total_count: number;
}

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
  steps?: StepProgress[];
  current_step?: number;
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

  async getSteppedProgress(level: Level): Promise<ProgressResult> {
    if (!level.steps || level.steps.length === 0) {
      return this.getProgress(level);
    }

    const steps: StepProgress[] = [];
    let currentStep = 0;
    let foundIncomplete = false;

    for (let i = 0; i < level.steps.length; i++) {
      const step = level.steps[i];
      const ruleResults = [];

      for (const rule of step.verification) {
        const passed = await this.checkRule(rule);
        ruleResults.push({
          type: rule.type,
          passed,
          description: rule.description,
        });
      }

      const stepPassed = ruleResults.every((r) => r.passed);
      steps.push({
        id: step.id,
        name: step.name,
        subtitle: step.subtitle,
        passed: stepPassed,
        rules: ruleResults,
        passed_count: ruleResults.filter((r) => r.passed).length,
        total_count: ruleResults.length,
      });

      if (!stepPassed && !foundIncomplete) {
        currentStep = i;
        foundIncomplete = true;
      }
    }

    // Past-the-end sentinel when all steps complete
    if (!foundIncomplete) {
      currentStep = level.steps.length;
    }

    const allRules = steps.flatMap((s) =>
      s.rules.map((r) => ({ ...r, tool_name: undefined, path: undefined }))
    );

    return {
      rules: allRules,
      completed: steps.every((s) => s.passed),
      passed_count: allRules.filter((r) => r.passed).length,
      total_count: allRules.length,
      steps,
      current_step: currentStep,
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
    } catch (err) {
      console.error(`[verification] checkRule ${rule.type} failed:`, err);
      return false;
    }
  }

  // Message log reading — uses sha256 hash of workspace path as primary lookup
  private readMessagesLog(): Array<Record<string, any>> {
    const projectsDir = path.join(os.homedir(), ".claude", "projects");
    if (!fs.existsSync(projectsDir)) return [];

    const absWorkspace = path.resolve(this.workspaceDir);
    const hash = crypto.createHash("sha256").update(absWorkspace).digest("hex").slice(0, 16);
    let projectDir = "";
    const dirs = fs.readdirSync(projectsDir);

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
    return new RegExp(pattern, "i").test(content);
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

  // Allowlisted async command execution
  private async checkCommandOutput(command?: string, expected?: string): Promise<boolean> {
    if (!command) return false;
    try {
      const parts = command.split(/\s+/);
      const cmd = parts[0];
      const args = parts.slice(1);

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
    // Simple glob: convert *pattern* to regex and match against directory entries
    const regexStr = pattern
      .replace(/[.+^${}()|[\]\\]/g, "\\$&")
      .replace(/\*/g, ".*")
      .replace(/\?/g, ".");
    const regex = new RegExp(`^${regexStr}$`, "i");
    try {
      const entries = fs.readdirSync(this.workspaceDir, { recursive: true }) as string[];
      return entries.some((e) => regex.test(path.basename(e)));
    } catch {
      return false;
    }
  }

  private checkHomeGlobExists(pattern?: string): boolean {
    if (!pattern) return false;
    const dir = path.join(os.homedir(), ".claude");
    const regexStr = pattern
      .replace(/[.+^${}()|[\]\\]/g, "\\$&")
      .replace(/\*/g, ".*")
      .replace(/\?/g, ".");
    const regex = new RegExp(`^${regexStr}$`, "i");
    try {
      const entries = fs.readdirSync(dir, { recursive: true }) as string[];
      return entries.some((e) => regex.test(path.basename(e)));
    } catch {
      return false;
    }
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
