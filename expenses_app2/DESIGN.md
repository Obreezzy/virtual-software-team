# Design: command-line expense tracker (single file: app.py)

Standard library only. Plain functions, no classes. Every message in this design
is plain ASCII (no special dashes or quotes) and must be used exactly as written.

## Files and testing rules

- Data lives in a CSV file (default `expenses.csv` in the current folder) whose
  header row is exactly `date,category,amount,note`.
- Every `open()` of the CSV uses `newline=""` and `encoding="utf-8"`. (Without
  `newline=""`, Windows inserts blank lines between rows.)
- Use the `csv` module for all reading and writing, so notes containing commas
  or quotes work.
- Every function that touches the file takes a `path` argument, and `main`
  accepts an optional `path`, so tests use a temporary file and never touch a
  real `expenses.csv`.
- Appending a row never rewrites existing rows, so no backup files are needed.

## Data structures

An entry is a flat dict with exactly these keys:

```python
{"date": "2023-05-12", "category": "Food", "amount": 12.5, "note": "Lunch at cafe"}
# date: str "YYYY-MM-DD" | category: str, already normalised
# amount: float greater than 0, 2 decimals | note: str (may be empty)
```

The category totals are a flat dict of category -> total, each rounded to 2 decimals:

```python
{"Food": 123.45, "Transport": 67.89, "Utilities": 200.0}
```

## Functions

### `validate_date(date_str: str) -> None`

Raises `ValueError("Date must be in YYYY-MM-DD format and a real calendar day.")`
unless `date_str` is exactly 10 characters long and
`datetime.strptime(date_str, "%Y-%m-%d")` succeeds. (So "2023-5-1" and
"2023-02-30" are both rejected.)

### `validate_amount(amount_str: str) -> float`

Strips whitespace and converts with `float()`. Raises
`ValueError("Amount must be a positive number.")` if the text is not a number,
is not finite (nan, inf), or is zero or negative. Otherwise returns the float.

### `normalise_category(category: str) -> str`

Returns `category.strip().title()`. Raises `ValueError("Category cannot be empty.")`
if nothing is left after stripping.

### `make_entry(date: str, category: str, amount: float, note: str) -> dict`

Returns an entry dict (see above) with the category normalised and the amount
rounded to 2 decimals.

### `ensure_csv_exists(path: str) -> None`

Creates the CSV file containing only the header row if the file does not exist.

### `append_entry(path: str, entry: dict) -> None`

Calls `ensure_csv_exists(path)`, then appends one row `date,category,amount,note`,
writing the amount with exactly 2 decimals (`f"{amount:.2f}"`).

### `load_entries(path: str) -> list[dict]`

Returns `[]` if the file does not exist. Otherwise reads with `csv.DictReader`
and returns the valid rows as entry dicts (built with `make_entry`). A row is
skipped, with a warning printed to stderr, in these cases (checked in this order):

- date, category or amount is missing or blank: reason `missing value`
- amount fails `validate_amount`: reason `invalid amount`
- date fails `validate_date`: reason `invalid date`

The warning is `Warning: skipping malformed row {line}: {reason}`, where `{line}`
is `reader.line_num` (the header is line 1, so the first data row is line 2).

### `filter_by_month(entries: list[dict], year_month: str) -> list[dict]`

Returns the entries whose `date[:7] == year_month`, in the original order.

### `aggregate_by_category(entries: list[dict]) -> dict[str, float]`

Applies `normalise_category` to each entry's category (so "food" and "Food" are
the same category), sums the amounts per category, and rounds each total to 2
decimals.

### `format_report(year_month: str, totals: dict[str, float]) -> str`

Builds the report text:

- First line: `Expenses for <year_month>`
- Then one line per category, sorted alphabetically, built with
  `f"{category:<12}{total:>10.2f}{pct:>9.2f}%"` where `pct = 100 * total / overall`
  (use 0.0 when `overall` is 0)
- Last line: `f"Overall total: {overall:.2f}"`, where `overall` is the sum of the
  totals rounded to 2 decimals
- Lines are joined with `"\n"`, with no trailing newline.
- If `totals` is empty there are no category lines: the report is only the first
  and last line.

### `print_error(message: str) -> None`

Writes `message` and a newline to stderr.

### `handle_add(args: list[str], path: str) -> None`

`args` is `[date, category, amount, note]`. Raises
`ValueError("Usage: add <date> <category> <amount> <note>")` if there are not
exactly 4 items. Validates the date and amount, builds the entry with
`make_entry`, appends it with `append_entry`, and prints `Entry added.` to stdout.

### `handle_report(args: list[str], path: str) -> None`

`args` is `[year_month]`. Raises
`ValueError("Usage: report <year-month> (format YYYY-MM)")` if there is not
exactly 1 item or it does not match `^\d{4}-(0[1-9]|1[0-2])$`. Otherwise loads
the entries, filters by month, aggregates, and prints the result of `format_report`.

