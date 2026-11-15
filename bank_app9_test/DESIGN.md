**Design - `app.py`**

The program is a single-module, interactive command-line bank-account manager.  
All state lives in one flat dictionary **`accounts`** that maps a *canonical* (lower-cased) account key to a record containing the user-provided name (preserving case) and a `Decimal` balance.

```python
# Tiny in-memory example
accounts = {
    "alice": {"name": "Alice", "balance": Decimal("123.45")},
    "bob123": {"name": "Bob123", "balance": Decimal("0.00")},
}
```

The JSON file `accounts.json` stores the same structure, but balances are written as strings (e.g. `"123.45"`).  
If the file is missing the program starts with `{}`.  
If the file cannot be parsed it is renamed to `accounts.json.bak` and an empty dictionary is used.

All monetary values are handled with `decimal.Decimal` limited to **exactly two decimal places**.  
All user-visible errors are caught, printed as a clean line, and the program continues.

---

### Public API (functions)

| Function | Signature | Input | Output / Side-effects | Behaviour |
|----------|-----------|-------|----------------------|-----------|
| **`load_accounts`** | `def load_accounts(file_path: str) -> dict[str, dict[str, Decimal]]:` | `file_path` - path to `accounts.json` | Returns the accounts dictionary (may be empty). May rename a corrupted file to `file_path + ".bak"` | - If `file_path` does not exist -> return `{}`.<br>- If the file exists and contains valid JSON -> parse it, converting each balance string to `Decimal` (two-dp).<br>- If JSON decoding fails or the structure is invalid -> rename the file to `file_path + ".bak"` and return `{}`. |
| **`save_accounts`** | `def save_accounts(accounts: dict[str, dict[str, Decimal]], file_path: str) -> None:` | `accounts` - the in-memory dict; `file_path` - path to `accounts.json` | Writes a temporary file `file_path + ".tmp"` then atomically renames it to `file_path`. | - Serialises each balance as a string with exactly two decimal places (`quantize(Decimal("0.01"))`).<br>- Guarantees that a partially written file never replaces the existing one. |
| **`validate_new_account_name`** | `def validate_new_account_name(name: str, accounts: dict) -> str:` | `name` - raw user input; `accounts` - current dict | Returns the canonical lower-cased key if the name is valid **and not already used**; otherwise raises `ValueError` with a friendly message. | - Strip surrounding whitespace.<br>- Must be non-empty after stripping.<br>- Must contain only alphanumeric characters (`str.isalnum()`).<br>- Case-insensitive uniqueness: `name.lower()` must not be a key in `accounts`. |
| **`validate_existing_account_name`** | `def validate_existing_account_name(name: str, accounts: dict) -> str:` | `name` - raw user input; `accounts` - current dict | Returns the canonical lower-cased key if the name exists; otherwise raises `ValueError`. | - Same whitespace and alphanumeric checks as `validate_new_account_name`.<br>- After validation, `name.lower()` **must** be present in `accounts`. |
| **`parse_amount`** | `def parse_amount(text: str) -> Decimal:` | `text` - raw user input | Returns a `Decimal` with exactly two decimal places if valid; otherwise raises `ValueError`. | - Strip whitespace.<br>- `Decimal(text)` is attempted.<br>- Reject if `Decimal.is_finite()` is `False` (covers `NaN`, `Infinity`, `-Infinity`).<br>- Must be **greater than zero**.<br>- Must have at most two decimal places; enforce with `quantize(Decimal("0.01"))` and raise if the original has more than two. |
| **`create_account`** | `def create_account(canonical_key: str, original_name: str, accounts: dict) -> None:` | `canonical_key` - lower-cased name returned by validation; `original_name` - the exact user-provided name; `accounts` - dict | Inserts a new entry with balance `Decimal("0.00")`. Raises `ValueError` if the key already exists (should never happen if validation succeeded). |
| **`deposit`** | `def deposit(canonical_key: str, amount: Decimal, accounts: dict) -> None:` | `canonical_key` - existing account key; `amount` - positive `Decimal`; `accounts` - dict | Increases the account's balance by `amount`. |
| **`withdraw`** | `def withdraw(canonical_key: str, amount: Decimal, accounts: dict) -> None:` | `canonical_key` - existing account key; `amount` - positive `Decimal`; `accounts` - dict | Decreases balance by `amount`. Raises `ValueError` if the withdrawal would make the balance negative. |
| **`view_balance`** | `def view_balance(canonical_key: str, accounts: dict) -> Decimal:` | `canonical_key` - existing account key; `accounts` - dict | Returns the current balance. |
| **`list_accounts`** | `def list_accounts(accounts: dict) -> list[tuple[str, Decimal]]:` | `accounts` - dict | Returns a list of `(original_name, balance)` sorted alphabetically by `original_name`. |
| **`log_unexpected_error`** | `def log_unexpected_error(exc: BaseException, log_path: str = "error.log") -> None:` | `exc` - caught exception; optional `log_path` | Appends a timestamped traceback to `log_path`. |
| **`prompt_menu_choice`** | `def prompt_menu_choice() -> int:` | *none* | Returns an integer 1-6 after repeatedly prompting until a valid choice is entered. |
| **`prompt_new_account_name`** | `def prompt_new_account_name(accounts: dict) -> tuple[str, str]:` | `accounts` - dict | Repeatedly asks for a name, validates with `validate_new_account_name`, and returns `(canonical_key, original_name)`. |
| **`prompt_existing_account_name`** | `def prompt_existing_account_name(accounts: dict) -> str:` | `accounts` - dict | Repeatedly asks for a name, validates with `validate_existing_account_name`, and returns the canonical key. |
| **`prompt_amount`** | `def prompt_amount() -> Decimal:` | *none* | Repeatedly asks for an amount, parses with `parse_amount`, and returns the `Decimal`. |
| **`main`** | `def main() -> None:` | *none* | Interactive loop: <br>1. Load accounts.<br>2. Show numbered menu (Create, Deposit, Withdraw, View Balance, List All Accounts, Exit).<br>3. Dispatch to the appropriate functions.<br>4. After any mutating operation (create, deposit, withdraw) call `save_accounts`.<br>5. Catch `ValueError` from validation, print its message, and re-prompt.<br>6. Catch any other exception, log via `log_unexpected_error`, print a generic "An unexpected error occurred. Please try again." and continue.<br>7. Gracefully handle `KeyboardInterrupt` / EOF by printing "Good-bye!" and exiting. |

