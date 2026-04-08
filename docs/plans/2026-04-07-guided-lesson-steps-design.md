# Design: Guided 6-Step Lesson Structure

## Problem

The current Lesson 0 (Build an Expense Tracker) works but is too open-ended. Users get a flat checklist (requirements.md exists, plan.md exists, index.html exists, commit exists) with no guardrails or teaching. The verification items are just file-existence checks — they don't guide users through a professional workflow or teach Claude Code concepts.

## Solution

Restructure Lesson 0 into 6 explicit steps that teach a professional development workflow. Each step teaches a first-principles skill for working with Claude Code. Sub-steps start guided (exact prompts to type) and loosen up as the user gains momentum.

```
  DEFINE & PLAN      BUILD           VERIFY         CLAUDE.MD       REVIEW          SHIP
 ┌──────────┐     ┌──────┐       ┌──────┐       ┌──────┐       ┌──────┐       ┌──────┐
 │Converse  │ ──▶ │ Code │ ───▶  │ Test │ ───▶  │Onboard│ ──▶  │  QA  │ ───▶  │  Go  │
 │with Claude│    │ Impl │       │Prove │       │Claude │      │ Gate │       │ Live │
 └──────────┘     └──────┘       └──────┘       └──────┘       └──────┘       └──────┘
```

## Step-by-Step Design

### Step 1: Define & Plan — Have a conversation first

**Key teaching:** Don't just say "build X." Have a back-and-forth conversation with Claude to clarify requirements and create a plan before any code is written.

**Sub-steps:**
1. Start Claude Code by typing `claude` in the terminal
2. **Guided prompt:** "I want to build a simple expense tracker app. Before writing any code, ask me clarifying questions about what I want."
3. Answer Claude's questions (sidebar shows nudges if stuck, e.g., "Tip: think about what features matter most — categories? totals? charts?")
4. **Guided prompt:** "Write up the requirements in a file called requirements.md"
5. **Guided prompt:** "Now create a build plan in plan.md and wait for my approval before coding"
6. Review the plan, suggest changes if desired

**Verification rules:**
- `file_exists: requirements.md` — "Describe what you want"
- `file_contains: requirements.md` — pattern `(expense|budget|track|spend)` — "Requirements mention the app"
- `file_exists: plan.md` — "Create a build plan"
- `file_contains: plan.md` — pattern `(step|task|implement|build|phase)` — "Plan has actionable steps"
- `min_user_messages: 3` — "Have a conversation (at least 3 messages)"

**Sidebar content:**
```
Step 1 of 6: Define & Plan

Talk to Claude before coding. A good conversation
up front saves hours of rework.

💡 Try this prompt:
"I want to build a simple expense tracker app.
Before writing any code, ask me clarifying
questions about what I want."

Then answer Claude's questions and ask it to
write requirements.md and plan.md.
```

---

### Step 2: Build — Let Claude implement the plan

**Key teaching:** Build incrementally, one piece at a time. Let Claude follow the plan it created.

**Sub-steps:**
1. **Guided prompt:** "Start building the expense tracker based on the plan. Use a single index.html file with inline CSS and JavaScript. No frameworks, no npm."
2. Let Claude work — watch it read, edit, and iterate
3. If Claude asks questions, answer them

**Verification rules:**
- `file_exists: index.html` — "App file created"
- `file_contains: index.html` — pattern `<script` — "App has JavaScript"
- `file_contains: index.html` — pattern `(expense|add|amount|total)` — "App handles expenses"

**Sidebar content:**
```
Step 2 of 6: Build

Now let Claude build from the plan. Give it
constraints so it stays focused.

💡 Try this prompt:
"Start building based on the plan. Use a single
index.html file with inline CSS and JavaScript.
No frameworks, no npm."

Watch Claude work — it reads files, edits code,
and iterates. This is the core loop.
```

---

### Step 3: Verify — Prove it works

**Key teaching:** Don't trust that code works — verify it. Ask Claude to test the app and prove it works.

**Sub-steps:**
1. **Guided prompt:** "Open index.html in my browser so I can see the app"
2. Try the app — add an expense, check it shows up
3. **Guided prompt:** "The app looks good. Now write tests to make sure it keeps working. Create a test.html file that tests the core functions."
4. **Guided prompt:** "Run the tests and make sure they all pass"

**Verification rules:**
- `glob_exists: test*` — "Test file created"
- `min_user_messages: 6` — "Guided Claude through verification"

**Sidebar content:**
```
Step 3 of 6: Verify

Code that isn't tested is code that might break.
Ask Claude to prove the app works.

💡 Try this prompt:
"Open index.html in my browser so I can try it."

Then after checking it:
"Write tests for the core functions in a
test.html file, then run them."

Tests are proof. "It looks right" isn't enough.
```

---

### Step 4: CLAUDE.md — Teach Claude about your project

**Key teaching:** CLAUDE.md onboards Claude like a new teammate. It tells Claude how to test, where code lives, and what rules to follow — so it works effectively every session.

**Sub-steps:**
1. **Demonstrate the problem:** "Ask Claude: how do I run the tests for this project?" — Claude doesn't know (it has to search around or guess)
2. **Guided prompt:** "Create a CLAUDE.md file that teaches any new developer (or AI) about this project. Include: what the app does, how to run it, how to test it, the project structure, and any rules (single HTML file, no frameworks)."
3. **Verify:** Ask Claude the same question again — now it gets it right instantly

**Verification rules:**
- `file_exists: CLAUDE.md` — "Created project guide"
- `file_contains: CLAUDE.md` — pattern `(test|verify|run)` — "Explains how to test"
- `file_contains: CLAUDE.md` — pattern `(html|index|structure)` — "Documents project structure"

