**app.py – Design Specification**

---

## 1. Constants & Globals
| Name | Type | Value | Description |
|------|------|-------|-------------|
| `STORAGE_PATH` | `pathlib.Path` | `Path.home() / ".habits.json"` | File that holds all habit data. |
| `HABIT_NAME_PATTERN` | `re.Pattern` | `re.compile(r"^[A-Za-z0-9_]+$")` | Allowed characters for a habit name. |
| `DATE_FORMAT` | `str` | `"%Y-%m-%d"` | ISO‑8601 format used when serialising dates. |

---

## 2. Data model (what is stored in the JSON file)

```json
{
  "exercise": {"last_date": "2023-10-04", "streak": 5},
  "meditate": {"last_date": "2023-10-03", "streak": 2}
}
```

*Top‑level* – a **flat dict** keyed by habit name (string).  
*Value* – a dict with two keys:

| Key | Type | Meaning |
|-----|------|---------|
| `last_date` | `str` (ISO‑8601) | Calendar day of the most recent successful check‑in. |
| `streak` | `int` (≥ 0) | Number of consecutive days **including** `last_date`. |

---

## 3. Public functions (signatures, inputs, outputs, behaviour)

| Signature | Input | Output | Behaviour (including errors) |
|-----------|-------|--------|------------------------------|
| `def load_data() -> dict[str, dict[str, Any]]:` | *none* | habit dict (as described above) | <ul><li>If `STORAGE_PATH` does **not** exist → return `{}`.</li><li>If file exists but cannot be parsed (`json.JSONDecodeError`) → return `{}` after logging a warning.</li></ul> |
| `def save_data(data: dict[str, dict[str, Any]]) -> None:` | `data` – the habit dict | `None` | Serialises `data` to `STORAGE_PATH` using `json.dump(..., indent=2)`. Overwrites any existing file. |
| `def validate_habit_name(name: str) -> None:` | `name` – habit identifier | `None` | <ul><li>Raises `ValueError("Habit name must be non‑empty")` if `name == ""`.</li><li>Raises `ValueError("Habit name may contain only letters, digits and underscores")` if `HABIT_NAME_PATTERN` does not match.</li></ul> |
| `def get_today() -> datetime.date:` | *none* | today’s date (local) | Returns `datetime.date.today()`. Is isolated for easier testing. |
| `def checkin(habit: str, data: dict[str, dict[str, Any]], today: datetime.date) -> dict[str, dict[str, Any]]:` | <ul><li>`habit` – name to check‑in</li><li>`data` – current habit dict (as returned by `load_data`)</li><li>`today` – the date to treat as “now”</li></ul> | Updated habit dict (same object may be mutated) | Steps (all dates are `datetime.date` objects, converted to/from ISO strings only when persisting):<ol><li>`validate_habit_name` – may raise `ValueError`.</li><li>If `habit` not in `data` → create entry `{ "last_date": today, "streak": 1 }`.</li><li>Else retrieve `record = data[habit]` and parse `record["last_date"]` to a `date`.</li><li>If `record_date == today` → raise `ValueError("Already checked in today")`.</li><li>If `record_date == today - timedelta(days=1)` → `record["streak"] += 1`.</li><li>If `record_date < today - timedelta(days=1)` → `record["streak"] = 1` (missed day resets streak).</li><li>Finally set `record["last_date"] = today` (as ISO string).</li></ol> |
| `def compute_streak(record: dict[str, Any], today: datetime.date) -> tuple[int, bool]:` | `record` – a single habit’s stored dict; `today` – current date | `(streak, pending)` where:<ul><li>`streak` – int, the *effective* streak for display (0 if a day was missed).</li><li>`pending` – `True` if the habit **has not** been checked in today, otherwise `False`.</li></ul> | <ol><li>Parse `record["last_date"]` → `last_date`.</li><li>If `last_date == today` → `return (record["streak"], False)`.</li><li>If `last_date == today - timedelta(days=1)` → `return (record["streak"], True)`.</li><li>Otherwise (gap ≥ 2 days) → `return (0, True)` (streak is broken, pending check‑in). </li></ol> |
| `def status(data: dict[str, dict[str, Any]]) -> list[tuple[str, int, bool]]:` | `data` – habit dict | List of `(habit_name, streak, pending)` for every habit, sorted alphabetically. | Calls `compute_streak` for each habit. No I/O; the caller (CLI) formats the list. |
| `def list_habits(data: dict[str, dict[str, Any]]) -> list[str]:` | `data` – habit dict | Alphabetically sorted list of habit names. | Simple `sorted(data.keys())`. |
| `def parse_args(argv: list[str] | None = None) -> argparse.Namespace:` | Optional command‑line token list (default `sys.argv[1:]`). | Namespace with attributes `command` (`"checkin" | "status" | "list"`), `habit` (only for `checkin`). | Uses `argparse` to enforce sub‑commands and required arguments. |
| `def main() -> None:` | *none* | *none* (exits via `sys.exit`) | <ol><li>Parse arguments.</li><li>Load data (`load_data`).</li><li>Dispatch:</li><ul><li>`checkin` → call `checkin`, `save_data`, print success message.</li><li>`status` → call `status`, pretty‑print each habit line.</li><li>`list` → call `list_habits`, print each name.</li></ul></li><li>All `ValueError`s are caught and printed as `Error: <msg>`; program exits with code 1.</li></ol> |

