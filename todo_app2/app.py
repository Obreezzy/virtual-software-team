#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime, timezone
from typing import List, Dict

# Type alias for clarity
Task = Dict[str, object]


def fail(msg: object) -> None:
    """Print an error message to stderr and exit with a non-zero status."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def get_default_path() -> str:
    """Return the default JSON file path for storing tasks, with user home expanded."""
    # Expand the leading '~' to the actual home directory.
    return os.path.expanduser("~/.todo.json")


def _ensure_dir(path: str) -> None:
    """
    Ensure that the directory for *path* exists.
    If the directory component is empty (e.g., a bare filename), do nothing.
    """
    dir_name = os.path.dirname(os.path.abspath(path))
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)


def load_tasks(path: str) -> List[Task]:
    """Load tasks from a JSON file, handling missing or corrupted files."""
    if not os.path.exists(path):
        # Create an empty file (and its directory if needed)
        _ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            # If the JSON is not a list, treat as corrupted
            raise json.JSONDecodeError("Invalid format", "", 0)
    except json.JSONDecodeError:
        # Rename corrupted file to .bak (replace any existing backup)
        bak_path = path + ".bak"
        if os.path.exists(bak_path):
            os.remove(bak_path)
        os.replace(path, bak_path)
        # Create a new empty file
        _ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return []


def save_tasks(path: str, tasks: List[Task]) -> None:
    """Atomically write tasks to the JSON file."""
    tmp_path = path + ".tmp"
    _ensure_dir(path)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, sort_keys=False)
    os.replace(tmp_path, path)


def next_id(tasks: List[Task]) -> int:
    """Return the next task ID."""
    if not tasks:
        return 1
    max_id = max(task["id"] for task in tasks)  # type: ignore[arg-type]
    return max_id + 1


def add_task(tasks: List[Task], description: str) -> Task:
    """Create a new task and append it to the list."""
    desc = description.strip()
    if not desc:
        raise ValueError("Description cannot be empty")
    # Current UTC time, stored without a timezone suffix (same format as before)
    created = datetime.now(timezone.utc).replace(tzinfo=None)
    task: Task = {
        "id": next_id(tasks),
        "description": desc,
        "completed": False,
        "created": created.isoformat(timespec="seconds"),
    }
    tasks.append(task)
    return task


def list_tasks(tasks: List[Task], status: str = "all") -> List[Task]:
    """Return tasks filtered by status."""
    if status == "all":
        return list(tasks)
    if status == "pending":
        return [t for t in tasks if not t["completed"]]
    if status == "done":
        return [t for t in tasks if t["completed"]]
    raise ValueError("Invalid status filter")


def mark_done(tasks: List[Task], task_id: int) -> Task:
    """Mark a task as completed."""
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            return task
    raise ValueError("Task ID not found")


def remove_task(tasks: List[Task], task_id: int) -> Task:
    """Remove a task from the list."""
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            return tasks.pop(i)
    raise ValueError("Task ID not found")


def clear_tasks(tasks: List[Task], force: bool = False) -> List[Task]:
    """Remove all completed tasks, optionally after confirmation."""
    to_remove = [t for t in tasks if t["completed"]]
    if not to_remove:
        return []

    if not force:
        if not confirm("Remove all completed tasks? (y/N): "):
            return []

    removed: List[Task] = []
    for task in to_remove:
        tasks.remove(task)
        removed.append(task)
    return removed


def format_task_line(task: Task) -> str:
    """Return a formatted string for a single task."""
    status = "[x]" if task["completed"] else "[ ]"
    return f"{task['id']:>3}  {status} {task['description']}"


def print_tasks(tasks: List[Task]) -> None:
    """Print tasks to stdout."""
    if not tasks:
        print("No tasks.")
        return
    for task in tasks:
        print(format_task_line(task))


def confirm(prompt: str) -> bool:
    """Prompt the user for a yes/no answer, treating EOF as a negative response."""
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def parse_args(argv: List[str]) -> dict:
    """Parse command-line arguments into a dictionary."""
    if not argv or argv[0] in ("-h", "--help"):
        return {"command": "help"}

    cmd = argv[0]
    args = argv[1:]

    if cmd == "add":
        if not args:
            raise ValueError("add command requires a description")
        description = " ".join(args)
        return {"command": "add", "description": description}

    if cmd == "list":
        status = "all"
        for opt in args:
            if opt == "--all":
                status = "all"
            elif opt == "--pending":
                status = "pending"
            elif opt == "--done":
                status = "done"
            else:
                raise ValueError(f"Unknown option for list: {opt}")
        return {"command": "list", "status": status}

    if cmd == "done":
        if len(args) != 1:
            raise ValueError("done command requires exactly one task ID")
        try:
            task_id = int(args[0])
        except ValueError:
            raise ValueError("Task ID must be an integer")
        return {"command": "done", "id": task_id}

    if cmd == "remove":
        if len(args) != 1:
            raise ValueError("remove command requires exactly one task ID")
        try:
            task_id = int(args[0])
        except ValueError:
            raise ValueError("Task ID must be an integer")
        return {"command": "remove", "id": task_id}

    if cmd == "clear":
        force = False
        for opt in args:
            if opt == "--force":
                force = True
            else:
                raise ValueError(f"Unknown option for clear: {opt}")
        return {"command": "clear", "force": force}

    raise ValueError("Unknown command")


def _print_help() -> None:
    """Print usage information."""
    help_msg = """Usage: todo <command> [options]

Commands:
  add "description"          Add a new task
  list [--all|--pending|--done]   List tasks (default: --all)
  done <id>                  Mark a task as completed
  remove <id>                Delete a task
  clear [--force]            Remove completed tasks (skip confirmation with --force)
  -h, --help                 Show this help message
"""
    print(help_msg)


def main(argv: List[str] | None = None, path: str | None = None) -> None:
    """Entry point for the todo CLI."""
    if argv is None:
        argv = sys.argv[1:]

    try:
        opts = parse_args(argv)
    except ValueError as e:
        fail(e)

    command = opts["command"]

    if command == "help":
        _print_help()
        sys.exit(0)

    if path is None:
        path = get_default_path()

    tasks = load_tasks(path)

    try:
        if command == "add":
            task = add_task(tasks, opts["description"])
            print(f"Added task {task['id']}.")
            save_tasks(path, tasks)

        elif command == "list":
            filtered = list_tasks(tasks, status=opts["status"])
            print_tasks(filtered)

        elif command == "done":
            already_done = any(
                t["id"] == opts["id"] and t["completed"] for t in tasks
            )
            task = mark_done(tasks, opts["id"])
            if already_done:
                print(f"Task {task['id']} is already completed.")
            else:
                print(f"Marked task {task['id']} as completed.")
                save_tasks(path, tasks)

        elif command == "remove":
            task = remove_task(tasks, opts["id"])
            print(f"Removed task {task['id']}.")
            save_tasks(path, tasks)

        elif command == "clear":
            removed = clear_tasks(tasks, force=opts["force"])
            if removed:
                print(f"Cleared {len(removed)} completed task(s).")
                save_tasks(path, tasks)
            else:
                print("No completed tasks to clear.")

        else:
            raise ValueError("Unknown command")
    except ValueError as e:
        fail(e)


if __name__ == "__main__":
    main()