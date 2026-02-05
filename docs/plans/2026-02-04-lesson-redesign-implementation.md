# Lesson Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the course from 9 lessons to 11, adding CLAUDE.md and Read/Edit/Verify lessons, renumbering existing lessons, and updating all content.

**Architecture:** Directory-based lesson system where the backend matches levels by `{XX}-` prefix on directory names. Each level has a `lesson.yaml` and an `exercise/` directory. Renumbering means renaming directories AND updating the `number` field in each YAML.

**Tech Stack:** YAML lesson files, Python exercise files, SQLite database, shell scripts

---

### Task 1: Rename existing lesson directories (02-09 → 04-11)

Rename in reverse order to avoid collisions. The backend finds lessons by directory prefix (`{XX}-*`), so renaming directories changes lesson numbers.

**Files:**
- Rename: `levels/09-worktrees/` → `levels/11-worktrees/`
- Rename: `levels/08-hooks/` → `levels/10-hooks/`
- Rename: `levels/07-plugins/` → `levels/09-plugins/`
- Rename: `levels/06-mcp-servers/` → `levels/08-mcp-servers/`
- Rename: `levels/05-skills/` → `levels/07-skills/`
- Rename: `levels/04-sub-agents/` → `levels/06-sub-agents/`
- Rename: `levels/03-spec-driven/` → `levels/05-spec-driven/`
- Rename: `levels/02-planning-mode/` → `levels/04-planning-mode/`

