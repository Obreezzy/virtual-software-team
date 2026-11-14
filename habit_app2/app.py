#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Constants
DEFAULT_PATH = Path.home() / ".habits.json"
DATE_FORMAT = "%Y-%m-%d"


def get_today() -> datetime.date:
    """Return today's date."""
    return datetime.date.today()


def validate_habit_name(name: str) -> None:
    """Validate habit name according to the specification."""
    if name == "":
        raise ValueError("Habit name must be non-empty")
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(
            "Habit name may contain only letters, digits and underscores"
        )


def load_data(path: str) -> Dict[str, Dict[str, Any]]:
    """Load habit data from a JSON file."""
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("JSON is not a dict")
        return data
    except Exception as exc:  # includes JSONDecodeError, OSError, ValueError
        bak_path = str(path) + ".bak"
        try:
            os.replace(str(p), bak_path)
        except OSError:
            # If rename fails, ignore – we still want to report the warning.
            pass
        print(
            "Warning: the habit file was unreadable; it was renamed to .bak and a new one will be started.",
            file=sys.stderr,
        )
        return {}


def save_data(path: str, data: Dict[str, Dict[str, Any]]) -> None:
    """Save habit data atomically."""
    tmp_path = str(path) + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def checkin(habit: str, data: Dict[str, Dict[str, Any]], today: datetime.date) -> Dict[
    str, Dict[str, Any]
]:
    """Record a check‑in for a habit."""
    validate_habit_name(habit)
    today_str = today.strftime(DATE_FORMAT)

    if habit not in data:
        data[habit] = {"last_date": today_str, "streak": 1}
        return data

    record = data[habit]
    last_date_str = record["last_date"]
    last_date = datetime.datetime.strptime(last_date_str, DATE_FORMAT).date()

    if last_date == today:
        raise ValueError("Already checked in today")
    if last_date > today:
        raise ValueError("Last check-in is dated in the future")

    # Determine new streak
    if last_date == today - datetime.timedelta(days=1):
        record["streak"] = record["streak"] + 1
    else:
        record["streak"] = 1

    record["last_date"] = today_str
    return data


def compute_streak(
    record: Dict[str, Any], today: datetime.date
) -> Tuple[int, bool]:
    """Compute current streak and whether a check‑in is pending."""
    last_date = datetime.datetime.strptime(
        record["last_date"], DATE_FORMAT
    ).date()
    streak = record["streak"]

    if last_date >= today:
        return streak, False
    if last_date == today - datetime.timedelta(days=1):
        return streak, True
    # missed a day
    return 0, True


def status(
    data: Dict[str, Dict[str, Any]], today: datetime.date
) -> List[Tuple[str, int, bool]]:
    """Return status tuples for all habits."""
    result: List[Tuple[str, int, bool]] = []
    for name in sorted(data):
        streak, pending = compute_streak(data[name], today)
        result.append((name, streak, pending))
    return result


def list_habits(data: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return sorted habit names."""
    return sorted(data)


def format_status_line(name: str, streak: int, pending: bool) -> str:
    """Format a single status line."""
    return f"{name:<12}{streak:>3}  {'pending' if pending else 'done'}"


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """Parse command‑line arguments."""
    parser = argparse.ArgumentParser(prog="app.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # checkin command
    parser_checkin = subparsers.add_parser("checkin", help="Check in a habit")
    parser_checkin.add_argument("habit", help="Habit name")

    # status command
    subparsers.add_parser("status", help="Show status of all habits")

    # list command
    subparsers.add_parser("list", help="List all habit names")

    return parser.parse_args(argv)


def main(
    argv: List[str] | None = None,
    path: str = str(DEFAULT_PATH),
    today: datetime.date | None = None,
) -> int:
    """Entry point."""
    if argv is None:
        argv = sys.argv[1:]
    if today is None:
        today = get_today()

    try:
        args = parse_args(argv)

        if args.command == "checkin":
            data = load_data(path)
            try:
                checkin(args.habit, data, today)
            except ValueError as ve:
                print(f"Error: {ve}", file=sys.stderr)
                return 1
            save_data(path, data)
            streak = data[args.habit]["streak"]
            print(f"Checked in: {args.habit} (streak: {streak})")
            return 0

        elif args.command == "status":
            data = load_data(path)
            lines = status(data, today)
            if not lines:
                print("No habits yet.")
            else:
                for name, streak, pending in lines:
                    print(format_status_line(name, streak, pending))
            return 0

        elif args.command == "list":
            data = load_data(path)
            names = list_habits(data)
            if not names:
                print("No habits yet.")
            else:
                for n in names:
                    print(n)
            return 0

        else:
            # Should never happen because argparse enforces choices
            return 1

    except ValueError as ve:
        print(f"Error: {ve}", file=sys.stderr)
        return 1
    except OSError as oe:
        print(f"I/O error: {oe}", file=sys.stderr)
        return 1
    except SystemExit:
        # argparse may call sys.exit; let it propagate
        raise


if __name__ == "__main__":
    sys.exit(main())
