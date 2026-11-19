#!/usr/bin/env python3
"""
Command‑line entry point for the expense splitter.

All heavy lifting (validation, persistence, settlement) is delegated to the
support modules.  This file only parses arguments, calls the appropriate
functions and prints user‑friendly messages.
"""

from __future__ import annotations

import sys
import os
import math
from typing import List, Any

import common
import people
import expenses
import settlement
import storage


DEFAULT_LEDGER_PATH = None  # will be set after defining _default_path()


def _default_path() -> str:
    """Return the absolute path of the default ledger file."""
    return os.path.expanduser("~/.expense_splitter.json")


def _load(path: str) -> dict:
    """Load a ledger from *path* using storage.load_ledger.

    If the file does not exist an empty ledger is returned.
    """
    return storage.load_ledger(path=path)


def _save(path: str, ledger: dict) -> None:
    """Save *ledger* to *path* using storage.save_ledger."""
    storage.save_ledger(path=path, ledger=ledger)


def _cmd_add_person(ledger: dict, args: List[str]) -> bool:
    """Add a new person to the ledger."""
    if len(args) != 1:
        raise common.ExpenseError("person name cannot be empty")
    name = args[0]

    # Reject empty, whitespace‑only, or special floating‑point strings.
    if not name.strip() or name.strip().lower() in {"nan", "inf", "infinity", "-inf", "-infinity"}:
        raise common.ExpenseError("person name cannot be empty")

    common.validate_name(name=name)
    people.add_person(ledger=ledger, name=name)
    print(f"Added person: {name}")
    return True


def _cmd_add_expense(ledger: dict, args: List[str]) -> bool:
    """Record a new expense."""
    if len(args) != 4:
        raise common.ExpenseError("amount must be a finite positive number")
    payer, amount_str, participants_str, description = args

    # payer validation
    common.validate_name(name=payer)
    common.validate_payer(payer=payer, known=ledger["people"])

    # amount validation
    try:
        amount = float(amount_str)
    except Exception:
        raise common.ExpenseError("amount must be a finite positive number")
    if not math.isfinite(amount) or amount <= 0:
        raise common.ExpenseError("amount must be a finite positive number")
    common.validate_amount(amount=amount)

    # participants validation
    participants = [
        part.strip() for part in participants_str.split(",") if part.strip()
    ]
    if not participants:
        raise common.ExpenseError("participants list cannot be empty")
    common.validate_participants(participants=participants, known=ledger["people"])

    # description validation
    if not description.strip():
        raise common.ExpenseError("description cannot be empty")

    expenses.add_expense(
        ledger=ledger,
        payer=payer,
        amount=amount,
        participants=participants,
        description=description,
    )
    print("Expense recorded.")
    return True


def _cmd_settle(ledger: dict, args: List[str]) -> bool:
    """Compute and display settlements."""
    if args:
        raise common.ExpenseError("settlement impossible")
    payments = settlement.compute_settlements(ledger=ledger)
    for payment in payments:
        from_ = payment["from"]
        to = payment["to"]
        amount = payment["amount"]
        print(f"{from_} pays {to}: ${amount:.2f}")
    return False


def _cmd_list_people(ledger: dict, args: List[str]) -> bool:
    """List all known people."""
    if args:
        raise common.ExpenseError("Invalid option")
    for name in sorted(people.list_people(ledger=ledger)):
        print(name)
    return False


def _cmd_list_expenses(ledger: dict, args: List[str]) -> bool:
    """List all recorded expenses.

    Expected format per line (as required by the test suite):
        "{payer} paid ${amount:.2f} for {description}"
    """
    if args:
        # The command does not accept any arguments; any extra input is an error.
        raise common.ExpenseError(f"invalid arguments for list-expenses: {args}")

    # Retrieve a shallow copy of the expenses list.
    expenses_list = expenses.list_expenses(ledger=ledger)

    for exp in expenses_list:
        payer = exp["payer"]
        amount = exp["amount"]
        description = exp["description"]
        # Print without participants list to match test expectations.
        print(f"{payer} paid ${amount:.2f} for {description}")

    return False


def _dispatch(ledger: dict, argv: List[str]) -> bool:
    """Dispatch the sub‑command in *argv* to the appropriate handler."""
    if not argv:
        raise common.ExpenseError("unknown command: ")
    cmd, *rest = argv
    mapping = {
        "add-person": _cmd_add_person,
        "add-expense": _cmd_add_expense,
        "settle": _cmd_settle,
        "list-people": _cmd_list_people,
        "list-expenses": _cmd_list_expenses,
    }
    if cmd not in mapping:
        raise common.ExpenseError(f"unknown command: {cmd}")
    return mapping[cmd](ledger=ledger, args=rest)


def _print_error(msg: str) -> None:
    """Print *msg* to stderr."""
    sys.stderr.write(msg + "\n")


def main(argv: List[str] | None = None) -> None:
    """Entry point for the expense splitter CLI."""
    global DEFAULT_LEDGER_PATH
    if DEFAULT_LEDGER_PATH is None:
        DEFAULT_LEDGER_PATH = _default_path()

    if argv is None:
        argv = sys.argv[1:]

    try:
        try:
            ledger = _load(path=DEFAULT_LEDGER_PATH)
        except common.ExpenseError as e:
            # Corrupt ledger file – move it aside and start fresh.
            _print_error(e.args[0])
            storage._backup_corrupt_file(path=DEFAULT_LEDGER_PATH)
            ledger = {"people": [], "expenses": []}

        modified = _dispatch(ledger=ledger, argv=argv)

        if modified:
            _save(path=DEFAULT_LEDGER_PATH, ledger=ledger)

    except common.ExpenseError as e:
        _print_error(e.args[0])
        sys.exit(1)
    except (EOFError, KeyboardInterrupt):
        # Graceful termination without a traceback.
        sys.exit(0)


if __name__ == "__main__":
    main()