### `main(argv: list[str] | None = None, path: str = "expenses.csv") -> int`

`argv` defaults to `sys.argv[1:]`. The first item is the command (`add` or
`report`); the rest are passed to `handle_add` or `handle_report`. Returns 0 on
success.

- `ValueError` (including usage errors): `print_error(str(error))` and return 1.
- Missing or unknown command: `print_error("Unknown command. Use: add, report")`
  and return 1.
- `OSError`: `print_error(f"I/O error: {error}")` and return 1.
- Do not catch any other exception.

The file ends with `if __name__ == "__main__": sys.exit(main())`.

## Worked examples

1. format_report("2023-05", {'Food': 123.45, 'Transport': 67.89, 'Utilities': 200.0})  ->  these 5 lines joined with "\n":

```text
Expenses for 2023-05
Food            123.45    31.55%
Transport        67.89    17.35%
Utilities       200.00    51.11%
Overall total: 391.34
```

(overall = 391.34; the percentages are 123.45/391.34, 67.89/391.34 and 200.00/391.34 of 100.)


2. format_report("2023-06", {})  ->  'Expenses for 2023-06\nOverall total: 0.00'

3. validate_date("2022-12-31")  ->  None

4. validate_date("2022-02-30")  ->  raises ValueError("Date must be in YYYY-MM-DD format and a real calendar day.")

5. validate_date("2022-5-1")  ->  raises ValueError("Date must be in YYYY-MM-DD format and a real calendar day.")

6. validate_amount("  42.5  ")  ->  42.5

7. validate_amount("-3")  ->  raises ValueError("Amount must be a positive number.")

8. validate_amount("abc")  ->  raises ValueError("Amount must be a positive number.")

9. validate_amount("inf")  ->  raises ValueError("Amount must be a positive number.")

10. normalise_category("food")  ->  'Food'

11. normalise_category("  TRANSPORT ")  ->  'Transport'

12. normalise_category("   ")  ->  raises ValueError("Category cannot be empty.")

13. make_entry("2023-05-12", "food", 12.5, "Lunch at cafe")  ->  {'date': '2023-05-12', 'category': 'Food', 'amount': 12.5, 'note': 'Lunch at cafe'}

14. filter_by_month(<the 4 entries below>, "2023-05")  ->  the first 3 entries, in the same order
(the 4th has date 2023-06-01)

```python
[{'date': '2023-05-01', 'category': 'Food', 'amount': 10.0, 'note': ''}, {'date': '2023-05-02', 'category': 'food', 'amount': 20.0, 'note': ''}, {'date': '2023-05-03', 'category': 'Transport', 'amount': 15.5, 'note': ''}, {'date': '2023-06-01', 'category': 'Food', 'amount': 5.0, 'note': ''}]
```

15. aggregate_by_category(<the first 3 entries above>)  ->  {'Food': 30.0, 'Transport': 15.5}   # "food" and "Food" are merged

16. load_entries("nonexistent.csv")  ->  []

17. After `append_entry(path, make_entry("2023-05-12", "food", 12.5, "Lunch, with colleague"))` the file
contains exactly these 2 lines (the note is quoted because it contains a comma):

```text
date,category,amount,note
2023-05-12,Food,12.50,"Lunch, with colleague"
```

and `load_entries(path)` returns:  [{'date': '2023-05-12', 'category': 'Food', 'amount': 12.5, 'note': 'Lunch, with colleague'}]

18. For a file with these lines:

```text
date,category,amount,note
2023-05-01,Food,10.00,Lunch
2023-05-02,Food,abc,Bad amount
2023-13-01,Food,5.00,Bad date
2023-05-04,,3.00,No category
```

`load_entries(path)` returns only the first data row, [{'date': '2023-05-01', 'category': 'Food', 'amount': 10.0, 'note': 'Lunch'}],
and prints these lines to stderr:

```text
Warning: skipping malformed row 3: invalid amount
Warning: skipping malformed row 4: invalid date
Warning: skipping malformed row 5: missing value
```

## Example session

Error messages are printed to stderr and `main` returns 1; everything else goes
to stdout. Notes with spaces must be quoted on the command line.

```text
$ python app.py add 2023-05-12 Food 12.50 "Lunch at cafe"
Entry added.
$ python app.py add 2023-05-20 transport 30 "Bus pass"
Entry added.
$ python app.py add 2023-06-02 Food 8 Snack
Entry added.
$ python app.py report 2023-05
Expenses for 2023-05
Food             12.50    29.41%
Transport        30.00    70.59%
Overall total: 42.50
$ python app.py report 2023-07
Expenses for 2023-07
Overall total: 0.00
$ python app.py add 2023-02-30 Food 5 "Bad date"
Date must be in YYYY-MM-DD format and a real calendar day.
$ python app.py add 2023-05-21 Food -5 Refund
Amount must be a positive number.
$ python app.py report 2023-5
Usage: report <year-month> (format YYYY-MM)
$ python app.py delete
Unknown command. Use: add, report
```
