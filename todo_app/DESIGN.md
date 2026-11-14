**app.py – corrected design specification**

---

## Data structures

```python
# A single task record – flat dictionary, never nested.
Task = dict[
    "id", int,                # auto‑incremented unique identifier
    "description", str,       # user supplied text
    "completed", bool,        # True when the task is done
    "created", str            # ISO‑8601 UTC timestamp, e.g. "2023-01-01T12:00:00"
]

# Example JSON file content (a list of such dicts):
# [
#   {"id": 1, "description": "Buy milk", "completed": false,
#    "created": "2023-01-01T12:00:00"},
#   {"id": 2, "description": "Read book", "completed": true,
#    "created": "2023-01-02T09:30:00"}
# ]
```

---

## Public functions (flat, no class hierarchy)

| Function | Signature | Input description | Output / side‑effects | Behaviour & validation |
|----------|-----------|-------------------|----------------------|------------------------|
| `get_default_path` | `def get_default_path() -> str:` | *none* | Full path to the JSON file, e.g. `"/home/user/.todo.json"` | Expands `~` to the current user’s home directory (`os.path.expanduser`). |
| `load_tasks` | `def load_tasks(path: str) -> list[Task]:` | `path` – file system path to the JSON file | List of `Task` objects (may be empty) | *If the file does not exist* → creates an empty file at `path` and returns `[]`. <br>*If the file exists but cannot be parsed as JSON* → overwrites the file with `[]` and returns `[]`. <br>*Otherwise* → returns the parsed list. |
| `save_tasks` | `def save_tasks(path: str, tasks: list[Task]) -> None:` | `path` – file system path, `tasks` – list of `Task` | Writes a pretty‑printed JSON representation to `path` (overwrites) | Performs an atomic write: write to `path + ".tmp"` then `os.replace`. |
| `next_id` | `def next_id(tasks: list[Task]) -> int:` | `tasks` – current list | Integer ID that is one greater than the maximum existing ID, or `1` if the list is empty | Scans `tasks` for `max(task["id"] for task in tasks)`; returns `max_id + 1`. |
| `add_task` | `def add_task(tasks: list[Task], description: str) -> Task:` | `tasks` – current list, `description` – non‑empty string | The newly created `Task` (also appended to `tasks`) | • Strips whitespace; if the result is empty → raise `ValueError("Description cannot be empty")`. <br>• Generates `id` via `next_id`. <br>• Sets `completed=False`. <br>• Sets `created` to `datetime.utcnow().isoformat(timespec='seconds')`. |
| `list_tasks` | `def list_tasks(tasks: list[Task], status: str = "all") -> list[Task]:` | `tasks` – current list, `status` – `"all"`, `"pending"` or `"done"` | Sub‑list of tasks matching the filter, preserving original order | `"pending"` → `task["completed"] is False`; `"done"` → `task["completed"] is True`; `"all"` → no filter. <br>Any other value → raise `ValueError("Invalid status filter")`. |
| `mark_done` | `def mark_done(tasks: list[Task], task_id: int) -> Task:` | `tasks` – current list, `task_id` – integer ID | The updated `Task` (also mutated inside `tasks`) | Finds the task with `task["id"] == task_id`. <br>If not found → raise `ValueError("Task ID not found")`. <br>Sets `task["completed"] = True`. |
| `remove_task` | `def remove_task(tasks: list[Task], task_id: int) -> Task:` | `tasks` – current list, `task_id` – integer ID | The removed `Task` (also removed from `tasks`) | Same lookup rule as `mark_done`. <br>Removes the dict from the list and returns it. |
| `clear_tasks` | `def clear_tasks(tasks: list[Task], force: bool = False) -> list[Task]:` | `tasks` – current list, `force` – if `True` skip confirmation prompt | List of tasks that were removed (empty list if none) | • Determines the set `to_remove = [t for t in tasks if t["completed"]]`. <br>• If `to_remove` is empty → returns `[]` without prompting. <br>• If `force` is `False` → calls `confirm("Remove all completed tasks? (y/N): ")`; if the user declines, returns `[]`. <br>• If the user confirms **or** `force` is `True` → removes each task in `to_remove` from `tasks` and returns the list of removed tasks. <br>**Never** removes pending tasks. |
| `format_task_line` | `def format_task_line(task: Task) -> str:` | `task` – a single task | Human‑readable line for CLI output, e.g. `"  1  [ ] Buy milk"` | Status column: `"[ ]"` for pending, `"[x]"` for done. <br>ID column is right‑aligned to width 3 (`f"{task['id']:>3}"`). |
| `print_tasks` | `def print_tasks(tasks: list[Task]) -> None:` | `tasks` – list to display | Writes formatted lines to `stdout` (one per task) | Calls `format_task_line` for each task in order. <br>If `tasks` is empty → prints `"No tasks."`. |
| `confirm` | `def confirm(prompt: str) -> bool:` | `prompt` – message shown to the user | `True` if the user types a case‑insensitive `"y"` or `"yes"`; otherwise `False` | Reads a line from `stdin`, strips whitespace, lower‑cases it. |
| `parse_args` | `def parse_args(argv: list[str]) -> dict:` | `argv` – command‑line arguments (excluding program name) | Dictionary with keys `command` (str) and command‑specific options | Implements a minimal hand‑rolled parser (no external libraries). Recognises sub‑commands `add`, `list`, `done`, `remove`, `clear`, and global `-h/--help`. Raises `ValueError` with a helpful message for unknown commands or malformed options. |
| `main` | `def main(argv: list[str] | None = None) -> None:` | Optional `argv` (defaults to `sys.argv[1:]`) | Executes the CLI, prints results, exits with appropriate status | • Calls `parse_args`. <br>• Loads tasks via `load_tasks(get_default_path())`. <br>• Dispatches to the appropriate function based on `command`. <br>• Persists changes with `save_tasks` when the command mutates the list (`add`, `done`, `remove`, `clear`). <br>• Prints human‑readable messages (e.g. “Added task 3.”). <br>• Catches `ValueError`, prints the message to `stderr`, and exits with code 1. <br>• `--help` prints a short usage description and exits with code 0. |

