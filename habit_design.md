# Design: command-line habit tracker (single file: app.py)

Standard library only. Plain functions, no classes. Every message in this design is
plain ASCII (no special dashes or quotes) and must be used exactly as written.

## Files, dates and testing rules

- Habit data lives in a JSON file. The default is `DEFAULT_PATH = Path.home() / ".habits.json"`.
- Every function that touches the file takes a `path` argument, and `main` accepts an
  optional `path` and an optional `today`, so tests use a temporary file and a fixed
  date and never touch the real file or the real clock.
- Open files with `encoding="utf-8"`.
- `DATE_FORMAT = "%Y-%m-%d"`.
- **Dates inside the `data` dict are always ISO strings** such as `"2023-10-05"`, never
  `date` objects. The `today` arguments are `datetime.date` objects. Convert with
  `today.strftime(DATE_FORMAT)` and `datetime.datetime.strptime(text, DATE_FORMAT).date()`.

## Data model

The JSON file holds one flat dict keyed by habit name:

```json
{
  "exercise": {"last_date": "2023-10-04", "streak": 5},
  "meditate": {"last_date": "2023-10-03", "streak": 2}
}
```

`last_date` is the ISO date of the most recent check-in. `streak` is a whole number of
consecutive days that ends on `last_date` (1 or more).

## Functions

### `get_today() -> datetime.date`

Returns `datetime.date.today()`.

### `validate_habit_name(name: str) -> None`

- Raises `ValueError("Habit name must be non-empty")` if `name == ""`.
- Raises `ValueError("Habit name may contain only letters, digits and underscores")`
  unless `re.fullmatch(r"[A-Za-z0-9_]+", name)` succeeds. (Use `fullmatch`; a pattern
  ending in `$` would let a trailing newline through.)

### `load_data(path: str) -> dict`

- If the file does not exist, returns `{}`.
- If the file cannot be read as JSON, or the JSON is not a dict: renames the file to
  `path + ".bak"` (replacing any older backup, using `os.replace`), prints
  `Warning: the habit file was unreadable; it was renamed to .bak and a new one will be started.`
  to stderr, and returns `{}`. (The unreadable file is never overwritten, so no data is lost.)

### `save_data(path: str, data: dict) -> None`

Writes `data` with `json.dump(data, f, indent=2, sort_keys=True)` to `path + ".tmp"`, then
`os.replace(path + ".tmp", path)`.

### `checkin(habit: str, data: dict, today: datetime.date) -> dict`

Changes `data` in place and also returns that same dict. Steps:

1. `validate_habit_name(habit)`.
2. If `habit` is not in `data`: set `data[habit] = {"last_date": <today as ISO string>, "streak": 1}`
   and return `data` (stop here).
3. Otherwise read the stored `last_date` and convert it to a `date`.
4. If it equals `today`: raise `ValueError("Already checked in today")`.
5. If it is after `today`: raise `ValueError("Last check-in is dated in the future")`.
6. If it equals `today` minus 1 day: `streak` becomes `streak + 1`. If it is older than that
   (a missed day): `streak` becomes `1`.
7. Set `last_date` to `today` as an ISO string, and return `data`.

### `compute_streak(record: dict, today: datetime.date) -> tuple[int, bool]`

Returns `(streak, pending)` for one habit's stored record. `pending` is True when the habit
still needs a check-in today. Let `last` be `record["last_date"]` as a `date`:

- `last >= today`: return `(record["streak"], False)`
- `last == today - 1 day`: return `(record["streak"], True)`
- older than that (a missed day): return `(0, True)` (the streak is broken)

### `status(data: dict, today: datetime.date) -> list[tuple[str, int, bool]]`

Returns `(habit_name, streak, pending)` for every habit, sorted by name, using
`compute_streak`. No printing.

### `list_habits(data: dict) -> list[str]`

Returns `sorted(data)`.

### `format_status_line(name: str, streak: int, pending: bool) -> str`

Returns `f"{name:<12}{streak:>3}  {'pending' if pending else 'done'}"`.

### `parse_args(argv: list[str] | None = None) -> argparse.Namespace`

Uses `argparse` with required sub-commands: `checkin HABIT`, `status`, `list`. The result
has `command` and, for `checkin`, `habit`. Bad usage makes argparse print its own usage
message and exit with code 2 (`SystemExit(2)`; do not catch it).

### `main(argv: list[str] | None = None, path: str = str(DEFAULT_PATH), today: datetime.date | None = None) -> int`

`argv` defaults to `sys.argv[1:]` and `today` defaults to `get_today()`. Returns 0 on success.

- `checkin`: load the data, call `checkin`, save, and print `Checked in: <habit> (streak: <streak>)`.
- `status`: print one `format_status_line` per habit; if there are no habits print `No habits yet.`
- `list`: print one habit name per line; if there are none print `No habits yet.`
- On `ValueError`: print `Error: <message>` to stderr and return 1.
- On `OSError`: print `I/O error: <message>` to stderr and return 1.

