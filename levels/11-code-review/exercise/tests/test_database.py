"""Tests for database operations."""

import pytest
from datetime import datetime
from database import (
    init_db,
    save_expense,
    load_expenses,
    get_expense_by_id,
    remove_expense,
    clear_all_expenses,
    get_expense_count
)
from models import Expense


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_init_creates_table(self):
        """Test that init_db creates the expenses table."""
        init_db()
        # If we get here without error, table was created
        expenses = load_expenses()
        assert isinstance(expenses, list)

    def test_init_idempotent(self):
        """Test that init_db can be called multiple times safely."""
        init_db()
        init_db()
        init_db()
        # Should not raise any errors


class TestSaveAndLoad:
    """Tests for saving and loading expenses."""

    def test_save_and_load_single(self):
        """Test saving and loading a single expense."""
        expense = Expense(
            id="test123",
            amount=50.0,
            category="Food",
            description="Test expense",
            date=datetime(2026, 1, 15, 12, 0)
        )
        save_expense(expense)

        expenses = load_expenses()
        assert len(expenses) == 1
        assert expenses[0].id == "test123"
        assert expenses[0].amount == 50.0
        assert expenses[0].category == "Food"

    def test_save_multiple(self):
        """Test saving multiple expenses."""
        for i in range(5):
            expense = Expense(
                id=f"test{i}",
                amount=float(i * 10),
                category="Test",
                description=f"Expense {i}",
                date=datetime.now()
            )
            save_expense(expense)

        expenses = load_expenses()
        assert len(expenses) == 5

    def test_load_preserves_data(self):
        """Test that all expense fields are preserved on load."""
        original = Expense(
            id="preserve123",
            amount=99.99,
            category="Shopping",
            description="Test all fields",
            date=datetime(2026, 6, 15, 14, 30),
            recurring=True,
            recurring_frequency="monthly"
        )
        save_expense(original)

        loaded = load_expenses()[0]
        assert loaded.id == original.id
        assert loaded.amount == original.amount
        assert loaded.category == original.category
        assert loaded.description == original.description
        assert loaded.date == original.date
        assert loaded.recurring == original.recurring
        assert loaded.recurring_frequency == original.recurring_frequency

    def test_load_ordered_by_date(self):
        """Test that load_expenses returns results ordered by date descending."""
        dates = [
            datetime(2026, 1, 1),
            datetime(2026, 1, 15),
            datetime(2026, 1, 10),
        ]
        for i, date in enumerate(dates):
            expense = Expense(
                id=f"date{i}",
                amount=10.0,
                category="Test",
                description=f"Expense {i}",
                date=date
            )
            save_expense(expense)

        expenses = load_expenses()
        loaded_dates = [e.date for e in expenses]
        assert loaded_dates == sorted(loaded_dates, reverse=True)


class TestGetExpenseById:
    """Tests for getting expense by ID."""

    def test_get_existing(self):
        """Test retrieving an existing expense by ID."""
        expense = Expense(
            id="findme123",
            amount=25.0,
            category="Transport",
            description="Bus fare",
            date=datetime.now()
        )
        save_expense(expense)

        result = get_expense_by_id("findme123")
        assert result is not None
        assert result.id == "findme123"
        assert result.description == "Bus fare"

    def test_get_nonexistent(self):
        """Test that non-existent ID returns None."""
        result = get_expense_by_id("does-not-exist")
        assert result is None

    def test_get_after_multiple_saves(self):
        """Test getting specific expense after saving multiple."""
        for i in range(10):
            expense = Expense(
                id=f"multi{i}",
                amount=float(i),
                category="Test",
                description=f"Expense {i}",
                date=datetime.now()
            )
            save_expense(expense)

        result = get_expense_by_id("multi5")
        assert result is not None
        assert result.amount == 5.0


class TestRemoveExpense:
    """Tests for removing expenses."""

    def test_remove_existing(self):
        """Test removing an existing expense."""
        expense = Expense(
            id="removeme",
            amount=10.0,
            category="Test",
            description="To be removed",
            date=datetime.now()
        )
        save_expense(expense)
        assert get_expense_by_id("removeme") is not None

        result = remove_expense("removeme")
        assert result is True
        assert get_expense_by_id("removeme") is None

    def test_remove_nonexistent(self):
        """Test removing non-existent expense returns False."""
        result = remove_expense("fake-id")
        assert result is False

    def test_remove_only_target(self):
        """Test that remove only deletes the target expense."""
        for i in range(3):
            expense = Expense(
                id=f"keep{i}",
                amount=float(i),
                category="Test",
                description=f"Expense {i}",
                date=datetime.now()
            )
            save_expense(expense)

        remove_expense("keep1")

        expenses = load_expenses()
        ids = [e.id for e in expenses]
        assert "keep0" in ids
        assert "keep1" not in ids
        assert "keep2" in ids


class TestClearAll:
    """Tests for clearing all expenses."""

    def test_clear_removes_all(self):
        """Test that clear_all_expenses removes everything."""
        for i in range(5):
            expense = Expense(
                id=f"clear{i}",
                amount=float(i),
                category="Test",
                description=f"Expense {i}",
                date=datetime.now()
            )
            save_expense(expense)

        assert len(load_expenses()) == 5

        clear_all_expenses()
        assert len(load_expenses()) == 0

    def test_clear_empty_db(self):
        """Test that clearing empty database doesn't error."""
        clear_all_expenses()  # Should not raise


class TestExpenseCount:
    """Tests for getting expense count."""

    def test_count_empty(self):
        """Test count on empty database."""
        assert get_expense_count() == 0

    def test_count_with_expenses(self):
        """Test count with expenses."""
        for i in range(7):
            expense = Expense(
                id=f"count{i}",
                amount=float(i),
                category="Test",
                description=f"Expense {i}",
                date=datetime.now()
            )
            save_expense(expense)

        assert get_expense_count() == 7
