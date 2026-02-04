"""Tests for expense models.

This test file includes intentionally failing tests that students fix
during the course:

- test_add_negative_amount_should_fail: Fails until Lesson 3 (validation bug)
- test_list_by_category_case_insensitive: Fails until Lesson 4 (case bug)
"""

import pytest
from datetime import datetime
from models import (
    add_expense,
    list_expenses,
    delete_expense,
    get_expense,
    get_total_by_category,
    Expense
)


class TestAddExpense:
    """Tests for the add_expense function."""

    def test_add_basic_expense(self):
        """Test adding a simple expense."""
        expense = add_expense(50.0, "Food", "Lunch at cafe")

        assert expense.amount == 50.0
        assert expense.category == "Food"
        assert expense.description == "Lunch at cafe"
        assert expense.id is not None
        assert len(expense.id) == 8  # UUID prefix

    def test_add_expense_with_date(self):
        """Test adding expense with specific date."""
        date = datetime(2026, 1, 15, 12, 30)
        expense = add_expense(25.0, "Transport", "Uber to meeting", date)

        assert expense.date == date
        assert expense.amount == 25.0

    def test_add_expense_default_date(self):
        """Test that expense gets current date if not specified."""
        before = datetime.now()
        expense = add_expense(10.0, "Food", "Snack")
        after = datetime.now()

        assert before <= expense.date <= after

    def test_add_expense_persists(self):
        """Test that added expense can be retrieved."""
        expense = add_expense(75.0, "Shopping", "New book")

        retrieved = get_expense(expense.id)
        assert retrieved is not None
        assert retrieved.amount == 75.0
        assert retrieved.description == "New book"

    # =========================================================
    # BUG TESTS - These fail until students fix them in Lesson 3
    # =========================================================

    def test_add_negative_amount_should_fail(self):
        """BUG TEST: Negative amounts should raise ValueError.

        This test FAILS initially - students fix this in Lesson 3
        by adding validation to add_expense().

        Expected fix:
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")
        """
        with pytest.raises(ValueError, match="[Aa]mount"):
            add_expense(-50.0, "Food", "Invalid expense")

    def test_add_zero_amount_should_fail(self):
        """BUG TEST: Zero amount should raise ValueError.

        This test FAILS initially - students fix this in Lesson 3.
        """
        with pytest.raises(ValueError, match="[Aa]mount"):
            add_expense(0, "Food", "Free lunch doesn't exist")

    def test_add_empty_category_should_fail(self):
        """BUG TEST: Empty category should raise ValueError.

        This test FAILS initially - students fix this in Lesson 3.
        """
        with pytest.raises(ValueError, match="[Cc]ategory"):
            add_expense(50.0, "", "No category")

    def test_add_whitespace_category_should_fail(self):
        """BUG TEST: Whitespace-only category should raise ValueError."""
        with pytest.raises(ValueError, match="[Cc]ategory"):
            add_expense(50.0, "   ", "Whitespace category")


class TestListExpenses:
    """Tests for the list_expenses function."""

    def test_list_all_expenses(self, sample_expenses):
        """Test listing all expenses without filters."""
        expenses = list_expenses()
        assert len(expenses) == 5

    def test_list_empty(self):
        """Test listing when no expenses exist."""
        expenses = list_expenses()
        assert len(expenses) == 0

    def test_list_by_category(self):
        """Test filtering by category (exact match)."""
        add_expense(50.0, "Food", "Lunch")
        add_expense(30.0, "Transport", "Uber")
        add_expense(25.0, "Food", "Coffee")

        food = list_expenses(category="Food")
        assert len(food) == 2
        assert all(e.category == "Food" for e in food)

    def test_list_by_month(self):
        """Test filtering by month."""
        add_expense(50.0, "Food", "Jan expense", datetime(2026, 1, 15))
        add_expense(30.0, "Food", "Feb expense", datetime(2026, 2, 10))

        jan = list_expenses(month="2026-01")
        assert len(jan) == 1
        assert jan[0].description == "Jan expense"

    def test_list_with_limit(self):
        """Test limiting number of results."""
        for i in range(10):
            add_expense(float(i + 1), "Food", f"Expense {i}")

        limited = list_expenses(limit=5)
        assert len(limited) == 5

    def test_list_sorted_by_date(self):
        """Test that results are sorted by date descending."""
        add_expense(10.0, "Food", "Old", datetime(2026, 1, 1))
        add_expense(20.0, "Food", "New", datetime(2026, 1, 15))
        add_expense(30.0, "Food", "Middle", datetime(2026, 1, 10))

        expenses = list_expenses()
        dates = [e.date for e in expenses]
        assert dates == sorted(dates, reverse=True)

    # =========================================================
    # BUG TESTS - These fail until students fix them in Lesson 4
    # =========================================================

    def test_list_by_category_case_insensitive(self, mixed_case_expenses):
        """BUG TEST: Category filter should be case-insensitive.

        This test FAILS initially - students fix this in Lesson 4.

        The seed data includes lowercase "food" entries that won't
        match "Food" until the bug is fixed.

        Expected fix in list_expenses():
            if category:
                category_lower = category.lower()
                expenses = [e for e in expenses if e.category.lower() == category_lower]
        """
        # mixed_case_expenses has: "Food", "food", "FOOD"
        food = list_expenses(category="Food")
        assert len(food) == 3, (
            f"Expected 3 'Food' expenses (case-insensitive), got {len(food)}. "
            "Fix: make category filtering case-insensitive."
        )

    def test_list_category_lowercase_query(self, mixed_case_expenses):
        """BUG TEST: Lowercase category query should still find matches."""
        food = list_expenses(category="food")  # lowercase query
        assert len(food) == 3, "Lowercase 'food' should match all Food variants"


class TestDeleteExpense:
    """Tests for the delete_expense function."""

    def test_delete_existing(self):
        """Test deleting an existing expense."""
        expense = add_expense(50.0, "Food", "To be deleted")

        result = delete_expense(expense.id)
        assert result is True

        # Verify it's gone
        assert get_expense(expense.id) is None

    def test_delete_nonexistent(self):
        """Test deleting non-existent expense returns False."""
        result = delete_expense("fake-id-12345")
        assert result is False

    def test_delete_twice(self):
        """Test that deleting same expense twice fails second time."""
        expense = add_expense(50.0, "Food", "Delete me")

        assert delete_expense(expense.id) is True
        assert delete_expense(expense.id) is False


class TestGetExpense:
    """Tests for the get_expense function."""

    def test_get_existing(self):
        """Test getting an existing expense."""
        created = add_expense(99.99, "Shopping", "Test item")

        retrieved = get_expense(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.amount == 99.99

    def test_get_nonexistent(self):
        """Test getting non-existent expense returns None."""
        result = get_expense("nonexistent-id")
        assert result is None


class TestGetTotalByCategory:
    """Tests for the get_total_by_category function."""

    def test_total_single_category(self):
        """Test total for a single category."""
        add_expense(50.0, "Food", "Item 1")
        add_expense(30.0, "Food", "Item 2")
        add_expense(100.0, "Shopping", "Other category")

        total = get_total_by_category("Food")
        assert total == 80.0

    def test_total_empty_category(self):
        """Test total for category with no expenses."""
        add_expense(50.0, "Food", "Food item")

        total = get_total_by_category("Transport")
        assert total == 0.0
