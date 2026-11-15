#!/usr/bin/env python3
"""
Bank Account Manager – a simple interactive CLI for managing accounts.

All monetary values are handled with decimal.Decimal limited to exactly two
decimal places. Data is persisted in a JSON file (accounts.json) where
balances are stored as strings.
"""

import json
import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation, getcontext

# Ensure enough precision for large amounts
getcontext().prec = 28

ACCOUNTS_FILE = "accounts.json"
MAX_AMOUNT = Decimal("1000000000000")  # 1e12


def load_accounts(file_path: str) -> dict[str, dict[str, Decimal]]:
    """Load accounts from a JSON file.

    Returns an empty dict if the file does not exist.
    Corrupted files are renamed to <file_path>.corrupt and the program exits.
    """
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        _handle_corrupt(file_path)

    if not isinstance(raw, dict):
        _handle_corrupt(file_path)

    accounts: dict[str, dict[str, Decimal]] = {}
    for key, rec in raw.items():
        if not isinstance(key, str) or not isinstance(rec, dict):
            _handle_corrupt(file_path)
        name = rec.get("name")
        bal_str = rec.get("balance")
        if not isinstance(name, str) or not isinstance(bal_str, str):
            _handle_corrupt(file_path)
        try:
            bal = Decimal(bal_str)
        except InvalidOperation:
            _handle_corrupt(file_path)
        if not bal.is_finite() or bal < 0:
            _handle_corrupt(file_path)
        try:
            bal = bal.quantize(Decimal("0.01"))
        except InvalidOperation:
            _handle_corrupt(file_path)
        accounts[key.lower()] = {"name": name, "balance": bal}
    return accounts


def _handle_corrupt(file_path: str) -> None:
    """Rename a corrupted file to <file_path>.corrupt and exit with a message."""
    corrupt_path = f"{file_path}.corrupt"
    try:
        os.replace(file_path, corrupt_path)
    except OSError:
        pass
    print(f"Corrupted data file detected. Renamed to '{corrupt_path}'.")
    sys.exit(1)


