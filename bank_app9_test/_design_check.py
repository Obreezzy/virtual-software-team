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


from decimal import Decimal, InvalidOperation, getcontext
from typing import Dict, Tuple, List

# Ensure two‑decimal precision context (not strictly needed but safe)
getcontext().prec = 28

# ---------- Core functions ----------
def parse_amount(text: str) -> Decimal:
    txt = text.strip()
    try:
        d = Decimal(txt)
    except InvalidOperation:
        raise ValueError("Invalid decimal.")
    if not d.is_finite():
        raise ValueError("Amount must be a finite number.")
    if d <= 0:
        raise ValueError("Amount must be positive.")
    quant = d.quantize(Decimal("0.01"))
    if d != quant:
        raise ValueError("Too many decimal places.")
    return quant

def _clean_name(name: str) -> str:
    return name.strip()

def validate_new_account_name(name: str, accounts: Dict) -> str:
    clean = _clean_name(name)
    if not clean:
        raise ValueError("Account name cannot be empty or contain whitespace.")
    if not clean.isalnum():
        raise ValueError("Account name must be alphanumeric and unique.")
    key = clean.lower()
    if key in accounts:
        raise ValueError("Account name must be alphanumeric and unique.")
    return key

def validate_existing_account_name(name: str, accounts: Dict) -> str:
    clean = _clean_name(name)
    if not clean:
        raise ValueError("Account name cannot be empty or contain whitespace.")
    if not clean.isalnum():
        raise ValueError("Account name must be alphanumeric and exist.")
    key = clean.lower()
    if key not in accounts:
        raise ValueError("Account not found.")
    return key

def create_account(canonical_key: str, original_name: str, accounts: Dict) -> None:
    if canonical_key in accounts:
        raise ValueError("Account already exists.")
    accounts[canonical_key] = {"name": original_name, "balance": Decimal("0.00")}

def deposit(canonical_key: str, amount: Decimal, accounts: Dict) -> None:
    accounts[canonical_key]["balance"] += amount

def withdraw(canonical_key: str, amount: Decimal, accounts: Dict) -> None:
    if accounts[canonical_key]["balance"] - amount < Decimal("0.00"):
        raise ValueError("Insufficient funds.")
    accounts[canonical_key]["balance"] -= amount

def view_balance(canonical_key: str, accounts: Dict) -> Decimal:
    return accounts[canonical_key]["balance"]

def list_accounts(accounts: Dict) -> List[Tuple[str, Decimal]]:
    lst = [(rec["name"], rec["balance"]) for rec in accounts.values()]
    return sorted(lst, key=lambda x: x[0])

# ---------- Tests ----------
# helpers `check` and `check_raises` are assumed to exist.

# parse_amount
check("parse_amount 10", lambda: parse_amount("10"), Decimal("10.00"))
check("parse_amount 0.99", lambda: parse_amount("0.99"), Decimal("0.99"))
check("parse_amount spaced", lambda: parse_amount(" 5.5 "), Decimal("5.50"))
check_raises("parse_amount negative", lambda: parse_amount("-3"), ValueError, None)
check_raises("parse_amount too many dp", lambda: parse_amount("12.345"), ValueError, None)
check_raises("parse_amount nan", lambda: parse_amount("nan"), ValueError, None)

# validate_new_account_name
check("new name Alice empty dict", lambda: validate_new_account_name("Alice", {}), "alice")
check("new name bob123 with other", lambda: validate_new_account_name("bob123", {"alice": {}}), "bob123")
check_raises("new name invalid char", lambda: validate_new_account_name("Bob_1", {}), ValueError, None)
check_raises("new name whitespace", lambda: validate_new_account_name("  ", {}), ValueError, None)
check_raises("new name duplicate", lambda: validate_new_account_name("Alice", {"alice": {}}), ValueError, None)

# validate_existing_account_name
check("existing Alice present", lambda: validate_existing_account_name("Alice", {"alice": {}}), "alice")
check_raises("existing bob123 missing", lambda: validate_existing_account_name("bob123", {"alice": {}}), ValueError, None)
check_raises("existing whitespace", lambda: validate_existing_account_name("  ", {"alice": {}}), ValueError, None)

# create_account
acc = {}
create_account("alice", "Alice", acc)
check("create_account result", lambda: acc,
      {"alice": {"name": "Alice", "balance": Decimal("0.00")}})

# deposit
deposit("alice", Decimal("25.00"), acc)
check("deposit balance", lambda: acc["alice"]["balance"], Decimal("25.00"))

# withdraw success
withdraw("alice", Decimal("5.00"), acc)
check("withdraw balance", lambda: acc["alice"]["balance"], Decimal("20.00"))

# withdraw insufficient
check_raises("withdraw insufficient", lambda: withdraw("alice", Decimal("30.00"), acc), ValueError, None)

# view_balance
check("view_balance", lambda: view_balance("alice", acc), Decimal("20.00"))

# list_accounts
mixed = {
    "bob": {"name": "Bob", "balance": Decimal("0.00")},
    "alice": {"name": "Alice", "balance": Decimal("20.00")}
}
check("list_accounts order", lambda: list_accounts(mixed),
      [("Alice", Decimal("20.00")), ("Bob", Decimal("0.00"))])