**Sidebar content:**
```
Step 4 of 6: CLAUDE.md

CLAUDE.md is how you onboard Claude to your
project — like onboarding a new teammate.

💡 First, try asking Claude:
"How do I run the tests for this project?"
(Notice it has to guess or search around.)

Now create the guide:
"Create a CLAUDE.md that explains: what this app
does, how to run it, how to test it, the project
structure, and the rules (single file, no
frameworks)."

Ask the same question again — instant answer.
```

---

### Step 5: Review — Quality gates before you're done

**Key teaching:** Before shipping, review your own work. Ask Claude to look at the code with fresh eyes and suggest improvements.

**Sub-steps:**
1. **Guided prompt:** "Review the code in index.html. Look for bugs, missing edge cases, or things that could be simpler. List what you find."
2. Review Claude's suggestions — pick which ones to fix
3. **Guided prompt:** "Fix the issues you found" (or pick specific ones)

**Verification rules:**
- `min_user_messages: 8` — "Reviewed and improved the code"

**Sidebar content:**
```
Step 5 of 6: Review

Good developers review before they ship. Ask
Claude to look at the code with fresh eyes.

💡 Try this prompt:
"Review index.html for bugs, edge cases, or
things that could be simpler. List what you find."

Then pick which suggestions to apply:
"Fix the issues you found."

Quality gates catch problems before users do.
```

---

### Step 6: Ship — Commit with confidence

**Key teaching:** Save your work with a meaningful commit message. The commit is your save point.

**Sub-steps:**
1. **Guided prompt:** "Commit all the code with a descriptive commit message that explains what we built."
2. Done — celebrate!

**Verification rules:**
- `commit_exists: .*` — "Committed your work"

**Sidebar content:**
```
Step 6 of 6: Ship

Save your work. A good commit message is a
gift to your future self.

💡 Try this prompt:
"Commit all the code with a descriptive message
explaining what we built."

🎉 That's it — you shipped!
```

---

## Changes Required

### 1. lesson.yaml (server/levels/00-build-expense-tracker/)

Complete rewrite. The new format needs:
- `steps` array (new field) with 6 step objects, each containing:
  - `id`, `name`, `description` (sidebar text)
  - `guided_prompts` array (prompts to show the user)
  - `verification` rules (scoped to this step)
  - `hints` (timed nudges if stuck)
- Remove old flat `verification` array
- Remove `workspace_setup.files` (no pre-created CLAUDE.md — user creates it in step 4)
- Keep `workspace_setup.git_init: true`

### 2. Level type + loading (server/src/routes/levels.ts)

- Add `Step` interface with fields: `id`, `name`, `description`, `guided_prompts`, `verification`, `hints`
- Add `steps` array to `Level` interface
- Parse steps from lesson.yaml

### 3. Verification engine (server/src/verification.ts)

- Support step-scoped verification: `getStepProgress(level, stepIndex)` in addition to `getProgress(level)`
- The existing `getProgress` can be composed from step results

### 4. Sessions API (server/src/routes/sessions.ts)

- Add endpoint or extend `/progress` to return per-step progress
- Track current step index per session

### 5. Frontend — App.tsx sidebar

- Replace flat checklist with step-based UI:
  - Show all 6 steps in sidebar (collapsed)
  - Current step expanded with description, guided prompts, and verification checklist
  - Completed steps show checkmark, collapsed
  - Upcoming steps show number, grayed out
- Step auto-advances when all verification rules pass
- Progress bar shows "Step X of 6" instead of "N of M checks"

### 6. Frontend — useVerificationProgress.ts

- Poll per-step progress instead of flat list
- Track `currentStep` state
- Auto-advance logic: when all rules in current step pass, advance to next step

### 7. Remove workspace_setup CLAUDE.md

Currently lesson.yaml pre-creates a CLAUDE.md with project rules. This must be removed because:
- Step 4 teaches the user to create CLAUDE.md themselves
- Pre-creating it defeats the learning objective
- The constraints (single HTML file, no frameworks) are now communicated via the step 2 guided prompt

## What stays the same

- Terminal + WebSocket architecture
- Session lifecycle (create, poll, delete)
- The app being built (expense tracker)
- Auth flow
- Leaderboard
- PTY spawning
- Time limits and message limits
- Git init in workspace setup

## UI Mockup (sidebar)

```
┌─────────────────────────────┐
│ Build an Expense Tracker    │
│                             │
│ ✓ 1. Define & Plan          │
│ ✓ 2. Build                  │
│ ▶ 3. Verify            3/6  │
│ ┌─────────────────────────┐ │
│ │ Code that isn't tested  │ │
│ │ is code that might      │ │
│ │ break. Ask Claude to    │ │
│ │ prove the app works.    │ │
│ │                         │ │
│ │ 💡 Try this prompt:     │ │
│ │ "Open index.html in my  │ │
│ │ browser so I can try    │ │
│ │ it."                    │ │
│ │                         │ │
│ │ ○ Test file created     │ │
│ │ ✓ Guided through verify │ │
│ └─────────────────────────┘ │
│   4. CLAUDE.md              │
│   5. Review                 │
│   6. Ship                   │
│                             │
│ [End Session]               │
└─────────────────────────────┘
```

## Open Questions

1. Should step auto-advance immediately when verification passes, or show a "Continue to next step" button? (Recommend: button, so user can read the success state)
2. Should we keep timed hints per step, or are the guided prompts sufficient? (Recommend: keep hints as fallback after 3-5 minutes per step)
3. Should the intro text change or is the current "Zero to working app" still good? (Recommend: update to mention the 6-step workflow)
