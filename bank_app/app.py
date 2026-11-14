#!/usr/bin/env python3
"""
Bank Account Manager
"""

import json
import os
import pathlib
import sys
import tempfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Constants
TWOPLACES = Decimal("0.01")
ACCOUNT_FILE = pathlib.Path(__file__).with_name("accounts.json")
TEMP_SUFFIX = ".tmp"

# Type alias
Accounts = dict[str, str]


def load_accounts(path: pathlib.Path) -> Accounts:
    """
    Load accounts from a JSON file.
    Returns an empty dict if the file does not exist.
    Raises a RuntimeError if the file exists but cannot be parsed as JSON.
    """
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise RuntimeError("accounts file is corrupted")
            # Ensure all values are strings (they should be)
            return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError as e:
        raise RuntimeError("accounts file is corrupted") from e
    except OSError as e:
        raise RuntimeError("cannot read accounts file") from e


def save_accounts(path: pathlib.Path, accounts: Accounts) -> None:
    """
    Atomically write accounts to a JSON file using a temporary file.
    Guarantees that a failed write never overwrites a previously good file.
    Cleans up the temporary file if replacement fails.
    """
    # Write to a temporary file in the same directory
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=path.name,
        suffix=TEMP_SUFFIX,
    ) as tmp:
        json.dump(accounts, tmp, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_path = pathlib.Path(tmp.name)

    try:
        os.replace(temp_path, path)
    except OSError as e:
        # Cleanup stray temp file and re‑raise
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise RuntimeError("failed to save accounts") from e


def validate_name(name: str) -> str:
    """Strip whitespace and ensure the name is non‑empty."""
    stripped = name.strip()
    if not stripped:
        raise ValueError("account name must be non-empty")
    return stripped


def validate_amount(txt: str) -> Decimal:
    """Parse a monetary amount, ensure it is a positive finite Decimal."""
    try:
        d = Decimal(txt)
    except (InvalidOperation, ValueError):
        raise ValueError("amount must be a number")
    if not d.is_finite():
        raise ValueError("amount must be a number")
    if d <= 0:
        raise ValueError("amount must be positive")
    return d.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _parse_balance(value: str) -> Decimal:
    """Convert a stored balance string to a Decimal, validating the format."""
    try:
        return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise RuntimeError("account data corrupted")


def create_account(accounts: Accounts, name: str, initial: Decimal) -> None:
    """Add a new account with the given initial balance."""
    if name in accounts:
        raise ValueError("account already exists")
    accounts[name] = str(initial.quantize(TWOPLACES, rounding=ROUND_HALF_UP))


def list_accounts(accounts: Accounts) -> list[tuple[str, Decimal]]:
    """Return a sorted list of (name, balance) tuples."""
    result: list[tuple[str, Decimal]] = []
    for name in sorted(accounts.keys()):
        bal = _parse_balance(accounts[name])
        result.append((name, bal))
    return result


def view_account(accounts: Accounts, name: str) -> Decimal:
    """Return the balance of the given account."""
    try:
        bal_str = accounts[name]
    except KeyError:
        raise KeyError("account not found")
    return _parse_balance(bal_str)


def deposit(accounts: Accounts, name: str, amount: Decimal) -> Decimal:
    """Add amount to account balance and return new balance."""
    if name not in accounts:
        raise KeyError("account not found")
    current = _parse_balance(accounts[name])
    new_bal = (current + amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    accounts[name] = str(new_bal)
    return new_bal


def withdraw(accounts: Accounts, name: str, amount: Decimal) -> Decimal:
    """Subtract amount from account balance and return new balance."""
    if name not in accounts:
        raise KeyError("account not found")
    current = _parse_balance(accounts[name])
    if current - amount < 0:
        raise ValueError("insufficient funds")
    new_bal = (current - amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    accounts[name] = str(new_bal)
    return new_bal


def print_menu() -> None:
    """Display the static menu."""
    menu = """=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit"""
    print(menu)


def main() -> None:
    # Load accounts, handling possible corruption
    try:
        accounts = load_accounts(ACCOUNT_FILE)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    while True:
        try:
            print_menu()
            choice = input("Select option: ").strip()
            if not choice:
                continue

            if choice == "1":
                # Create account
                name = validate_name(input("Enter account name: "))
                init_txt = input(
                    "Enter initial balance (or leave empty for 0): "
                ).strip()
                if init_txt == "":
                    initial = Decimal("0.00")
                else:
                    # Allow zero and positive amounts for initial balance
                    try:
                        d = Decimal(init_txt)
                    except (InvalidOperation, ValueError):
                        raise ValueError("amount must be a number")
                    if not d.is_finite():
                        raise ValueError("amount must be a number")
                    if d < 0:
                        raise ValueError("amount must be positive")
                    initial = d.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

                old_accounts = accounts.copy()
                create_account(accounts, name, initial)
                try:
                    save_accounts(ACCOUNT_FILE, accounts)
                except Exception as e:
                    accounts.clear()
                    accounts.update(old_accounts)
                    print(f"Error: {e}\n")
                    continue
                print(f"Account '{name}' created.\n")

            elif choice == "2":
                # List accounts
                lst = list_accounts(accounts)
                print("Accounts:")
                for n, b in lst:
                    print(f"  {n} : {b:.2f}")
                print()

            elif choice == "3":
                # View account
                name = validate_name(input("Enter account name: "))
                bal = view_account(accounts, name)
                print(f"Balance for '{name}': {bal:.2f}\n")

            elif choice == "4":
                # Deposit
                name = validate_name(input("Enter account name: "))
                amount = validate_amount(input("Enter deposit amount: "))
                old_accounts = accounts.copy()
                new_bal = deposit(accounts, name, amount)
                try:
                    save_accounts(ACCOUNT_FILE, accounts)
                except Exception as e:
                    accounts.clear()
                    accounts.update(old_accounts)
                    print(f"Error: {e}\n")
                    continue
                print(f"Deposited {amount:.2f}. New balance: {new_bal:.2f}\n")

            elif choice == "5":
                # Withdraw
                name = validate_name(input("Enter account name: "))
                amount = validate_amount(input("Enter withdrawal amount: "))
                old_accounts = accounts.copy()
                new_bal = withdraw(accounts, name, amount)
                try:
                    save_accounts(ACCOUNT_FILE, accounts)
                except Exception as e:
                    accounts.clear()
                    accounts.update(old_accounts)
                    print(f"Error: {e}\n")
                    continue
                print(f"Withdrew {amount:.2f}. New balance: {new_bal:.2f}\n")

            elif choice == "6":
                print("Good-bye!")
                break

            else:
                continue

        except (ValueError, KeyError) as e:
            print(f"Error: {e}\n")
        except (EOFError, KeyboardInterrupt):
            print("\nGood-bye!")
            break
        except Exception as e:
            # Unexpected problems: inform user and exit cleanly
            print("Error: unexpected problem - please restart")
            sys.exit(1)


if __name__ == "__main__":
    main()
