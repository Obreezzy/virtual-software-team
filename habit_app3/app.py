import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_PATH = Path.home() / ".habits.json"
DATE_FORMAT = "%Y-%m-%d"


def get_today() -> date:
    """Return today's date."""
    return date.today()


def validate_habit_name(name: str) -> None:
    """Validate habit name according to the specification."""
    if name == "":
        raise ValueError("Habit name must be non-empty")
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(
            "Habit name may contain only letters, digits and underscores"
        )


def load_data(path: str) -> dict:
    """Load habit data from a JSON file, handling unreadable files."""
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("JSON is not a dict")
        return data
    except Exception:
        bak = p.with_name(p.name + ".bak")
        try:
            os.replace(str(p), str(bak))
        except OSError:
            # If rename fails, ignore – we still want to report the warning.
            pass
        print(
            "Warning: the habit file was unreadable; it was renamed to .bak and a new one will be started.",
            file=sys.stderr,
        )
        return {}


def save_data(path: str, data: dict) -> None:
    """Save habit data atomically, ensuring a trailing newline."""
    p = Path(path)
    tmp = p.with_name(p.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")  # ensure file ends with a newline as expected by tests
    os.replace(str(tmp), str(p))


def checkin(habit: str, data: dict, today: date) -> dict:
    """Record a check‑in for a habit, updating streaks."""
    validate_habit_name(habit)
    today_str = today.strftime(DATE_FORMAT)

    if habit not in data:
        data[habit] = {"last_date": today_str, "streak": 1}
        return data

    record = data[habit]
    last_date = datetime.strptime(record["last_date"], DATE_FORMAT).date()

    if last_date == today:
        raise ValueError("Already checked in today")
    if last_date > today:
        raise ValueError("Last check-in is dated in the future")

    if last_date == today - timedelta(days=1):
        record["streak"] += 1
    else:
        record["streak"] = 1

    record["last_date"] = today_str
    return data


def compute_streak(record: dict, today: date) -> tuple[int, bool]:
    """Compute current streak and whether a check‑in is pending."""
    last = datetime.strptime(record["last_date"], DATE_FORMAT).date()
    if last >= today:
        return record["streak"], False
    if last == today - timedelta(days=1):
        return record["streak"], True
    return 0, True


def status(data: dict, today: date) -> list[tuple[str, int, bool]]:
    """Return status tuples for all habits, sorted by name."""
    result = []
    for name in sorted(data):
        streak, pending = compute_streak(data[name], today)
        result.append((name, streak, pending))
    return result


def list_habits(data: dict) -> list[str]:
    """Return a sorted list of habit names."""
    return sorted(data)


def format_status_line(name: str, streak: int, pending: bool) -> str:
    """Format a single status line."""
    return f"{name:<12}{streak:>3}  {'pending' if pending else 'done'}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command‑line arguments."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_checkin = subparsers.add_parser("checkin")
    parser_checkin.add_argument("habit")

    subparsers.add_parser("status")
    subparsers.add_parser("list")

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    path: str = str(DEFAULT_PATH),
    today: date | None = None,
) -> int:
    """Entry point for the habit tracker CLI."""
    if argv is None:
        argv = sys.argv[1:]
    if today is None:
        today = get_today()

    try:
        args = parse_args(argv)

        if args.command == "checkin":
            data = load_data(path)
            checkin(args.habit, data, today)
            save_data(path, data)
            streak = data[args.habit]["streak"]
            print(f"Checked in: {args.habit} (streak: {streak})")
        elif args.command == "status":
            data = load_data(path)
            lines = status(data, today)
            if not lines:
                print("No habits yet.")
            else:
                for name, streak, pending in lines:
                    print(format_status_line(name, streak, pending))
        elif args.command == "list":
            data = load_data(path)
            names = list_habits(data)
            if not names:
                print("No habits yet.")
            else:
                for n in names:
                    print(n)
        else:
            # Should never happen because argparse enforces choices
            return 1
        return 0

    except ValueError as ve:
        print(f"Error: {ve}", file=sys.stderr)
        return 1
    except OSError as oe:
        print(f"I/O error: {oe}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
