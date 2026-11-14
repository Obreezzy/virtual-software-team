# Bank Account Manager  

A tiny command‑line utility that lets you keep track of multiple bank accounts.  
All data are stored in a local **`accounts.json`** file, so balances survive between runs.

## Features  

| What you can do | How it works |
|-----------------|--------------|
| **Create** an account with an optional initial balance (non‑negative, two‑decimal precision) | `1` |
| **List** all accounts with their current balances | `2` |
| **View** the balance of a single account | `3` |
| **Deposit** a positive amount into an existing account | `4` |
| **Withdraw** a positive amount (rejected if it would make the balance negative) | `5` |
| **Quit** the program | `6` |

All user input is validated. Invalid entries (unknown account, non‑numeric or negative amounts, insufficient funds, etc.) produce a clear error message and return you to the menu – the program never crashes or raises a traceback.

## Prerequisites  

* Python 3.8+ (standard library only)

## Running the program  

```bash
# Make the script executable (optional)
chmod +x app.py

# Start the interactive manager
./app.py          # or: python3 app.py
```

You will see a menu like:

```
=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option:
```

Enter the number of the operation you want and follow the prompts.

## Running the tests  

The test suite lives in **`test_app.py`** and uses the built‑in `unittest` framework.

```bash
python -m unittest test_app.py
```

All tests should pass. The suite creates a temporary accounts file, so your real `accounts.json` is left untouched.

## Example session  

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
Enter account name: Savings
Enter initial balance (or leave empty for 0): 150.75
Account 'Savings' created.

=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option: 4
Enter account name: Savings
Enter deposit amount: 49.25
Deposited 49.25. New balance: 200.00

=== Bank Account Manager ===
1) Create account
2) List accounts
3) View account
4) Deposit
5) Withdraw
6) Quit
Select option: 5
Enter account name: Savings
Enter withdrawal amount: 250
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
  Savings : 200.00

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

The balance is saved in `accounts.json`, so restarting the program will show the same account with its last known balance.

---

*Enjoy managing your simple bank accounts safely and reliably!*