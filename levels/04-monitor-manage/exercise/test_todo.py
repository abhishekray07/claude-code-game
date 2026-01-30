"""Tests for todo app."""
import json
import os
import tempfile

import pytest

# We'll patch TODO_FILE before importing todo
_test_file = tempfile.mktemp(suffix=".json")


@pytest.fixture(autouse=True)
def setup_test_file(monkeypatch):
    """Setup test file for each test."""
    import todo
    monkeypatch.setattr(todo, "TODO_FILE", _test_file)

    # Clean before test
    if os.path.exists(_test_file):
        os.remove(_test_file)

    yield

    # Clean after test
    if os.path.exists(_test_file):
        os.remove(_test_file)


def test_add_todo():
    """Test adding a todo."""
    import todo
    todo.add_todo("Test task")

    todos = todo.load_todos()
    assert len(todos) == 1
    assert todos[0]["text"] == "Test task"
    assert todos[0]["done"] is False


def test_list_todos_empty(capsys):
    """Test listing when no todos."""
    import todo
    todo.list_todos()

    captured = capsys.readouterr()
    assert "No todos" in captured.out


def test_list_todos(capsys):
    """Test listing todos."""
    import todo
    todo.add_todo("Task 1")
    todo.add_todo("Task 2")

    todo.list_todos()

    captured = capsys.readouterr()
    # This test will fail due to the bug!
    assert "Task 1" in captured.out


def test_complete_todo():
    """Test completing a todo."""
    import todo
    todo.add_todo("Test task")
    todo.complete_todo(1)

    todos = todo.load_todos()
    assert todos[0]["done"] is True
