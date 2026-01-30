# Claude Code Course: Build an Expense Tracker

> **Project-Based Learning**: Students build a real Expense Tracker app from scratch, learning Claude Code features progressively with each lesson.

**Tech Stack**: Python + SQLite (simple CLI app)
**Format**: Watch video → Hands-on exercise → Verification

---

## Module 1: Mental Model (Lessons 1-2)

### Lesson 1: Context is Everything
**Objective**: Understand that LLMs are pure functions - context determines output quality

**Key Concepts**:
- LLMs have no memory, no state - only what's in the context window
- Context quality curve (too little → vague, too much → "lost in the middle")
- `/context` command to monitor usage
- Context amnesia: Claude forgets early information when context fills up

**The Experiment**:
We'll prove Claude has no memory by:
1. Giving Claude a "secret phrase" at the start
2. Filling the context with lots of file reads
3. Asking Claude to recall the secret phrase → watch it struggle or forget

**What Students Do**:

**Step 1: Establish a baseline**
```
You: "Remember this secret phrase for later: PURPLE_ELEPHANT_42.
     I'll ask you about it at the end. Now, what does this expense tracker do?"
```
Claude will confirm and explain the codebase.

**Step 2: Fill the context**
```
You: "Read every Python file in this project and summarize each one."
You: "Now read all the test files too."
You: "Explain how the database module works in detail."
You: "Show me the full implementation of the reports module."
```
Run `/context` - watch it climb to 50%+

**Step 3: Test for amnesia**
```
You: "What was the secret phrase I told you at the beginning?"
```

**What happens?** At high context, Claude may:
- Get it wrong
- Say it doesn't remember
- Confuse it with something else
- Take longer to find it (buried in "middle" of context)

**Exercise Files**:
```
expense_tracker/
├── main.py           # Entry point (~100 lines)
├── models.py         # Data models (~150 lines)
├── database.py       # SQLite helpers (~200 lines)
├── utils.py          # Utility functions (~100 lines)
├── reports.py        # Report generation (~150 lines)
├── config.py         # Configuration (~50 lines)
├── cli.py            # CLI interface (~200 lines)
├── validators.py     # Input validation (~100 lines)
├── exporters.py      # Export to CSV/JSON (~150 lines)
├── tests/
│   ├── test_models.py
│   ├── test_database.py
│   ├── test_reports.py
│   └── test_cli.py
└── README.md         # Documentation
```
(~1500 lines total - enough to fill context when all read)

**Practical Task**:
"Run this experiment:
1. Tell Claude a secret phrase: 'PURPLE_ELEPHANT_42'
2. Ask Claude to read and summarize EVERY file in the project
3. Run `/context` to see usage (aim for 50%+)
4. Ask Claude to recall your secret phrase
5. Observe: Did Claude remember? How confident was it?"

**Verification**:
```yaml
- type: message_exists
- type: tool_called
  tool_name: Read
```

**Bonus Challenge**: Try the same experiment but use a sub-agent to read files instead.
Does the parent session remember the secret phrase better? (Spoiler: yes!)

**Alternative Experiment: Conflicting Information**

Another way to see context issues - give Claude conflicting facts:

**Step 1: Tell Claude something false**
```
You: "Important: This project uses PostgreSQL, not SQLite.
     Remember this - the files might say SQLite but we migrated to PostgreSQL."
```

**Step 2: Have Claude read the actual code**
```
You: "Read database.py and explain how the database works."
```
(The file clearly uses SQLite)

**Step 3: Ask a question**
```
You: "What database does this project use?"
```

**What happens?** Claude may:
- Get confused between what you said vs. what's in the code
- Confidently say PostgreSQL (wrong - trusting your early message)
- Correctly say SQLite (ignoring your instruction)
- Hedge and mention both

**The lesson**: Context isn't just about size - it's about **quality**.
Contradictory information in context leads to unreliable outputs.

---

**Key Takeaway**:
- Context is finite. Information gets "lost in the middle" as it fills up.
- Conflicting context leads to confusion and wrong answers.
- This is why intentional context management matters.
- Sub-agents help by keeping exploration OUT of your main context.

---

### Lesson 2: CLAUDE.md - Your Project's Memory
**Objective**: Create persistent project context that survives sessions

**Key Concepts**:
- CLAUDE.md is read on every session start
- High-leverage: 1 line here affects every interaction
- Keep it lean: project purpose, commands, conventions

**What Students Do**:
- Notice Claude doesn't know project conventions
- Create CLAUDE.md with:
  - Project description (1-2 sentences)
  - How to run: `python main.py`
  - How to test: `pytest`
  - Code style: "Use type hints, no docstrings unless complex"
- Start a new session and see Claude automatically knows the context

**Exercise Files**: Same as Lesson 1, but NO CLAUDE.md initially

**Practical Task**:
"Claude doesn't know how to run tests. Create a CLAUDE.md file that tells Claude:
1. What this project is
2. How to run the app
3. How to run tests
4. Your code style preferences"

**Verification**:
```yaml
- type: file_exists
  path: CLAUDE.md
- type: file_contains
  path: CLAUDE.md
  pattern: '(pytest|test|run)'
```

**Key Takeaway**: CLAUDE.md is your project's memory - invest time here for 10x returns.

---

## Module 2: Core Loop (Lessons 3-4)

### Lesson 3: Read → Edit → Verify
**Objective**: Experience Claude's core workflow for making changes

**Key Concepts**:
- Claude reads code before editing (never blind edits)
- Claude makes surgical edits, not full rewrites
- You verify the changes work

