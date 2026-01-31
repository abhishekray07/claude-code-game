"""Tests for report generation.

Note: These tests will FAIL until students implement reports.py in Lesson 6.
The tests serve as a specification for what needs to be implemented.
"""

import pytest
from datetime import datetime
from models import add_expense, Expense
from reports import (
    generate_monthly_report,
    get_category_breakdown,
    get_top_expenses,
    save_report
)


class TestGenerateMonthlyReport:
    """Tests for the generate_monthly_report function."""

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_report_for_empty_month(self):
        """Test report generation for month with no expenses."""
        report = generate_monthly_report("2020-01")
        assert "No expenses" in report or "no expenses" in report.lower()

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_report_includes_total(self):
        """Test that report includes total amount."""
        add_expense(100.0, "Food", "Groceries", datetime(2026, 1, 15))
        add_expense(50.0, "Transport", "Uber", datetime(2026, 1, 15))

        report = generate_monthly_report("2026-01")

        # Should contain total of $150
        assert "150" in report

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_report_includes_categories(self):
        """Test that report includes category breakdown."""
        add_expense(100.0, "Food", "Groceries", datetime(2026, 1, 15))
        add_expense(50.0, "Transport", "Uber", datetime(2026, 1, 15))

        report = generate_monthly_report("2026-01")

        assert "Food" in report
        assert "Transport" in report

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_report_defaults_to_current_month(self):
        """Test that no month argument uses current month."""
        # This test is tricky since it depends on current date
        # Just verify it doesn't error
        report = generate_monthly_report()
        assert report is not None
        assert isinstance(report, str)

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_report_format_is_markdown(self):
        """Test that report is formatted as markdown."""
        add_expense(100.0, "Food", "Test", datetime(2026, 1, 15))
        report = generate_monthly_report("2026-01")

        # Should have markdown headers
        assert "#" in report


class TestGetCategoryBreakdown:
    """Tests for the get_category_breakdown function."""

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_single_category(self):
        """Test breakdown with single category."""
        expenses = [
            Expense("1", 50.0, "Food", "Lunch", datetime.now()),
            Expense("2", 25.0, "Food", "Coffee", datetime.now()),
        ]

        breakdown = get_category_breakdown(expenses)

        assert "Food" in breakdown
        assert breakdown["Food"] == 75.0

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_multiple_categories(self):
        """Test breakdown with multiple categories."""
        expenses = [
            Expense("1", 50.0, "Food", "Lunch", datetime.now()),
            Expense("2", 30.0, "Transport", "Bus", datetime.now()),
            Expense("3", 20.0, "Food", "Snack", datetime.now()),
        ]

        breakdown = get_category_breakdown(expenses)

        assert breakdown["Food"] == 70.0
        assert breakdown["Transport"] == 30.0

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_empty_list(self):
        """Test breakdown with empty expense list."""
        breakdown = get_category_breakdown([])
        assert breakdown == {}


class TestGetTopExpenses:
    """Tests for the get_top_expenses function."""

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_top_expenses_ordering(self):
        """Test that expenses are sorted by amount descending."""
        expenses = [
            Expense("1", 25.0, "Food", "Small", datetime.now()),
            Expense("2", 100.0, "Bills", "Big", datetime.now()),
            Expense("3", 50.0, "Shopping", "Medium", datetime.now()),
        ]

        top = get_top_expenses(expenses, 3)

        assert top[0].amount == 100.0
        assert top[1].amount == 50.0
        assert top[2].amount == 25.0

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_top_n_limit(self):
        """Test limiting to N expenses."""
        expenses = [
            Expense(str(i), float(i * 10), "Cat", "Desc", datetime.now())
            for i in range(1, 11)
        ]

        top = get_top_expenses(expenses, 3)
        assert len(top) == 3

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_top_with_fewer_expenses(self):
        """Test when requesting more than available."""
        expenses = [
            Expense("1", 50.0, "Food", "Only one", datetime.now()),
        ]

        top = get_top_expenses(expenses, 5)
        assert len(top) == 1

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_default_n_is_5(self):
        """Test that default n value is 5."""
        expenses = [
            Expense(str(i), float(i), "Cat", "Desc", datetime.now())
            for i in range(10)
        ]

        top = get_top_expenses(expenses)
        assert len(top) == 5


class TestSaveReport:
    """Tests for the save_report function."""

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_save_creates_file(self, tmp_path, monkeypatch):
        """Test that save_report creates a file."""
        import os
        monkeypatch.chdir(tmp_path)

        report_content = "# Test Report\n\nThis is a test."
        path = save_report(report_content, "test-report.md")

        assert path.exists()
        assert path.read_text() == report_content

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_save_creates_directory(self, tmp_path, monkeypatch):
        """Test that save_report creates reports directory if needed."""
        import os
        monkeypatch.chdir(tmp_path)

        save_report("# Test", "2026-01.md")

        assert (tmp_path / "reports").is_dir()

    @pytest.mark.skip(reason="Implement in Lesson 6")
    def test_save_returns_path(self, tmp_path, monkeypatch):
        """Test that save_report returns the file path."""
        import os
        monkeypatch.chdir(tmp_path)

        path = save_report("# Test", "my-report.md")

        assert path.name == "my-report.md"
        assert "reports" in str(path)
