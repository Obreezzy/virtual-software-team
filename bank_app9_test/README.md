> **Warning:** this code did not pass all of its tests or the review. See last_test_output.txt. Parts of this README may be inaccurate.

# Bank Account Manager

A tiny command-line tool for creating and managing simple bank accounts.  
Accounts are identified by a user-chosen name, balances are stored with two
decimal places, and all data is persisted in `accounts.json` between runs.

## Features

* Create a new account with a unique alphanumeric name.  
* Deposit or withdraw money (positive amounts, up to 1 trillion).  
* View the balance of a specific account.  
* List all existing accounts.  
* All operations are saved immediately; the data file is loaded automatically
  when the program starts.  
* Invalid input is handled gracefully - the program never shows a Python
  traceback to the user.

## Requirements

* Python 3.8 or newer (the script uses only the standard library).

## Running the program

```bash
python app.py
```

You will see a welcome message and a prompt (`> `).  Enter one of the
following commands (case-insensitive):

| Command | Syntax | Description |
|---------|--------|-------------|
| **create** | `create account <name>` | Add a new account with zero balance. |
| **deposit** | `deposit <amount> to <name>` | Add money to an existing account. |
| **withdraw** | `withdraw <amount> from <name>` | Remove money (cannot make balance negative). |
| **balance** | `balance <name>` | Show the current balance of the account. |
| **list** | `list` | Show all accounts sorted alphabetically. |
| **exit** | `exit` | Quit the program. |

All monetary values are displayed with two decimal places (e.g. `$12.34`).

## Running the tests

The test suite is in `test_app.py`.  Execute it with the standard unittest
module:

```bash
python -m unittest test_app.py
```

All tests should pass without errors.

## Example session

```
$ python app.py
Welcome to Bank Account Manager.
> create account Savings
Account 'Savings' created.
> deposit 1500.00 to Savings
Deposited $1500.00 to 'Savings'.
> withdraw 200.50 from Savings
Withdrew $200.50 from 'Savings'.
> balance Savings
Balance for 'Savings': $1299.50
> list
Accounts:
  Savings - $1299.50
> exit
Good-bye!
```

In this example a new account called **Savings** is created, $1500 is
deposited, $200.50 is withdrawn, the balance is displayed, all accounts are
listed, and finally the program exits.  

The data is stored in `accounts.json` in the current directory, so the same
accounts are available the next time you run the program.