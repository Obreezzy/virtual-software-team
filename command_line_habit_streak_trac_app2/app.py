"""Commandâ€‘line entry point for the habit streak tracker."""

from __future__ import annotations

import datetime
import sys
from typing import List

import habit_logic
import core


def _print_error(msg: str) -> None:
    """Write *msg* to standard error followed by a newline."""
    sys.stderr.write(msg + "\n")


def _ensure_nonempty_str(value: str, field: str) -> str:
    """Strip *value* and ensure it is not empty.

    Raises:
        core.HabitError: If the stripped value is empty.
    """
    stripped = value.strip()
    if not stripped:
        raise core.HabitError(f"{field} must be a nonâ€‘empty string")
    return stripped


def _ensure_iso_date(value: str, field: str) -> str:
    """Validate that *value* is a real ISOâ€‘format date (YYYYâ€‘MMâ€‘DD).

    Raises:
        core.HabitError: If the value cannot be parsed as a date.
    """
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise core.HabitError(f"{field} must be a valid ISO date (YYYY-MM-DD)")
    return value


def main(argv: list[str] | None = None) -> None:
    """Parse commandâ€‘line arguments and execute the requested subâ€‘command.

    Errors are reported via ``_print_error``.  When *argv* is supplied the
    program exits with status 1 on error; otherwise it returns to the caller
    (interactive use).
    """
    interactive = argv is None
    if argv is None:
        argv = sys.argv[1:]

    try:
        if not argv:
            raise core.HabitError("no command supplied")

        # first token is the command
        cmd = argv[0]
        raw_args = argv[1:]

        # Validate command before any heavy imports
        valid_commands = {"add", "log", "streak", "missed", "list"}
        if cmd not in valid_commands:
            raise core.HabitError("Invalid option")

        # Import storage only after the command is known to be valid
        try:
            import storage
        except Exception as exc:
            # Convert any importâ€‘time problem into a clean HabitError
            raise core.HabitError("Failed to access data storage") from exc

        # Load data (may be empty)
        path = storage.get_default_path()
        data = storage.load_data(path)

        if cmd == "add":
            if len(raw_args) != 1:
                raise core.HabitError("add command requires exactly one argument")
            name = _ensure_nonempty_str(raw_args[0], "habit_name")
            data = habit_logic.add_habit(data=data, name=name)
            storage.save_data(path, data)
            print(f'Added habit "{name}"')

        elif cmd == "log":
            if len(raw_args) != 2:
                raise core.HabitError("log command requires exactly two arguments")
            name = _ensure_nonempty_str(raw_args[0], "habit_name")
            iso_date = _ensure_iso_date(raw_args[1], "date")
            data = habit_logic.log_habit(data=data, name=name, iso_date=iso_date)
            storage.save_data(path, data)
            print(f'Logged "{name}" for {iso_date}')

        elif cmd == "streak":
            if not (1 <= len(raw_args) <= 2):
                raise core.HabitError("streak command requires one or two arguments")
            name = _ensure_nonempty_str(raw_args[0], "habit_name")
            if len(raw_args) == 2:
                today = _ensure_iso_date(raw_args[1], "today")
            else:
                today = datetime.date.today().isoformat()
            streak_info = habit_logic.get_streaks(data=data, name=name, today=today)
            print(
                f"Current streak: {streak_info["current"]} days, "
                f"Longest streak: {streak_info["longest"]} days"
            )

        elif cmd == "missed":
            if len(raw_args) > 1:
                raise core.HabitError("missed command takes at most one argument")
            if raw_args:
                yesterday = _ensure_iso_date(raw_args[0], "yesterday")
            else:
                yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            missed: List[str] = habit_logic.get_missed_yesterday(
                data=data, yesterday=yesterday
            )
            if missed:
                for habit in sorted(missed):
                    print(habit)
            else:
                print("No missed habits")

        elif cmd == "list":
            if raw_args:
                raise core.HabitError("list command takes no arguments")
            habits = sorted(data.keys())
            if habits:
                for habit in habits:
                    print(habit)
            else:
                print("No habits defined")

    except core.HabitError as e:
        _print_error(str(e))
        if not interactive:
            sys.exit(1)

    except (KeyboardInterrupt, EOFError):
        # Silent termination; in nonâ€‘interactive mode exit with 0,
        # otherwise just return to the caller.
        if not interactive:
            sys.exit(0)

    # Any other exception is allowed to propagate â€“ it indicates a bug.


if __name__ == "__main__":
    main()

