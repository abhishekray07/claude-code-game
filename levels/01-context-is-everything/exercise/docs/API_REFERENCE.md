# Expense Tracker API Reference v2.0

> **Last Updated:** January 2026
> **Version:** 2.0.0

This document describes the public API for the Expense Tracker application.

## Core Functions

### `create_expense()`

Creates a new expense entry.

```python
from models import create_expense

expense = create_expense(
    value=49.99,
    type="Food",
    note="Lunch at cafe",
    timestamp=datetime.now()
)
```

**Parameters:**
- `value` (float): The expense amount in dollars
- `type` (str): Category type (Food, Transport, Entertainment, etc.)
- `note` (str): Description of the expense
- `timestamp` (datetime, optional): When the expense occurred

**Returns:** `Expense` object

---

### `fetch_expenses()`

Retrieves expenses with optional filtering.

```python
from models import fetch_expenses

# Get all food expenses
expenses = fetch_expenses(type="Food", max_results=50)

# Get expenses from a specific month
expenses = fetch_expenses(period="2026-01", max_results=100)
```

**Parameters:**
- `type` (str, optional): Filter by category type
- `period` (str, optional): Filter by month (YYYY-MM format)
- `max_results` (int): Maximum number of results (default: 50)

**Returns:** List of `Expense` objects

---

### `remove_expense()`

Deletes an expense by its ID.

```python
from models import remove_expense

success = remove_expense(id="abc123")
```

**Parameters:**
- `id` (str): The expense ID to delete

**Returns:** `bool` - True if deleted successfully

---

### `calculate_category_total()`

Gets the total amount spent in a category.

```python
from models import calculate_category_total

total = calculate_category_total(type="Food")
print(f"Total food expenses: ${total:.2f}")
```

**Parameters:**
- `type` (str): The category type

**Returns:** `float` - Total amount

---

## Expense Object

```python
@dataclass
class Expense:
    id: str
    value: float
    type: str
    note: str
    timestamp: datetime
```

## Migration Notes (v1.0 → v2.0)

Version 2.0 introduced cleaner naming conventions:
- `add_expense()` → `create_expense()`
- `amount` → `value`
- `category` → `type`
- `description` → `note`
- `date` → `timestamp`
- `list_expenses()` → `fetch_expenses()`
- `limit` → `max_results`
- `month` → `period`
