"""common module – validation utilities for the expense splitter.

Provides:
- ExpenseError: custom exception for validation problems.
- validate_amount
- validate_name
- validate_people_list
- validate_participants
- validate_payer
- validate_expense_dict
"""

from __future__ import annotations

import math
from typing import List, Dict, Any

__all__ = [
    "ExpenseError",
    "validate_amount",
    "validate_name",
    "validate_people_list",
    "validate_participants",
    "validate_payer",
    "validate_expense_dict",
]


class ExpenseError(ValueError):
    """Exception raised for user‑visible validation errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def validate_amount(amount: float) -> None:
    """Validate that *amount* is a finite number greater than zero.

    Raises:
        ExpenseError: if the amount is not a positive finite number.
    """
    if not isinstance(amount, (int, float)):
        raise ExpenseError("amount must be a positive finite number")
    if not math.isfinite(amount) or amount <= 0:
        raise ExpenseError("amount must be a positive finite number")


def validate_name(name: str) -> None:
    """Validate that *name* is a non‑empty string after stripping whitespace.

    Raises:
        ExpenseError: if the name is not a non‑empty string.
    """
    if not isinstance(name, str):
        raise ExpenseError("name must be a non-empty string")
    if len(name.strip()) == 0:
        raise ExpenseError("name must be a non-empty string")


def validate_people_list(people: List[str]) -> None:
    """Validate a list of unique, non‑empty person names.

    Raises:
        ExpenseError: for an empty list, duplicate names, or invalid names.
    """
    if not isinstance(people, list):
        raise ExpenseError("people list cannot be empty")
    if len(people) == 0:
        raise ExpenseError("people list cannot be empty")

    seen = set()
    for person in people:
        validate_name(person)
        stripped = person.strip()
        if stripped in seen:
            raise ExpenseError(f'duplicate person "{stripped}"')
        seen.add(stripped)


def validate_participants(participants: List[str], known: List[str]) -> None:
    """Validate participants list against known people.

    Raises:
        ExpenseError: for an empty list, unknown names, duplicate names,
                      or invalid names.
    """
    if not isinstance(participants, list):
        raise ExpenseError("participants list cannot be empty")
    if len(participants) == 0:
        raise ExpenseError("participants list cannot be empty")

    known_set = set(name.strip() for name in known)
    seen = set()
    for participant in participants:
        validate_name(participant)
        stripped = participant.strip()
        if stripped not in known_set:
            raise ExpenseError(f'participant "{stripped}" is not a known person')
        if stripped in seen:
            raise ExpenseError(f'duplicate participant "{stripped}"')
        seen.add(stripped)


def validate_payer(payer: str, known: List[str]) -> None:
    """Validate that *payer* is a known person.

    Raises:
        ExpenseError: if the payer is unknown or invalid.
    """
    validate_name(payer)
    stripped = payer.strip()
    known_set = set(name.strip() for name in known)
    if stripped not in known_set:
        raise ExpenseError(f'payer "{stripped}" is not a known person')


def validate_expense_dict(expense: Dict[str, Any], known: List[str]) -> None:
    """Validate an expense dictionary.

    Expected keys: 'payer', 'amount', 'participants', 'description'.

    Raises:
        ExpenseError: for missing/extra keys or any sub‑validation failure.
    """
    required_keys = {"payer", "amount", "participants", "description"}
    if not isinstance(expense, dict) or set(expense.keys()) != required_keys:
        raise ExpenseError(
            "expense must contain keys payer, amount, participants, description"
        )

    # Validate each field
    validate_payer(expense["payer"], known)
    validate_amount(expense["amount"])
    if not isinstance(expense["participants"], list):
        raise ExpenseError("participants list cannot be empty")
    validate_participants(expense["participants"], known)

    # Description: must be a string; strip whitespace (empty allowed)
    desc = expense["description"]
    if not isinstance(desc, str):
        raise ExpenseError("description must be a string")
    # Stripping is performed for consistency, though the result is not used.
    _ = desc.strip()