The file ends with `if __name__ == "__main__": sys.exit(main())`.

## Worked examples

All `today` values are `datetime.date` objects, and dates inside `data` are ISO strings.

1. validate_habit_name('exercise')  ->  None

2. validate_habit_name('')  ->  raises ValueError("Habit name must be non-empty")

3. validate_habit_name('my habit')  ->  raises ValueError("Habit name may contain only letters, digits and underscores")

4. validate_habit_name('read-books')  ->  raises ValueError("Habit name may contain only letters, digits and underscores")

5. validate_habit_name('exercise\n')  ->  raises ValueError("Habit name may contain only letters, digits and underscores")

6. checkin('exercise', {}, date(2023, 10, 5))  ->  {"exercise": {"last_date": "2023-10-05", "streak": 1}}

7. checkin('exercise', {"exercise": {"last_date": "2023-10-04", "streak": 5}}, date(2023, 10, 5))  ->  {"exercise": {"last_date": "2023-10-05", "streak": 6}}

8. checkin('exercise', {"exercise": {"last_date": "2023-10-03", "streak": 3}}, date(2023, 10, 5))  ->  {"exercise": {"last_date": "2023-10-05", "streak": 1}}

9. checkin('exercise', {"exercise": {"last_date": "2023-10-05", "streak": 1}}, date(2023, 10, 5))  ->  raises ValueError("Already checked in today")

10. checkin('exercise', {"exercise": {"last_date": "2023-10-06", "streak": 2}}, date(2023, 10, 5))  ->  raises ValueError("Last check-in is dated in the future")

11. checkin('meditate', {"exercise": {"last_date": "2023-10-05", "streak": 6}}, date(2023, 10, 5))  ->  {"exercise": {"last_date": "2023-10-05", "streak": 6}, "meditate": {"last_date": "2023-10-05", "streak": 1}}

12. checkin('bad-name', {}, date(2023, 10, 5))  ->  raises ValueError("Habit name may contain only letters, digits and underscores")

13. (`checkin` changes the dict it is given AND returns that same dict.)

14. compute_streak({"last_date": "2023-10-05", "streak": 6}, date(2023, 10, 5))  ->  (6, False)

15. compute_streak({"last_date": "2023-10-04", "streak": 5}, date(2023, 10, 5))  ->  (5, True)

16. compute_streak({"last_date": "2023-10-02", "streak": 4}, date(2023, 10, 5))  ->  (0, True)

17. compute_streak({"last_date": "2023-10-06", "streak": 2}, date(2023, 10, 5))  ->  (2, False)

18. status({"exercise": {"last_date": "2023-10-05", "streak": 6}, "meditate": {"last_date": "2023-10-04", "streak": 3}, "read": {"last_date": "2023-09-30", "streak": 2}}, date(2023, 10, 5))  ->  [('exercise', 6, False), ('meditate', 3, True), ('read', 0, True)]

19. status({}, date(2023, 10, 5))  ->  []

20. list_habits(<the same dict>)  ->  ['exercise', 'meditate', 'read']

21. format_status_line("exercise", 6, False)  ->  'exercise      6  done'

22. format_status_line("read", 0, True)  ->  'read          0  pending'

23. load_data(<path of a file that does not exist>)  ->  {}

24. After `save_data(path, {"read": {...}, "exercise": {...}})` the file contains exactly this text (2-space indent, keys sorted), and `load_data(path)` returns the same dict:

```text
{
  "exercise": {
    "last_date": "2023-10-05",
    "streak": 6
  },
  "read": {
    "last_date": "2023-09-30",
    "streak": 2
  }
}
```

25. If the file contains `{not json`, `load_data(path)` returns {}, the file is renamed to `path + ".bak"` (so the old text is kept there), and this line is printed to stderr:

```text
Warning: the habit file was unreadable; it was renamed to .bak and a new one will be started.
```

## Example session

The line `# today = ...` is not typed: it says which date the program treats as today. (Tests
pass it as `main(argv, path=..., today=date(...))`.) Error messages go to stderr and `main`
returns 1; everything else goes to stdout.

```text
# today = 2023-10-05
$ python app.py status
No habits yet.
$ python app.py checkin exercise
Checked in: exercise (streak: 1)
$ python app.py checkin meditate
Checked in: meditate (streak: 1)
$ python app.py status
exercise      1  done
meditate      1  done
$ python app.py checkin exercise
Error: Already checked in today
# today = 2023-10-06
$ python app.py status
exercise      1  pending
meditate      1  pending
$ python app.py checkin exercise
Checked in: exercise (streak: 2)
# today = 2023-10-09
$ python app.py status
exercise      0  pending
meditate      0  pending
$ python app.py list
exercise
meditate
$ python app.py checkin Bad-Name
Error: Habit name may contain only letters, digits and underscores
```
