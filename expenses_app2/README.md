# Expense Tracker – `app.py`

A tiny command‑line expense tracker that stores entries in a CSV file
(`expenses.csv` by default).  
All logic lives in a single file, uses only the Python standard library,
and provides two commands:

* **add** – record a new expense  
* **report** – show a monthly summary

---

## How it works

* Each expense is a row `date,category,amount,note` in the CSV file.  
* The file is created automatically with a header if it does not exist.  
* Dates must be `YYYY‑MM‑DD` and represent a real calendar day.  
* Amounts must be positive numbers (finite, non‑zero).  
* Categories are normalised to title case (`food` → `Food`).  
* `report` aggregates amounts per category for the requested month and
  prints a formatted table with percentages and the overall total.

---

## Running the program

```bash
# Add an expense
python app.py add 2023-05-12 Food 12.50 "Lunch at cafe"

# Add another expense (category is case‑insensitive)
python app.py add 2023-05-20 transport 30 "Bus pass"

# Show the report for May 2023
python app.py report 2023-05
```

**Output**

```
Expenses for 2023-05
Food             12.50    29.41%
Transport        30.00    70.59%
Overall total: 42.50
```

*All messages that are not errors are printed to **stdout**.  
Error and warning messages go to **stderr**.*

The CSV file (`expenses.csv`) is created in the current directory
unless you modify the `path` argument when calling `main()` from Python code.

---

## Running the tests

The test suite is in `test_app.py`.  Execute it with the standard unittest
module:

```bash
python -m unittest
```

The tests use temporary files, so the real `expenses.csv` is never touched.

---

## Command reference

| Command | Arguments | Description |
|---------|-----------|-------------|
| `add`   | `<date> <category> <amount> <note>` | Validate the inputs, append a new row to the CSV, and print `Entry added.` |
| `report`| `<year-month>` (format `YYYY-MM`) | Load the CSV, filter entries for the given month, aggregate by category, and print a formatted report. |

Invalid usage or validation errors result in a message printed to **stderr**
and an exit code of `1`.

---

## Example session (including error handling)

```text
$ python app.py add 2023-05-12 Food 12.50 "Lunch at cafe"
Entry added.
$ python app.py add 2023-05-20 transport 30 "Bus pass"
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

--- 

*That's all you need to start tracking expenses with `app.py`.*