---

### Error-handling policy

| Source | How it is handled |
|--------|-------------------|
| **Validation errors** (`ValueError` from `validate_*`, `parse_amount`, `withdraw`) | Caught in `main`, the exception message is printed (e.g. `Error: account name must be alphanumeric and unique.`) and the user is re-prompted for that input. |
| **Unexpected errors** (IO failures, JSON decode errors, etc.) | Caught by a top-level `except Exception as e:` in `main`, logged with `log_unexpected_error`, and the user sees `An unexpected error occurred. Please try again.` |
| **Non-finite numbers** (`nan`, `inf`, `-inf`) | Detected in `parse_amount` via `Decimal.is_finite()` and raise `ValueError` with "Amount must be a finite number." |
| **Empty or whitespace-only names** | Detected in both name-validation functions and raise `ValueError` with "Account name cannot be empty or contain whitespace." |
| **Impossible dates** - not applicable (no date handling). |

All error messages are short, friendly, and printed without a traceback.

---

### Worked examples  

*The trickiest rule (`parse_amount`) is shown first.*

```python
parse_amount("10")                == Decimal("10.00")
parse_amount("0.99")              == Decimal("0.99")
parse_amount(" 5.5 ")             == Decimal("5.50")
parse_amount("-3")                raises ValueError  # not positive
parse_amount("12.345")            raises ValueError  # more than 2 dp
parse_amount("nan")               raises ValueError  # not finite

validate_new_account_name("Alice", {})                     == "alice"
validate_new_account_name("bob123", {"alice": {...}})      == "bob123"
validate_new_account_name("Bob_1", {})                     raises ValueError  # '_' not alphanumeric
validate_new_account_name("  ", {})                        raises ValueError  # empty after strip
validate_new_account_name("Alice", {"alice": {...}})       raises ValueError  # duplicate

validate_existing_account_name("Alice", {"alice": {...}})  == "alice"
validate_existing_account_name("bob123", {"alice": {...}}) raises ValueError  # not found
validate_existing_account_name("  ", {"alice": {...}})    raises ValueError  # empty after strip

create_account("alice", "Alice", {})  # accounts becomes {"alice": {"name":"Alice","balance":Decimal("0.00")}}

deposit("alice", Decimal("25.00"), {"alice": {"name":"Alice","balance":Decimal("0.00")}})
# balance now Decimal("25.00")

withdraw("alice", Decimal("5.00"), {"alice": {"name":"Alice","balance":Decimal("25.00")}})
# balance now Decimal("20.00")

withdraw("alice", Decimal("30.00"), {"alice": {"name":"Alice","balance":Decimal("20.00")}})
# raises ValueError  # insufficient funds

view_balance("alice", {"alice": {"name":"Alice","balance":Decimal("20.00")}}) == Decimal("20.00")

list_accounts({
    "bob":   {"name":"Bob","balance":Decimal("0.00")},
    "alice": {"name":"Alice","balance":Decimal("20.00")}
}) == [("Alice", Decimal("20.00")), ("Bob", Decimal("0.00"))]
```

---

### Example session (interactive)

```
Welcome to Bank Account Manager.
1) Create account
2) Deposit
3) Withdraw
4) View balance
5) List all accounts
6) Exit
Select an option [1-6]: 1
Enter new account name:   # user types only spaces
Error: account name cannot be empty or contain whitespace.
Enter new account name: Alice!
Error: account name must be alphanumeric and unique.
Enter new account name: Alice
Account 'Alice' created.

1) Create account
2) Deposit
3) Withdraw
4) View balance
5) List all accounts
6) Exit
Select an option [1-6]: 1
Enter new account name: alice
Error: account name must be alphanumeric and unique.
Enter new account name: Bob123
Account 'Bob123' created.

1) Create account
2) Deposit
3) Withdraw
4) View balance
5) List all accounts
6) Exit
Select an option [1-6]: 2
Enter account name: alice
Enter amount to deposit: -5
Error: amount must be a positive number.
Enter amount to deposit: 100.00
Deposited $100.00 to 'Alice'.

1) Create account
2) Deposit
3) Withdraw
4) View balance
5) List all accounts
6) Exit
Select an option [1-6]: 4
Enter account name: ALICE
Balance for 'Alice': $100.00

1) Create account
2) Deposit
3) Withdraw
4) View balance
5) List all accounts
6) Exit
Select an option [1-6]: 3
Enter account name: alice
Enter amount to withdraw: 150
Error: insufficient funds - withdrawal would make balance negative.

1) Create account
2) Deposit
3) Withdraw
4) View balance
5) List all accounts
6) Exit
Select an option [1-6]: 5
Accounts:
  Alice -  Alice - $100.00
  Bob123 - $0.00

1) Create account
2) Deposit
3) Withdraw
4) View balance
5) List all accounts
6) Exit
Select an option [1-6]: 6
Goodbye!