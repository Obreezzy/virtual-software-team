**Design - `app.py`**  

The module implements a tiny interactive bank-account manager.  
All monetary values are handled with `decimal.Decimal` rounded to **exactly two decimal places**.  
Account data are stored in a flat JSON file `accounts.json` (same directory as the script).  
The design contains only **function signatures** and precise behavioural rules - no bodies.

---

### 1. Data model  

| Symbol | Type | Description | JSON representation | Example |
|--------|------|-------------|---------------------|---------|
| `Accounts` | `dict[str, str]` | Mapping **account name -> balance string** (`"123.45"`). Storing the balance as a string preserves the exact decimal representation because `json` cannot serialise `Decimal`. | `{ "Alice": "100.00", "Bob": "0.00" }` | `{"Alice": "100.00", "Bob": "0.00"}` |

*All balances in the dictionary are always quantised to two decimal places.*

---

### 2. Constants  

```python
from decimal import Decimal, ROUND_HALF_UP
import pathlib

TWOPLACES = Decimal("0.01")                     # quantisation step
ACCOUNT_FILE = pathlib.Path(__file__).with_name("accounts.json")
TEMP_SUFFIX = ".tmp"                            # temporary file suffix
```

---

### 3. Public functions  

| Function | Signature | Input (raw) | Output / side-effects | Behaviour & validation |
|----------|-----------|-------------|-----------------------|------------------------|
| `load_accounts` | `def load_accounts(path: pathlib.Path) -> Accounts:` | `path` - full path to *accounts.json* | Returns the accounts dictionary. If the file does not exist -> returns `{}`. If the file exists but cannot be parsed as JSON -> returns `{}` **without printing any warning** (the corrupted file is left untouched). | No exception propagates to the user. |
| `save_accounts` | `def save_accounts(path: pathlib.Path, accounts: Accounts) -> None:` | `path`, `accounts` | Writes a temporary file `path.with_suffix(TEMP_SUFFIX)`, flushes, then atomically replaces the original file with `os.replace`. | Guarantees that a failed write never overwrites a previously good file. |
| `validate_name` | `def validate_name(name: str) -> str:` | `name` - raw user input | Returns the stripped name (`name.strip()`). | Raises `ValueError("account name must be non-empty")` if the stripped string is empty. |
| `validate_amount` | `def validate_amount(txt: str) -> Decimal:` | `txt` - raw user input | Returns a `Decimal` **quantised to two places**. | 1. Parse with `Decimal(txt)`. 2. If parsing fails -> raise `ValueError("amount must be a number")`. 3. If the resulting `Decimal` is not finite (`not d.is_finite()`) -> raise the same error. 4. If `d <= 0` -> raise `ValueError("amount must be positive")`. 5. Return `d.quantize(TWOPLACES, rounding=ROUND_HALF_UP)`. |
| `create_account` | `def create_account(accounts: Accounts, name: str, initial: Decimal) -> None:` | `accounts`, `name` (already validated), `initial` (already validated, **>= 0**) | Inserts a new entry **and updates the dictionary in-place**. | Raises `ValueError("account already exists")` if `name` is already a key. Stores `str(initial.quantize(TWOPLACES))`. |
| `list_accounts` | `def list_accounts(accounts: Accounts) -> list[tuple[str, Decimal]]:` | `accounts` | Returns a list of `(name, balance)` tuples **sorted alphabetically by name**. | Balances are returned as `Decimal` quantised to two places. No error conditions. |
| `view_account` | `def view_account(accounts: Accounts, name: str) -> Decimal:` | `accounts`, `name` (validated) | Returns the balance as a `Decimal`. | Raises `KeyError("account not found")` if `name` is absent. |
| `deposit` | `def deposit(accounts: Accounts, name: str, amount: Decimal) -> Decimal:` | `accounts`, `name`, `amount` (validated, **> 0**) | **Updates** `accounts[name]` with the new balance **and returns** that new balance as `Decimal`. | Raises `KeyError("account not found")` if missing. |
| `withdraw` | `def withdraw(accounts: Accounts, name: str, amount: Decimal) -> Decimal:` | `accounts`, `name`, `amount` (validated, **> 0**) | **Updates** `accounts[name]` with the new balance **and returns** that new balance as `Decimal`. | Raises `KeyError("account not found")` if missing. Raises `ValueError("insufficient funds")` if `balance - amount < 0`. |
| `print_menu` | `def print_menu() -> None:` | - | Prints the static menu (see *Example session*). | No return value. |
| `main` | `def main() -> None:` | - | Runs the interactive loop, handling all user input. Catches `ValueError` and `KeyError` from the functions above and prints a clean error line (`Error: ...`). On `EOFError` or `KeyboardInterrupt` the program exits cleanly. | After any error the menu is shown again; the program never shows a traceback. |