**Step 1: Rename directories in reverse order**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels
mv 09-worktrees 11-worktrees
mv 08-hooks 10-hooks
mv 07-plugins 09-plugins
mv 06-mcp-servers 08-mcp-servers
mv 05-skills 07-skills
mv 04-sub-agents 06-sub-agents
mv 03-spec-driven 05-spec-driven
mv 02-planning-mode 04-planning-mode
```

**Step 2: Verify directories exist with correct numbering**

```bash
ls -d levels/*/
```

Expected: `01-context-is-everything/`, `04-planning-mode/`, `05-spec-driven/`, `06-sub-agents/`, `07-skills/`, `08-mcp-servers/`, `09-plugins/`, `10-hooks/`, `11-worktrees/` (gaps at 02, 03 are expected — we create those next)

**Step 3: Commit**

```bash
git add levels/
git commit -m "refactor: renumber lesson directories 02-09 → 04-11"
```

---

### Task 2: Update lesson.yaml number fields for renamed lessons

Each renamed lesson still has the old `number:` field. Update to match new directory prefix.

**Files:**
- Modify: `levels/04-planning-mode/lesson.yaml` — `number: 2` → `number: 4`
- Modify: `levels/05-spec-driven/lesson.yaml` — `number: 3` → `number: 5`
- Modify: `levels/06-sub-agents/lesson.yaml` — `number: 4` → `number: 6`
- Modify: `levels/07-skills/lesson.yaml` — `number: 5` → `number: 7`
- Modify: `levels/08-mcp-servers/lesson.yaml` — `number: 6` → `number: 8`
- Modify: `levels/09-plugins/lesson.yaml` — `number: 7` → `number: 9`
- Modify: `levels/10-hooks/lesson.yaml` — `number: 8` → `number: 10`
- Modify: `levels/11-worktrees/lesson.yaml` — `number: 9` → `number: 11`

**Step 1: Update each file**

In `levels/04-planning-mode/lesson.yaml`, change:
```yaml
number: 2
```
to:
```yaml
number: 4
```

In `levels/05-spec-driven/lesson.yaml`, change:
```yaml
number: 3
```
to:
```yaml
number: 5
```

In `levels/06-sub-agents/lesson.yaml`, change:
```yaml
number: 4
```
to:
```yaml
number: 6
```

In `levels/07-skills/lesson.yaml`, change:
```yaml
number: 5
```
to:
```yaml
number: 7
```

In `levels/08-mcp-servers/lesson.yaml`, change:
```yaml
number: 6
```
to:
```yaml
number: 8
```

In `levels/09-plugins/lesson.yaml`, change:
```yaml
number: 7
```
to:
```yaml
number: 9
```

In `levels/10-hooks/lesson.yaml`, change:
```yaml
number: 8
```
to:
```yaml
number: 10
```

In `levels/11-worktrees/lesson.yaml`, change:
```yaml
number: 9
```
to:
```yaml
number: 11
```

**Step 2: Verify all number fields match directory prefixes**

```bash
for f in levels/*/lesson.yaml; do echo "$(dirname $f | xargs basename): $(grep '^number:' $f)"; done
```

Expected: Each directory prefix matches its `number:` value.

**Step 3: Commit**

```bash
git add levels/*/lesson.yaml
git commit -m "refactor: update lesson number fields to match new directory numbering"
```

---

### Task 3: Update Lesson 11 (Worktrees) success message

The capstone success message lists all 9 old lessons. Update it to list all 11 new lessons.

**Files:**
- Modify: `levels/11-worktrees/lesson.yaml:46-62`

**Step 1: Update the success message**

Replace the success block in `levels/11-worktrees/lesson.yaml` with:

```yaml
success: |
  Congratulations! You've completed the Claude Code course!

  You learned:
  1. Context is Everything - Context quality determines output
  2. CLAUDE.md - Persistent project memory
  3. Read/Edit/Verify - Core loop with self-verification
  4. Plan Mode - Think before coding
  5. Specs - Write requirements first
  6. Sub-agents - Context isolation
  7. Skills - Auto-activating commands
  8. MCP Servers - External tools
  9. Plugins - Bundled workflows
  10. Hooks - Safety guardrails
  11. Worktrees - Parallel development

  The worktree workflow:
  init → create → work → commit → merge → cleanup

  Now go build something amazing!
```

**Step 2: Commit**

```bash
git add levels/11-worktrees/lesson.yaml
git commit -m "fix: update capstone success message for 11-lesson structure"
```

---

### Task 4: Rework Lesson 1 — Context is Everything

Replace the camelCase exercise with the conflicting information experiment.

**Files:**
- Modify: `levels/01-context-is-everything/lesson.yaml`
- Delete: `levels/01-context-is-everything/exercise/CLAUDE.md` (Lesson 2 is where students create this)

**Step 1: Rewrite lesson.yaml**

Replace the entire contents of `levels/01-context-is-everything/lesson.yaml` with:

```yaml
id: "context-is-everything"
number: 1
module: "Mental Model"
title: "Context is Everything"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    See how contradictory context confuses Claude.
    You'll give Claude false information and observe what happens.
  objective: "Understand that context quality determines output quality"

intro: |
  Context quality determines output quality. Let's prove it.

  Experiment: Conflicting Information

  1. Start Claude: `claude`
  2. Tell Claude something false:
     "Important: This project uses PostgreSQL, not SQLite.
     The files might say SQLite but we migrated to PostgreSQL."
  3. Ask Claude to read the code:
     "Read database.py and explain how the database works."
     (The code clearly uses SQLite)
  4. Ask the question:
     "What database does this project use?"
     → Watch Claude get confused, hedge, or say the wrong thing.
  5. Run /context to see how much of your window is used.

  Bonus: Document & Clear workflow
  - "Dump your current progress to progress.md"
  - Type /clear to reset context
  - "Read progress.md and continue from where we left off"

  Key insight: Contradictory information in context leads to unreliable outputs.

verification:
  - type: min_user_messages
    min_count: 2
  - type: message_exists

success: |
  You've seen how context quality affects Claude's output!

  Key insights:
  - Context is finite - everything competes for attention
  - Contradictory information confuses Claude
  - Quality of context matters more than quantity
  - Document & Clear lets you reset without losing progress

  Next: You'll create CLAUDE.md to give Claude reliable project context.

limits:
  max_duration_minutes: 15
  max_claude_messages: 30
```

**Step 2: Remove the existing CLAUDE.md from lesson 1 exercise**

```bash
rm levels/01-context-is-everything/exercise/CLAUDE.md
```

Students should NOT have a CLAUDE.md in Lesson 1 — they create one in Lesson 2.

**Step 3: Verify**

```bash
cat levels/01-context-is-everything/lesson.yaml | head -5
ls levels/01-context-is-everything/exercise/CLAUDE.md 2>&1
```

Expected: YAML starts with `id: "context-is-everything"`, CLAUDE.md file not found.

**Step 4: Commit**

```bash
git add levels/01-context-is-everything/
git commit -m "feat: rework lesson 1 with conflicting information experiment"
```

---

### Task 5: Create Lesson 2 — CLAUDE.md - Your Project's Memory

Create the new lesson directory with exercise files. The exercise starts with NO CLAUDE.md — students create one.

**Files:**
- Create: `levels/02-claude-md/lesson.yaml`
- Create: `levels/02-claude-md/exercise/` — copy from lesson 1 exercise (same expense tracker, minus CLAUDE.md and historical_data)

**Step 1: Create directory structure**

```bash
mkdir -p levels/02-claude-md/exercise
```

**Step 2: Copy exercise files from lesson 1 (without CLAUDE.md or historical_data)**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game
cp levels/01-context-is-everything/exercise/database.py levels/02-claude-md/exercise/
cp levels/01-context-is-everything/exercise/main.py levels/02-claude-md/exercise/
cp levels/01-context-is-everything/exercise/models.py levels/02-claude-md/exercise/
cp levels/01-context-is-everything/exercise/pyproject.toml levels/02-claude-md/exercise/
cp levels/01-context-is-everything/exercise/README.md levels/02-claude-md/exercise/
cp levels/01-context-is-everything/exercise/reports.py levels/02-claude-md/exercise/
cp levels/01-context-is-everything/exercise/seed_data.py levels/02-claude-md/exercise/
cp levels/01-context-is-everything/exercise/utils.py levels/02-claude-md/exercise/
cp -r levels/01-context-is-everything/exercise/data levels/02-claude-md/exercise/
cp -r levels/01-context-is-everything/exercise/tests levels/02-claude-md/exercise/
```

**Step 3: Create lesson.yaml**

Write `levels/02-claude-md/lesson.yaml`:

```yaml
id: "claude-md"
number: 2
module: "Mental Model"
title: "CLAUDE.md - Your Project's Memory"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Claude doesn't know your project yet. Create CLAUDE.md to fix that.
  objective: "Create a CLAUDE.md that gives Claude persistent project context"

intro: |
  Claude has zero memory between sessions. CLAUDE.md fixes this.

  It's loaded automatically at the start of every session.

  Experiment:

  1. Start Claude: `claude`
  2. Ask: "How do I run the tests for this project?"
     → Claude doesn't know. It has to read files to figure it out.
  3. Now create CLAUDE.md with project context.

     Type: "Create a CLAUDE.md file with:
     - What this project is (1-2 sentences)
     - The tech stack (Python + SQLite)
     - How to run the app: python main.py
     - How to test: pytest -v
     - Code conventions: use type hints, keep functions focused"

  4. Exit Claude (Ctrl+C twice) and start a new session: `claude`
  5. Ask the same question: "How do I run the tests?"
     → Claude knows immediately from CLAUDE.md.

  Important: Keep CLAUDE.md under 40-60 lines.
  Claude's system prompt has ~50 instructions already. Models follow
  about 150-200 total. Every line you add competes for attention.

  Rule of thumb: If Claude can figure it out by reading your code,
  don't put it in CLAUDE.md.

verification:
  - type: file_contains
    description: "Create CLAUDE.md with test instructions"
    path: "CLAUDE.md"
    pattern: "(pytest|test)"

success: |
  You created your project's memory!

  CLAUDE.md best practices:
  - Keep it under 40-60 lines (attention budget)
  - Include: stack, commands, conventions, gotchas
  - Exclude: anything Claude can figure out from code
  - Every "Don't X" should include "Do Y instead"
  - Update it when Claude makes a mistake (self-improvement loop)

  CLAUDE.md is the highest-leverage file in your project.

limits:
  max_duration_minutes: 15
  max_claude_messages: 30
```

**Step 4: Verify**

```bash
ls levels/02-claude-md/exercise/
cat levels/02-claude-md/lesson.yaml | head -5
ls levels/02-claude-md/exercise/CLAUDE.md 2>&1
```

Expected: All exercise files present, YAML starts with `id: "claude-md"`, no CLAUDE.md in exercise dir.

**Step 5: Commit**

```bash
git add levels/02-claude-md/
git commit -m "feat: add lesson 2 - CLAUDE.md Your Project's Memory"
```

---

### Task 6: Create Lesson 3 — Read → Edit → Verify

Create the new lesson directory. Exercise has the negative-amount bug in `models.py` AND a starter CLAUDE.md (from L2) without verification rules — students add those.

**Files:**
- Create: `levels/03-read-edit-verify/lesson.yaml`
- Create: `levels/03-read-edit-verify/exercise/` — copy from lesson 2 exercise + add starter CLAUDE.md

**Step 1: Create directory and copy exercise files**

```bash
mkdir -p levels/03-read-edit-verify/exercise
cd /Users/abhishekray/Projects/opslane/claude-code-game
cp levels/02-claude-md/exercise/database.py levels/03-read-edit-verify/exercise/
cp levels/02-claude-md/exercise/main.py levels/03-read-edit-verify/exercise/
cp levels/02-claude-md/exercise/models.py levels/03-read-edit-verify/exercise/
cp levels/02-claude-md/exercise/pyproject.toml levels/03-read-edit-verify/exercise/
cp levels/02-claude-md/exercise/README.md levels/03-read-edit-verify/exercise/
cp levels/02-claude-md/exercise/reports.py levels/03-read-edit-verify/exercise/
cp levels/02-claude-md/exercise/seed_data.py levels/03-read-edit-verify/exercise/
cp levels/02-claude-md/exercise/utils.py levels/03-read-edit-verify/exercise/
cp -r levels/02-claude-md/exercise/data levels/03-read-edit-verify/exercise/
cp -r levels/02-claude-md/exercise/tests levels/03-read-edit-verify/exercise/
```

**Step 2: Create starter CLAUDE.md (simulating what student built in L2, without verification section)**

Write `levels/03-read-edit-verify/exercise/CLAUDE.md`:

```markdown
# Expense Tracker

A CLI expense tracking application built with Python and SQLite.

## Stack
- Python 3.10+
- SQLite (via stdlib sqlite3)
- pytest for testing

## Commands
- Run app: `python main.py`
- Run tests: `pytest -v`
- Seed data: `python seed_data.py`

## Code Style
- Use type hints for all function parameters and return values
- Keep functions focused and under 50 lines
```

**Step 3: Verify models.py still has the negative-amount bug**

```bash
grep -n "BUG" levels/03-read-edit-verify/exercise/models.py | head -3
```

Expected: Lines showing `BUG: No validation` and `BUG: Should validate amount > 0`.

**Step 4: Create lesson.yaml**

Write `levels/03-read-edit-verify/lesson.yaml`:

```yaml
id: "read-edit-verify"
number: 3
module: "Core Loop"
title: "Read, Edit, Verify"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Fix a real bug and teach Claude to verify its own work.
  objective: "Fix the negative amount bug and add verification rules to CLAUDE.md"

intro: |
  Claude's core loop: Read → Edit → Verify. Let's see it in action.

  The add_expense() function has a bug - it accepts negative amounts.

  1. Start Claude: `claude`
  2. Ask Claude to fix the bug:
     "The add_expense function in models.py allows negative amounts.
     Fix it so amounts must be greater than 0."
  3. Watch Claude read the file, make a surgical edit, and report done.
  4. Now make Claude PROVE it works:
     "Run pytest -v and confirm your fix works."
     → Claude runs tests, sees results, fixes any remaining issues.
  5. Finally, codify verification in CLAUDE.md:
     "Add a Verification section to CLAUDE.md that says:
     after any code change, run pytest -v and fix failing tests.
     All tests must pass before considering a task complete."

  This is the single highest-leverage habit: give Claude a way to
  verify its own work. It 2-3x's the quality of output.

verification:
  - type: file_contains
    description: "Fix negative amount validation"
    path: "models.py"
    pattern: "(amount\\s*<=\\s*0|amount\\s*<\\s*0|ValueError)"
  - type: file_contains
    description: "Add verification rules to CLAUDE.md"
    path: "CLAUDE.md"
    pattern: "(pytest|[Vv]erif)"

success: |
  You experienced the core loop AND taught Claude to verify its work!

  What happened:
  1. Claude READ models.py before editing (never blind edits)
  2. Claude made a SURGICAL edit (not a full rewrite)
  3. Claude VERIFIED by running tests
  4. You codified verification in CLAUDE.md (permanent behavior)

  From now on, Claude will check its own work every session.
  This is the #1 tip from the Claude Code team.

limits:
  max_duration_minutes: 15
  max_claude_messages: 30
```

**Step 5: Verify**

```bash
ls levels/03-read-edit-verify/exercise/
cat levels/03-read-edit-verify/exercise/CLAUDE.md
cat levels/03-read-edit-verify/lesson.yaml | head -5
```

Expected: All exercise files + CLAUDE.md present, CLAUDE.md has no verification section, YAML starts with `id: "read-edit-verify"`.

**Step 6: Commit**

```bash
git add levels/03-read-edit-verify/
git commit -m "feat: add lesson 3 - Read Edit Verify with self-verification"
```

---

### Task 7: Update Lesson 4 (Plan Mode) module name

The module changed from "Planning" to match the new structure. Also update the intro to reference the new lesson numbering.

**Files:**
- Modify: `levels/04-planning-mode/lesson.yaml`

**Step 1: Update module and intro**

In `levels/04-planning-mode/lesson.yaml`, the `module` is already "Planning" which is correct. The `number` was updated in Task 2. Verify the intro doesn't reference old lesson numbers.

Read the file, confirm no references to "Lesson 2" or old numbering. The current intro is self-contained (doesn't reference other lessons), so no changes needed beyond the number update from Task 2.

**Step 2: Verify**

```bash
grep -n 'number:' levels/04-planning-mode/lesson.yaml
```

Expected: `number: 4`

**Step 3: Commit (skip if no changes beyond Task 2)**

No additional commit needed — Task 2 already committed the number change.

---

### Task 8: Update Lesson 6 (Sub-Agents) intro to reference Lesson 1

The design calls for sub-agents to callback to Lesson 1's context lesson. Update the intro.

**Files:**
- Modify: `levels/06-sub-agents/lesson.yaml`

**Step 1: Update intro text**

Replace the `intro:` block in `levels/06-sub-agents/lesson.yaml` with:

```yaml
intro: |
  Sub-agents = fresh context window. Parent gets a clean summary.

  Remember Lesson 1? Context is finite. Sub-agents solve that.

  You want to understand how the reporting module works, but don't
  want all those details filling your main context.

  Type: claude

  First, run /context to see your current context usage.

  Say: "Use a sub-agent to analyze reports.py and summarize how it
  generates reports. I just want a summary, not all the details."

  After getting the summary, run /context again.
  Your main context should barely have moved.
```

**Step 2: Commit**

```bash
git add levels/06-sub-agents/lesson.yaml
git commit -m "feat: update sub-agents lesson to reference lesson 1 context concept"
```

---

### Task 9: Update Lesson 7 (Skills) intro for clarity

Update the skills intro to distinguish from CLAUDE.md (taught in L2).

**Files:**
- Modify: `levels/07-skills/lesson.yaml`

**Step 1: Update intro text**

Replace the `intro:` block in `levels/07-skills/lesson.yaml` with:

```yaml
intro: |
  Skills live in .claude/skills/ and auto-activate based on context.

  CLAUDE.md (Lesson 2) loads every session - it's always-on context.
  Skills load on demand - only when Claude thinks they're relevant.

  Use CLAUDE.md for things that always matter.
  Use skills for workflow-specific instructions.

  Create a code explainer skill:

  Type: claude

  Say: "Create a skill called 'code-explainer' that activates when I ask
  to explain code. It should read the relevant files and explain what
  they do in plain English."

  After creating, test it by asking: "Explain the models.py file"
```

**Step 2: Commit**

```bash
git add levels/07-skills/lesson.yaml
git commit -m "feat: update skills lesson to distinguish from CLAUDE.md"
```

---

### Task 10: Clean up __pycache__ from exercise directories

Several exercise directories have `__pycache__` directories that shouldn't be in source control.

**Files:**
- Delete: `levels/04-planning-mode/exercise/__pycache__/` (if exists)
- Delete: `levels/05-spec-driven/exercise/__pycache__/` (if exists)
- Delete: Any other `__pycache__` dirs in levels/

**Step 1: Find and remove all __pycache__ directories**

```bash
find /Users/abhishekray/Projects/opslane/claude-code-game/levels -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
```

**Step 2: Verify .gitignore covers __pycache__**

```bash
grep "__pycache__" /Users/abhishekray/Projects/opslane/claude-code-game/.gitignore
```

If not present, add it.

**Step 3: Commit**

```bash
git add -A levels/
git commit -m "chore: remove __pycache__ from exercise directories"
```

---

### Task 11: Final verification — all 11 lessons load correctly

Run a check that all lessons have valid YAML and correct numbering.

**Step 1: List all lessons and verify numbering**

```bash
for f in /Users/abhishekray/Projects/opslane/claude-code-game/levels/*/lesson.yaml; do
  dir=$(dirname "$f" | xargs basename)
  num=$(grep '^number:' "$f" | awk '{print $2}')
  id=$(grep '^id:' "$f" | awk '{print $2}')
  title=$(grep '^title:' "$f" | sed 's/^title: //')
  echo "$dir | number=$num | id=$id | $title"
