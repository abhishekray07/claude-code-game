"""Report generation for expense tracker.

This module generates expense reports with summaries and breakdowns.

TODO: This module is incomplete. Students implement it in Lesson 4.

Features to implement:
- Monthly expense report
- Category breakdown
- Top expenses list
- Export to markdown file
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models import Expense


def generate_monthly_report(month: Optional[str] = None) -> str:
    """Generate a monthly expense report.

    Args:
        month: Month in YYYY-MM format. Defaults to current month.

    Returns:
        Formatted report as a string.

    The report should include:
    - Total spent
    - Number of expenses
    - Breakdown by category with percentages
    - Top 5 expenses

    TODO (Lesson 4): Implement this function.
    """
    raise NotImplementedError(
        "Implement this in Lesson 4! "
        "The function should return a formatted report string."
    )


def get_category_breakdown(expenses: list["Expense"]) -> dict[str, float]:
    """Get spending breakdown by category.

    Args:
        expenses: List of Expense objects

    Returns:
        Dictionary mapping category name to total amount

    Example:
        >>> expenses = [Expense(..., category="Food", amount=50), ...]
        >>> get_category_breakdown(expenses)
        {'Food': 75.0, 'Transport': 30.0}

    TODO (Lesson 4): Implement this function.
    """
    raise NotImplementedError(
        "Implement this in Lesson 4! "
        "Sum amounts by category and return as dict."
    )


def get_top_expenses(expenses: list["Expense"], n: int = 5) -> list["Expense"]:
    """Get the top N expenses by amount.

    Args:
        expenses: List of Expense objects
        n: Number of top expenses to return (default 5)

    Returns:
        List of the N highest expenses, sorted by amount descending

    TODO (Lesson 4): Implement this function.
    """
    raise NotImplementedError(
        "Implement this in Lesson 4! "
        "Sort by amount and return top N."
    )


def save_report(report: str, filename: str) -> Path:
    """Save report to a file in the reports directory.

    Args:
        report: The report content as a string
        filename: Name of the file (e.g., '2026-01.md')

    Returns:
        Path to the saved file

    Creates the reports/ directory if it doesn't exist.

    TODO (Lesson 4): Implement this function.
    """
    raise NotImplementedError(
        "Implement this in Lesson 4! "
        "Save to reports/{filename} and return the path."
    )


# Reference implementation (for instructor use)
# Students should implement similar logic:
#
# def generate_monthly_report(month: Optional[str] = None) -> str:
#     from models import list_expenses
#     from utils import format_currency
#
#     if month is None:
#         month = datetime.now().strftime("%Y-%m")
#
#     expenses = list_expenses(month=month)
#
#     if not expenses:
#         return f"# Expense Report: {month}\n\nNo expenses found."
#
#     total = sum(e.amount for e in expenses)
#     breakdown = get_category_breakdown(expenses)
#     top = get_top_expenses(expenses, 5)
#
#     report = f"# Expense Report: {month}\n\n"
#     report += f"## Summary\n"
#     report += f"- **Total Spent:** {format_currency(total)}\n"
#     report += f"- **Number of Expenses:** {len(expenses)}\n\n"
#
#     report += "## By Category\n"
#     for cat, amount in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
#         pct = (amount / total) * 100
#         report += f"- {cat}: {format_currency(amount)} ({pct:.1f}%)\n"
#
#     report += "\n## Top 5 Expenses\n"
#     for i, exp in enumerate(top, 1):
#         report += f"{i}. {format_currency(exp.amount)} - {exp.description} ({exp.category})\n"
#
#     return report
