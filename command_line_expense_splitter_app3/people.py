from __future__ import annotations

from typing import List, Dict, Any

from common import ExpenseError, validate_name


def add_person(ledger: Dict[str, Any], name: str) -> None:
    """
    Add a new person to the ledger.

    Parameters
    ----------
    ledger : dict
        Must contain the keys ``'people'`` (list) and ``'expenses'`` (list).
    name : str
        Name of the person to add.

    Raises
    ------
    ExpenseError
        * ``'name must be a non-empty string'`` – raised by ``validate_name`` for
          non‑string inputs.
        * ``'person name cannot be empty'`` – when the stripped name is empty.
        * ``'person already exists: {name}'`` – when the name is already present.
    """
    # 1. Ensure the input is a string; let validate_name raise the correct message for non‑strings.
    if not isinstance(name, str):
        validate_name(name)  # will raise ExpenseError('name must be a non-empty string')
    
    # 2. Check for empty‑after‑strip condition before calling validate_name,
    #    because validate_name would raise the generic message.
    if name.strip() == "":
        raise ExpenseError("person name cannot be empty")
    
    # 3. At this point the name is a non‑empty string; validate_name should now pass.
    validate_name(name)

    # 4. Ensure the person is not already in the ledger.
    if name in ledger["people"]:
        raise ExpenseError(f"person already exists: {name}")

    # 5. Append the new person.
    ledger["people"].append(name)


def list_people(ledger: Dict[str, Any]) -> List[str]:
    """
    Return a new list of all people in the ledger, sorted alphabetically.

    Parameters
    ----------
    ledger : dict
        Must contain the key ``'people'`` (list).

    Returns
    -------
    List[str]
        Sorted copy of the people list.
    """
    return sorted(ledger["people"])