done
```

Expected output (11 lines, sequential numbering):
```
01-context-is-everything | number=1 | id="context-is-everything" | Context is Everything
02-claude-md | number=2 | id="claude-md" | CLAUDE.md - Your Project's Memory
03-read-edit-verify | number=3 | id="read-edit-verify" | Read, Edit, Verify
04-planning-mode | number=4 | id="planning-mode" | Plan Mode for Complex Features
05-spec-driven | number=5 | id="spec-driven" | Spec-Driven Development
06-sub-agents | number=6 | id="sub-agents" | Sub-Agents for Context Isolation
07-skills | number=7 | id="skills" | Skills (Auto-Activating Commands)
08-mcp-servers | number=8 | id="mcp-servers" | MCP Servers for Documentation
09-plugins | number=9 | id="plugins" | Installing Plugins
10-hooks | number=10 | id="hooks" | Safety Hooks
11-worktrees | number=11 | id="worktrees" | Git Worktrees for Parallel Work
```

**Step 2: Verify each exercise directory has core files**

```bash
for d in /Users/abhishekray/Projects/opslane/claude-code-game/levels/*/exercise; do
  dir=$(dirname "$d" | xargs basename)
  files=$(ls "$d"/*.py 2>/dev/null | wc -l)
  echo "$dir: $files Python files"
done
```

Expected: Each lesson has 7-8 Python files.

**Step 3: Verify no CLAUDE.md in lessons 1 or 2 exercises (students create it)**

```bash
ls /Users/abhishekray/Projects/opslane/claude-code-game/levels/01-context-is-everything/exercise/CLAUDE.md 2>&1
ls /Users/abhishekray/Projects/opslane/claude-code-game/levels/02-claude-md/exercise/CLAUDE.md 2>&1
ls /Users/abhishekray/Projects/opslane/claude-code-game/levels/03-read-edit-verify/exercise/CLAUDE.md 2>&1
```

Expected: L1 — not found. L2 — not found. L3 — found (starter CLAUDE.md without verification section).

---

## Task Summary

| Task | Description | Type |
|------|-------------|------|
| 1 | Rename directories 02-09 → 04-11 | Rename |
| 2 | Update number fields in all renamed lesson.yaml files | Edit |
| 3 | Update Lesson 11 capstone success message | Edit |
| 4 | Rework Lesson 1 with conflicting info experiment | Rewrite |
| 5 | Create Lesson 2 — CLAUDE.md | New |
| 6 | Create Lesson 3 — Read/Edit/Verify | New |
| 7 | Verify Lesson 4 (Plan Mode) is correct | Verify |
| 8 | Update Lesson 6 (Sub-Agents) intro | Edit |
| 9 | Update Lesson 7 (Skills) intro | Edit |
| 10 | Clean up __pycache__ directories | Cleanup |
| 11 | Final verification — all 11 lessons correct | Verify |
