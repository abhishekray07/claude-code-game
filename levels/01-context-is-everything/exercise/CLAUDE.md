# Expense Tracker

A CLI expense tracking application built with Python and SQLite.

## Code Style

- Use type hints for all function parameters and return values

## Testing

Always run tests before committing: `python -m pytest tests/ -v`

## Architecture

- `main.py` - CLI entry point using argparse
- `models.py` - Business logic and data structures
- `database.py` - SQLite persistence layer
- `reports.py` - Report generation (stub)
- `utils.py` - Formatting helpers
