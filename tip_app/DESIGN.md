**app.py - Design Specification**

---

### 1. Public API (plain functions - no class hierarchy)

| Function | Signature | Input description | Return value | Behaviour (exact rule) |
|----------|-----------|-------------------|--------------|------------------------|
| `parse_args(argv: list[str]) -> tuple[Decimal, Decimal, int]` | `def parse_args(argv: list[str]) -> tuple[Decimal, Decimal, int]:` | `argv` - the list returned by `sys.argv` (including the script name). | `(bill, percent, people)` - `bill` and `percent` as **`Decimal`**, `people` as `int`. | * Validate that **exactly three** user-supplied arguments are present (`len(argv) == 4`). <br>* Convert `argv[1]` and `argv[2]` to `Decimal`. If conversion fails -> raise `InputError(ERROR_MESSAGES["bill_type"])` or `ERROR_MESSAGES["percent_type"]`. <br>* Ensure both `Decimal` values are **> 0**; otherwise raise the corresponding "positive" error. <br>* Validate `argv[3]` matches the regex `^[1-9]\d*$` (positive integer string). If not -> raise `InputError(ERROR_MESSAGES["people_type"])`. <br>* Convert the validated string to `int`. |
| `calculate_tip(bill: Decimal, percent: Decimal) -> Decimal` | `def calculate_tip(bill: Decimal, percent: Decimal) -> Decimal:` | `bill` - positive amount of the bill (Decimal).<br>`percent` - positive tip percent (Decimal). | Raw tip amount (Decimal). | **Trickiest rule** - first divide `percent` by `Decimal('100')`, then multiply by `bill`:<br>`tip = bill * (percent / Decimal('100'))`. No rounding is performed here. |
| `calculate_total(bill: Decimal, tip: Decimal) -> Decimal` | `def calculate_total(bill: Decimal, tip: Decimal) -> Decimal:` | `bill` - positive bill amount (Decimal).<br>`tip` - tip amount returned by `calculate_tip`. | Raw total amount (Decimal). | `total = bill + tip`. |
| `calculate_share(total: Decimal, people: int) -> Decimal` | `def calculate_share(total: Decimal, people: int) -> Decimal:` | `total` - raw total amount (Decimal).<br>`people` - positive integer number of diners. | Raw per-person amount (Decimal). | `share = total / Decimal(people)`. |
| `format_currency(value: Decimal) -> str` | `def format_currency(value: Decimal) -> str:` | `value` - any monetary amount (Decimal). | String of the form `"$X.XX"` (two decimal places). | Uses **`Decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`** (half-away-from-zero) and returns `f"${rounded:.2f}"`. |
| `main() -> None` | `def main() -> None:` | No arguments - reads `sys.argv`. | Prints three result lines **or** a single error line. | * Calls `parse_args`. <br>* Calls the three calculation helpers. <br>* Passes each raw result to `format_currency`. <br>* Prints: <br> `Tip: $X.XX` <br> `Total: $X.XX` <br> `Each person pays: $X.XX` <br>* Catches any `InputError`, prints its message to **`sys.stderr`**, and exits with status 1. No traceback is ever shown. |

---

### 2. Flat lookup table (single-level `dict`)

```python
# Tiny example (the whole table is shown, not a nested structure)
ERROR_MESSAGES = {
    "arg_count": "Error: exactly three arguments required: BILL PERCENT PEOPLE.",   # 61 chars
    "bill_type": "Error: BILL must be a number.",                                 # 29 chars
    "percent_type": "Error: PERCENT must be a number.",                           # 32 chars
    "people_type": "Error: PEOPLE must be a positive integer.",                  # 41 chars
    "bill_positive": "Error: BILL must be a positive number.",                   # 38 chars
    "percent_positive": "Error: PERCENT must be a positive number.",             # 41 chars
    "people_positive": "Error: PEOPLE must be a positive integer."               # 41 chars
}
```

*All keys are flat strings; each comment now shows the **exact** character count (including spaces and punctuation).*

---

### 3. Exceptions

```python
class InputError(Exception):
    """Raised when command-line arguments are missing, malformed, or non-positive."""
    pass
```

---

### 4. Detailed behaviour & rules

