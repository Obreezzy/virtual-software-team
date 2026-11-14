def check(label, actual, expected):
    try:
        got = actual() if callable(actual) else actual
    except Exception as e:
        print(f"MISMATCH {label}: the rules raise {type(e).__name__}: {e}")
        return
    try:
        if isinstance(got, float) or isinstance(expected, float):
            ok = abs(float(got) - float(expected)) <= 0.006
        else:
            ok = got == expected
    except Exception:
        ok = got == expected
    print(("OK " if ok else "MISMATCH ") + f"{label}: design says {expected!r}, rules give {got!r}")


def check_raises(label, func, exc, message=None):
    try:
        func()
    except exc as e:
        if message is not None and str(e) != message:
            print(f"MISMATCH {label}: design says message {message!r}, rules give {str(e)!r}")
        else:
            print(f"OK {label}")
    except Exception as e:
        print(f"MISMATCH {label}: design says {exc.__name__}, rules raise {type(e).__name__}: {e}")
    else:
        print(f"MISMATCH {label}: design says {exc.__name__} is raised, but the rules do not raise")


import json
import os
import pathlib
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Constants
TWOPLACES = Decimal("0.01")
ACCOUNT_FILE = pathlib.Path(__file__).with_name("accounts.json")
TEMP_SUFFIX = ".tmp"

# Type alias for clarity (not enforced at runtime)
Accounts = dict[str, str]

