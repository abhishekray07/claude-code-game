# Expense Tracker Course Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update all 12 lesson directories to use the Expense Tracker project with the new curriculum.

**Architecture:** Replace existing todo app exercises with expense tracker. Each lesson gets its own copy of exercise files, with lesson-specific modifications (bugs fixed, features added) based on curriculum progression.

**Tech Stack:** Python 3.10+, SQLite, pytest, existing FastAPI backend, React frontend.

---

## Task 1: Rename Lesson Directories to Match New Curriculum

**Files:**
- Rename: `levels/02-first-bug-fix/` → `levels/02-claude-md/`
- Rename: `levels/03-claude-md/` → `levels/03-read-edit-verify/`
- Rename: `levels/04-monitor-manage/` → `levels/04-debugging/`
- Rename: `levels/07-testing-debugging/` → `levels/07-sub-agents/`
- Rename: `levels/08-git-integration/` → `levels/08-custom-commands/`
- Rename: `levels/10-mcp-servers/` → `levels/10-code-search/`
- Rename: `levels/11-parallel-work/` → `levels/11-code-review/`
- Rename: `levels/12-hooks-safety/` → `levels/12-scale-safety/`

**Step 1: Rename directories**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels

# Create temp to avoid conflicts
mv 02-first-bug-fix 02-claude-md-new
mv 03-claude-md 03-read-edit-verify
mv 02-claude-md-new 02-claude-md

