import { Router } from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import YAML from "yaml";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LEVELS_DIR = path.resolve(__dirname, "../../levels");

export const levelsRouter = Router();

// Types matching the Python Level model
export interface VerificationRule {
  type: string;
  tool_name?: string;
  min_count?: number;
  path?: string;
  pattern?: string;
  command?: string;
  expected_output?: string;
  description?: string;
}

export interface Hint {
  after_minutes: number;
  text: string;
}

export interface WorkspaceFile {
  path: string;
  content: string;
}

export interface WorkspaceSetup {
  git_init?: boolean;
  git_config?: Record<string, string>;
  files?: WorkspaceFile[];
}

export interface Level {
  id: string;
  number: number;
  title: string;
  module: string;
  intro: string;
  track?: string;
  video?: { url: string; duration_seconds: number };
  exercise?: { intro: string; objective: string };
  verification: VerificationRule[];
  hints: Hint[];
  success: string;
  limits: { max_duration_minutes: number; max_claude_messages: number };
  workspace_setup?: WorkspaceSetup;
}

export function loadLevelByNumber(num: number): Level | null {
  const prefix = String(num).padStart(2, "0");
  const entries = fs.readdirSync(LEVELS_DIR, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && entry.name.startsWith(`${prefix}-`)) {
      const lessonPath = path.join(LEVELS_DIR, entry.name, "lesson.yaml");
      if (fs.existsSync(lessonPath)) {
        const raw = YAML.parse(fs.readFileSync(lessonPath, "utf-8"));
        return parseLevel(raw);
      }
    }
  }
  return null;
}

export function listLevels(): Array<{ id: string; number: number; title: string; module: string; track?: string }> {
  const levels: Array<{ id: string; number: number; title: string; module: string; track?: string }> = [];
  const entries = fs.readdirSync(LEVELS_DIR, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && /^\d{2}-/.test(entry.name)) {
      const lessonPath = path.join(LEVELS_DIR, entry.name, "lesson.yaml");
      if (fs.existsSync(lessonPath)) {
        const raw = YAML.parse(fs.readFileSync(lessonPath, "utf-8"));
        levels.push({ id: raw.id, number: raw.number, title: raw.title, module: raw.module, track: raw.track });
      }
    }
  }
  return levels.sort((a, b) => a.number - b.number);
}

function parseLevel(data: Record<string, any>): Level {
  const level: Level = {
    id: data.id,
    number: data.number,
    title: data.title,
    module: data.module,
    intro: data.intro,
    track: data.track,
    video: data.video ? { url: data.video.url, duration_seconds: data.video.duration_seconds } : undefined,
    exercise: data.exercise ? { intro: data.exercise.intro, objective: data.exercise.objective } : undefined,
    verification: (data.verification || []).map((r: any) => ({
      type: r.type,
      tool_name: r.tool_name,
      min_count: r.min_count,
      path: r.path,
      pattern: r.pattern,
      command: r.command,
      expected_output: r.expected_output,
      description: r.description,
    })),
    hints: (data.hints || []).map((h: any) => ({ after_minutes: h.after_minutes, text: h.text })),
    success: data.success,
    limits: {
      max_duration_minutes: data.limits?.max_duration_minutes ?? 15,
      max_claude_messages: data.limits?.max_claude_messages ?? 20,
    },
  };

  if (data.workspace_setup) {
    level.workspace_setup = {
      git_init: data.workspace_setup.git_init ?? false,
      git_config: data.workspace_setup.git_config,
      files: (data.workspace_setup.files || []).map((f: any) => ({
        path: f.path,
        content: f.content,
      })),
    };
  }

  return level;
}

// GET /api/levels
levelsRouter.get("/api/levels", (_req, res) => {
  res.json(listLevels());
});

// GET /api/levels/:number
levelsRouter.get("/api/levels/:number", (req, res) => {
  const num = parseInt(req.params.number, 10);
  const level = loadLevelByNumber(num);
  if (!level) {
    res.status(404).json({ detail: `Level ${num} not found` });
    return;
  }
  res.json(level);
});
