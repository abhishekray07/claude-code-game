#!/usr/bin/env python3
"""Simple TODO CLI app - starter project for Claude Code Game."""
import json
import os
from datetime import datetime

TODO_FILE = os.path.expanduser("~/.todos.json")


def load_todos() -> list[dict]:
    """Load todos from file."""
    if not os.path.exists(TODO_FILE):
        return []
    with open(TODO_FILE, "r") as f:
        return json.load(f)


def save_todos(todos: list[dict]):
    """Save todos to file."""
    with open(TODO_FILE, "w") as f:
        json.dump(todos, f, indent=2)


def add_todo(text: str):
    """Add a new todo."""
    todos = load_todos()
    todo = {
        "id": len(todos) + 1,
        "text": text,
        "done": False,
        "created": datetime.now().isoformat(),
    }
    todos.append(todo)
    save_todos(todos)
    print(f"Added: {text}")


def list_todos():
    """List all todos."""
    todos = load_todos()
    if not todos:
        print("No todos yet!")
        return

    for todo in todos:
        status = "✓" if todo["done"] else " "
        # BUG: Should be todo["text"], not todo["title"]
        print(f"[{status}] {todo['id']}: {todo['title']}")


def complete_todo(todo_id: int):
    """Mark a todo as complete."""
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = True
            save_todos(todos)
            print(f"Completed: {todo['text']}")
            return
    print(f"Todo {todo_id} not found")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: todo.py <command> [args]")
        print("Commands: add, list, done")
        return

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: todo.py add <text>")
            return
        add_todo(" ".join(sys.argv[2:]))
    elif cmd == "list":
        list_todos()
    elif cmd == "done":
        if len(sys.argv) < 3:
            print("Usage: todo.py done <id>")
            return
        complete_todo(int(sys.argv[2]))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
