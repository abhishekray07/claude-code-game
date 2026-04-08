# Guided 6-Step Lesson Structure — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure Lesson 0 from a flat checklist into 6 guided steps that teach a professional Claude Code workflow: Define & Plan → Build → Verify → CLAUDE.md → Review → Ship.

**Architecture:** Add a `steps` array to the Level type. Each step has its own verification rules, sidebar content, and guided prompts. The frontend renders a step-based accordion sidebar that auto-advances when a step's rules all pass. The backend returns per-step progress via optional `steps` and `current_step` fields on the existing `ProgressResult`.

**Tech Stack:** TypeScript, React, Express, YAML, node-pty (unchanged)

---

### Task 1: Rewrite lesson.yaml with 6-step structure

**Files:**
- Modify: `server/levels/00-build-expense-tracker/lesson.yaml`

**Step 1: Replace the lesson.yaml with the new 6-step structure**

Note: No `hints` on steps (the guided prompts serve this purpose). No `min_user_messages` on Steps 3/5 (they auto-pass since message count is global).

```yaml
id: "build-expense-tracker"
number: 0
module: "Build"
title: "Build an Expense Tracker"
track: "beginner"

exercise:
  intro: |
    Build a working expense tracker app using Claude Code.
    No coding experience needed — Claude does the coding, you guide the process.
  objective: "Build a working expense tracker app by learning the professional dev workflow"

intro: |
  Zero to working app. You + Claude Code. 6 steps.

  You'll learn the professional workflow: define what to build, plan it,
  code it, verify it works, teach Claude about your project, review
  the code, and ship it.

  Start Claude Code by typing: claude

workspace_setup:
  git_init: true
  git_config:
    user.name: "Builder"
    user.email: "builder@local"

steps:
  - id: "define-and-plan"
    name: "Define & Plan"
    subtitle: "Have a conversation first"
    description: |
      Don't just say "build X." Talk to Claude first —
      ask it to understand what you want before writing code.

      A good conversation up front saves hours of rework.
    guided_prompts:
      - text: "I want to build a simple expense tracker app. Before writing any code, ask me clarifying questions about what I want."
        label: "Start the conversation"
      - text: "Write up the requirements in a file called requirements.md"
        label: "Save the requirements"
      - text: "Now create a build plan in plan.md and wait for my approval before coding"
        label: "Create the plan"
    verification:
      - type: min_user_messages
        min_count: 3
        description: "Have a conversation with Claude"
      - type: file_exists
        path: "requirements.md"
        description: "Requirements doc created"
      - type: file_contains
        path: "requirements.md"
        pattern: "(expense|budget|track|spend|cost)"
        description: "Requirements describe the app"
      - type: file_exists
        path: "plan.md"
        description: "Build plan created"
      - type: file_contains
        path: "plan.md"
        pattern: "(step|task|implement|build|phase|component)"
        description: "Plan has actionable steps"

  - id: "build"
    name: "Build"
    subtitle: "Let Claude implement the plan"
    description: |
      Now let Claude build from the plan. Give it clear
      constraints so it stays focused.

      Watch Claude work — it reads files, edits code,
      and iterates. This is the core loop.
    guided_prompts:
      - text: "Start building the expense tracker based on the plan. Use a single index.html file with inline CSS and JavaScript. No frameworks, no npm, no build tools. Use localStorage for persistence."
        label: "Start building"
    verification:
      - type: file_exists
        path: "index.html"
        description: "App file created"
      - type: file_contains
        path: "index.html"
        pattern: "<script"
        description: "App has JavaScript"
      - type: file_contains
        path: "index.html"
        pattern: "(expense|add|amount|total)"
        description: "App handles expenses"

  - id: "verify"
    name: "Verify"
    subtitle: "Prove it works"
    description: |
      Code that isn't tested is code that might break.
      Ask Claude to prove the app works.

      "It looks right" isn't enough — tests are proof.
    guided_prompts:
      - text: "Open index.html in my browser so I can see the app"
        label: "See the app"
      - text: "Write tests for the core functions. Create a test file that verifies adding expenses, listing them, and calculating totals."
        label: "Write tests"
      - text: "Run the tests and fix any failures"
        label: "Run tests"
    verification:
      - type: glob_exists
        pattern: "test*"
        description: "Test file created"

  - id: "claude-md"
    name: "CLAUDE.md"
    subtitle: "Teach Claude about your project"
    description: |
      CLAUDE.md onboards Claude like a new teammate. It tells
      Claude how to test, where code lives, and what rules
      to follow — so it works effectively every session.
    guided_prompts:
      - text: "How do I run the tests for this project?"
        label: "Ask without CLAUDE.md (notice Claude has to search)"
      - text: "Create a CLAUDE.md file that teaches any developer or AI about this project. Include: what the app does, how to run it, how to test it, the file structure, and the rules (single HTML file, no frameworks, localStorage)."
        label: "Create the project guide"
      - text: "How do I run the tests for this project?"
        label: "Ask again — instant answer this time"
    verification:
      - type: file_exists
        path: "CLAUDE.md"
        description: "Project guide created"
      - type: file_contains
        path: "CLAUDE.md"
        pattern: "(test|verify|run)"
        description: "Explains how to test"
      - type: file_contains
        path: "CLAUDE.md"
        pattern: "(html|index|structure|file)"
        description: "Documents project structure"

  - id: "review"
    name: "Review"
    subtitle: "Quality gates before you're done"
    description: |
      Before shipping, review your work. Ask Claude to look
      at the code with fresh eyes and suggest improvements.

      Quality gates catch problems before users do.
    guided_prompts:
      - text: "Review the code in index.html. Look for bugs, missing edge cases, or things that could be simpler. List what you find."
        label: "Ask for a review"
      - text: "Fix the issues you found"
        label: "Apply fixes"
    verification:
      - type: file_changed
        path: "index.html"
        description: "Code improved after review"

  - id: "ship"
    name: "Ship"
    subtitle: "Commit with confidence"
    description: |
      Save your work. A good commit message is a gift to
      your future self.
    guided_prompts:
      - text: "Commit all the code with a descriptive commit message that explains what we built and how."
        label: "Ship it"
    verification:
      - type: commit_exists
        pattern: ".*"
        description: "Code committed"

success: |
  You just built a real app with AI — and learned the professional workflow!

  Here's what you practiced:
  1. Define & Plan — talked to Claude before coding
  2. Build — let Claude implement from a plan
  3. Verify — proved it works with tests
  4. CLAUDE.md — onboarded Claude to your project
  5. Review — quality-checked before shipping
  6. Ship — committed with a clear message

  This workflow works for any project, not just expense trackers.

limits:
  max_duration_minutes: 45
  max_claude_messages: 80
```