---

### 4. Error-handling policy (messages printed by `main`)  

| Situation | Message printed (to **stdout**) |
|-----------|---------------------------------|
| Empty or whitespace-only account name | `Error: account name must be non-empty` |
| Duplicate account name on creation | `Error: account already exists` |
| Non-numeric amount, or NaN/Inf | `Error: amount must be a number` |
| Amount <= 0 (deposit/withdraw) | `Error: amount must be positive` |
| Withdrawal would make balance negative | `Error: insufficient funds` |
| Unknown account name for view/deposit/withdraw | `Error: account not found` |
| Any unexpected exception (should never happen) | `Error: unexpected problem - please restart` (the exception is logged internally, not shown) |

All messages end with a newline and contain no traceback.

---

### 5. Worked examples  

```python
# 1. Tricky case - withdrawal that would go negative
withdraw({"Alice": "50.00"}, "Alice", Decimal("60.00"))
# raises ValueError("insufficient funds")

# 2. Successful account creation with explicit initial balance
accounts = {}
create_account(accounts, "Alice", Decimal("100.00"))
accounts == {"Alice": "100.00"}

# 3. Creation with empty initial-balance prompt (defaults to 0.00)
accounts = {}
create_account(accounts, "Bob", Decimal("0.00"))
accounts == {"Bob": "0.00"}

# 4. Duplicate creation
create_account(accounts, "Bob", Decimal("10.00"))
# raises ValueError("account already exists")

# 5. Deposit (updates dict and returns new balance)
deposit(accounts, "Bob", Decimal("25.50")) == Decimal("25.50")
accounts == {"Bob": "25.50"}

# 6. Withdrawal within balance
withdraw(accounts, "Bob", Decimal("5.00")) == Decimal("20.50")
accounts == {"Bob": "20.50"}

# 7. View balance
view_account(accounts, "Bob") == Decimal("20.50")

# 8. List accounts (alphabetical)
list_accounts({"Charlie": "0.00", "Bob": "20.50"}) == [
    ("Bob",     Decimal("20.50")),
    ("Charlie", Decimal("0.00"))
]

# 9. Invalid amount string
validate_amount("12.3a")
# raises ValueError("amount must be a number")
```

All `Decimal` results are shown with two decimal places (e.g., `Decimal("20.5")` -> `Decimal("20.50")`).

---

### 6. Example session  

```
$ python app.py
=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option: 1
Enter account name:   Alice   
Enter initial balance (or leave empty for 0): 100.00
Account 'Alice' created.

=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option: 4
Enter account name: Alice
Enter deposit amount: 25.50
Deposited 25.50. New balance: 125.50

=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option: 5
Enter account name: Alice
Enter withdrawal amount: 130.00
Error: insufficient funds

=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option: 2
Accounts:
  Alice : 125.50

=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option: 6
Good-bye!
$
```

*Notes*  

* Account names are stripped of surrounding whitespace.  
* Leaving the *initial balance* prompt empty defaults to `0.00`.  
* All monetary output is formatted with exactly two decimal places.  
* After any error the menu re-appears; the program never terminates abruptly.  
* `Ctrl+C` or `Ctrl+D` (EOF) would also end the loop cleanly.

---

### 7. Persistence details  

*File location* - `accounts.json` resides in the same directory as `app.py`.  

*Loading* - `load_accounts` reads the file; if the file is missing or contains invalid JSON, it returns an empty dictionary **silently** (no warning printed).  

*Saving* - `save_accounts` writes to `accounts.json.tmp`, flushes the file, then atomically replaces the original file with `os.replace`. This guarantees that a crash during write never corrupts the existing data.  

*No backup or warning messages are required by the specification; the design follows the requirements exactly.*

---

**End of corrected design.** The next step (Developer) will implement the signatures exactly as described, respecting all validation, update, and persistence rules.