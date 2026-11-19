"""core.py – Habit streak tracking data structures and error type.

This module defines only the public API required by the rest of the
application: a custom exception type and two type aliases.  It contains
no runtime logic, I/O, or side‑effects.
"""

from __future__ import annotations

from typing import TypedDict, Dict, List

__all__ = ["HabitError", "HabitData", "StreakInfo"]


class HabitError(Exception):
    """Exception raised for user‑visible error conditions.

    The message should be a short, human‑readable sentence without trailing
    punctuation.  Callers are expected to catch this exception and present
    the message to the user.
    """
    pass


# Type aliases – they are simple aliases to built‑in containers; the module
# does not enforce the constraints described in the design (e.g. ordering,
# uniqueness, non‑empty habit names).  Down‑stream code must respect those
# contracts.
HabitData = Dict[str, List[str]]
StreakInfo = Dict[str, int]
