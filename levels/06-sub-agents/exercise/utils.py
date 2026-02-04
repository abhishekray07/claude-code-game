"""Utility functions for the expense tracker."""

from datetime import datetime, timedelta
from typing import Optional
import locale


def format_currency(amount: float) -> str:
    """Format amount as currency.

    Args:
        amount: The numeric amount

    Returns:
        Formatted string like '$1,234.56'

    Example:
        >>> format_currency(1234.5)
        '$1,234.50'
    """
    try:
        locale.setlocale(locale.LC_ALL, '')
        return locale.currency(amount, grouping=True)
    except (locale.Error, ValueError):
        # Fallback if locale not available
        return f"${amount:,.2f}"


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a date string in various formats.

    Supports:
    - YYYY-MM-DD (2026-01-15)
    - MM/DD/YYYY (01/15/2026)
    - 'today'
    - 'yesterday'

    Args:
        date_str: The date string to parse

    Returns:
        datetime object or None if input is None

    Raises:
        ValueError: If date format is not recognized

    Example:
        >>> parse_date('2026-01-15')
        datetime(2026, 1, 15, 0, 0, 0)
        >>> parse_date('today')
        datetime(...)  # Today at midnight
    """
    if not date_str:
        return None

    date_str = date_str.lower().strip()

    # Handle relative dates
    if date_str == 'today':
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if date_str == 'yesterday':
        return (datetime.now() - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # Try YYYY-MM-DD (ISO format)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        pass

    # Try MM/DD/YYYY (US format)
    try:
        return datetime.strptime(date_str, '%m/%d/%Y')
    except ValueError:
        pass

    # Try DD/MM/YYYY (European format)
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        pass

    raise ValueError(f"Could not parse date: {date_str}. Use YYYY-MM-DD format.")


def validate_category(category: str) -> str:
    """Normalize category name.

    Capitalizes first letter, strips whitespace.

    Args:
        category: Raw category input

    Returns:
        Normalized category name

    Example:
        >>> validate_category('  food  ')
        'Food'
    """
    return category.strip().capitalize()


def format_date(dt: datetime) -> str:
    """Format a datetime for display.

    Args:
        dt: The datetime to format

    Returns:
        Formatted string like 'Jan 15, 2026'
    """
    return dt.strftime('%b %d, %Y')


def format_month(month_str: str) -> str:
    """Format a YYYY-MM string for display.

    Args:
        month_str: Month in YYYY-MM format

    Returns:
        Formatted string like 'January 2026'

    Example:
        >>> format_month('2026-01')
        'January 2026'
    """
    dt = datetime.strptime(month_str, '%Y-%m')
    return dt.strftime('%B %Y')


# Valid categories for validation/suggestions
VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Entertainment",
    "Shopping",
    "Bills",
    "Health",
    "Education",
    "Travel",
    "Other"
]


def suggest_category(partial: str) -> list[str]:
    """Suggest categories matching a partial input.

    Args:
        partial: Partial category name

    Returns:
        List of matching categories

    Example:
        >>> suggest_category('fo')
        ['Food']
    """
    partial_lower = partial.lower()
    return [cat for cat in VALID_CATEGORIES if cat.lower().startswith(partial_lower)]
