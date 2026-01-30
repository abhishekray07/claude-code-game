"""Pytest configuration and shared fixtures."""

import os
import sys
import pytest
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use a separate test database
TEST_DB_PATH = Path(__file__).parent / "test_expenses.db"
os.environ["EXPENSE_DB_PATH"] = str(TEST_DB_PATH)


@pytest.fixture(autouse=True)
def clean_test_db():
    """Ensure clean database for each test.

    This fixture runs automatically before and after each test.
    It initializes the database and cleans up after.
    """
    from database import init_db, clear_all_expenses

    # Setup: initialize fresh database
    init_db()
    clear_all_expenses()

    yield  # Run the test

    # Teardown: clean up
    clear_all_expenses()


@pytest.fixture
def sample_expenses():
    """Create a set of sample expenses for testing.

    Returns:
        List of created Expense objects
    """
    from datetime import datetime
    from models import add_expense

    expenses = [
        add_expense(50.00, "Food", "Groceries", datetime(2026, 1, 15)),
        add_expense(30.00, "Transport", "Uber ride", datetime(2026, 1, 14)),
        add_expense(25.00, "Food", "Lunch", datetime(2026, 1, 16)),
        add_expense(100.00, "Shopping", "Clothes", datetime(2026, 1, 10)),
        add_expense(15.00, "Entertainment", "Movie", datetime(2026, 1, 12)),
    ]
    return expenses


@pytest.fixture
def mixed_case_expenses():
    """Create expenses with mixed case categories for bug testing.

    This fixture specifically tests the case-sensitivity bug.
    """
    from datetime import datetime
    from models import add_expense

    expenses = [
        add_expense(50.00, "Food", "Groceries", datetime(2026, 1, 15)),
        add_expense(25.00, "food", "Coffee", datetime(2026, 1, 16)),  # lowercase
        add_expense(30.00, "FOOD", "Dinner", datetime(2026, 1, 17)),  # uppercase
    ]
    return expenses