**Step 2: Verify the YAML is valid**

Run: `cd server && node -e "const YAML = require('yaml'); const fs = require('fs'); console.log(JSON.stringify(YAML.parse(fs.readFileSync('levels/00-build-expense-tracker/lesson.yaml', 'utf-8')).steps.length))"`
Expected: `6`

**Step 3: Commit**

```bash
git add server/levels/00-build-expense-tracker/lesson.yaml
git commit -m "feat: rewrite lesson 0 with 6-step guided structure"
```

---

### Task 2: Add Step types, per-step verification, and API changes

**Files:**
- Modify: `server/src/routes/levels.ts` (interfaces and parseLevel)
- Modify: `server/src/verification.ts` (StepProgress, getSteppedProgress)
- Modify: `server/src/routes/sessions.ts` (API responses + progress endpoint)

**Step 1: Add Step-related interfaces to levels.ts**

Add after the `VerificationRule` interface (after line 22):

```typescript
export interface GuidedPrompt {
  text: string;
  label: string;
}

export interface Step {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  guided_prompts: GuidedPrompt[];
  verification: VerificationRule[];
}
```

Add `steps?: Step[];` to the Level interface (after `verification`).

**Step 2: Update `parseLevel` to parse steps**

Add after the `workspace_setup` parsing block (around line 123):

