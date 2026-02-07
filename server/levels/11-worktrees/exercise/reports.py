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
