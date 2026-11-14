# app.py – Simple CLI Password Utility

## What it does
`app.py` provides two command‑line functions:

| Command | Description |
|---------|-------------|
| `generate <length>` | Creates a cryptographically‑random password of the requested length (8‑64). The password always contains at least one lowercase letter, one uppercase letter, one digit, and one symbol (`!@#$%^&*()-_=+[]{}|;:,.<>?`). |
| `check <password>` | Analyses a password and prints a strength rating: **weak**, **medium**, or **strong** based on length and the presence of the four character classes. |

Invalid usage or arguments result in a clear error message on **stderr** and a non‑zero exit code.

## Running the program

```bash
# Generate a 12‑character password
python app.py generate 12

# Check the strength of a password
python app.py check My$ecreT123
```

The script can also be imported and its core functions (`generate_password`, `rate_password`) used programmatically.

## Running the tests

The test suite lives in `test_app.py`. Execute it with the standard library test runner:

```bash
python -m unittest test_app.py
```

All tests should pass on any Python 3.8+ interpreter.

## Example

```bash
$ python app.py generate 16
aB3!k9$Qz%Lm2@hR

$ python app.py check aB3!k9$Qz%Lm2@hR
strong
```

The first command prints a 16‑character password that satisfies the required character classes.  
The second command rates that password as **strong** because it is at least 12 characters long and contains all four classes.