def load_accounts(path: pathlib.Path) -> Accounts:
    """Load accounts from a JSON file. Return empty dict on missing file or parse error."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all values are strings representing decimals with two places
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            return {}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        return {}

def save_accounts(path: pathlib.Path, accounts: Accounts) -> None:
    """Write accounts to a temporary file then atomically replace the target."""
    temp_path = path.with_suffix(TEMP_SUFFIX)
    try:
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        # Cleanup temp file if something went wrong and it still exists
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass

def validate_name(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        raise ValueError("account name must be non-empty")
    return stripped

def validate_amount(txt: str) -> Decimal:
    try:
        d = Decimal(txt)
    except (InvalidOperation, ValueError):
        raise ValueError("amount must be a number")
    if not d.is_finite():
        raise ValueError("amount must be a number")
    if d <= 0:
        raise ValueError("amount must be positive")
    return d.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

def create_account(accounts: Accounts, name: str, initial: Decimal) -> None:
    if name in accounts:
        raise ValueError("account already exists")
    # initial is already validated (>=0) by caller
    accounts[name] = str(initial.quantize(TWOPLACES, rounding=ROUND_HALF_UP))

def list_accounts(accounts: Accounts) -> list[tuple[str, Decimal]]:
    result: list[tuple[str, Decimal]] = []
    for name, bal_str in sorted(accounts.items(), key=lambda kv: kv[0]):
        bal = Decimal(bal_str).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        result.append((name, bal))
    return result

def view_account(accounts: Accounts, name: str) -> Decimal:
    try:
        bal_str = accounts[name]
    except KeyError:
        raise KeyError("account not found")
    return Decimal(bal_str).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

def deposit(accounts: Accounts, name: str, amount: Decimal) -> Decimal:
    if name not in accounts:
        raise KeyError("account not found")
    current = Decimal(accounts[name])
    new_balance = (current + amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    accounts[name] = str(new_balance)
    return new_balance

def withdraw(accounts: Accounts, name: str, amount: Decimal) -> Decimal:
    if name not in accounts:
        raise KeyError("account not found")
    current = Decimal(accounts[name])
    new_balance = (current - amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if new_balance < 0:
        raise ValueError("insufficient funds")
    accounts[name] = str(new_balance)
    return new_balance

def print_menu() -> None:
    menu = """=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit"""
    print(menu)

def main() -> None:
    accounts = load_accounts(ACCOUNT_FILE)
    while True:
        try:
            print_menu()
            choice = input("Select option: ").strip()
            if choice == "1":
                name = validate_name(input("Enter account name: "))
                init_txt = input("Enter initial balance (or leave empty for 0): ").strip()
                initial = Decimal("0.00") if not init_txt else validate_amount(init_txt)
                create_account(accounts, name, initial)
                print(f"Account '{name}' created.")
                save_accounts(ACCOUNT_FILE, accounts)
            elif choice == "2":
                print("Accounts:")
                for n, b in list_accounts(accounts):
                    print(f"  {n} : {b}")
            elif choice == "3":
                name = validate_name(input("Enter account name: "))
                bal = view_account(accounts, name)
                print(f"Balance for {name}: {bal}")
            elif choice == "4":
                name = validate_name(input("Enter account name: "))
                amt = validate_amount(input("Enter deposit amount: "))
                new_bal = deposit(accounts, name, amt)
                print(f"Deposited {amt}. New balance: {new_bal}")
                save_accounts(ACCOUNT_FILE, accounts)
            elif choice == "5":
                name = validate_name(input("Enter account name: "))
                amt = validate_amount(input("Enter withdrawal amount: "))
                new_bal = withdraw(accounts, name, amt)
                print(f"Withdrew {amt}. New balance: {new_bal}")
                save_accounts(ACCOUNT_FILE, accounts)
            elif choice == "6":
                print("Good-bye!")
                break
            else:
                print("Invalid option.")
        except (ValueError, KeyError) as e:
            print(f"Error: {e}")
        except (EOFError, KeyboardInterrupt):
            print("\nGood-bye!")
            break
        except Exception:
            print("Error: unexpected problem - please restart")

# -------------------- Tests / Checks --------------------
# The helpers `check` and `check_raises` are assumed to exist.

# 1. Withdrawal that would go negative
check_raises(
    "withdraw negative balance",
    lambda: withdraw({"Alice": "50.00"}, "Alice", Decimal("60.00")),
    ValueError,
    "insufficient funds"
)

# 2. Successful account creation with explicit initial balance
def _test_create_alice():
    accounts = {}
    create_account(accounts, "Alice", Decimal("100.00"))
    return accounts == {"Alice": "100.00"}
check("create Alice with 100.00", lambda: _test_create_alice(), True)

# 3. Creation with empty initial balance (defaults to 0.00)
def _test_create_bob_zero():
    accounts = {}
    create_account(accounts, "Bob", Decimal("0.00"))
    return accounts == {"Bob": "0.00"}
check("create Bob with 0.00", lambda: _test_create_bob_zero(), True)

# 4. Duplicate creation raises error
def _dup_creation():
    accounts = {"Bob": "0.00"}
    create_account(accounts, "Bob", Decimal("10.00"))
check_raises(
    "duplicate account creation",
    lambda: _dup_creation(),
    ValueError,
    "account already exists"
)

# 5. Deposit updates dict and returns new balance
def _test_deposit():
    accounts = {"Bob": "0.00"}
    result = deposit(accounts, "Bob", Decimal("25.50"))
    return result == Decimal("25.50") and accounts == {"Bob": "25.50"}
check("deposit to Bob", lambda: _test_deposit(), True)

# 6. Withdrawal within balance
def _test_withdraw():
    accounts = {"Bob": "25.50"}
    result = withdraw(accounts, "Bob", Decimal("5.00"))
    return result == Decimal("20.50") and accounts == {"Bob": "20.50"}
check("withdraw from Bob", lambda: _test_withdraw(), True)

# 7. View balance
def _test_view():
    accounts = {"Bob": "20.50"}
    return view_account(accounts, "Bob") == Decimal("20.50")
check("view Bob balance", lambda: _test_view(), True)

# 8. List accounts alphabetical
def _test_list():
    accounts = {"Charlie": "0.00", "Bob": "20.50"}
    return list_accounts(accounts) == [
        ("Bob", Decimal("20.50")),
        ("Charlie", Decimal("0.00"))
    ]
check("list accounts sorted", lambda: _test_list(), True)

# 9. Invalid amount string raises error
check_raises(
    "validate_amount non-numeric",
    lambda: validate_amount("12.3a"),
    ValueError,
    "amount must be a number"
)
