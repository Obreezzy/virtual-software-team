> **Warning:** this project is not fully resolved (modules with problems: storage). See last_test_output.txt.

# Habit Tracker  

A tiny command-line tool that lets you keep track of daily habits.  
All data is stored in a single JSON file (`~/.habit_tracker.json`).  
The program can:

* add a new habit  
* log a habit as done on a given date  
* show the current and longest streak for a habit  
* list habits that were missed yesterday  
* list all known habits  

Errors are reported as clear messages without a Python traceback.

---

## Files  

| File | Purpose |
|------|---------|
| `core.py` | Defines the public exception `HabitError` and the type aliases `HabitData` and `StreakInfo`. |
| `storage.py` | Loads and saves the JSON habit file. Handles missing files, malformed JSON and atomic writes. |
| `habit_logic.py` | Implements the business logic: adding habits, logging dates, computing streaks and finding missed habits. |
| `app.py` | The command-line interface. Parses sub-commands, calls the logic layer and prints human-readable results. |
| `test_*.py` | Unit tests for each module. Run with `python -m unittest`. |

---

## Requirements  

* Python 3.9+  
* No external dependencies  

---

## Installation  

Copy the four source files (`app.py`, `core.py`, `storage.py`, `habit_logic.py`) into a directory of your choice.  
Make sure the directory is on your `PYTHONPATH` or run the program from that directory.

---

## Running the program  

```bash
python app.py <subcommand> [options]
```

The program uses the following sub-commands:

| Sub-command | Description |
|-------------|-------------|
| `add <habit>` | Create a new habit. |
| `log <habit> <date>` | Record that `<habit>` was completed on `<date>` (ISO format `YYYY-MM-DD`). |
| `streak <habit>` | Show the current and longest streak for `<habit>` as of today. |
| `missed` | List habits that have **no** entry for yesterday. |
| `list` | List all habit names. |

Invalid options or malformed data raise a `HabitError`; the program prints the error message to **stderr** and exits with a non-zero status.

### Help  

The program does not provide a full help screen. Any unknown option (including `-h`) results in:

```text
Invalid option
```

---

## Running the tests  

All tests are standard `unittest` modules. Execute them from the directory that contains the source files:

```bash
python -m unittest
```

The command discovers `test_core.py`, `test_storage.py`, `test_habit_logic.py` and `test_app.py` and runs the suite. All tests should pass.

---

## Example session  

```bash
# Add two habits
$ python app.py add exercise
Habit "exercise" added.

$ python app.py add reading
Habit "reading" added.

# Log today's exercise
$ python app.py log exercise 2023-10-01
Logged "exercise" for 2023-10-01.

# Log yesterday's reading
$ python app.py log reading 2023-09-30
Logged "reading" for 2023-09-30.

# Show streak for exercise (assuming today is 2023-10-01)
$ python app.py streak exercise
Current streak: 1 day(s)
Longest streak: 1 day(s)

# List habits missed yesterday (2023-09-30)
$ python app.py missed
Missed yesterday:
- exercise

# List all habits
$ python app.py list
Habits:
- exercise
- reading
```

All dates must be valid ISO strings; otherwise the program prints an error like:

```text
Error: Invalid date format for "2023-02-30". Expected YYYY-MM-DD.
```

---

## License  

The code is released under the MIT License. Feel free to modify and redistribute.