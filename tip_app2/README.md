# app.py – Simple Tip Calculator

## What it does
`app.py` is a tiny command‑line utility that calculates a restaurant tip, the total bill, and how much each person should pay.

* **Inputs** – three positional arguments:  
  1. **BILL** – total amount before tip (positive float)  
  2. **PERCENT** – tip percentage (positive float)  
  3. **PEOPLE** – number of people sharing the bill (integer ≥ 1)

* **Output** – three lines, each showing a monetary value rounded to two decimal places:  

```
Tip: $X.XX
Total: $X.XX
Each person owes: $X.XX
```

If the arguments are missing or invalid, the program prints an error message and exits with a non‑zero status.

---

## How to run

```bash
python app.py BILL PERCENT PEOPLE
```

Example:

```bash
python app.py 100 15 4
```

Output:

```
Tip: $15.00
Total: $115.00
Each person owes: $28.75
```

---

## How to run the tests

The test suite is in `test_app.py`. Run it with the standard library `unittest` module:

```bash
python -m unittest test_app.py
```

All tests should pass if the program is unchanged.

---

## One complete example

```bash
$ python app.py 85.50 18 3
Tip: $15.39
Total: $100.89
Each person owes: $33.63
```

* Calculation details:  
  * Tip = 85.50 × 18 / 100 = 15.39  
  * Total = 85.50 + 15.39 = 100.89  
  * Share = 100.89 / 3 = 33.63 (rounded half‑away‑from‑zero)  

The script uses only the Python standard library (`sys`, `math`, `decimal`).