mv 04-monitor-manage 04-debugging
mv 07-testing-debugging 07-sub-agents
mv 08-git-integration 08-custom-commands
mv 10-mcp-servers 10-code-search
mv 11-parallel-work 11-code-review
mv 12-hooks-safety 12-scale-safety
```

**Step 2: Verify directory structure**

Run: `ls -la /Users/abhishekray/Projects/opslane/claude-code-game/levels/`

Expected:
```
01-context-is-everything
02-claude-md
03-read-edit-verify
04-debugging
05-spec-driven
06-planning-mode
07-sub-agents
08-custom-commands
09-skills
10-code-search
11-code-review
12-scale-safety
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: rename lesson directories to match new curriculum"
```

---

## Task 2: Update Lesson 1 - Context is Everything

**Files:**
- Modify: `levels/01-context-is-everything/lesson.yaml`
- Replace: `levels/01-context-is-everything/exercise/*`

**Step 1: Clear old exercise files**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/01-context-is-everything/exercise/*
```

**Step 2: Copy expense tracker files**

```bash
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/exercises/expense-tracker/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/01-context-is-everything/exercise/
```

**Step 3: Seed the database**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/01-context-is-everything/exercise
python seed_data.py
```

**Step 4: Update lesson.yaml**

Replace contents of `levels/01-context-is-everything/lesson.yaml`:

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
    Prove that Claude has no memory with the Secret Phrase Experiment.
    Give Claude a phrase, fill the context, then test recall.
  objective: "Experience context limits firsthand"

intro: |
  LLMs have NO memory. Only what's in the context window matters.

  Let's prove it with an experiment:

  1. Tell Claude a secret phrase: PURPLE_ELEPHANT_42
  2. Ask Claude to read every file in the project
  3. Ask Claude to recall the phrase

  Type: claude

  Then say: "Remember this secret phrase for later: PURPLE_ELEPHANT_42.
  I'll ask about it at the end. Now, what does this expense tracker do?"

verification:
  - type: message_exists
  - type: tool_called
    tool_name: Read

hints:
  - after_minutes: 2
    text: "Start with: 'Remember this secret phrase: PURPLE_ELEPHANT_42'"
  - after_minutes: 5
    text: "Ask Claude to read ALL Python files, then ask for the secret phrase"

success: |
  You experienced context limits!

  If Claude struggled to recall the phrase after reading many files,
  you witnessed "lost in the middle" - early context gets buried.

  Key insight: Context is finite. Manage it intentionally.

limits:
  max_duration_minutes: 15
  max_claude_messages: 25
```

**Step 5: Verify lesson loads**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/backend
python -c "from app.services.levels import load_level; l = load_level(1); print(f'Loaded: {l.title}')"
```

Expected: `Loaded: Context is Everything`

**Step 6: Commit**

```bash
git add levels/01-context-is-everything/
git commit -m "feat(lesson-1): context experiment with expense tracker"
```

---

## Task 3: Update Lesson 2 - CLAUDE.md

**Files:**
- Modify: `levels/02-claude-md/lesson.yaml`
- Replace: `levels/02-claude-md/exercise/*`

**Step 1: Clear and copy exercise files**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/02-claude-md/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/exercises/expense-tracker/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/02-claude-md/exercise/
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/02-claude-md/exercise && python seed_data.py
```

**Step 2: Update lesson.yaml**

Replace contents of `levels/02-claude-md/lesson.yaml`:

```yaml
id: "claude-md"
number: 2
module: "Mental Model"
title: "CLAUDE.md - Your Project's Memory"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 240

exercise:
  intro: |
    Claude doesn't know your project conventions.
    Create a CLAUDE.md file to give it persistent memory.
  objective: "Create a CLAUDE.md file with project context"

intro: |
  CLAUDE.md is read at the start of every session.

  It's high-leverage: one line here affects every interaction.

  This project has no CLAUDE.md. Create one with:
  - Project description (1-2 sentences)
  - How to run: python main.py
  - How to test: pytest
  - Code style preferences

  Type: claude

  Say: "Create a CLAUDE.md file for this expense tracker project"

verification:
  - type: file_exists
    path: CLAUDE.md
  - type: file_contains
    path: CLAUDE.md
    pattern: "(pytest|python|expense)"

hints:
  - after_minutes: 2
    text: "Ask Claude: 'Create a CLAUDE.md for this project'"
  - after_minutes: 4
    text: "Include: how to run, how to test, code style"

success: |
  Your project now has persistent memory!

  Start a new Claude session and it will automatically know
  about the expense tracker without you explaining anything.

  CLAUDE.md is high-leverage context.

limits:
  max_duration_minutes: 10
  max_claude_messages: 15
```

**Step 3: Commit**

```bash
git add levels/02-claude-md/
git commit -m "feat(lesson-2): CLAUDE.md creation exercise"
```

---

## Task 4: Update Lesson 3 - Read → Edit → Verify

**Files:**
- Modify: `levels/03-read-edit-verify/lesson.yaml`
- Replace: `levels/03-read-edit-verify/exercise/*`

**Step 1: Clear and copy exercise files**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/03-read-edit-verify/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/exercises/expense-tracker/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/03-read-edit-verify/exercise/
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/03-read-edit-verify/exercise && python seed_data.py
```

**Step 2: Verify bug exists**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/03-read-edit-verify/exercise
python -c "from models import add_expense; e = add_expense(-50, 'Food', 'Negative'); print(f'Bug exists: {e.amount}')"
```

Expected: `Bug exists: -50.0` (bug allows negative amounts)

**Step 3: Update lesson.yaml**

Replace contents of `levels/03-read-edit-verify/lesson.yaml`:

```yaml
id: "read-edit-verify"
number: 3
module: "Core Loop"
title: "Read → Edit → Verify"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    The expense tracker accepts negative amounts - that's a bug!
    Watch Claude's Read → Edit → Verify workflow as it fixes this.
  objective: "Fix the negative amount validation bug"

intro: |
  Claude's core workflow: Read → Edit → Verify

  The expense tracker has a bug - try this:
    python main.py add -50 Food "Negative expense"

  It works! But negative expenses shouldn't be allowed.

  Type: claude

  Say: "The add_expense function allows negative amounts. Fix this bug."

  Watch how Claude:
  1. Reads models.py to understand the code
  2. Edits to add validation
  3. Suggests running tests to verify

verification:
  - type: tool_called
    tool_name: Read
  - type: tool_called
    tool_name: Edit
  - type: file_contains
    path: models.py
    pattern: "(amount\\s*<=?\\s*0|ValueError|raise.*[Aa]mount)"

hints:
  - after_minutes: 2
    text: "Tell Claude: 'add_expense allows negative amounts - fix it'"
  - after_minutes: 4
    text: "After the fix, run: pytest tests/test_models.py -k negative -v"

success: |
  Bug fixed! You saw the core loop:

  1. READ: Claude read models.py first
  2. EDIT: Claude added validation (amount > 0)
  3. VERIFY: Tests should now pass

  Run: pytest tests/test_models.py::TestAddExpense -v

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 4: Commit**

```bash
git add levels/03-read-edit-verify/
git commit -m "feat(lesson-3): fix negative amount bug exercise"
```

---

## Task 5: Update Lesson 4 - Debugging

**Files:**
- Modify: `levels/04-debugging/lesson.yaml`
- Replace: `levels/04-debugging/exercise/*`
- Modify: `levels/04-debugging/exercise/models.py` (apply lesson 3 fix)

**Step 1: Clear and copy exercise files**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/04-debugging/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/exercises/expense-tracker/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/04-debugging/exercise/
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/04-debugging/exercise && python seed_data.py
```

**Step 2: Apply lesson 3 fix to models.py**

In `levels/04-debugging/exercise/models.py`, replace the `add_expense` function:

```python
def add_expense(
    amount: float,
    category: str,
    description: str,
    date: Optional[datetime] = None
) -> Expense:
    """Add a new expense with validation."""
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")

    if not category or not category.strip():
        raise ValueError("Category cannot be empty")

    expense = Expense(
        id=generate_id(),
        amount=amount,
        category=category.strip(),
        description=description,
        date=date or datetime.now()
    )
    save_expense(expense)
    return expense
```

**Step 3: Verify case-sensitivity bug still exists**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/04-debugging/exercise
pytest tests/test_models.py::TestListExpenses::test_list_by_category_case_insensitive -v
```

Expected: FAILED (case-sensitivity bug still exists)

**Step 4: Update lesson.yaml**

Replace contents of `levels/04-debugging/lesson.yaml`:

```yaml
id: "debugging"
number: 4
module: "Core Loop"
title: "Debugging with Claude"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Run pytest, see failures, share with Claude, let it investigate and fix.
  objective: "Fix the case-sensitivity bug using Claude's debugging workflow"

intro: |
  Debugging workflow: Share error → Investigate → Fix → Verify

  Run the tests:
    pytest tests/test_models.py -v

  You'll see a failure about case-insensitive filtering.
  "Food" doesn't match "food" - but it should!

  Type: claude

  Copy the test failure and say: "This test is failing. Can you investigate and fix it?"

verification:
  - type: file_contains
    path: models.py
    pattern: "\\.lower\\(\\)"
  - type: command_output
    command: "pytest tests/test_models.py::TestListExpenses::test_list_by_category_case_insensitive -v"
    expected_output: "(PASSED|passed)"

hints:
  - after_minutes: 2
    text: "Run pytest and share the failure output with Claude"
  - after_minutes: 4
    text: "The fix needs .lower() for case-insensitive comparison"

success: |
  Bug fixed! Category filtering is now case-insensitive.

  Debugging workflow:
  1. Run tests → see failure
  2. Share error with Claude
  3. Claude reads code, proposes fix
  4. Verify fix with tests

  All tests should pass now: pytest tests/test_models.py -v

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 5: Commit**

```bash
git add levels/04-debugging/
git commit -m "feat(lesson-4): case-sensitivity debugging exercise"
```

---

## Task 6: Update Lesson 5 - Spec-Driven Development

**Files:**
- Modify: `levels/05-spec-driven/lesson.yaml`
- Replace: `levels/05-spec-driven/exercise/*`
- Apply: Both lesson 3 and 4 fixes

**Step 1: Clear and copy exercise files with fixes**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/05-spec-driven/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/04-debugging/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/05-spec-driven/exercise/
```

**Step 2: Apply lesson 4 fix (case-insensitive)**

In `levels/05-spec-driven/exercise/models.py`, update `list_expenses`:

```python
def list_expenses(
    category: Optional[str] = None,
    month: Optional[str] = None,
    limit: int = 100
) -> list[Expense]:
    """List expenses with optional filters."""
    expenses = load_expenses()

    if category:
        category_lower = category.lower()
        expenses = [e for e in expenses if e.category.lower() == category_lower]

    if month:
        expenses = [e for e in expenses if e.date.strftime('%Y-%m') == month]

    expenses.sort(key=lambda x: x.date, reverse=True)
    return expenses[:limit]
```

**Step 3: Create specs directory**

```bash
mkdir -p /Users/abhishekray/Projects/opslane/claude-code-game/levels/05-spec-driven/exercise/specs
```

**Step 4: Update lesson.yaml**

Replace contents of `levels/05-spec-driven/lesson.yaml`:

```yaml
id: "spec-driven"
number: 5
module: "Planning"
title: "Spec-Driven Development"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Write a spec for recurring expenses, then have Claude implement it.
  objective: "Create a spec and implement recurring expenses feature"

intro: |
  Better specs = better code. Write the spec first!

  You want to add recurring expenses (monthly bills like rent, subscriptions).

  Create a spec file first:
    specs/recurring-expenses.md

  Include:
  - Problem: Why do we need this?
  - Requirements: What must it do?
  - Implementation: How should it work?

  Type: claude

  Say: "I want to add recurring expenses. Help me write a spec first,
  then implement it."

verification:
  - type: file_exists
    path: specs/recurring-expenses.md
  - type: file_contains
    path: specs/recurring-expenses.md
    pattern: "(requirement|problem|implement)"
  - type: file_contains
    path: models.py
    pattern: "(recurring|frequency)"

hints:
  - after_minutes: 2
    text: "Ask Claude to help write a spec in specs/recurring-expenses.md"
  - after_minutes: 5
    text: "After spec is written, ask Claude to implement it"

success: |
  You practiced spec-driven development!

  1. Wrote the spec first (requirements, approach)
  2. Reviewed the spec before implementing
  3. Claude implemented to spec

  Specs eliminate ambiguity and improve results.

limits:
  max_duration_minutes: 20
  max_claude_messages: 25
```

**Step 5: Commit**

```bash
git add levels/05-spec-driven/
git commit -m "feat(lesson-5): spec-driven recurring expenses exercise"
```

---

## Task 7: Update Lesson 6 - Plan Mode

**Files:**
- Modify: `levels/06-planning-mode/lesson.yaml`
- Replace: `levels/06-planning-mode/exercise/*`

**Step 1: Copy exercise files from lesson 5**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/06-planning-mode/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/05-spec-driven/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/06-planning-mode/exercise/
```

**Step 2: Ensure reports.py is still a stub**

Verify `levels/06-planning-mode/exercise/reports.py` has `NotImplementedError`.

**Step 3: Update lesson.yaml**

Replace contents of `levels/06-planning-mode/lesson.yaml`:

```yaml
id: "planning-mode"
number: 6
module: "Planning"
title: "Plan Mode for Complex Features"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Use plan mode to implement the reports module - a multi-file feature.
  objective: "Use plan mode to implement monthly expense reports"

intro: |
  Plan mode is for complex, multi-step features.

  The reports module (reports.py) is empty - it raises NotImplementedError.

  Use plan mode to implement:
  - generate_monthly_report()
  - get_category_breakdown()
  - get_top_expenses()
  - save_report()

  Type: claude

  Press Shift+Tab to toggle plan mode, then say:
  "Implement the reports module with monthly reports, category breakdown, and top expenses"

verification:
  - type: file_contains
    path: reports.py
    pattern: "def generate_monthly_report"
  - type: file_contains
    path: reports.py
    pattern: "def get_category_breakdown"

hints:
  - after_minutes: 2
    text: "Press Shift+Tab to enter plan mode before describing the feature"
  - after_minutes: 5
    text: "Review Claude's plan, then approve to implement"

success: |
  You used plan mode for a complex feature!

  1. Entered plan mode (Shift+Tab)
  2. Described the feature
  3. Reviewed the plan
  4. Approved and implemented

  Test it: python -c "from reports import generate_monthly_report; print(generate_monthly_report('2026-01'))"

limits:
  max_duration_minutes: 20
  max_claude_messages: 30
```

**Step 4: Commit**

```bash
git add levels/06-planning-mode/
git commit -m "feat(lesson-6): plan mode for reports implementation"
```

---

## Task 8: Update Lesson 7 - Sub-Agents

**Files:**
- Modify: `levels/07-sub-agents/lesson.yaml`
- Replace: `levels/07-sub-agents/exercise/*`

**Step 1: Copy exercise files from lesson 6 with reports implemented**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/07-sub-agents/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/06-planning-mode/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/07-sub-agents/exercise/
```

**Step 2: Create a fully implemented reports.py**

Replace `levels/07-sub-agents/exercise/reports.py`:

```python
"""Report generation for expense tracker."""

from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models import Expense


def generate_monthly_report(month: Optional[str] = None) -> str:
    """Generate a monthly expense report."""
    from models import list_expenses
    from utils import format_currency

    if month is None:
        month = datetime.now().strftime("%Y-%m")

    expenses = list_expenses(month=month)

    if not expenses:
        return f"# Expense Report: {month}\n\nNo expenses found."

    total = sum(e.amount for e in expenses)
    breakdown = get_category_breakdown(expenses)
    top = get_top_expenses(expenses, 5)

    report = f"# Expense Report: {month}\n\n"
    report += f"## Summary\n"
    report += f"- **Total Spent:** {format_currency(total)}\n"
    report += f"- **Number of Expenses:** {len(expenses)}\n\n"

    report += "## By Category\n"
    for cat, amount in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
        pct = (amount / total) * 100
        report += f"- {cat}: {format_currency(amount)} ({pct:.1f}%)\n"

    report += "\n## Top 5 Expenses\n"
    for i, exp in enumerate(top, 1):
        report += f"{i}. {format_currency(exp.amount)} - {exp.description} ({exp.category})\n"

    return report


def get_category_breakdown(expenses: list["Expense"]) -> dict[str, float]:
    """Get spending breakdown by category."""
    breakdown: dict[str, float] = {}
    for exp in expenses:
        breakdown[exp.category] = breakdown.get(exp.category, 0) + exp.amount
    return breakdown


def get_top_expenses(expenses: list["Expense"], n: int = 5) -> list["Expense"]:
    """Get the top N expenses by amount."""
    return sorted(expenses, key=lambda x: x.amount, reverse=True)[:n]


def save_report(report: str, filename: str) -> Path:
    """Save report to a file."""
    path = Path("reports") / filename
    path.parent.mkdir(exist_ok=True)
    path.write_text(report)
    return path
```

**Step 3: Update lesson.yaml**

Replace contents of `levels/07-sub-agents/lesson.yaml`:

```yaml
id: "sub-agents"
number: 7
module: "Building Blocks"
title: "Sub-Agents for Context Isolation"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Use a sub-agent to explore the codebase without polluting your main context.
  objective: "Use sub-agents to keep your main context clean"

intro: |
  Sub-agents = fresh context window. Parent gets a clean summary.

  You want to understand how the reporting module works, but don't
  want all those details filling your main context.

  Type: claude

  Say: "Use a sub-agent to analyze reports.py and summarize how it
  generates reports. I just want a summary, not all the details."

  After, run /context to see your context stayed clean.

verification:
  - type: message_exists
  - type: tool_called
    tool_name: Task

hints:
  - after_minutes: 2
    text: "Ask Claude to 'use a sub-agent' to explore reports.py"
  - after_minutes: 4
    text: "Run /context after to verify your context is still low"

success: |
  You used sub-agents for context isolation!

  The sub-agent explored reports.py in its own context.
  You got a clean summary without the noise.

  Sub-agents are for research and exploration.
  Keep your main session clean for actual work.

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 4: Commit**

```bash
git add levels/07-sub-agents/
git commit -m "feat(lesson-7): sub-agents for context isolation"
```

---

## Task 9: Update Lesson 8 - Custom Commands

**Files:**
- Modify: `levels/08-custom-commands/lesson.yaml`
- Replace: `levels/08-custom-commands/exercise/*`

**Step 1: Copy exercise files from lesson 7**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/08-custom-commands/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/07-sub-agents/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/08-custom-commands/exercise/
```

**Step 2: Create .claude/commands directory**

```bash
mkdir -p /Users/abhishekray/Projects/opslane/claude-code-game/levels/08-custom-commands/exercise/.claude/commands
```

**Step 3: Update lesson.yaml**

Replace contents of `levels/08-custom-commands/lesson.yaml`:

```yaml
id: "custom-commands"
number: 8
module: "Building Blocks"
title: "Custom Commands"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Create slash commands for repetitive workflows.
  objective: "Create /report, /backup, and /test commands"

intro: |
  Commands are in .claude/commands/*.md
  Invoke with /command-name

  Create three commands:
  1. /report - Generate monthly expense report
  2. /backup - Export expenses to JSON
  3. /test - Run pytest with verbose output

  Type: claude

  Say: "Create a /report command that generates a monthly expense report.
  Put it in .claude/commands/report.md"

verification:
  - type: file_exists
    path: .claude/commands/report.md
  - type: file_exists
    path: .claude/commands/backup.md
  - type: file_exists
    path: .claude/commands/test.md

hints:
  - after_minutes: 2
    text: "Ask Claude to create .claude/commands/report.md"
  - after_minutes: 5
    text: "Create backup.md and test.md the same way"

success: |
  You created custom commands!

  Test them:
  - /report - generates expense report
  - /backup - exports to JSON
  - /test - runs pytest

  Commands codify repetitive workflows.

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 4: Commit**

```bash
git add levels/08-custom-commands/
git commit -m "feat(lesson-8): custom commands exercise"
```

---

## Task 10: Update Lesson 9 - Skills

**Files:**
- Modify: `levels/09-skills/lesson.yaml`
- Replace: `levels/09-skills/exercise/*`

**Step 1: Copy exercise files from lesson 8**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/09-skills/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/08-custom-commands/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/09-skills/exercise/
```

**Step 2: Create .claude/skills directory**

```bash
mkdir -p /Users/abhishekray/Projects/opslane/claude-code-game/levels/09-skills/exercise/.claude/skills
```

**Step 3: Update lesson.yaml**

Replace contents of `levels/09-skills/lesson.yaml`:

```yaml
id: "skills"
number: 9
module: "Building Blocks"
title: "Skills (Auto-Activating Commands)"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Create skills that activate automatically based on context.
  objective: "Create lint and test-after-edit skills"

intro: |
  Skills are in .claude/skills/*.md
  They auto-activate when relevant (no /command needed).

  Commands = manual (/command-name)
  Skills = automatic (triggered by context)

  Create two skills:
  1. lint.md - Suggest running ruff after Python edits
  2. test-after-edit.md - Suggest running tests after code changes

  Type: claude

  Say: "Create a lint skill in .claude/skills/lint.md that suggests
  running ruff check after Python files are edited"

verification:
  - type: file_exists
    path: .claude/skills/lint.md
  - type: file_exists
    path: .claude/skills/test-after-edit.md

hints:
  - after_minutes: 2
    text: "Ask Claude to create .claude/skills/lint.md"
  - after_minutes: 5
    text: "Skills have a YAML frontmatter with triggers"

success: |
  You created auto-activating skills!

  Edit a Python file and see if the skill activates.

  Skills = automatic
  Commands = manual

  Choose based on workflow.

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 4: Commit**

```bash
git add levels/09-skills/
git commit -m "feat(lesson-9): skills (auto-activating commands)"
```

---

## Task 11: Update Lesson 10 - Code Search Workflow

**Files:**
- Modify: `levels/10-code-search/lesson.yaml`
- Replace: `levels/10-code-search/exercise/*`

**Step 1: Copy exercise files from lesson 9**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/10-code-search/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/09-skills/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/10-code-search/exercise/
```

**Step 2: Update lesson.yaml**

Replace contents of `levels/10-code-search/lesson.yaml`:

```yaml
id: "code-search"
number: 10
module: "Workflows"
title: "Code Search Workflow"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Create a /search command that uses sub-agents to explore the codebase.
  objective: "Build a code search workflow combining commands and sub-agents"

intro: |
  Combine primitives into powerful workflows.

  Create a /search command that:
  1. Takes a query like "how does filtering work?"
  2. Uses a sub-agent to grep, read files, trace code
  3. Returns a summary with file:line references

  Type: claude

  Say: "Create a /search command in .claude/commands/search.md that
  uses sub-agents to explore the codebase and return a summary"

verification:
  - type: file_exists
    path: .claude/commands/search.md
  - type: file_contains
    path: .claude/commands/search.md
    pattern: "(sub-agent|Task|grep|search)"

hints:
  - after_minutes: 2
    text: "The search command should describe using sub-agents"
  - after_minutes: 5
    text: "Test with: /search how does category filtering work?"

success: |
  You built a code search workflow!

  Test it: /search how does the database work?

  You combined primitives (commands + sub-agents) into
  a powerful exploration tool.

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 3: Commit**

```bash
git add levels/10-code-search/
git commit -m "feat(lesson-10): code search workflow"
```

---

## Task 12: Update Lesson 11 - Code Review Workflow

**Files:**
- Modify: `levels/11-code-review/lesson.yaml`
- Replace: `levels/11-code-review/exercise/*`

**Step 1: Copy exercise files from lesson 10**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/11-code-review/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/10-code-search/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/11-code-review/exercise/
```

**Step 2: Update lesson.yaml**

Replace contents of `levels/11-code-review/lesson.yaml`:

```yaml
id: "code-review"
number: 11
module: "Workflows"
title: "Code Review Workflow"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    Create a code review skill that checks for quality issues before commits.
  objective: "Build an automated code review workflow"

intro: |
  Automate quality gates with skills.

  Create a review skill that checks before commits:
  - Type hints on functions
  - No hardcoded secrets
  - Tests for new functions

  Type: claude

  Say: "Create a code review skill in .claude/skills/review.md that
  runs before git commits and checks for type hints, secrets, and missing tests"

verification:
  - type: file_exists
    path: .claude/skills/review.md
  - type: file_contains
    path: .claude/skills/review.md
    pattern: "(type hint|secret|test|commit)"

hints:
  - after_minutes: 2
    text: "The skill should trigger before git commit"
  - after_minutes: 5
    text: "Include a checklist of things to verify"

success: |
  You built a code review workflow!

  Add a function without type hints, then try to commit.
  The skill should catch it.

  Automate quality gates with skills + hooks.

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 3: Commit**

```bash
git add levels/11-code-review/
git commit -m "feat(lesson-11): code review workflow"
```

---

## Task 13: Update Lesson 12 - Scale & Safety

**Files:**
- Modify: `levels/12-scale-safety/lesson.yaml`
- Replace: `levels/12-scale-safety/exercise/*`

**Step 1: Copy exercise files from lesson 11**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/12-scale-safety/exercise/*
cp -r /Users/abhishekray/Projects/opslane/claude-code-game/levels/11-code-review/exercise/* \
  /Users/abhishekray/Projects/opslane/claude-code-game/levels/12-scale-safety/exercise/
```

**Step 2: Initialize git in exercise directory**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/12-scale-safety/exercise
git init
git add -A
git commit -m "Initial commit"
```

**Step 3: Update lesson.yaml**

Replace contents of `levels/12-scale-safety/lesson.yaml`:

```yaml
id: "scale-safety"
number: 12
module: "Scale & Safety"
title: "Parallel Work, Git & Safety"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 360

exercise:
  intro: |
    Set up safety hooks and practice git worktrees for parallel development.
  objective: "Configure safety guardrails and practice parallel workflows"

intro: |
  The final lesson: Scale safely.

  1. Add safety hooks to block dangerous commands
  2. Create a git worktree for parallel work
  3. Practice /rewind to undo mistakes

  Type: claude

  Say: "Create a .claude/settings.json with hooks that block 'rm -rf'
  and require confirmation for 'git push --force'"

verification:
  - type: file_exists
    path: .claude/settings.json
  - type: file_contains
    path: .claude/settings.json
    pattern: "(hooks|block|rm -rf)"

hints:
  - after_minutes: 2
    text: "Ask Claude to create safety hooks in .claude/settings.json"
  - after_minutes: 5
    text: "Try: git worktree add ../feature-branch feature/csv-export"

success: |
  Congratulations! You've completed the Claude Code course!

  You learned:
  1. Context management (CLAUDE.md, sub-agents)
  2. Core loop (Read → Edit → Verify)
  3. Planning (specs, plan mode)
  4. Building blocks (commands, skills)
  5. Workflows (search, review)
  6. Scale & safety (worktrees, hooks)

  Now go build something amazing!

limits:
  max_duration_minutes: 20
  max_claude_messages: 25
```

**Step 4: Commit**

```bash
git add levels/12-scale-safety/
git commit -m "feat(lesson-12): scale and safety final lesson"
```

---

## Task 14: Clean Up Old Files

**Files:**
- Delete: `levels/starter-app/` (replaced by expense-tracker)

**Step 1: Remove old starter-app**

```bash
rm -rf /Users/abhishekray/Projects/opslane/claude-code-game/levels/starter-app
```

**Step 2: Commit**

```bash
git add -A
git commit -m "chore: remove old starter-app (replaced by expense-tracker)"
```

---

## Task 15: Final Verification

**Step 1: Verify all lesson directories exist**

```bash
ls -la /Users/abhishekray/Projects/opslane/claude-code-game/levels/
```

Expected: 12 directories (01 through 12)

**Step 2: Verify all lesson.yaml files load**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/backend
python -c "
from app.services.levels import load_level
for i in range(1, 13):
    level = load_level(i)
    if level:
        print(f'{i}: {level.title}')
    else:
        print(f'{i}: MISSING')
"
```

Expected: All 12 lessons print with titles

**Step 3: Verify exercise files in each lesson**

```bash
for i in $(seq -w 1 12); do
  dir=$(ls -d /Users/abhishekray/Projects/opslane/claude-code-game/levels/${i}-*/ 2>/dev/null)
  if [ -d "$dir/exercise" ]; then
    count=$(ls "$dir/exercise" | wc -l)
    echo "${i}: $count files"
  else
    echo "${i}: NO EXERCISE DIR"
  fi
