# tip calculator

A tiny command‑line utility that calculates a tip, the total bill, and how much each person should pay.

## What it does
* Validates three positional arguments:  
  `BILL` – positive number (e.g. `23.50`)  
  `PERCENT` – positive number (e.g. `18`)  
  `PEOPLE` – positive integer (e.g. `3`)
* Computes  

```
tip   = BILL * (PERCENT / 100)
total = BILL + tip
share = total / PEOPLE
```

* Prints the results rounded to two decimal places:

```
Tip: $X.XX
Total: $X.XX
Each person pays: $X.XX
```

All calculations use the `decimal` module with half‑away‑from‑zero rounding.

## Run the program

```bash
python app.py BILL PERCENT PEOPLE
```

Example:

```bash
$ python app.py 100 15 4
Tip: $15.00
Total: $115.00
Each person pays: $28.75
```

If the arguments are missing, non‑numeric, or not positive, the program prints an error message to **stderr** and exits with status 1.

## Run the tests

The test suite lives in `test_app.py`. Execute it with the standard library test runner:

```bash
python -m unittest
```

(or `python -m unittest test_app.py` to run only that file).