*All functions are pure except where noted (they mutate the supplied `tasks` list or perform I/O). No class hierarchy is used; the only “lookup table” is the flat list of task dictionaries.*

---

## Error handling rules (exact)

| Situation | Raised exception | Message |
|-----------|------------------|---------|
| `add_task` receives an empty or whitespace‑only description | `ValueError` | `"Description cannot be empty"` |
| `list_tasks` receives a status other than `"all"`, `"pending"` or `"done"` | `ValueError` | `"Invalid status filter"` |
| `mark_done` or `remove_task` cannot find the supplied `task_id` | `ValueError` | `"Task ID not found"` |
| `parse_args` receives an unknown sub‑command or malformed option | `ValueError` | `"Unknown command"` or a specific usage hint |
| JSON file is missing or corrupted | *no exception* – `load_tasks` returns `[]` and rewrites an empty file | – |
| `clear_tasks` called with `force=False` and the user declines confirmation | *no exception* – returns empty list, no deletion | – |

---

## Worked examples (rounded to two decimals where applicable – none needed here)

```python
# 1. Loading from a non‑existent file → empty list
tasks = load_tasks("/tmp/nonexistent.json")
tasks == []                                            # file now exists and is empty

# 2. Adding the first task (timestamp shown as an example)
t1 = add_task(tasks, "Buy milk")
t1 == {"id": 1,
       "description": "Buy milk",
       "completed": False,
       "created": "2023-01-01T12:00:00"}               # any ISO‑8601 UTC string

# 3. Adding a second task
t2 = add_task(tasks, "Read book")
t2["id"] == 2

# 4. Listing pending tasks
list_tasks(tasks, status="pending") == [t1, t2]

# 5. Marking task 1 as done
mark_done(tasks, 1)["completed"] == True

# 6. Listing only done tasks
list_tasks(tasks, status="done") == [t1]

# 7. Removing task 2
removed = remove_task(tasks, 2)
removed["description"] == "Read book"
len(tasks) == 1                                        # only t1 remains

# 8. Clearing completed tasks (force=False, user confirms “y”)
# Assume `confirm` returns True in this test.
cleared = clear_tasks(tasks, force=False)
cleared == [t1]                                        # t1 was completed, so removed
len(tasks) == 0

# 9. Error case – empty description
# Raises ValueError with message "Description cannot be empty"
add_task(tasks, "   ")                                 # -> ValueError

# 10. Error case – unknown status filter
# Raises ValueError with message "Invalid status filter"
list_tasks(tasks, status="finished")                  # -> ValueError
```

---

## Example session (what a user types, what the program prints)

```
$ todo add "Buy milk"
Added task 1.

$ todo add "Read book"
Added task 2.

$ todo list --pending
  1  [ ] Buy milk
  2  [ ] Read book

$ todo done 1
Marked task 1 as completed.

$ todo list --done
  1  [x] Buy milk

$ todo remove 2
Removed task 2.

$ todo clear
Remove all completed tasks? (y/N): y
Cleared 1 completed task(s).

$ todo list
No tasks.

$ todo --help
Usage: todo <command> [options]

Commands:
  add "description"          Add a new task
  list [--all|--pending|--done]   List tasks (default: --all)
  done <id>                  Mark a task as completed
  remove <id>                Delete a task
  clear [--force]            Remove completed tasks (skip confirmation with --force)
  -h, --help                 Show this help message
```

*The session contains only the commands required by the specification; there is no `quit` command.*