done
```

Expected: Each lesson has 10+ files

**Step 4: Run expense tracker tests in lesson 3**

```bash
cd /Users/abhishekray/Projects/opslane/claude-code-game/levels/03-read-edit-verify/exercise
pytest tests/test_models.py -v --tb=no | grep -E "(PASSED|FAILED)" | head -10
```

Expected: Some tests PASS, validation tests FAIL (the bug to fix)

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete expense tracker course - all 12 lessons"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Rename directories | 8 directories |
| 2 | Lesson 1: Context | lesson.yaml, exercise/* |
| 3 | Lesson 2: CLAUDE.md | lesson.yaml, exercise/* |
| 4 | Lesson 3: Read/Edit/Verify | lesson.yaml, exercise/* |
| 5 | Lesson 4: Debugging | lesson.yaml, exercise/*, models.py fix |
| 6 | Lesson 5: Spec-Driven | lesson.yaml, exercise/*, both fixes |
| 7 | Lesson 6: Plan Mode | lesson.yaml, exercise/* |
| 8 | Lesson 7: Sub-Agents | lesson.yaml, exercise/*, reports.py |
| 9 | Lesson 8: Commands | lesson.yaml, exercise/* |
| 10 | Lesson 9: Skills | lesson.yaml, exercise/* |
| 11 | Lesson 10: Code Search | lesson.yaml, exercise/* |
| 12 | Lesson 11: Code Review | lesson.yaml, exercise/* |
| 13 | Lesson 12: Scale/Safety | lesson.yaml, exercise/* |
| 14 | Cleanup | Remove starter-app |
| 15 | Final verification | Test all lessons |

**Total tasks:** 15
**Estimated time:** 2-3 hours