1. **Argument count** - If `len(argv) != 4` -> raise `InputError(ERROR_MESSAGES["arg_count"])`.
2. **Bill conversion** - `Decimal(argv[1])`. `InvalidOperation` -> raise `InputError(ERROR_MESSAGES["bill_type"])`. If `bill <= 0` -> raise `InputError(ERROR_MESSAGES["bill_positive"])`.
3. **Percent conversion** - `Decimal(argv[2])`. Same handling with `"percent_type"` / `"percent_positive"`.
4. **People validation** - Raw string `argv[3]` must match `^[1-9]\d*$`. If not -> raise `InputError(ERROR_MESSAGES["people_type"])`. After the regex passes, `people = int(argv[3])`. (No further positivity check needed because the regex guarantees > 0.)
5. **Tip calculation** - `tip = bill * (percent / Decimal('100'))`.  
   *Example*: `bill = Decimal('57.25')`, `percent = Decimal('18')` -> `tip = Decimal('10.305')`.
6. **Total** - `total = bill + tip`.  
   Example: `total = Decimal('67.555')`.
7. **Share** - `share = total / Decimal(people)`.  
   Example (`people = 2`): `share = Decimal('33.7775')`.
8. **Rounding for display** - `format_currency` rounds **half-away-from-zero** using `ROUND_HALF_UP`.  
   *Examples*: `Decimal('10.305') -> "$10.31"`, `Decimal('67.555') -> "$67.56"`, `Decimal('33.7775') -> "$33.78"`.
9. **Tie-breaking example** - `bill = Decimal('0.05')`, `percent = Decimal('10')` -> `tip = Decimal('0.005')`. After rounding -> `"$0.01"` (away from zero).

All printed lines end with a newline (`\n`). Errors are printed **only to `stderr`**.

---

### 5. Worked examples (function-level)

```python
# normal calculations
calculate_tip(Decimal('100'), Decimal('15')) == Decimal('15')
calculate_total(Decimal('100'), Decimal('15')) == Decimal('115')
calculate_share(Decimal('115'), 3) == Decimal('38.33333333333333333333333333')
format_currency(Decimal('38.3333333333333333')) == "$38.33"

# trickiest rule (division by 100 then multiplication)
calculate_tip(Decimal('57.25'), Decimal('18')) == Decimal('10.305')
calculate_total(Decimal('57.25'), Decimal('10.305')) == Decimal('67.555')
calculate_share(Decimal('67.555'), 2) == Decimal('33.7775')
format_currency(Decimal('33.7775')) == "$33.78"

# tie-breaking (half-away-from-zero)
calculate_tip(Decimal('0.05'), Decimal('10')) == Decimal('0.005')
format_currency(Decimal('0.005')) == "$0.01"

# parsing
parse_args(['app.py', '100', '15', '3']) == (Decimal('100'), Decimal('15'), 3)
parse_args(['app.py', '0.01', '0.5', '1']) == (Decimal('0.01'), Decimal('0.5'), 1)

# error cases (raise InputError with shown message)
parse_args(['app.py', '-50', '10', '2'])   -> InputError("Error: BILL must be a positive number.")
parse_args(['app.py', '100', 'abc', '2'])  -> InputError("Error: PERCENT must be a number.")
parse_args(['app.py', '100', '10', '0'])   -> InputError("Error: PEOPLE must be a positive integer.")
parse_args(['app.py', '100', '10', '2.5']) -> InputError("Error: PEOPLE must be a positive integer.")
parse_args(['app.py', '100', '10'])        -> InputError("Error: exactly three arguments required: BILL PERCENT PEOPLE.")
```

---

### 6. Example session (exact user input / program output)

```
$ python app.py 100 15 3
Tip: $15.00
Total: $115.00
Each person pays: $38.33

$ python app.py 57.25 18 2
Tip: $10.31
Total: $67.56
Each person pays: $33.78

$ python app.py 0.05 10 1
Tip: $0.01
Total: $0.06
Each person pays: $0.06

$ python app.py -20 10 2
Error: BILL must be a positive number.

$ python app.py 100 abc 2
Error: PERCENT must be a number.

$ python app.py 100 10 0
Error: PEOPLE must be a positive integer.

$ python app.py 100 10 2.5
Error: PEOPLE must be a positive integer.

$ python app.py 100 10
Error: exactly three arguments required: BILL PERCENT PEOPLE.
```

*The user exits the shell in the usual way (`Ctrl-D`, `$ exit