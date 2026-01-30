#!/usr/bin/env python3
"""Expense Tracker CLI - Track your daily expenses."""

import argparse
from datetime import datetime
from models import add_expense, list_expenses, delete_expense, get_expense
from utils import format_currency, parse_date
from database import init_db


def main():
    parser = argparse.ArgumentParser(description="Track your expenses")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add expense
    add_parser = subparsers.add_parser("add", help="Add a new expense")
    add_parser.add_argument("amount", type=float, help="Amount spent")
    add_parser.add_argument("category", help="Category (Food, Transport, etc.)")
    add_parser.add_argument("description", help="What was the expense for?")
    add_parser.add_argument("--date", help="Date (YYYY-MM-DD), defaults to today")

    # List expenses
    list_parser = subparsers.add_parser("list", help="List expenses")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument("--month", help="Filter by month (YYYY-MM)")
    list_parser.add_argument("--limit", type=int, default=10, help="Max results")

    # Delete expense
    delete_parser = subparsers.add_parser("delete", help="Delete an expense")
    delete_parser.add_argument("id", help="Expense ID to delete")

    # Show single expense
    show_parser = subparsers.add_parser("show", help="Show expense details")
    show_parser.add_argument("id", help="Expense ID")

    # Summary
    subparsers.add_parser("summary", help="Show spending summary")

    args = parser.parse_args()

    # Initialize database
    init_db()

    if args.command == "add":
        date = parse_date(args.date) if args.date else datetime.now()
        expense = add_expense(args.amount, args.category, args.description, date)
        print(f"Added expense: {expense.id} - {format_currency(expense.amount)}")

    elif args.command == "list":
        expenses = list_expenses(
            category=args.category,
            month=args.month,
            limit=args.limit
        )
        if not expenses:
            print("No expenses found.")
        for exp in expenses:
            print(f"{exp.id} | {exp.date.strftime('%Y-%m-%d')} | "
                  f"{exp.category:12} | {format_currency(exp.amount):>10} | {exp.description}")

    elif args.command == "delete":
        if delete_expense(args.id):
            print(f"Deleted expense {args.id}")
        else:
            print(f"Expense {args.id} not found")

    elif args.command == "show":
        expense = get_expense(args.id)
        if expense:
            print(f"ID:          {expense.id}")
            print(f"Amount:      {format_currency(expense.amount)}")
            print(f"Category:    {expense.category}")
            print(f"Description: {expense.description}")
            print(f"Date:        {expense.date.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"Expense {args.id} not found")

    elif args.command == "summary":
        expenses = list_expenses()
        total = sum(e.amount for e in expenses)
        print(f"Total expenses: {format_currency(total)}")

        # Group by category
        categories: dict[str, float] = {}
        for exp in expenses:
            categories[exp.category] = categories.get(exp.category, 0) + exp.amount

        print("\nBy category:")
        for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat:15} {format_currency(amount):>10}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
