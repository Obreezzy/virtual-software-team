Requirements:
- The program stores habits and the dates each habit was completed in a JSON file.
- Users can add a new habit, log a habit as done on a specific date, and list all habits.
- The program reports the current streak and the longest streak for any habit.
- It can list habits that were missed yesterday.
- All dates are ISO strings (YYYY-MM-DD) and are validated.
- Invalid commands or data raise a clear HabitError without a traceback to the user.
- The JSON file is created if it does not exist and is written atomically.
- The command‑line interface uses sub‑commands: add, log, streak, missed, list.
Shared data formats (every module must follow these EXACTLY):
* HabitData: dict where each key is a non‑empty habit name (str) and each value is a list of ISO date strings (YYYY-MM-DD) sorted in ascending order, e.g. {'exercise': ['2023-09-01', '2023-09-02']}
* StreakInfo: dict with keys 'current' and 'longest', both int, e.g. {'current': 5, 'longest': 12}
Modules (in build order; each may import only the ones before it):
1. core.py - Define shared exception and type aliases.
   - class HabitError(Exception)  # raised for any user‑visible error condition
   - HabitData = dict[str, list[str]]  # mapping habit name to list of ISO date strings, sorted ascending
   - StreakInfo = dict[str, int]  # {'current': int, 'longest': int}
2. storage.py - Load and save habit data to a JSON file.
   - def get_default_path() -> str  # returns path '~/.habit_tracker.json' expanded to an absolute path
   - def load_data(file_path: str) -> HabitData  # reads JSON, returns empty dict if file missing, raises HabitError on malformed JSON
   - def save_data(file_path: str, data: HabitData) -> None  # writes JSON atomically, raises HabitError on I/O failure
3. habit_logic.py - Business logic for managing habits and computing streaks.
   - def add_habit(data: HabitData, name: str) -> HabitData  # adds a new habit with empty date list, raises HabitError if name exists or empty
   - def log_habit(data: HabitData, name: str, date: str) -> HabitData  # records date for habit, keeps dates sorted, raises HabitError for unknown habit or invalid date format
   - def get_streaks(data: HabitData, name: str, today: str) -> StreakInfo  # returns current and longest streak in days, raises HabitError if habit unknown or today not ISO
   - def get_missed_yesterday(data: HabitData, yesterday: str) -> list[str]  # returns list of habit names that have no entry for the given date, raises HabitError on invalid date
4. app.py - Command‑line interface and program entry point.
   - def main(argv: list[str] | None = None) -> None  # parses arguments, calls storage and habit_logic, prints human‑readable results, exits with 0 or prints error message
   - def _print_error(msg: str) -> None  # prints error to stderr without traceback
