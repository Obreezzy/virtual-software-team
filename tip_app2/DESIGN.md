**app.py - design specification**  

The module contains only plain functions and a single `main()` entry-point.  
All validation errors are raised as `ValueError` with a short message; `main()` catches them, prints the message prefixed by **`Error:`**, and exits with status 1 (no traceback).

---

## 1. Public API  

| Function | Signature | Input description | Return value | Behaviour / validation |
|----------|-----------|-------------------|--------------|------------------------|
| `parse_float` | `def parse_float(arg: str, *, name: str) -> float:` | `arg` - raw command-line token; `name` - e.g. `"BILL"` or `"PERCENT"` for messages. | `float` - the parsed number. | 1. `value = float(arg)` - if this raises `ValueError` -> `raise ValueError(f"{name} must be a number")`. <br>2. If `not math.isfinite(value)` -> `raise ValueError(f"{name} must be a finite number")`. <br>3. If `value <= 0` -> `raise ValueError(f"{name} must be > 0")`. |
| `parse_int` | `def parse_int(arg: str, *, name: str) -> int:` | `arg` - raw token; `name` - e.g. `"PEOPLE"`. | `int` - the parsed integer. | 1. `value = int(arg)` - if this raises `ValueError` -> `raise ValueError(f"{name} must be an integer")`. <br>2. If `value <= 0` -> `raise ValueError(f"{name} must be >= 1")`. |
| `compute_tip` | `def compute_tip(bill: float, percent: float) -> float:` | `bill` - positive amount; `percent` - positive percentage. | `float` - **exact** tip (no rounding). | `return bill * (percent / 100)`. |
| `compute_total` | `def compute_total(bill: float, tip: float) -> float:` | `bill` - original amount; `tip` - exact tip from `compute_tip`. | `float` - **exact** total (no rounding). | `return bill + tip`. |
| `compute_share` | `def compute_share(total: float, people: int) -> float:` | `total` - exact total; `people` - integer >= 1. | `float` - **exact** per-person amount (no rounding). | `return total / people`. |
| `round_money` | `def round_money(value: float) -> float:` | `value` - any monetary amount (exact). | `float` - rounded to two decimal places **using "half-away-from-zero"**. | ```python\nfrom decimal import Decimal, ROUND_HALF_UP\nreturn float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))\n``` |
| `format_money` | `def format_money(value: float) -> str:` | `value` - already rounded to two decimals. | `str` - `"$X.XX"` (always two digits after the decimal point). | `return f"${value:0.2f}"`. |
| `main` | `def main() -> None:` | - | - | 1. Reads `sys.argv[1:]`. <br>2. If the argument count is **not exactly three**, raises `ValueError("exactly three arguments required: BILL PERCENT PEOPLE")`. <br>3. Calls `parse_float` for `BILL` and `PERCENT`, `parse_int` for `PEOPLE`. <br>4. Computes `tip = compute_tip(bill, percent)`, `total = compute_total(bill, tip)`, `share = compute_share(total, people)`. <br>5. Rounds each monetary value with `round_money`. <br>6. Prints three lines (see **Formatted output**). <br>7. Catches any `ValueError`, prints `Error: <message>` to **stdout**, and exits with status 1. |

*All functions are pure; only `main()` performs I/O.*

---

## 2. Tiny data examples (illustrating shape)

```python
# parse_float
parse_float("123.45", name="BILL")          # -> 123.45
parse_float("-5", name="BILL")              # raises ValueError("BILL must be > 0")
parse_float("nan", name="BILL")             # raises ValueError("BILL must be a finite number")
parse_float("abc", name="BILL")             # raises ValueError("BILL must be a number")

# parse_int
parse_int("4", name="PEOPLE")               # -> 4
parse_int("0", name="PEOPLE")               # raises ValueError("PEOPLE must be >= 1")
parse_int("2.5", name="PEOPLE")             # raises ValueError("PEOPLE must be an integer")

# compute_tip
compute_tip(100.0, 15.0)                     # -> 15.0

# compute_total
compute_total(100.0, 15.0)                   # -> 115.0

# compute_share
compute_share(115.0, 3)                     # -> 38.333333333333336

# round_money (half-away-from-zero)
round_money(38.333333333333336)             # -> 38.33
round_money(5.625)                          # -> 5.63   (exactly halfway)

# format_money
format_money(38.33)                         # -> "$38.33"
format_money(5.63)                          # -> "$5.63"
```

---

## 3. Worked examples  

*The first line demonstrates the *trickiest* rule - rounding a value that is exactly halfway between two cents.*

| Call (rounded values shown) | Result |
|-----------------------------|--------|
| `share = round_money(compute_share(compute_total(10.00, compute_tip(10.00, 12.5)), 2))` | `share == 5.63` |
| `tip = round_money(compute_tip(10.00, 12.5))` | `tip == 1.25` |
| `total = round_money(compute_total(10.00, 1.25))` | `total == 11.25` |
| `format_money(tip)` | `"$1.25"` |
| `format_money(total)` | `"$11.25"` |
| `format_money(share)` | `"$5.63"` |
| **Simple case** - `bill=100, percent=20, people=2` -> `tip==20.00`, `total==120.00`, `share==60.00` | `Tip: $20.00\nTotal: $120.00\nEach person owes: $60.00` |
| **Error - wrong number of arguments** (4 supplied) | raises `ValueError("exactly three arguments required: BILL PERCENT PEOPLE")` |
| **Error - non-numeric BILL** - `parse_float("abc", name="BILL")` | raises `ValueError("BILL must be a number")` |
| **Error - BILL = nan** - `parse_float("nan", name="BILL")` | raises `ValueError("BILL must be a finite number")` |
| **Error - PERCENT <= 0** - `parse_float("-5", name="PERCENT")` | raises `ValueError("PERCENT must be > 0")` |
| **Error - PEOPLE not an integer** - `parse_int("2.5", name="PEOPLE")` | raises `ValueError("PEOPLE must be an integer")` |
| **Error - PEOPLE = 0** - `parse_int("0", name="PEOPLE")` | raises `ValueError("PEOPLE must be >= 1")` |

All monetary results are shown **rounded to two decimal places** and **displayed with exactly two digits** after the decimal point.

---

## 4. Example session  

```
$ python app.py 100 15 3
Tip: $15.00
Total: $115.00
Each person owes: $38.33

$ python app.py 123.45 15.5 3
Tip: $19.13
Total: $142.58
Each person owes: $47.53

$ python app.py 10 12.5 2
Tip: $1.25
Total: $11.25
Each person owes: $5.63

$ python app.py 50 -10 2
Error: PERCENT must be > 0

$ python app.py 80 12 abc
Error: PEOPLE must be an integer

$ python app.py 80 12
Error: exactly three arguments required: BILL PERCENT PEOPLE

$ python app.py 1 1 1 1
Error: exactly three arguments required: BILL PERCENT PEOPLE
```

The program terminates after each invocation; the user "quits" simply by ending the command-line session (or pressing `Ctrl-C`).  

---

### Summary of guarantees  

* Exactly three arguments are required; any other count triggers the **exact** error message shown above.  
* `parse_float` distinguishes "must be a number" from "must be a finite number".  
* `parse_int` enforces integer-only input and a minimum of 1.  
* Rounding uses `Decimal(..., ROUND_HALF_UP)` -> "half-away-from-zero".  
* All error messages are printed as `Error: <message>` with exit status 1, never a traceback.  

The design now aligns perfectly with the worked examples, the example session, and the original requirements.