```typescript
if (data.steps) {
  level.steps = data.steps.map((s: any) => ({
    id: s.id,
    name: s.name,
    subtitle: s.subtitle || "",
    description: s.description || "",
    guided_prompts: (s.guided_prompts || []).map((p: any) => ({
      text: p.text,
      label: p.label || "",
    })),
    verification: (s.verification || []).map((r: any) => ({
      type: r.type,
      tool_name: r.tool_name,
      min_count: r.min_count,
      path: r.path,
      pattern: r.pattern,
      command: r.command,
      expected_output: r.expected_output,
      description: r.description,
    })),
  }));
}
```

**Step 3: Add StepProgress and extend ProgressResult in verification.ts**

Add after the `ProgressResult` interface (line 25):

```typescript
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
```

Add optional fields to `ProgressResult`:

```typescript
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
```

**Step 4: Add getSteppedProgress method to VerificationEngine**

Add after `getProgress`:

```typescript
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
```

**Step 5: Update session API responses to include steps**

In `sessions.ts`, add `steps` to the level object in the POST response (line ~193):

```typescript
steps: level.steps ?? null,
```

And in the PATCH response (line ~253):

```typescript
steps: level.steps ?? null,
```

**Step 6: Update the progress API endpoint**

Replace the GET `/progress` endpoint:

```typescript
sessionsRouter.get("/api/sessions/:sessionId/progress", async (req: Request, res: Response) => {
  const sessionId = req.params.sessionId as string;
  const session = sessions.get(sessionId);
  if (!session) {
    res.status(404).json({ detail: "Session not found" });
    return;
  }
  session.lastActivity = Date.now();
  const engine = new VerificationEngine(session.workspaceDir);

  const progress = (session.level.steps && session.level.steps.length > 0)
    ? await engine.getSteppedProgress(session.level)
    : await engine.getProgress(session.level);

  if (progress.completed && !session.completed) {
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
```

**Step 7: Run typecheck**

Run: `cd server && npx tsc --noEmit`
Expected: No errors

**Step 8: Commit**

```bash
git add server/src/routes/levels.ts server/src/verification.ts server/src/routes/sessions.ts
git commit -m "feat: add step types, per-step verification, and stepped progress API"
```

---

### Task 3: Update frontend types and useVerificationProgress hook

**Files:**
- Modify: `frontend/src/hooks/useVerificationProgress.ts`
- Modify: `frontend/src/App.tsx:19-36` (types)

**Step 1: Update useVerificationProgress to handle step data**

Add `StepProgress` interface and update `VerificationProgress` to include optional step fields:

```typescript
interface StepProgress {
  id: string;
  name: string;
  subtitle: string;
  passed: boolean;
  rules: VerificationRule[];
  passed_count: number;
  total_count: number;
}

export interface VerificationProgress {
  rules: VerificationRule[];
  completed: boolean;
  passed_count: number;
  total_count: number;
  steps?: StepProgress[];
  current_step?: number;
}
```

The rest of useVerificationProgress.ts stays the same — no hook logic changes needed, just the types.

**Step 2: Add frontend types for steps in App.tsx**

Add after the existing interfaces (around line 35):

```typescript
interface GuidedPrompt {
  text: string;
  label: string;
}

interface LevelStep {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  guided_prompts: GuidedPrompt[];
}
```

Add to the `Level` interface:

```typescript
steps?: LevelStep[];
```

**Step 3: Run typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/hooks/useVerificationProgress.ts frontend/src/App.tsx
git commit -m "feat: update frontend types for step-based progress"
```

---

### Task 4: Build step-based sidebar UI and update hero copy

**Files:**
- Create: `frontend/src/components/StepSidebar.tsx`
- Modify: `frontend/src/App.tsx` (exercise phase sidebar + hero copy)
- Modify: `frontend/src/App.css` (step styles)

**Step 1: Create StepSidebar component**

Create `frontend/src/components/StepSidebar.tsx`:

```typescript
import type { VerificationProgress } from "../hooks/useVerificationProgress";

interface GuidedPrompt {
  text: string;
  label: string;
}

interface LevelStep {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  guided_prompts: GuidedPrompt[];
}

