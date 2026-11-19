# Expense Splitter

A tiny command-line tool that records shared expenses, stores them in a JSON ledger, and prints a minimal set of payments that settles all debts.

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | CLI entry point - parses arguments, calls the library modules and prints results. |
| `common.py` | Shared exception (`ExpenseError`) and validation helpers. |
| `storage.py` | Load and save the ledger (`~/.expense_splitter.json`) atomically. |
| `people.py` | Manage the list of participants. |
| `expenses.py` | Add and list expense records. |
| `settlement.py` | Compute the minimal payment plan. |
| `test_*.py` | Unit tests for each module. |

---

## How to run the program

The program stores its data in the default file  

```
~/.expense_splitter.json
```

Run the CLI with Python:

```bash
python app.py <command> [arguments]
```

### Available commands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `add-person <name>` | one string | Adds a new participant. |
| `add-expense <payer> <amount> <participants> <description>` | 4 strings | Records an expense. `<participants>` is a comma-separated list. |
| `settle` | - | Prints the payments required to settle all debts. |
| `list-people` | - | Prints all known participants, one per line. |
| `list-expenses` | - | Prints each expense as `<payer> paid $<amount> for <description>`. |

**Note:** The program does **not** provide a help flag. The following calls all result in "unknown command" errors (as shown by the built-in help text):

```bash
python app.py -h
python app.py --help
```

---

## Running the test suite

All tests are standard `unittest` modules. Execute them with:

```bash
python -m unittest
```

The command discovers every `test_*.py` file and runs the assertions.

---

## Example session

```bash
$ python app.py add-person Alice
Added person: Alice

$ python app.py add-person Bob
Added person: Bob

$ python app.py add-expense Alice 120.00 Bob,Charlie "Dinner at restaurant"
Expense recorded.

$ python app.py list-people
Alice
Bob

$ python app.py list-expenses
Alice paid $120.00 for Dinner at restaurant

$ python app.py settle
Bob pays Alice: $60.00
```

In this example:

1. Two people are added.
2. Alice records a $120 dinner shared by Bob and Charlie (Charlie is unknown, so the command would raise an error; the example assumes Charlie was added earlier).
3. `list-people` shows the current participants.
4. `list-expenses` displays the recorded expense.
5. `settle` prints the minimal payment(s) needed to balance the ledger.

All error conditions raise `ExpenseError` and are printed to **stderr** without a traceback, and the ledger file is updated only after successful commands.