# storage.py
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from typing import Final

from core import HabitError, HabitData

# Public constants
DEFAULT_FILENAME: Final[str] = ".habit_tracker.json"
DEFAULT_PATH: Final[str] = os.path.expanduser(f"~/{DEFAULT_FILENAME}")


def get_default_path() -> str:
    """Return the absolute path to the default habit JSON file."""
    return DEFAULT_PATH


def _is_iso_date(s: str) -> bool:
    """Return True iff *s* is a valid ISOâ€‘8601 date (YYYYâ€‘MMâ€‘DD)."""
    if not isinstance(s, str):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def _validate_habit_data(data: HabitData) -> None:
    """
    Validate that *data* conforms to the HabitData specification.

    Raises:
        HabitError: If the data is malformed.
    """
    if not isinstance(data, dict):
        raise HabitError("malformed habit data")

    for key, value in data.items():
        # 1. Keys â€“ nonâ€‘empty, nonâ€‘whitespace strings
        if not isinstance(key, str) or not key.strip():
            raise HabitError("malformed habit data")

        # 2. Values â€“ list of strings
        if not isinstance(value, list):
            raise HabitError("malformed habit data")
        for item in value:
            if not isinstance(item, str) or not _is_iso_date(item):
                raise HabitError("malformed habit data")

        # 3. List must be sorted ascending (lexicographically == chronological)
        if value != sorted(value):
            raise HabitError("malformed habit data")


def load_data(file_path: str) -> HabitData:
    """Load habit data from *file_path*.

    Returns an empty dict if the file does not exist.
    Raises HabitError with precise messages for all error conditions.
    """
    if not isinstance(file_path, str) or not file_path:
        raise HabitError("cannot read habit file")

    if not os.path.exists(file_path):
        return {}

    # Check read permission before attempting to open
    if not os.access(file_path, os.R_OK):
        raise HabitError("cannot read habit file")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                raise HabitError("malformed JSON file")
    except OSError:
        raise HabitError("cannot read habit file")

    # Validate structure
    _validate_habit_data(data)
    return data  # type: ignore[return-value]


def save_data(file_path: str, data: HabitData) -> None:
    """Save *data* to *file_path* atomically.

    Raises HabitError with precise messages for all error conditions.
    """
    # Validate data first
    _validate_habit_data(data)

    if not isinstance(file_path, str) or not file_path:
        raise HabitError("cannot write habit file")

    dir_name = os.path.dirname(file_path) or "."
    # Ensure we can write to the target directory
    if not os.access(dir_name, os.W_OK):
        raise HabitError("cannot write habit file")

    try:
        # Create a temporary file in the same directory
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=dir_name,
            mode="w",
            encoding="utf-8",
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp_name = tmp.name
    except OSError:
        raise HabitError("cannot write habit file")

    try:
        os.replace(tmp_name, file_path)
    except OSError:
        # Attempt to clean up the temp file before raising
        try:
            os.remove(tmp_name)
        finally:
            raise HabitError("cannot replace habit file")
