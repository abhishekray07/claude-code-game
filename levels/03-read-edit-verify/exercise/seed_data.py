#!/usr/bin/env python3
"""Seed the database with sample expenses for learning.

Run this script to populate the database with example data:
    python seed_data.py

This creates a realistic set of expenses for students to work with.
"""

from datetime import datetime
from database import init_db, clear_all_expenses
from models import add_expense

# Sample expenses for the course
# Note: One entry has lowercase "food" to trigger the case-sensitivity bug
SAMPLE_EXPENSES = [
    # January 2026 - Primary month for exercises
    (45.50, "Food", "Grocery shopping at Whole Foods", "2026-01-15"),
    (12.00, "Transport", "Uber to airport", "2026-01-14"),
    (89.99, "Shopping", "Running shoes from Nike", "2026-01-10"),
    (150.00, "Bills", "Electric bill", "2026-01-01"),
    (8.50, "food", "Coffee at Starbucks", "2026-01-20"),  # lowercase - triggers bug!
    (35.00, "Entertainment", "Movie tickets for two", "2026-01-18"),
    (22.00, "Food", "Lunch with team", "2026-01-19"),
    (65.00, "Health", "Gym membership monthly", "2026-01-01"),
    (15.75, "Food", "Thai takeout dinner", "2026-01-17"),
    (42.00, "Transport", "Weekly metro pass", "2026-01-13"),
    (28.99, "Entertainment", "Netflix + Spotify", "2026-01-05"),
    (120.00, "Shopping", "Winter jacket on sale", "2026-01-08"),

    # December 2025 - For month filtering tests
    (200.00, "Shopping", "Holiday gifts for family", "2025-12-20"),
    (55.00, "Food", "Holiday dinner groceries", "2025-12-25"),
    (75.00, "Entertainment", "Concert tickets", "2025-12-15"),
    (30.00, "Transport", "Airport parking", "2025-12-23"),

    # November 2025 - Additional historical data
    (95.00, "Bills", "Internet bill", "2025-11-15"),
    (180.00, "Health", "Doctor visit copay", "2025-11-10"),
    (45.00, "Food", "Birthday dinner", "2025-11-22"),
]


def seed_database(verbose: bool = True) -> int:
    """Initialize and seed the database with sample data.

    Args:
        verbose: Whether to print progress messages

    Returns:
        Number of expenses added
    """
    if verbose:
        print("Initializing database...")
    init_db()

    if verbose:
        print("Clearing existing data...")
    clear_all_expenses()

    if verbose:
        print("Adding sample expenses...")

    count = 0
    for amount, category, desc, date_str in SAMPLE_EXPENSES:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        expense = add_expense(amount, category, desc, date)
        count += 1
        if verbose:
            print(f"  Added: {expense.id} - ${amount:.2f} - {desc[:40]}")

    if verbose:
        print(f"\n{'='*50}")
        print(f"Seeded {count} expenses successfully!")
        print(f"{'='*50}")
        print("\nTry these commands:")
        print("  python main.py list")
        print("  python main.py list --category Food")
        print("  python main.py summary")
        print("  pytest -v")

    return count


def main():
    """Entry point for seeding script."""
    seed_database()


if __name__ == "__main__":
    main()