---

## 4. Error handling summary

| Situation | Raised / Returned | Message (shown to user) |
|-----------|-------------------|--------------------------|
| Invalid habit name (empty) | `ValueError` from `validate_habit_name` | “Habit name must be non‑empty” |
| Invalid habit name (bad chars) | `ValueError` from `validate_habit_name` | “Habit name may contain only letters, digits and underscores” |
| Duplicate check‑in on same day | `ValueError` from `checkin` | “Already checked in today” |
| JSON file corrupted | `json.JSONDecodeError` caught inside `load_data` | (no user‑visible error; file is treated as empty) |
| Unknown sub‑command / missing argument | `argparse` prints its own usage message and exits with code 2. |

---

## 5. Worked examples  

All dates are `datetime.date` objects.

```python
# 1. Fresh check‑in creates a habit
checkin("exercise", {}, date(2023, 10, 5))
# == {"exercise": {"last_date": "2023-10-05", "streak": 1}}

# 2. Consecutive day increments streak
checkin(
    "exercise",
    {"exercise": {"last_date": "2023-10-04", "streak": 5}},
    date(2023, 10, 5)
)
# == {"exercise": {"last_date": "2023-10-05", "streak": 6}}

# 3. Missed a day → streak resets
checkin(
    "exercise",
    {"exercise": {"last_date": "2023-10-03", "streak": 3}},
    date(2023, 10, 5)
)
# == {"exercise": {"last_date": "2023-10-05", "streak": 1}}

# 4. Duplicate check‑in on same day raises
checkin(
    "exercise",
    {"exercise": {"last_date": "2023-10-05", "streak": 1}},
    date(2023, 10, 5)
)
# raises ValueError("Already checked in today")

# 5. Compute streak when already checked today
compute_streak(
    {"last_date": "2023-10-05", "streak": 6},
    date(2023, 10, 5)
)
# == (6, False)   # pending = False (already done)

# 6. Compute streak when yesterday was last check‑in
compute_streak(
    {"last_date": "2023-10-04", "streak": 5},
    date(2023, 10, 5)
)
# == (5, True)    # pending =```python
# 7. Compute streak after a missed day (gap ≥ 2)
compute_streak(
    {"last_date": "2023-10-02", "streak": 4},
    date(2023, 10, 5)
)
# == (0, True)    # streak broken, pending check‑in

# 8. status() on mixed data
status({
    "exercise": {"last_date": "2023-10-05", "streak": 6},
    "meditate": {"last_date": "2023-10-04", "streak": 3},
    "read":     {"last_date": "2023-09-30", "streak": 2}
})
# == [
#        ("exercise", 6, False),   # already checked today
#        ("meditate", 3, True),    # pending (yesterday was last)
#        ("read", 0, True)         # streak broken, pending
#    ]
```

---

## Example session  

User runs the program interactively from a terminal.

```
$ python app.py checkin exercise
Checked in: exercise (streak: 1)

$ python app.py checkin meditate
Checked in: meditate (streak: 1)

$ python app.py status
exercise  1  (pending)
meditate  1  (pending)

$ python app.py checkin exercise
Checked in: exercise (streak: 2)

$ python app.py status
exercise  2  (pending)
meditate  1  (pending)

$ python app.py list
exercise
meditate

$ python app.py checkin exercise   # same day again
Error: Already checked in today
```