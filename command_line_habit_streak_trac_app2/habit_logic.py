# app.py
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Dict, Tuple

from core import HabitError, HabitData, StreakInfo


def _parse_iso_date(s: str) -> date:
    """
    Convert a string to a datetime.date, ensuring the exact YYYY-MM-DD format.
    Raises HabitError with a precise message on failure.
    """
    if not isinstance(s, str):
        raise HabitError(f'date "{s}" is not a valid ISO date (YYYY-MM-DD)')
    try:
        # datetime.date.fromisoformat enforces the YYYY-MM-DD format
        d = date.fromisoformat(s)
    except Exception:
        raise HabitError(f'date "{s}" is not a valid ISO date (YYYY-MM-DD)')
    # No need to check for nan/inf on strings, but keep the guard for symmetry
    return d


def _consecutive_streaks(dates: List[date], today: date) -> Tuple[int, int]:
    """
    Given a **sorted** list of dates, return (current, longest) streak lengths.
    `current` is the streak ending on `today`. If the most recent logged date
    is before `today`, `current` is 0.
    `longest` is the maximum length of any consecutive run in the list.
    """
    if not dates:
        return 0, 0

    # Longest streak
    longest = 0
    run_len = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] + timedelta(days=1):
            run_len += 1
        else:
            longest = max(longest, run_len)
            run_len = 1
    longest = max(longest, run_len)

    # Current streak
    if dates[-1] != today:
        current = 0
    else:
        current = 1
        # Walk backwards through the list
        for i in range(len(dates) - 2, -1, -1):
            expected = dates[i + 1] - timedelta(days=1)
            if dates[i] == expected:
                current += 1
            else:
                break

    return current, longest


def add_habit(data: HabitData, name: str) -> HabitData:
    """
    Return a new HabitData with `name` added and an empty date list.
    Raises HabitError on validation problems.
    """
    if not isinstance(name, str) or not name.strip():
        raise HabitError('habit name must be a non-empty string')
    if name in data:
        raise HabitError(f'habit "{name}" already exists')
    new_data = dict(data)  # shallow copy of the dict
    new_data[name] = []     # new empty list for the habit
    return new_data


def log_habit(data: HabitData, name: str, iso_date: str) -> HabitData:
    """
    Return a new HabitData where `iso_date` is inserted into the sorted list
    for `name`. Raises HabitError on validation problems.
    """
    if name not in data:
        raise HabitError(f'habit "{name}" does not exist')
    # Validate date string
    parsed_date = _parse_iso_date(iso_date)

    # Convert existing strings to dates for comparison
    existing_strs = data[name]
    existing_dates = [date.fromisoformat(d) for d in existing_strs]

    if parsed_date in existing_dates:
        raise HabitError(f'date "{iso_date}" already logged for habit "{name}"')

    # Insert while keeping order
    new_dates = existing_dates + [parsed_date]
    new_dates.sort()
    new_strs = [d.isoformat() for d in new_dates]

    new_data = dict(data)
    new_data[name] = new_strs
    return new_data


def get_streaks(data: HabitData, name: str, today: str) -> StreakInfo:
    """
    Compute current and longest consecutive-day streaks for `name` as of `today`.
    Returns a StreakInfo dict.
    """
    if name not in data:
        raise HabitError(f'habit "{name}" does not exist')
    today_date = _parse_iso_date(today)

    date_strs = data[name]
    dates = [date.fromisoformat(d) for d in date_strs]  # already sorted
    current, longest = _consecutive_streaks(dates, today_date)

    return {'current': current, 'longest': longest}  # type: ignore[return-value]


def get_missed_yesterday(data: HabitData, yesterday: str) -> List[str]:
    """
    Return a sorted list of habit names that do NOT have an entry for `yesterday`.
    """
    y_date = _parse_iso_date(yesterday)
    y_iso = y_date.isoformat()
    missed: List[str] = []
    for habit, dates in data.items():
        if y_iso not in dates:
            missed.append(habit)
    missed.sort()
    return missed
