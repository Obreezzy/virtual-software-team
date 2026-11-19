"""
expenses.py
~~~~~~~~~~

Library module that adds and lists expense records in a shared *Ledger*.

Shared data formats (must be obeyed exactly):
    Ledger   = {'people': List[str], 'expenses': List[Expense]}
    Expense  = {'payer': str,
                'amount': float,          # always > 0, two-decimal precision is not required
                'participants': List[str],
                'description': str}
    Payment  = {'from': str, 'to': str, 'amount': float}
"""

from __future__ import annotations

from typing import List, Dict, Any

# Public exception class and validation helpers are defined in ``common``.
# They must be used - they raise ``ExpenseError`` with the exact messages
# documented below.
from common import ExpenseError, validate_amount, validate_payer, \
    validate_participants, validate_name


def add_expense(
    ledger: Dict[str, Any],
    payer: str,
    amount: float,
    participants: List[str],
    description: str,
) -> None:
    """
    Validate arguments and append a new expense record to ``ledger['expenses']``.

    The validation helpers from ``common`` are used, but their error messages are
    normalised to match the exact wording required by the design specification.
    """
    # 1. Amount
    try:
        validate_amount(amount)                     # may raise ExpenseError
    except ExpenseError:
        raise ExpenseError('amount must be positive')

    # 2. Payer
    try:
        validate_payer(payer, ledger['people'])    # may raise ExpenseError
    except ExpenseError:
        raise ExpenseError('payer must be an existing person')

    # 3. Participants
    try:
        validate_participants(participants, ledger['people'])  # may raise ExpenseError
    except ExpenseError:
        raise ExpenseError('participants must be non-empty list of existing people')

    # 4. Description
    description_stripped = description.strip()
    if description_stripped == '':
        raise ExpenseError('description must not be empty')

    # 5. Name sanity (redundant but required by spec)
    # These calls use the helper but any message they raise is not expected to
    # reach the user because earlier checks catch the same conditions first.
    validate_name(payer)
    for name in participants:
        validate_name(name)

    # Build and store the expense record
    expense: Dict[str, Any] = {
        'payer': payer,
        'amount': amount,
        'participants': participants,
        'description': description_stripped,
    }
    ledger['expenses'].append(expense)


def list_expenses(ledger: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return a shallow copy of the expense list stored in ``ledger``.

    The returned list contains the same expense dictionaries; callers must treat
    them as immutable.
    """
    return list(ledger['expenses'])


__all__ = ['add_expense', 'list_expenses', 'ExpenseError']
