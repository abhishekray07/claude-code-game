"""Expense data models and core operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid
from database import save_expense, load_expenses, remove_expense, get_expense_by_id


@dataclass
class Expense:
    """Represents a single expense entry."""
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


def get_expense(expense_id: str) -> Optional[Expense]:
    """Get a single expense by ID.

    Args:
        expense_id: The unique expense ID

    Returns:
        The Expense if found, None otherwise
    """
    return get_expense_by_id(expense_id)


def delete_expense(expense_id: str) -> bool:
    """Delete an expense by ID.

    Args:
        expense_id: The unique expense ID

    Returns:
        True if deleted, False if not found
    """
    return remove_expense(expense_id)


def get_total_by_category(category: str) -> float:
    """Get total spent in a category.

    Args:
        category: The category name

    Returns:
        Total amount spent in that category

    Note: Also case-sensitive - shares bug with list_expenses.
    """
    expenses = list_expenses(category=category)
    return sum(e.amount for e in expenses)


def get_categories() -> list[str]:
    """Get all unique categories from expenses.

    Returns:
        List of category names
    """
    expenses = load_expenses()
    return list(set(e.category for e in expenses))