def save_accounts(accounts: dict[str, dict[str, Decimal]], file_path: str) -> None:
    """Save accounts atomically to a JSON file."""
    tmp_path = f"{file_path}.tmp"
    serialisable = {}
    for key, rec in accounts.items():
        serialisable[key] = {
            "name": rec["name"],
            "balance": f"{rec['balance'].quantize(Decimal('0.01'))}",
        }
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(serialisable, f, indent=2, sort_keys=True)
        os.replace(tmp_path, file_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def validate_new_account_name(name: str, accounts: dict) -> str:
    """Validate a new account name and return its canonical lower‑cased key."""
    stripped = name.strip()
    if not stripped:
        raise ValueError("account name cannot be empty or contain whitespace.")
    if not stripped.isalnum():
        raise ValueError("account name must be alphanumeric.")
    canonical = stripped.lower()
    if canonical in accounts:
        raise ValueError("account name must be unique.")
    return canonical


def validate_existing_account_name(name: str, accounts: dict) -> str:
    """Validate an existing account name and return its canonical key."""
    stripped = name.strip()
    if not stripped:
        raise ValueError("account name cannot be empty or contain whitespace.")
    if not stripped.isalnum():
        raise ValueError("account name must be alphanumeric.")
    canonical = stripped.lower()
    if canonical not in accounts:
        raise ValueError("account not found.")
    return canonical


def parse_amount(text: str) -> Decimal:
    """Parse a monetary amount, enforcing positivity, finiteness and two dp."""
    stripped = text.strip()
    try:
        amount = Decimal(stripped)
    except InvalidOperation:
        raise ValueError("amount must be a valid number.")
    if not amount.is_finite():
        raise ValueError("amount must be a finite number.")
    if amount <= 0:
        raise ValueError("amount must be a positive number.")
    if amount > MAX_AMOUNT:
        raise ValueError("amount exceeds the maximum allowed (1e12).")
    if amount.as_tuple().exponent < -2:
        raise ValueError("amount cannot have more than two decimal places.")
    amount = amount.quantize(Decimal("0.01"))
    return amount


def create_account(canonical_key: str, original_name: str, accounts: dict) -> None:
    """Insert a new account with zero balance."""
    accounts[canonical_key] = {"name": original_name, "balance": Decimal("0.00")}


def deposit(canonical_key: str, amount: Decimal, accounts: dict) -> None:
    """Add amount to the account balance."""
    accounts[canonical_key]["balance"] += amount


def withdraw(canonical_key: str, amount: Decimal, accounts: dict) -> None:
    """Subtract amount from the account balance, ensuring non‑negative result."""
    if accounts[canonical_key]["balance"] - amount < 0:
        raise ValueError("insufficient funds - withdrawal would make balance negative.")
    accounts[canonical_key]["balance"] -= amount


def view_balance(canonical_key: str, accounts: dict) -> Decimal:
    """Return the current balance of the account."""
    return accounts[canonical_key]["balance"]


def list_accounts(accounts: dict) -> list[tuple[str, Decimal]]:
    """Return a sorted list of (original_name, balance) tuples."""
    result = [(rec["name"], rec["balance"]) for rec in accounts.values()]
    result.sort(key=lambda x: x[0].lower())
    return result


def _print_error(msg: str) -> None:
    """Print an error message in lower‑case as required by the tests."""
    print(f"error: {msg}")


def _parse_create(tokens: list[str], accounts: dict) -> None:
    if len(tokens) != 3:
        _print_error("invalid create command format.")
        return
    _, _, name = tokens
    try:
        canonical = validate_new_account_name(name, accounts)
    except ValueError as e:
        _print_error(str(e))
        return
    create_account(canonical, name.strip(), accounts)
    save_accounts(accounts, ACCOUNTS_FILE)
    print(f"Account '{name.strip()}' created.")


def _parse_deposit(tokens: list[str], accounts: dict) -> None:
    # Expected: deposit <amount> to <name>
    if len(tokens) != 4 or tokens[2].lower() != "to":
        _print_error("invalid deposit command format.")
        return
    _, amount_str, _, name = tokens
    try:
        amount = parse_amount(amount_str)
    except ValueError as e:
        _print_error(str(e))
        return
    try:
        canonical = validate_existing_account_name(name, accounts)
    except ValueError as e:
        _print_error(str(e))
        return
    deposit(canonical, amount, accounts)
    save_accounts(accounts, ACCOUNTS_FILE)
    print(f"Deposited ${amount:.2f} to '{accounts[canonical]['name']}'.")


def _parse_withdraw(tokens: list[str], accounts: dict) -> None:
    # Expected: withdraw <amount> from <name>
    if len(tokens) != 4 or tokens[2].lower() != "from":
        _print_error("invalid withdraw command format.")
        return
    _, amount_str, _, name = tokens
    try:
        amount = parse_amount(amount_str)
    except ValueError as e:
        _print_error(str(e))
        return
    try:
        canonical = validate_existing_account_name(name, accounts)
    except ValueError as e:
        _print_error(str(e))
        return
    try:
        withdraw(canonical, amount, accounts)
    except ValueError as e:
        _print_error(str(e))
        return
    save_accounts(accounts, ACCOUNTS_FILE)
    print(f"Withdrew ${amount:.2f} from '{accounts[canonical]['name']}'.")


def _parse_balance(tokens: list[str], accounts: dict) -> None:
    # Expected: balance <name>
    if len(tokens) != 2:
        _print_error("invalid balance command format.")
        return
    _, name = tokens
    try:
        canonical = validate_existing_account_name(name, accounts)
    except ValueError as e:
        _print_error(str(e))
        return
    bal = view_balance(canonical, accounts)
    print(f"Balance for '{accounts[canonical]['name']}': ${bal:.2f}")


def _parse_list(tokens: list[str], accounts: dict) -> None:
    if len(tokens) != 1:
        _print_error("invalid list command format.")
        return
    lst = list_accounts(accounts)
    if not lst:
        print("No accounts found.")
    else:
        print("Accounts:")
        for name, bal in lst:
            print(f"  {name} - ${bal:.2f}")


def main() -> None:
    accounts = load_accounts(ACCOUNTS_FILE)
    print("Welcome to Bank Account Manager.")
    while True:
        try:
            line = input("> ")
        except (KeyboardInterrupt, EOFError):
            print("\nGood-bye!")
            break
        if not line.strip():
            continue
        tokens = line.strip().split()
        cmd = tokens[0].lower()
        if cmd == "create":
            _parse_create(tokens, accounts)
        elif cmd == "deposit":
            _parse_deposit(tokens, accounts)
        elif cmd == "withdraw":
            _parse_withdraw(tokens, accounts)
        elif cmd == "balance":
            _parse_balance(tokens, accounts)
        elif cmd == "list":
            _parse_list(tokens, accounts)
        elif cmd == "exit":
            print("Good-bye!")
            break
        else:
            _print_error("unknown command.")


if __name__ == "__main__":
    main()