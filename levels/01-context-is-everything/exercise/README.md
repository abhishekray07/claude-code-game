# Expense Tracker

A simple CLI expense tracker built with Python and SQLite.

This is the project used throughout the Claude Code course. You'll learn to use
Claude Code to understand, debug, and extend this codebase.

## Quick Start

```bash
# 1. Seed the database with sample data
python seed_data.py

# 2. Try some commands
python main.py list
python main.py summary
python main.py list --category Food
```

## Commands

### Add an expense
```bash
python main.py add <amount> <category> <description> [--date YYYY-MM-DD]

# Examples:
python main.py add 45.50 Food "Grocery shopping"
python main.py add 25.00 Transport "Uber" --date 2026-01-15
```

### List expenses
```bash
python main.py list [--category CATEGORY] [--month YYYY-MM] [--limit N]

# Examples:
python main.py list
python main.py list --category Food
python main.py list --month 2026-01
python main.py list --limit 5
```

### Show expense details
```bash
python main.py show <expense_id>

# Example:
python main.py show abc123
```

### Delete an expense
```bash
python main.py delete <expense_id>

# Example:
python main.py delete abc123
```

### View spending summary
```bash
python main.py summary
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models.py

# Run tests matching a pattern
pytest -k "category"
```

## Project Structure

```
expense_tracker/
├── main.py           # CLI entry point
├── models.py         # Expense data model and core functions
├── database.py       # SQLite database operations
├── utils.py          # Helper functions (formatting, parsing)
├── reports.py        # Report generation (Lesson 6)
├── seed_data.py      # Script to populate sample data
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_models.py    # Model tests
│   ├── test_database.py  # Database tests
│   └── test_reports.py   # Report tests (Lesson 6)
├── data/
│   └── expenses.db   # SQLite database (created on first run)
└── README.md
```

## Course Lessons

This codebase is used in the following lessons:

| Lesson | Focus | What You'll Do |
|--------|-------|----------------|
| 1 | Context | Explore the codebase, see context limits |
| 2 | CLAUDE.md | Create project memory |
| 3 | Bug Fix | Fix the negative amount validation bug |
| 4 | Debugging | Fix the case-sensitive category bug |
| 5 | Specs | Add recurring expenses feature |
| 6 | Planning | Implement the reports module |
| 7+ | Building Blocks | Create commands, skills, workflows |

## Known Issues (For Learning)

This codebase has intentional bugs for learning purposes:

1. **Negative amounts accepted** (Lesson 3)
   - `add_expense()` doesn't validate that amount > 0
   - Tests `test_add_negative_amount_should_fail` and `test_add_zero_amount_should_fail` fail

2. **Case-sensitive category filtering** (Lesson 4)
   - `list_expenses(category="Food")` won't find expenses with category "food" or "FOOD"
   - Test `test_list_by_category_case_insensitive` fails

3. **Reports not implemented** (Lesson 6)
   - `reports.py` has stub functions that raise `NotImplementedError`
   - All tests in `test_reports.py` are skipped until implementation

## Development

### Requirements
- Python 3.10+
- pytest (for running tests)

### Setup
```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install pytest ruff

# Initialize database
python seed_data.py
```

### Code Style
- Type hints on all function signatures
- Docstrings on public functions
- Black-compatible formatting
- No unused imports