export function StepSidebar({
  steps,
  verificationProgress,
  levelComplete,
}: {
  steps: LevelStep[];
  verificationProgress: VerificationProgress | null;
  levelComplete: boolean;
}) {
  const currentStep = verificationProgress?.current_step ?? 0;
  const stepProgresses = verificationProgress?.steps ?? [];

  return (
    <div className="step-sidebar">
      {steps.map((step, index) => {
        const stepProgress = stepProgresses[index];
        const isPassed = stepProgress?.passed ?? false;
        const isCurrent = index === currentStep && !levelComplete;
        const isFuture = index > currentStep && !levelComplete;

        return (
          <div
            key={step.id}
            className={`step-item ${isPassed ? "passed" : ""} ${isCurrent ? "current" : ""} ${isFuture ? "future" : ""}`}
          >
            <div className="step-header">
              <span className="step-indicator">
                {isPassed ? "✓" : index + 1}
              </span>
              <div className="step-title">
                <span className="step-name">{step.name}</span>
                {step.subtitle && (
                  <span className="step-subtitle">{step.subtitle}</span>
                )}
              </div>
            </div>

            {isCurrent && (
              <div className="step-body">
                <p className="step-description">{step.description}</p>

                {step.guided_prompts.length > 0 && (
                  <div className="guided-prompts">
                    {step.guided_prompts.map((prompt, pi) => (
                      <div key={pi} className="guided-prompt">
                        <span className="prompt-label">{prompt.label}</span>
                        <code className="prompt-text">{prompt.text}</code>
                      </div>
                    ))}
                  </div>
                )}

                {stepProgress && stepProgress.rules.length > 0 && (
                  <ul className="step-checklist">
                    {stepProgress.rules.map((rule, ri) => (
                      <li key={ri} className={rule.passed ? "passed" : "pending"}>
                        <span className="check-icon">
                          {rule.passed ? "✓" : "○"}
                        </span>
                        <span className="check-label">
                          {rule.description || rule.type.replace(/_/g, " ")}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

**Step 2: Update App.tsx exercise phase sidebar to use StepSidebar**

Add import at top of App.tsx:

```typescript
import { StepSidebar } from "./components/StepSidebar";
import type { VerificationProgress } from "./hooks/useVerificationProgress";
```

Replace the sidebar `<div className="instructions">` content in the exercise phase with:

```typescript
<div className="instructions">
  {/* Step-based sidebar for lessons with steps */}
  {session.level.steps && session.level.steps.length > 0 ? (
    <>
      <StepSidebar
        steps={session.level.steps}
        verificationProgress={verificationProgress}
        levelComplete={levelComplete}
      />

      {verificationProgress && (
        <div className="progress-summary">
          Step {Math.min((verificationProgress.current_step ?? 0) + 1, session.level.steps.length)} of{" "}
          {session.level.steps.length}
        </div>
      )}
    </>
  ) : (
    <>
      {/* Original flat sidebar for non-step lessons */}
      {session.level.intro && (
        <div className="intro" style={{whiteSpace: 'pre-line', marginBottom: '1rem'}}>
          {session.level.intro}
        </div>
      )}
      {session.level.exercise && (
        <p className="objective">
          <strong>Objective:</strong> {session.level.exercise.objective}
        </p>
      )}

      {verificationProgress && verificationProgress.rules.length > 0 && (
        <div className="verification-progress">
          <h4>Progress</h4>
          <ul className="verification-checklist">
            {verificationProgress.rules.map((rule, index) => (
              <li key={index} className={rule.passed ? "passed" : "pending"}>
                <span className="check-icon">
                  {rule.passed ? "✓" : "○"}
                </span>
                <span className="check-label">
                  {getVerificationLabel(rule.type, rule)}
                </span>
              </li>
            ))}
          </ul>
          <div className="progress-summary">
            {verificationProgress.passed_count} of{" "}
            {verificationProgress.total_count} complete
          </div>
        </div>
      )}
    </>
  )}

  {/* Completion message — same for both layouts */}
  {levelComplete && (
    <div className="completion-message">
      {isKillerLesson ? (
        <>
          <p>You built a real app with AI!</p>
          {savedPath ? (
            <p style={{ fontSize: "0.875rem", color: "#4ade80" }}>
              Saved to: {savedPath}
            </p>
          ) : (
            <button
              onClick={saveWorkspace}
              disabled={saving}
              style={{ marginTop: "0.5rem" }}
            >
              {saving ? "Saving..." : "Save my code"}
            </button>
          )}
        </>
      ) : (
        <p>Nice work! You've completed this lesson's objective.</p>
      )}
    </div>
  )}
</div>
```

**Step 3: Update hero screen copy**

Change the hero subtitle from:

```typescript
<p className="subtitle">
  Zero to working app. You + Claude Code. 20 minutes.
</p>
```

To:

```typescript
<p className="subtitle">
  Zero to working app in 6 steps. You + Claude Code.
</p>
```

**Step 4: Add CSS for the step sidebar**

Append to `frontend/src/App.css`:

```css
/* Step-based sidebar */
.step-sidebar {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-item {
  border-left: 3px solid #333;
  padding: 0.5rem 0.75rem;
  transition: all 0.2s ease;
}

.step-item.passed {
  border-left-color: #4ade80;
}

.step-item.current {
  border-left-color: #60a5fa;
  background: rgba(96, 165, 250, 0.08);
}

.step-item.future {
  opacity: 0.5;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.step-indicator {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
  background: #333;
  color: #999;
}

.step-item.passed .step-indicator {
  background: #4ade80;
  color: #000;
}

.step-item.current .step-indicator {
  background: #60a5fa;
  color: #000;
}

.step-title {
  display: flex;
  flex-direction: column;
}

.step-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: #e5e5e5;
}

.step-subtitle {
  font-size: 0.75rem;
  color: #888;
}

.step-item.passed .step-name {
  color: #4ade80;
}

.step-body {
  margin-top: 0.75rem;
  padding-left: 2rem;
}

.step-description {
  font-size: 0.8125rem;
  color: #aaa;
  line-height: 1.5;
  white-space: pre-line;
  margin: 0 0 0.75rem 0;
}

.guided-prompts {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.guided-prompt {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.prompt-label {
  font-size: 0.75rem;
  color: #60a5fa;
  font-weight: 500;
}

.prompt-text {
  font-size: 0.75rem;
  color: #d4d4d4;
  background: rgba(255, 255, 255, 0.05);
  padding: 0.5rem;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
  cursor: text;
  user-select: all;
}

.step-checklist {
  list-style: none;
  padding: 0;
  margin: 0;
}

.step-checklist li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.8125rem;
}

.step-checklist li.passed {
  color: #4ade80;
}

.step-checklist li.pending {
  color: #888;
}

.step-checklist .check-icon {
  font-size: 0.75rem;
  width: 1rem;
  text-align: center;
}
```

**Step 5: Run typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/components/StepSidebar.tsx frontend/src/App.tsx frontend/src/App.css
git commit -m "feat: add step-based sidebar UI with guided prompts"
```

---

### Task 5: Build and verify end-to-end

**Step 1: Typecheck both projects**

Run: `cd server && npx tsc --noEmit && cd ../frontend && npx tsc --noEmit`
Expected: No errors in either

**Step 2: Build both projects**

Run: `cd server && npm run build && cd ../frontend && npm run build`
Expected: Both succeed

**Step 3: Copy frontend build into server and verify package size**

Run: `rm -rf server/frontend && cp -r frontend/dist server/frontend && cd server && npm pack --dry-run 2>&1 | tail -5`
Expected: Package < 5MB

**Step 4: Test locally**

Run: `cd server && npm run dev`
Then open browser, start lesson 0, verify:
- 6 steps appear in sidebar
- Step 1 is expanded with guided prompts and checklist
- Other steps are collapsed and grayed out
- Verification rules update in real-time as user completes tasks
- Steps auto-advance when all rules in current step pass
- "Step N of 6" progress shows at bottom

**Step 5: Verify clean working tree**

```bash
git status
```
Expected: Clean working tree (build artifacts gitignored)
