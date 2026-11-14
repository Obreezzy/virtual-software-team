# todo – simple command‑line task manager  

A tiny, dependency‑free Python CLI that stores a todo list in a JSON file (`~/.todo.json`).  
All data is kept as a flat list of dictionaries, each task having an **id**, **description**, **completed** flag and a UTC **created** timestamp.

---

## Quick start  

```bash
# run the program (the file must be executable or called with python)
python app.py add "Buy milk"          # add a new task
python app.py list                     # show all tasks
python app.py done 1                   # mark task 1 as completed
python app.py remove 2                 # delete task 2
python app.py clear --force            # delete all completed tasks without prompting
python app.py --help                   # show usage
```

The default storage location is `~/.todo.json`.  
You can supply a different path by calling `main` from another script, but the CLI always uses the default.

---

## Running the test suite  

The repository contains a single test file `test_app.py`.  
Execute it with the standard library test runner:

```bash
python -m unittest test_app.py
```

All tests run against temporary files, so your real `~/.todo.json` is never touched.

---

## Commands (hand‑rolled parser, no external packages)

| Command | Syntax | What it does |
|---------|--------|--------------|
| **add** | `add "description"` | Creates a new pending task. Prints `Added task <id>.` |
| **list** | `list [--all|--pending|--done]` | Shows tasks. Default is `--all`. |
| **done** | `done <id>` | Marks the given task as completed. Prints `Marked task <id> as completed.` |
| **remove** | `remove <id>` | Deletes the given task. Prints `Removed task <id>.` |
| **clear** | `clear [--force]` | Removes *only* completed tasks. Without `--force` you are prompted `Remove all completed tasks? (y/N):`. |
| **--help / -h** | `--help` | Prints a short usage message. |

Invalid input (unknown command, missing arguments, non‑integer IDs, etc.) results in a clear `ValueError` message printed to **stderr** and an exit code of 1.

---

## Example session  

```bash
$ python app.py add "Buy milk"
Added task 1.

$ python app.py add "Read book"
Added task 2.

$ python app.py list --pending
  1  [ ] Buy milk
  2  [ ] Read book

$ python app.py done 1
Marked task 1 as completed.

$ python app.py list --done
  1  [x] Buy milk

$ python app.py remove 2
Removed task 2.

$ python app.py clear
Remove all completed tasks? (y/N): y
Cleared 1 completed task(s).

$ python app.py list
No tasks.

$ python app.py --help
Usage: todo <command> [options]

Commands:
  add "description"          Add a new task
  list [--all|--pending|--done]   List tasks (default: --all)
  done <id>                  Mark a task as completed
  remove <id>                Delete a task
  clear [--force]            Remove completed tasks (skip confirmation with --force)
  -h, --help                 Show this help message
```

All commands above correspond directly to functions defined in **app.py** (`add_task`, `list_tasks`, `mark_done`, `remove_task`, `clear_tasks`, etc.) and operate on the JSON file atomically.