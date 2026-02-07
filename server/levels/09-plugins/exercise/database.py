"""SQLite database operations for expense storage."""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from contextlib import contextmanager

if TYPE_CHECKING:
    from models import Expense

# Database path - use environment variable for testing, otherwise default location
DB_PATH = Path(os.environ.get(
    "EXPENSE_DB_PATH",
    Path(__file__).parent / "data" / "expenses.db"
))


@contextmanager
def get_connection():
    """Get a database connection with proper cleanup.

    Yields:
        sqlite3.Connection with Row factory enabled

    Example:
        with get_connection() as conn:
            conn.execute("SELECT * FROM expenses")
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema.

    Creates the expenses table if it doesn't exist.
    Also creates the data directory if needed.
    """
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


def save_expense(expense: "Expense") -> None:
    """Save an expense to the database.

    Args:
        expense: The Expense object to save
    """
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


def load_expenses() -> list["Expense"]:
    """Load all expenses from the database.

    Returns:
        List of all Expense objects, ordered by date descending
    """
    from models import Expense  # Import here to avoid circular import

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


def get_expense_by_id(expense_id: str) -> Optional["Expense"]:
    """Get a single expense by ID.

    Args:
        expense_id: The unique expense ID

    Returns:
        The Expense if found, None otherwise
    """
    from models import Expense  # Import here to avoid circular import

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
    """Remove an expense from the database.

    Args:
        expense_id: The unique expense ID

    Returns:
        True if an expense was deleted, False if not found
    """
    with get_connection() as conn:
        cursor = conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        return cursor.rowcount > 0


def clear_all_expenses() -> None:
    """Clear all expenses from the database.

    WARNING: This deletes all data! Use only for testing.
    """
    with get_connection() as conn:
        conn.execute('DELETE FROM expenses')


def get_expense_count() -> int:
    """Get the total number of expenses.

    Returns:
        Count of expenses in database
    """
    with get_connection() as conn:
        row = conn.execute('SELECT COUNT(*) as count FROM expenses').fetchone()
        return row['count']
