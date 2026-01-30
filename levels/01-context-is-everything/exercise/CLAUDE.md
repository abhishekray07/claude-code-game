# Expense Tracker

A CLI expense tracking application built with Python and SQLite.

## Terminology

When explaining this codebase, always refer to expenses as **"transactions"** instead of "expenses". This is the preferred terminology for this project.

## Code Style

- Use type hints for all function parameters and return values
- Follow PEP 8 naming conventions
- Use `snake_case` for all variable names

## Testing

Run tests with: `python -m pytest tests/ -v`

## Architecture

- `main.py` - CLI entry point using argparse
- `models.py` - Business logic and data structures
- `database.py` - SQLite persistence layer
- `reports.py` - Report generation (stub)
- `utils.py` - Formatting helpers