**What Students Do**:
- Find that `add_expense()` has a bug (doesn't validate amount > 0)
- Ask Claude to fix it
- Watch Claude: Read the file → Edit the specific function → Suggest running tests
- Run tests to verify the fix

**Exercise Files**:
```python
# models.py - has intentional bug
def add_expense(amount: float, category: str, description: str) -> Expense:
    """Add a new expense."""
    # BUG: No validation - allows negative amounts!
    expense = Expense(
        id=generate_id(),
        amount=amount,  # Should validate amount > 0
        category=category,
        description=description,
        date=datetime.now()
    )
    save_expense(expense)
    return expense
```

**Practical Task**:
"The `add_expense` function allows negative amounts. Ask Claude to fix this bug.
Watch how Claude reads the code first, then makes a targeted edit."

**Verification**:
```yaml
- type: tool_called
  tool_name: Read
- type: tool_called
  tool_name: Edit
- type: file_contains
  path: models.py
  pattern: 'amount\s*[<>=]+\s*0|ValueError|raise'
```

**Key Takeaway**: Claude reads before editing. You verify after.

---

### Lesson 4: Debugging with Claude
**Objective**: Use Claude to diagnose and fix errors systematically

**Key Concepts**:
- Share error messages with Claude
- Claude can run commands to investigate
- Iterative debugging: fix → test → repeat

**What Students Do**:
- Run tests and see failures
- Copy the error output to Claude
- Let Claude investigate (read files, run commands)
- Claude fixes the issues
- Verify all tests pass

**Exercise Files**:
```python
# test_models.py - tests that expose bugs
def test_list_expenses_by_category():
    """Test filtering expenses by category."""
    add_expense(50.0, "Food", "Lunch")
    add_expense(30.0, "Transport", "Uber")
    add_expense(25.0, "Food", "Coffee")

    # BUG: list_expenses doesn't filter correctly
    food_expenses = list_expenses(category="Food")
    assert len(food_expenses) == 2  # Will fail!
```

**Practical Task**:
"Run `pytest` and share the failures with Claude. Ask Claude to investigate and fix
the bugs until all tests pass."

**Verification**:
```yaml
- type: command_output
  command: "pytest -v"
  expected_output: "passed"
```

**Key Takeaway**: Claude debugs by reading, hypothesizing, and testing fixes iteratively.

---

## Module 3: Planning (Lessons 5-6)

### Lesson 5: Spec-Driven Development
**Objective**: Write specifications before code for better results

**Key Concepts**:
- Specs eliminate ambiguity
- Research → Plan → Implement workflow
- Human reviews spec before implementation

**What Students Do**:
- Want to add "recurring expenses" feature
- Write a spec file first (`specs/recurring-expenses.md`):
  - Problem statement
  - Requirements (what it must do)
  - Non-requirements (what it won't do)
  - Implementation approach
- Have Claude implement from the spec
- Compare result to spec

**Exercise Files**: Template spec file

**Practical Task**:
"Create a spec for adding recurring expenses (monthly bills like rent, subscriptions).
Write it in `specs/recurring-expenses.md` with:
- Problem: Why do we need this?
- Requirements: What must it do?
- Implementation: How should it work?

Then ask Claude to implement it following the spec exactly."

**Verification**:
```yaml
- type: file_exists
  path: specs/recurring-expenses.md
- type: file_contains
  path: specs/recurring-expenses.md
  pattern: '(requirement|problem|implement)'
- type: file_contains
  path: models.py
  pattern: 'recurring|frequency|monthly'
```

**Key Takeaway**: Better specs = better code. Invest upfront.

---

### Lesson 6: Plan Mode for Complex Features
**Objective**: Use planning for multi-step features

**Key Concepts**:
- Plan mode for complex, multi-file changes
- Review the plan before approving
- Plans are checkpoints you can return to

**What Students Do**:
- Want to add expense reports (monthly summary, category breakdown)
- Use plan mode: "shift+tab to toggle plan mode"
- Review Claude's proposed plan
- Approve and let Claude implement
- If something goes wrong, rewind to the plan

**Practical Task**:
"Add a feature to generate monthly expense reports. Use plan mode:
1. Toggle plan mode (shift+tab)
2. Describe the feature
3. Review Claude's plan carefully
4. Approve and implement

The report should show: total spent, breakdown by category, top 3 expenses."

**Verification**:
```yaml
- type: file_exists
  path: reports.py
- type: file_contains
  path: reports.py
  pattern: 'monthly|summary|category'
```

**Key Takeaway**: For complex features, plan first. Review before implementing.

---

## Module 4: Building Blocks (Lessons 7-9)

### Lesson 7: Sub-Agents for Context Isolation
**Objective**: Use sub-agents to keep your main context clean

**Key Concepts**:
- Sub-agents = fresh context window
- Parent gets clean summary, not all the noise
- Use for research, exploration, one-off tasks

**What Students Do**:
- Need to research how other expense trackers handle categories
- Instead of polluting main context, spawn a sub-agent
- Sub-agent explores codebase, reads docs, gathers info
- Parent receives concise summary
- Check `/context` - main session stayed clean

**Practical Task**:
"You want to understand how the reporting module works without filling your context.
Ask Claude to spawn a sub-agent to investigate:
'Use a sub-agent to analyze reports.py and summarize how it generates reports.
I just want a summary, not all the details in my context.'

After, run `/context` - your context should still be low."

**Verification**:
```yaml
- type: message_exists  # Sub-agent returned summary
- type: tool_called
  tool_name: Task       # Sub-agent was spawned
```

**Key Takeaway**: Sub-agents are for context isolation, not roleplay. Keep your main session clean.

---

### Lesson 8: Custom Commands
**Objective**: Create manual slash commands for repetitive workflows

**Key Concepts**:
- Commands are in `.claude/commands/*.md`
- Invoke with `/command-name`
- Good for: deployment, reporting, setup

**What Students Do**:
- Create `/report` command that generates expense summary
- Create `/backup` command that exports data to JSON
- Create `/test` command that runs tests with coverage

**Exercise Structure**:
```
.claude/commands/
├── report.md   # Generate expense report
├── backup.md   # Export data to backup.json
└── test.md     # Run pytest with coverage
```

**Example Command** (`.claude/commands/report.md`):
```markdown
# Generate Expense Report

Generate a monthly expense report for the current month.

## Steps:
1. Read the current expenses from the database
2. Calculate total spent
3. Break down by category
4. List top 5 expenses
5. Save to `reports/YYYY-MM.md`
```

**Practical Task**:
"Create three custom commands:
1. `/report` - generates monthly expense report to `reports/` folder
2. `/backup` - exports all expenses to `backup.json`
3. `/test` - runs pytest with verbose output

Test each command after creating it."

**Verification**:
```yaml
- type: file_exists
  path: .claude/commands/report.md
- type: file_exists
  path: .claude/commands/backup.md
- type: file_exists
  path: .claude/commands/test.md
```

**Key Takeaway**: Commands codify repetitive workflows. Invoke manually with `/name`.

---

### Lesson 9: Skills (Auto-Activating Commands)
**Objective**: Create skills that activate automatically based on context

**Key Concepts**:
- Skills are in `.claude/skills/*.md`
- They auto-activate when Claude thinks they're relevant
- Good for: code review, testing, documentation patterns

**MCP vs Skills**:
- MCP: Protocol for external tools, costs tokens for tool definitions
- Skills: Markdown instructions, loaded dynamically, lightweight

**What Students Do**:
- Create a `lint` skill that runs when code is modified
- Create a `test-after-edit` skill that suggests running tests after edits
- Create a `security-check` skill that warns about common issues

**Example Skill** (`.claude/skills/test-after-edit.md`):
```markdown
---
name: test-after-edit
description: Remind to run tests after code changes
triggers:
  - after_tool: Edit
  - after_tool: Write
---

# Test After Edit

When code is modified, remind the user:
"I've made changes. Want me to run `pytest` to verify everything still works?"

Only suggest this for .py files, not config files.
```

**Practical Task**:
"Create two skills:
1. `lint.md` - When Python files are edited, suggest running `ruff check`
2. `test-after-edit.md` - After any code change, offer to run tests

Edit a Python file and see if the skill activates."

**Verification**:
```yaml
- type: file_exists
  path: .claude/skills/lint.md
- type: file_exists
  path: .claude/skills/test-after-edit.md
```

**Key Takeaway**: Skills auto-activate. Commands are manual. Choose based on workflow.

---

## Module 5: Workflows (Lessons 10-11)

### Lesson 10: Code Search Workflow
**Objective**: Combine sub-agents + commands for efficient code exploration

**Key Concepts**:
- Large codebases need systematic exploration
- Sub-agents can search in parallel
- Results feed back to main session

**What Students Do**:
- Create a `/search` command that:
  - Takes a query like "how is authentication handled?"
  - Spawns a sub-agent to grep, read files, trace code paths
  - Returns a summary with file:line references
- Test it on the expense tracker codebase

**Example Command** (`.claude/commands/search.md`):
```markdown
# Code Search

Search the codebase for a concept or pattern.

## Input
$ARGUMENTS = the search query (e.g., "how does expense filtering work?")

## Process
1. Use grep to find relevant files
2. Read the most relevant files
3. Trace the code path
4. Summarize findings with file:line references

## Output
- Summary of how the feature works
- Key files involved
- Entry points and flow
```

**Practical Task**:
"Create a `/search` command that helps explore the codebase.
Test it by running: `/search how does the category filtering work?`

The command should use sub-agents to explore and return a clean summary."

**Verification**:
```yaml
- type: file_exists
  path: .claude/commands/search.md
- type: message_exists  # Claude used the command
```

**Key Takeaway**: Combine primitives (sub-agents, commands) into powerful workflows.

---

### Lesson 11: Code Review Workflow
**Objective**: Build an automated code review workflow using hooks + skills

**Key Concepts**:
- Pre-commit hooks catch issues before they're committed
- Skills can enforce team standards
- Combine for quality gates

**What Students Do**:
- Create a `review` skill that checks:
  - Type hints present
  - No hardcoded secrets
  - Tests exist for new functions
- Add a pre-commit hook that runs the review
- Make a code change and see the review activate

**Example Skill** (`.claude/skills/review.md`):
```markdown
---
name: code-review
description: Review code for quality issues
triggers:
  - before_tool: Bash(git commit)
---

# Code Review Checklist

Before committing, verify:

## Must Have
- [ ] Type hints on function signatures
- [ ] No hardcoded API keys or secrets
- [ ] Error handling for external calls

## Should Have
- [ ] Tests for new functions
- [ ] Docstrings for public functions

If issues found, list them and ask if user wants to fix before committing.
```

**Practical Task**:
"Create a code review workflow:
1. Create `.claude/skills/review.md` with quality checks
2. Make it trigger before git commits
3. Add a function without type hints
4. Try to commit and see the review catch it"

**Verification**:
```yaml
- type: file_exists
  path: .claude/skills/review.md
- type: file_contains
  path: .claude/skills/review.md
  pattern: '(type hint|secret|test)'
```

**Key Takeaway**: Automate quality gates with skills + hooks.

---

## Module 6: Scale & Safety (Lesson 12)

### Lesson 12: Parallel Work, Git & Safety
**Objective**: Work on multiple features safely with worktrees and hooks

**Key Concepts**:
- Git worktrees: multiple branches checked out simultaneously
- Each worktree can have its own Claude session
- Hooks for safety guardrails
- Checkpoints with `/rewind`

**What Students Do**:
- Create a git worktree for a new feature branch
- Start Claude in the worktree (separate session)
- Work on feature while main branch stays stable
- Add safety hooks:
  - Prevent `rm -rf` commands
  - Require confirmation for destructive operations
- Practice `/rewind` to undo mistakes

**Git Worktree Commands**:
```bash
# Create worktree for feature branch
git worktree add ../expense-tracker-feature feature/export-csv

# List worktrees
git worktree list

# Remove when done
git worktree remove ../expense-tracker-feature
```

**Practical Task**:
"Set up parallel development:
1. Create a worktree: `git worktree add ../feature-branch feature/csv-export`
2. In the new worktree, start Claude and implement CSV export
3. Back in main, add a safety hook that blocks `rm -rf` commands
4. Test the safety hook
5. Practice `/rewind` to undo a change"

**Verification**:
```yaml
- type: file_contains
  path: .claude/settings.json
  pattern: 'hooks|block'
- type: commit_exists
  pattern: '.*'
```

**Key Takeaway**: Worktrees + hooks = safe parallel development with guardrails.

---

## Course Progression Summary

| Lesson | Title | Main Skill | Practical Output |
|--------|-------|------------|------------------|
| 1 | Context is Everything | Mental model | Understand context limits |
| 2 | CLAUDE.md | Project memory | Working CLAUDE.md file |
| 3 | Read → Edit → Verify | Core loop | Bug fix with tests |
| 4 | Debugging | Error diagnosis | All tests passing |
| 5 | Spec-Driven | Planning | Feature spec + implementation |
| 6 | Plan Mode | Complex features | Reports module |
| 7 | Sub-Agents | Context isolation | Clean exploration workflow |
| 8 | Custom Commands | Manual workflows | 3 slash commands |
| 9 | Skills | Auto-activation | 2 auto-activating skills |
| 10 | Code Search | Combined workflow | Search command |
| 11 | Code Review | Quality gates | Review skill + hooks |
| 12 | Scale & Safety | Parallel work | Worktrees + safety hooks |

---

## Final Project State

By the end, students have built:

```
expense_tracker/
├── .claude/
│   ├── commands/
│   │   ├── report.md
│   │   ├── backup.md
│   │   ├── test.md
│   │   └── search.md
│   ├── skills/
│   │   ├── lint.md
│   │   ├── test-after-edit.md
│   │   └── review.md
│   └── settings.json (hooks)
├── specs/
│   └── recurring-expenses.md
├── reports/
│   └── 2026-01.md
├── expense_tracker/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── reports.py
│   └── utils.py
├── tests/
│   ├── test_models.py
│   └── test_reports.py
├── CLAUDE.md
└── README.md
```

A complete expense tracking application with:
- Full CRUD for expenses
- Recurring expense support
- Monthly reports
- Data backup/export
- Custom commands for common workflows
- Skills for automated quality checks
- Safety hooks for guardrails
- Git workflow with worktrees

---

## Exercise Files Specification

### Base Expense Tracker Structure

The starter code is a Python CLI expense tracker with SQLite storage.
Students receive the same codebase for each lesson, but with different starting states.

```
expense_tracker/
├── main.py               # CLI entry point
├── models.py             # Expense dataclass + core functions
├── database.py           # SQLite operations
├── utils.py              # Helpers (date parsing, formatting)
├── reports.py            # Report generation (added in Lesson 6)
├── tests/
│   ├── __init__.py
│   ├── test_models.py    # Model tests (some failing initially)
│   ├── test_database.py  # DB tests
│   └── test_reports.py   # Report tests (added in Lesson 6)
├── data/
│   └── expenses.db       # SQLite database (seeded with sample data)
└── README.md             # Usage instructions
```

---

### File Contents

#### `main.py` (~80 lines)
```python
#!/usr/bin/env python3
"""Expense Tracker CLI - Track your daily expenses."""

import argparse
from datetime import datetime
from models import add_expense, list_expenses, delete_expense, get_expense
from utils import format_currency, parse_date
from database import init_db

def main():
    parser = argparse.ArgumentParser(description="Track your expenses")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add expense
    add_parser = subparsers.add_parser("add", help="Add a new expense")
    add_parser.add_argument("amount", type=float, help="Amount spent")
    add_parser.add_argument("category", help="Category (Food, Transport, etc.)")
    add_parser.add_argument("description", help="What was the expense for?")
    add_parser.add_argument("--date", help="Date (YYYY-MM-DD), defaults to today")

    # List expenses
    list_parser = subparsers.add_parser("list", help="List expenses")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument("--month", help="Filter by month (YYYY-MM)")
    list_parser.add_argument("--limit", type=int, default=10, help="Max results")

    # Delete expense
    delete_parser = subparsers.add_parser("delete", help="Delete an expense")
    delete_parser.add_argument("id", help="Expense ID to delete")

    # Show single expense
    show_parser = subparsers.add_parser("show", help="Show expense details")
    show_parser.add_argument("id", help="Expense ID")

    # Summary
    subparsers.add_parser("summary", help="Show spending summary")

    args = parser.parse_args()

    # Initialize database
    init_db()

    if args.command == "add":
        date = parse_date(args.date) if args.date else datetime.now()
        expense = add_expense(args.amount, args.category, args.description, date)
        print(f"Added expense: {expense.id} - {format_currency(expense.amount)}")

    elif args.command == "list":
        expenses = list_expenses(
            category=args.category,
            month=args.month,
            limit=args.limit
        )
        if not expenses:
            print("No expenses found.")
        for exp in expenses:
            print(f"{exp.id} | {exp.date.strftime('%Y-%m-%d')} | "
                  f"{exp.category:12} | {format_currency(exp.amount):>10} | {exp.description}")

    elif args.command == "delete":
        if delete_expense(args.id):
            print(f"Deleted expense {args.id}")
        else:
            print(f"Expense {args.id} not found")

    elif args.command == "show":
        expense = get_expense(args.id)
        if expense:
            print(f"ID:          {expense.id}")
            print(f"Amount:      {format_currency(expense.amount)}")
            print(f"Category:    {expense.category}")
            print(f"Description: {expense.description}")
            print(f"Date:        {expense.date.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"Expense {args.id} not found")

    elif args.command == "summary":
        expenses = list_expenses()
        total = sum(e.amount for e in expenses)
        print(f"Total expenses: {format_currency(total)}")

        # Group by category
        categories = {}
        for exp in expenses:
            categories[exp.category] = categories.get(exp.category, 0) + exp.amount

        print("\nBy category:")
        for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat:15} {format_currency(amount):>10}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

---

#### `models.py` (~100 lines)
```python
"""Expense data models and core operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid
from database import save_expense, load_expenses, remove_expense, get_expense_by_id

@dataclass
class Expense:
    id: str
    amount: float
    category: str
    description: str
    date: datetime
    recurring: bool = False
    recurring_frequency: Optional[str] = None  # 'daily', 'weekly', 'monthly'


def generate_id() -> str:
    """Generate a unique expense ID."""
    return str(uuid.uuid4())[:8]


def add_expense(
    amount: float,
    category: str,
    description: str,
    date: Optional[datetime] = None
) -> Expense:
    """Add a new expense.

    BUG (Lesson 3): No validation - allows negative amounts!
    """
    # TODO: Validate amount > 0
    # TODO: Validate category is not empty

    expense = Expense(
        id=generate_id(),
        amount=amount,
        category=category,
        description=description,
        date=date or datetime.now()
    )
    save_expense(expense)
    return expense


def list_expenses(
    category: Optional[str] = None,
    month: Optional[str] = None,
    limit: int = 100
) -> list[Expense]:
    """List expenses with optional filters.

    BUG (Lesson 4): Category filtering is case-sensitive!
    'food' won't match 'Food'. Should be case-insensitive.
    """
    expenses = load_expenses()

    if category:
        # BUG: Case-sensitive comparison
        expenses = [e for e in expenses if e.category == category]

    if month:
        # Filter by YYYY-MM
        expenses = [e for e in expenses if e.date.strftime('%Y-%m') == month]

    # Sort by date descending
    expenses.sort(key=lambda x: x.date, reverse=True)

    return expenses[:limit]


def get_expense(expense_id: str) -> Optional[Expense]:
    """Get a single expense by ID."""
    return get_expense_by_id(expense_id)


def delete_expense(expense_id: str) -> bool:
    """Delete an expense by ID."""
    return remove_expense(expense_id)


def get_total_by_category(category: str) -> float:
    """Get total spent in a category.

    BUG: Also case-sensitive - shares bug with list_expenses.
    """
    expenses = list_expenses(category=category)
    return sum(e.amount for e in expenses)
```

---

#### `database.py` (~120 lines)
```python
"""SQLite database operations for expense storage."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "data" / "expenses.db"


@contextmanager
def get_connection():
    """Get a database connection with proper cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                recurring INTEGER DEFAULT 0,
                recurring_frequency TEXT
            )
        ''')


def save_expense(expense) -> None:
    """Save an expense to the database."""
    with get_connection() as conn:
        conn.execute('''
            INSERT INTO expenses (id, amount, category, description, date, recurring, recurring_frequency)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            expense.id,
            expense.amount,
            expense.category,
            expense.description,
            expense.date.isoformat(),
            1 if expense.recurring else 0,
            expense.recurring_frequency
        ))


def load_expenses() -> list:
    """Load all expenses from the database."""
    from models import Expense  # Avoid circular import

    with get_connection() as conn:
        rows = conn.execute('SELECT * FROM expenses ORDER BY date DESC').fetchall()

    expenses = []
    for row in rows:
        expenses.append(Expense(
            id=row['id'],
            amount=row['amount'],
            category=row['category'],
            description=row['description'],
            date=datetime.fromisoformat(row['date']),
            recurring=bool(row['recurring']),
            recurring_frequency=row['recurring_frequency']
        ))

    return expenses


def get_expense_by_id(expense_id: str) -> Optional['Expense']:
    """Get a single expense by ID."""
    from models import Expense

    with get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM expenses WHERE id = ?',
            (expense_id,)
        ).fetchone()

    if not row:
        return None

    return Expense(
        id=row['id'],
        amount=row['amount'],
        category=row['category'],
        description=row['description'],
        date=datetime.fromisoformat(row['date']),
        recurring=bool(row['recurring']),
        recurring_frequency=row['recurring_frequency']
    )


def remove_expense(expense_id: str) -> bool:
    """Remove an expense from the database."""
    with get_connection() as conn:
        cursor = conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        return cursor.rowcount > 0


def clear_all_expenses():
    """Clear all expenses (for testing)."""
    with get_connection() as conn:
        conn.execute('DELETE FROM expenses')
```

---

#### `utils.py` (~60 lines)
```python
"""Utility functions for the expense tracker."""

from datetime import datetime
from typing import Optional
import locale


def format_currency(amount: float) -> str:
    """Format amount as currency.

    Returns formatted string like '$1,234.56'
    """
    try:
        locale.setlocale(locale.LC_ALL, '')
        return locale.currency(amount, grouping=True)
    except:
        # Fallback if locale not available
        return f"${amount:,.2f}"


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a date string in various formats.

    Supports:
    - YYYY-MM-DD
    - MM/DD/YYYY
    - today, yesterday
    """
    if not date_str:
        return None

    date_str = date_str.lower().strip()

    if date_str == 'today':
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if date_str == 'yesterday':
        from datetime import timedelta
        return (datetime.now() - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # Try YYYY-MM-DD
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        pass

    # Try MM/DD/YYYY
    try:
        return datetime.strptime(date_str, '%m/%d/%Y')
    except ValueError:
        pass

    raise ValueError(f"Could not parse date: {date_str}")


def validate_category(category: str) -> str:
    """Normalize category name.

    Capitalizes first letter, strips whitespace.
    """
    return category.strip().capitalize()


VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Entertainment",
    "Shopping",
    "Bills",
    "Health",
    "Education",
    "Other"
]
```

---

#### `tests/test_models.py` (~80 lines)
```python
"""Tests for expense models."""

import pytest
from datetime import datetime
from models import add_expense, list_expenses, delete_expense, get_expense, Expense
from database import init_db, clear_all_expenses


@pytest.fixture(autouse=True)
def setup_db():
    """Set up a clean database for each test."""
    init_db()
    clear_all_expenses()
    yield
    clear_all_expenses()


class TestAddExpense:
    def test_add_basic_expense(self):
        """Test adding a simple expense."""
        expense = add_expense(50.0, "Food", "Lunch")

        assert expense.amount == 50.0
        assert expense.category == "Food"
        assert expense.description == "Lunch"
        assert expense.id is not None

    def test_add_expense_with_date(self):
        """Test adding expense with specific date."""
        date = datetime(2026, 1, 15, 12, 0)
        expense = add_expense(25.0, "Transport", "Uber", date)

        assert expense.date == date

    def test_add_negative_amount_should_fail(self):
        """BUG TEST: Negative amounts should raise ValueError.

        This test will FAIL initially - students fix this in Lesson 3.
        """
        with pytest.raises(ValueError):
            add_expense(-50.0, "Food", "Invalid expense")

    def test_add_zero_amount_should_fail(self):
        """BUG TEST: Zero amount should raise ValueError."""
        with pytest.raises(ValueError):
            add_expense(0, "Food", "Free lunch?")


class TestListExpenses:
    def test_list_all_expenses(self):
        """Test listing all expenses."""
        add_expense(50.0, "Food", "Lunch")
        add_expense(30.0, "Transport", "Bus")

        expenses = list_expenses()
        assert len(expenses) == 2

    def test_list_by_category(self):
        """Test filtering by category."""
        add_expense(50.0, "Food", "Lunch")
        add_expense(30.0, "Transport", "Uber")
        add_expense(25.0, "Food", "Coffee")

        food = list_expenses(category="Food")
        assert len(food) == 2

    def test_list_by_category_case_insensitive(self):
        """BUG TEST: Category filter should be case-insensitive.

        This test will FAIL initially - students fix this in Lesson 4.
        """
        add_expense(50.0, "Food", "Lunch")
        add_expense(25.0, "food", "Coffee")  # lowercase

        # Should find both regardless of case
        food = list_expenses(category="Food")
        assert len(food) == 2

    def test_list_by_month(self):
        """Test filtering by month."""
        add_expense(50.0, "Food", "Lunch", datetime(2026, 1, 15))
        add_expense(30.0, "Food", "Dinner", datetime(2026, 2, 10))

        jan = list_expenses(month="2026-01")
        assert len(jan) == 1
        assert jan[0].description == "Lunch"


class TestDeleteExpense:
    def test_delete_existing(self):
        """Test deleting an expense."""
        expense = add_expense(50.0, "Food", "Lunch")

        result = delete_expense(expense.id)
        assert result is True

        # Verify it's gone
        assert get_expense(expense.id) is None

    def test_delete_nonexistent(self):
        """Test deleting non-existent expense."""
        result = delete_expense("fake-id")
        assert result is False
```

---

### Lesson-Specific File States

Each lesson starts with a specific state of the codebase:

| Lesson | State Changes |
|--------|--------------|
| 1-2 | Base code as shown above. All files present. 2 failing tests. |
| 3 | Same as 1-2. Student fixes negative amount validation. |
| 4 | After L3 fix. Student fixes case-insensitive category bug. |
| 5 | After L4 fixes. Student adds recurring expense feature. |
| 6 | After L5. `reports.py` is empty stub - student implements. |
| 7-9 | Full working code. Focus is on commands/skills, not code. |
| 10-11 | Full working code. Focus is on workflows. |
| 12 | Full working code + all commands/skills from previous lessons. |

---

### Sample Data (Seeded Database)

Each lesson starts with seeded sample expenses:

```python
SAMPLE_EXPENSES = [
    # January 2026
    {"amount": 45.50, "category": "Food", "desc": "Grocery shopping", "date": "2026-01-15"},
    {"amount": 12.00, "category": "Transport", "desc": "Uber to airport", "date": "2026-01-14"},
    {"amount": 89.99, "category": "Shopping", "desc": "Running shoes", "date": "2026-01-10"},
    {"amount": 150.00, "category": "Bills", "desc": "Electric bill", "date": "2026-01-01"},
    {"amount": 8.50, "category": "food", "desc": "Coffee", "date": "2026-01-20"},  # lowercase - triggers bug
    {"amount": 35.00, "category": "Entertainment", "desc": "Movie tickets", "date": "2026-01-18"},
    {"amount": 22.00, "category": "Food", "desc": "Lunch with team", "date": "2026-01-19"},
    {"amount": 65.00, "category": "Health", "desc": "Gym membership", "date": "2026-01-01"},

    # December 2025 (for month filtering tests)
    {"amount": 200.00, "category": "Shopping", "desc": "Holiday gifts", "date": "2025-12-20"},
    {"amount": 55.00, "category": "Food", "desc": "Holiday dinner", "date": "2025-12-25"},
]
```

This gives students:
- 10 expenses to work with
- A mix of categories
- One intentional lowercase "food" to trigger the case bug
- Data spanning two months for filter testing

---

### README.md (Provided to Students)
```markdown
# Expense Tracker

A simple CLI expense tracker built with Python and SQLite.

## Setup

```bash
# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install pytest

# Initialize database with sample data
python -c "from database import init_db; init_db()"
```

## Usage

```bash
# Add an expense
python main.py add 45.50 Food "Grocery shopping"

# Add expense with specific date
python main.py add 25.00 Transport "Uber" --date 2026-01-15

# List all expenses
python main.py list

# List expenses by category
python main.py list --category Food

# List expenses by month
python main.py list --month 2026-01

# Show expense details
python main.py show abc123

# Delete an expense
python main.py delete abc123

# Show spending summary
python main.py summary
```

## Running Tests

```bash
pytest -v
```

## Project Structure

- `main.py` - CLI entry point
- `models.py` - Expense data model and core functions
- `database.py` - SQLite database operations
- `utils.py` - Helper functions
- `tests/` - Test suite
```

---

#### `reports.py` (Stub for Lesson 6)
```python
"""Report generation for expense tracker.

TODO: This module is incomplete. Students implement it in Lesson 6.

Features to implement:
- Monthly expense report
- Category breakdown
- Top expenses
- Export to markdown file
"""

from datetime import datetime
from typing import Optional
from models import list_expenses, Expense
from utils import format_currency


def generate_monthly_report(month: Optional[str] = None) -> str:
    """Generate a monthly expense report.

    Args:
        month: Month in YYYY-MM format. Defaults to current month.

    Returns:
        Formatted report as string.

    TODO (Lesson 6): Implement this function.
    The report should include:
    - Total spent
    - Breakdown by category
    - Top 5 expenses
    """
    raise NotImplementedError("Implement this in Lesson 6!")


def get_category_breakdown(expenses: list[Expense]) -> dict[str, float]:
    """Get spending breakdown by category.

    TODO (Lesson 6): Implement this function.
    """
    raise NotImplementedError("Implement this in Lesson 6!")


def get_top_expenses(expenses: list[Expense], n: int = 5) -> list[Expense]:
    """Get the top N expenses by amount.

    TODO (Lesson 6): Implement this function.
    """
    raise NotImplementedError("Implement this in Lesson 6!")


def save_report(report: str, filename: str) -> None:
    """Save report to a file.

    TODO (Lesson 6): Implement this function.
    """
    raise NotImplementedError("Implement this in Lesson 6!")
```

---

#### `seed_data.py` (Setup Script)
```python
#!/usr/bin/env python3
"""Seed the database with sample expenses for learning."""

from datetime import datetime
from database import init_db, clear_all_expenses
from models import add_expense

SAMPLE_EXPENSES = [
    # January 2026
    (45.50, "Food", "Grocery shopping", "2026-01-15"),
    (12.00, "Transport", "Uber to airport", "2026-01-14"),
    (89.99, "Shopping", "Running shoes", "2026-01-10"),
    (150.00, "Bills", "Electric bill", "2026-01-01"),
    (8.50, "food", "Coffee", "2026-01-20"),  # lowercase - intentional bug trigger
    (35.00, "Entertainment", "Movie tickets", "2026-01-18"),
    (22.00, "Food", "Lunch with team", "2026-01-19"),
    (65.00, "Health", "Gym membership", "2026-01-01"),

    # December 2025 (for month filtering tests)
    (200.00, "Shopping", "Holiday gifts", "2025-12-20"),
    (55.00, "Food", "Holiday dinner", "2025-12-25"),
]


def seed_database():
    """Initialize and seed the database."""
    print("Initializing database...")
    init_db()

    print("Clearing existing data...")
    clear_all_expenses()

    print("Adding sample expenses...")
    for amount, category, desc, date_str in SAMPLE_EXPENSES:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        expense = add_expense(amount, category, desc, date)
        print(f"  Added: {expense.id} - ${amount:.2f} - {desc}")

    print(f"\nSeeded {len(SAMPLE_EXPENSES)} expenses.")
    print("Run 'python main.py list' to see them.")


if __name__ == "__main__":
    seed_database()
```

---

### Exercise File Variations by Lesson

#### Lesson 3 Fix (Validation)

After students complete Lesson 3, `models.py` should have:

```python
def add_expense(
    amount: float,
    category: str,
    description: str,
    date: Optional[datetime] = None
) -> Expense:
    """Add a new expense with validation."""
    # FIXED: Validate amount
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

---

#### Lesson 4 Fix (Case-Insensitive Categories)

After students complete Lesson 4, `models.py` should have:

```python
def list_expenses(
    category: Optional[str] = None,
    month: Optional[str] = None,
    limit: int = 100
) -> list[Expense]:
    """List expenses with optional filters."""
    expenses = load_expenses()

    if category:
        # FIXED: Case-insensitive comparison
        category_lower = category.lower()
        expenses = [e for e in expenses if e.category.lower() == category_lower]

    if month:
        expenses = [e for e in expenses if e.date.strftime('%Y-%m') == month]

    expenses.sort(key=lambda x: x.date, reverse=True)
    return expenses[:limit]
```

---

#### Lesson 5 Addition (Recurring Expenses)

After Lesson 5, students add to `models.py`:

```python
def add_recurring_expense(
    amount: float,
    category: str,
    description: str,
    frequency: str = "monthly"
) -> Expense:
    """Add a recurring expense.

    Args:
        frequency: 'daily', 'weekly', or 'monthly'
    """
    if frequency not in ('daily', 'weekly', 'monthly'):
        raise ValueError("Frequency must be 'daily', 'weekly', or 'monthly'")

    if amount <= 0:
        raise ValueError("Amount must be greater than 0")

    expense = Expense(
        id=generate_id(),
        amount=amount,
        category=category,
        description=description,
        date=datetime.now(),
        recurring=True,
        recurring_frequency=frequency
    )
    save_expense(expense)
    return expense


def list_recurring_expenses() -> list[Expense]:
    """List all recurring expenses."""
    expenses = load_expenses()
    return [e for e in expenses if e.recurring]
```

---

#### Lesson 6 Implementation (Reports)

After Lesson 6, `reports.py` should be fully implemented:

```python
"""Report generation for expense tracker."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from models import list_expenses, Expense
from utils import format_currency


def generate_monthly_report(month: Optional[str] = None) -> str:
    """Generate a monthly expense report."""
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    expenses = list_expenses(month=month)

    if not expenses:
        return f"# Expense Report: {month}\n\nNo expenses found."

    total = sum(e.amount for e in expenses)
    breakdown = get_category_breakdown(expenses)
    top = get_top_expenses(expenses, 5)

    report = f"""# Expense Report: {month}

## Summary
- **Total Spent:** {format_currency(total)}
- **Number of Expenses:** {len(expenses)}

## By Category
"""
    for cat, amount in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
        pct = (amount / total) * 100
        report += f"- {cat}: {format_currency(amount)} ({pct:.1f}%)\n"

    report += "\n## Top 5 Expenses\n"
    for i, exp in enumerate(top, 1):
        report += f"{i}. {format_currency(exp.amount)} - {exp.description} ({exp.category})\n"

    return report


def get_category_breakdown(expenses: list[Expense]) -> dict[str, float]:
    """Get spending breakdown by category."""
    breakdown = {}
    for exp in expenses:
        breakdown[exp.category] = breakdown.get(exp.category, 0) + exp.amount
    return breakdown


def get_top_expenses(expenses: list[Expense], n: int = 5) -> list[Expense]:
    """Get the top N expenses by amount."""
    return sorted(expenses, key=lambda x: x.amount, reverse=True)[:n]


def save_report(report: str, filename: str) -> None:
    """Save report to a file."""
    path = Path("reports") / filename
    path.parent.mkdir(exist_ok=True)
    path.write_text(report)
    print(f"Report saved to {path}")
```

---

### Testing Checklist

For exercise files to be ready:

1. [ ] Base code runs: `python main.py list` works
2. [ ] Seeding works: `python seed_data.py` populates data
3. [ ] Tests run: `pytest -v` executes (2 tests fail intentionally)
4. [ ] Bug 1 exists: Negative amounts accepted
5. [ ] Bug 2 exists: Category filtering is case-sensitive
6. [ ] reports.py stub raises NotImplementedError
7. [ ] Sample data has lowercase "food" entry to trigger bug

---

### Commands & Skills Templates (Lessons 8-11)

These are the expected outputs students create. Provided as reference for verification.

#### Lesson 8: Custom Commands

**`.claude/commands/report.md`**
```markdown
# Generate Expense Report

Generate a monthly expense report and save it to the reports folder.

## Arguments
- `$ARGUMENTS`: Optional month in YYYY-MM format. Defaults to current month.

## Steps
1. If no month provided, use current month
2. Import and call `generate_monthly_report(month)` from reports.py
3. Save output to `reports/{month}.md`
4. Print summary of total spent

## Example
User runs: `/report 2026-01`
Result: Creates `reports/2026-01.md` with full report
```

**`.claude/commands/backup.md`**
```markdown
# Backup Expenses

Export all expenses to a JSON backup file.

## Steps
1. Read all expenses from database using `list_expenses()`
2. Convert to JSON format with proper date serialization
3. Save to `backups/expenses_{timestamp}.json`
4. Print count of expenses backed up

## Output Format
```json
{
  "exported_at": "2026-01-20T10:30:00",
  "count": 10,
  "expenses": [
    {"id": "abc123", "amount": 45.50, "category": "Food", ...}
  ]
}
```
```

**`.claude/commands/test.md`**
```markdown
# Run Tests

Run the test suite with verbose output.

## Steps
1. Run `pytest -v` in the project root
2. If any tests fail, summarize which ones
3. Report pass/fail count

## Options
- Add `--coverage` argument to also run with coverage report
```

---

#### Lesson 9: Skills (Auto-Activating)

**`.claude/skills/lint.md`**
```markdown
---
name: lint
description: Suggest running linter after Python code changes
triggers:
  - after_tool: Edit
  - after_tool: Write
---

# Lint After Changes

When a Python file is modified (.py extension), suggest:

"I've modified Python code. Want me to run `ruff check {filename}` to check for issues?"

Only trigger for .py files. Skip for:
- __init__.py (usually empty)
- Test files (test_*.py) unless specifically editing test logic
- Config files (conftest.py, setup.py)
```

**`.claude/skills/test-after-edit.md`**
```markdown
---
name: test-after-edit
description: Remind to run tests after code changes
triggers:
  - after_tool: Edit
  - after_tool: Write
---

# Test After Edit

When code in these files is modified:
- models.py
- database.py
- utils.py
- reports.py

Suggest: "I've made changes to core code. Want me to run `pytest -v` to make sure nothing broke?"

Skip this reminder for:
- CLAUDE.md or documentation
- Files in .claude/ directory
- Test files themselves
```

---

#### Lesson 10: Search Command

**`.claude/commands/search.md`**
```markdown
# Code Search

Search the codebase for a concept, pattern, or functionality.

## Arguments
- `$ARGUMENTS`: The search query (e.g., "how does filtering work?")

## Process

### Step 1: Understand the Query
Determine if this is:
- A function/class lookup (grep for definition)
- A concept explanation (read related files)
- A flow trace (follow call chain)

### Step 2: Search
Use grep to find relevant files:
```
grep -r "keyword" --include="*.py" .
```

### Step 3: Read and Trace
Read the most relevant files (max 3).
Follow imports and function calls to understand the flow.

### Step 4: Summarize
Return a summary with:
- **Answer**: Direct answer to the question
- **Key Files**: List of relevant files with line numbers
- **Flow**: How data/control flows through the code

## Example
Query: "how does category filtering work?"

Answer: Category filtering happens in `list_expenses()` in models.py:42.
It compares the category parameter against each expense's category field.

Key Files:
- models.py:42-48 - list_expenses() filter logic
- database.py:67-82 - load_expenses() fetches from SQLite

Flow: CLI (main.py) → list_expenses(category=X) → load_expenses() → filter → return
```

---

#### Lesson 11: Code Review Skill

**`.claude/skills/review.md`**
```markdown
---
name: code-review
description: Review code quality before commits
triggers:
  - before_tool: Bash
  - pattern: git commit
---

# Pre-Commit Code Review

Before allowing a git commit, check the staged changes for:

## Must Fix (Block Commit)
- [ ] Hardcoded secrets (API keys, passwords, tokens)
- [ ] Syntax errors in Python files
- [ ] Import errors (missing modules)

## Should Fix (Warn)
- [ ] Missing type hints on new functions
- [ ] Functions over 50 lines (suggest splitting)
- [ ] No docstring on public functions
- [ ] Magic numbers without explanation

## Nice to Have (Mention)
- [ ] Test coverage for new functions
- [ ] Consistent naming conventions

## Process
1. Run `git diff --cached` to see staged changes
2. For each modified .py file, check against rules
3. If "Must Fix" issues found: List them and say "Please fix before committing"
4. If only "Should Fix": List them and ask "Commit anyway? (y/n)"
5. If clean: "Looks good! Proceeding with commit."

## Example Output
```
📋 Code Review

Must Fix:
- models.py:15 - Hardcoded API key detected: "sk-..."

Should Fix:
- models.py:42 - Function `process_data` missing type hints
- utils.py:28 - Magic number 86400 (add comment: seconds per day?)

Please fix the hardcoded API key before committing.
```
```

---

### Project Configuration Files

**`pyproject.toml`**
```toml
[project]
name = "expense-tracker"
version = "0.1.0"
description = "A simple CLI expense tracker for Claude Code course"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long (handled separately)
```

**`.gitignore`**
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
venv/
.venv/

# Database
*.db

# IDE
.idea/
.vscode/
*.swp

# Reports (generated)
reports/*.md

# Backups
backups/

# OS
.DS_Store
```

---

### File Size Targets

To ensure context fills appropriately in Lesson 1:

| File | Target Lines | Purpose |
|------|--------------|---------|
| main.py | 80-100 | CLI entry point |
| models.py | 100-120 | Core logic with bugs |
| database.py | 120-140 | SQLite operations |
| utils.py | 60-80 | Helpers |
| reports.py | 80-100 | Report generation (stub → full) |
| test_models.py | 80-100 | Tests with failing cases |
| test_database.py | 40-60 | DB tests |
| README.md | 50-70 | Documentation |

**Total: ~600-770 lines** in main files

With tests and config: **~800-1000 lines**

This should fill context to 40-60% when all files are read, which is enough to demonstrate context limits in Lesson 1.

---

### Lesson 12: Safety Hooks & Git Configuration

**`.claude/settings.json`** (After Lesson 12)
```json
{
  "hooks": {
    "pre_command": [
      {
        "pattern": "rm -rf",
        "action": "block",
        "message": "🛑 Blocked: 'rm -rf' is too dangerous. Use 'rm -r' with specific paths instead."
      },
      {
        "pattern": "git push --force",
        "action": "confirm",
        "message": "⚠️ Force push detected. This will overwrite remote history. Continue?"
      },
      {
        "pattern": "DROP TABLE|DROP DATABASE",
        "action": "block",
        "message": "🛑 Blocked: Destructive SQL operation detected."
      }
    ],
    "post_edit": [
      {
        "pattern": "\\.py$",
        "action": "run",
        "command": "ruff check --quiet"
      }
    ]
  },
  "safety": {
    "confirm_destructive_commands": true,
    "max_file_size_kb": 100,
    "blocked_paths": [
      "/etc",
      "/usr",
      "~/.ssh"
    ]
  }
}
```

---

### Additional Test Files

**`tests/test_database.py`**
```python
"""Tests for database operations."""

import pytest
from datetime import datetime
from database import init_db, clear_all_expenses, save_expense, load_expenses, get_expense_by_id
from models import Expense


@pytest.fixture(autouse=True)
def setup_db():
    """Set up a clean database for each test."""
    init_db()
    clear_all_expenses()
    yield
    clear_all_expenses()


class TestDatabaseOperations:
    def test_save_and_load(self):
        """Test saving and loading an expense."""
        expense = Expense(
            id="test123",
            amount=50.0,
            category="Food",
            description="Test expense",
            date=datetime.now()
        )
        save_expense(expense)

        expenses = load_expenses()
        assert len(expenses) == 1
        assert expenses[0].id == "test123"
        assert expenses[0].amount == 50.0

    def test_get_by_id(self):
        """Test retrieving expense by ID."""
        expense = Expense(
            id="abc456",
            amount=25.0,
            category="Transport",
            description="Bus fare",
            date=datetime.now()
        )
        save_expense(expense)

        result = get_expense_by_id("abc456")
        assert result is not None
        assert result.description == "Bus fare"

    def test_get_nonexistent_id(self):
        """Test retrieving non-existent expense."""
        result = get_expense_by_id("fake-id")
        assert result is None

    def test_clear_all(self):
        """Test clearing all expenses."""
        expense = Expense(
            id="temp123",
            amount=10.0,
            category="Other",
            description="Temporary",
            date=datetime.now()
        )
        save_expense(expense)
        assert len(load_expenses()) == 1

        clear_all_expenses()
        assert len(load_expenses()) == 0
```

**`tests/test_reports.py`** (Added after Lesson 6)
```python
"""Tests for report generation."""

import pytest
from datetime import datetime
from reports import generate_monthly_report, get_category_breakdown, get_top_expenses
from models import add_expense, Expense
from database import init_db, clear_all_expenses


@pytest.fixture(autouse=True)
def setup_db():
    """Set up a clean database for each test."""
    init_db()
    clear_all_expenses()
    yield
    clear_all_expenses()


class TestReportGeneration:
    def test_empty_month_report(self):
        """Test report for month with no expenses."""
        report = generate_monthly_report("2020-01")
        assert "No expenses found" in report

    def test_monthly_report_content(self):
        """Test report includes expected sections."""
        add_expense(100.0, "Food", "Groceries", datetime(2026, 1, 15))
        add_expense(50.0, "Transport", "Uber", datetime(2026, 1, 15))

        report = generate_monthly_report("2026-01")

        assert "Total Spent" in report
        assert "$150.00" in report or "150.00" in report
        assert "Food" in report
        assert "Transport" in report


class TestCategoryBreakdown:
    def test_single_category(self):
        """Test breakdown with single category."""
        expenses = [
            Expense("1", 50.0, "Food", "Lunch", datetime.now()),
            Expense("2", 25.0, "Food", "Coffee", datetime.now()),
        ]

        breakdown = get_category_breakdown(expenses)
        assert breakdown["Food"] == 75.0

    def test_multiple_categories(self):
        """Test breakdown with multiple categories."""
        expenses = [
            Expense("1", 50.0, "Food", "Lunch", datetime.now()),
            Expense("2", 30.0, "Transport", "Bus", datetime.now()),
            Expense("3", 20.0, "Food", "Snack", datetime.now()),
        ]

        breakdown = get_category_breakdown(expenses)
        assert breakdown["Food"] == 70.0
        assert breakdown["Transport"] == 30.0


class TestTopExpenses:
    def test_top_expenses_ordering(self):
        """Test expenses are sorted by amount descending."""
        expenses = [
            Expense("1", 25.0, "Food", "Small", datetime.now()),
            Expense("2", 100.0, "Bills", "Big", datetime.now()),
            Expense("3", 50.0, "Shopping", "Medium", datetime.now()),
        ]

        top = get_top_expenses(expenses, 3)
        assert top[0].amount == 100.0
        assert top[1].amount == 50.0
        assert top[2].amount == 25.0

    def test_top_n_limit(self):
        """Test limiting to N expenses."""
        expenses = [
            Expense(str(i), float(i * 10), "Cat", "Desc", datetime.now())
            for i in range(1, 11)
        ]

        top = get_top_expenses(expenses, 3)
        assert len(top) == 3
```

**`tests/conftest.py`**
```python
"""Pytest configuration and shared fixtures."""

import pytest
import os
from pathlib import Path

# Use in-memory or temp database for tests
os.environ["EXPENSE_TRACKER_TEST"] = "1"


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_expenses.db"
    os.environ["EXPENSE_DB_PATH"] = str(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()
```

---

### Checkpoint Files by Lesson

Each lesson saves a checkpoint of the expected state. Used for:
1. Resetting if student makes mistakes
2. Verifying correct completion
3. Starting later lessons from correct state

```
checkpoints/
├── lesson-01-start/          # Base files, no changes
├── lesson-02-complete/       # + CLAUDE.md
├── lesson-03-complete/       # + validation fix in models.py
├── lesson-04-complete/       # + case-insensitive fix
├── lesson-05-complete/       # + recurring expense feature
├── lesson-06-complete/       # + reports.py implemented
├── lesson-07-complete/       # (same code, sub-agent exercise)
├── lesson-08-complete/       # + .claude/commands/
├── lesson-09-complete/       # + .claude/skills/
├── lesson-10-complete/       # + search command
├── lesson-11-complete/       # + review skill
└── lesson-12-complete/       # + hooks + worktree demo
```

Each checkpoint is a complete copy that can be used to reset the sandbox.

---

### Implementation Notes

1. **Database Location**: Use `data/expenses.db` relative to project root. Tests use temp DB.

2. **Python Version**: Require 3.10+ for native type hints (`list[X]` instead of `List[X]`)

3. **No External Dependencies**: Core app uses only stdlib. Dev deps (pytest, ruff) are optional.

4. **Error Messages**: Make error messages helpful for debugging exercises.

5. **Code Comments**: Include `# BUG:` and `# TODO:` comments where students need to make changes.

6. **Consistent Style**: Use Black-compatible formatting, type hints, docstrings on public functions.

---

### Verification Scripts

For each lesson, create a verification script that runs after submission:

**`verify_lesson.py`**
```python
#!/usr/bin/env python3
"""Verify lesson completion."""

import sys
import subprocess
from pathlib import Path


def verify_lesson_3():
    """Verify: Negative amount validation added."""
    from models import add_expense

    try:
        add_expense(-10, "Food", "Invalid")
        print("❌ FAIL: Negative amounts should raise ValueError")
        return False
    except ValueError:
        print("✅ PASS: Negative amounts correctly rejected")
        return True


def verify_lesson_4():
    """Verify: Case-insensitive category filtering."""
    from models import add_expense, list_expenses
    from database import init_db, clear_all_expenses

    init_db()
    clear_all_expenses()

    add_expense(10, "Food", "Test1")
    add_expense(20, "food", "Test2")  # lowercase

    results = list_expenses(category="Food")
    clear_all_expenses()

    if len(results) == 2:
        print("✅ PASS: Category filtering is case-insensitive")
        return True
    else:
        print(f"❌ FAIL: Expected 2 results, got {len(results)}")
        return False


def verify_lesson_6():
    """Verify: Reports module implemented."""
    try:
        from reports import generate_monthly_report, get_category_breakdown

        # Should not raise NotImplementedError
        report = generate_monthly_report("2026-01")
        if "NotImplementedError" in str(type(report)):
            raise NotImplementedError()

        print("✅ PASS: Reports module implemented")
        return True
    except NotImplementedError:
        print("❌ FAIL: Reports module still has NotImplementedError")
        return False


def verify_lesson_8():
    """Verify: Custom commands created."""
    commands = [
        ".claude/commands/report.md",
        ".claude/commands/backup.md",
        ".claude/commands/test.md",
    ]

    all_exist = True
    for cmd in commands:
        if Path(cmd).exists():
            print(f"✅ {cmd} exists")
        else:
            print(f"❌ {cmd} missing")
            all_exist = False

    return all_exist


VERIFIERS = {
    3: verify_lesson_3,
    4: verify_lesson_4,
    6: verify_lesson_6,
    8: verify_lesson_8,
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_lesson.py <lesson_number>")
        sys.exit(1)

    lesson = int(sys.argv[1])
    if lesson in VERIFIERS:
        success = VERIFIERS[lesson]()
        sys.exit(0 if success else 1)
    else:
        print(f"No verifier for lesson {lesson}")
        sys.exit(1)
```
