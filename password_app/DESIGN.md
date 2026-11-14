**Module:** `pwdtool.py` (single-file CLI password utility, standard library only)

Plain functions only, plus one constant (`SYMBOLS`). All public functions are importable so tests can call them directly.

---

## 1. Constants

```python
SYMBOLS: str = "!@#$%^&*()-_=+[]{}|;:,.<>?"
```

Tiny example: `SYMBOLS[0] == "!"`, `SYMBOLS[-1] == "?"`, `len(SYMBOLS) == 26`.

Character classes used everywhere (generation AND rating), defined with these exact tests:

* lower  = `ch in string.ascii_lowercase`
* upper  = `ch in string.ascii_uppercase`
* digit  = `ch in string.digits`
* symbol = `not ch.isalnum()` (any character that is not a letter or digit; this includes characters outside SYMBOLS such as `~` or a space)

---

## 2. Public functions

| Function | Signature | Behaviour |
|----------|-----------|-----------|
| `generate_password` | `def generate_password(length: int) -> str:` | 1. If `type(length) is not int` raise `ValueError("Length must be an integer")`. 2. If `length < 8 or length > 64` raise `ValueError("Length must be between 8 and 64")`. 3. Pick one char each from `string.ascii_lowercase`, `string.ascii_uppercase`, `string.digits`, `SYMBOLS` using `secrets.choice`. 4. Pool = lowercase + uppercase + digits + `SYMBOLS`. Pick `length - 4` more chars from the pool with `secrets.choice`. 5. Shuffle all chars with `secrets.SystemRandom().shuffle` and return `"".join(...)`. The result has exactly `length` chars and always contains all four classes. |
| `rate_password` | `def rate_password(password: str) -> str:` | 1. If `password == ""` raise `ValueError("Password may not be empty")`. 2. `classes_present` = number of the four classes (lower, upper, digit, symbol) that occur at least once (0 to 4). 3. Apply in this order: **strong** if `len(password) >= 12` and `classes_present == 4`; else **medium** if `len(password) >= 10` and `classes_present >= 3`; else **weak**. Returns exactly `"weak"`, `"medium"` or `"strong"`. |
| `main` | `def main(argv: list[str] \| None = None) -> int:` | 1. If `argv is None` use `sys.argv[1:]`. 2. If `len(argv) != 2`: print `Usage: python pwdtool.py generate <length> \| python pwdtool.py check <password>` to **stderr** and return 1. 3. `generate`: `int(argv[1])` (on `ValueError` print `Length must be an integer` to stderr, return 1), call `generate_password`, print the result to stdout, return 0. 4. `check`: call `rate_password(argv[1])`, print the rating to stdout, return 0. 5. Any other command: print `Unknown command` to stderr, return 1. 6. Any `ValueError` raised by `generate_password` or `rate_password` is caught in `main`: print its message to stderr and return 1 (never a traceback). |

Module guard: `if __name__ == "__main__": sys.exit(main())`.

There are no other helper functions.

---

## 3. Worked examples (all checked by running code)

| Call | Result |
|------|--------|
| `rate_password("abcdefgh1$")` | `"medium"` (len 10, 3 classes) |
| `rate_password("Abcdefg1$xy")` | `"medium"` (len 11, 4 classes: not long enough for strong) |
| `rate_password("Abcdefghijkl1")` | `"medium"` (len 13, 3 classes: not all 4) |
| `rate_password("Abcdefgh1$Xy")` | `"strong"` (len 12, 4 classes) |
| `rate_password("Abcdef12")` | `"weak"` (len 8) |
| `rate_password("abcdefghij1")` | `"weak"` (len 11, only 2 classes) |
| `rate_password("abcDEF")` | `"weak"` |
| `rate_password("")` | raises `ValueError("Password may not be empty")` |
| `generate_password(5)` | raises `ValueError("Length must be between 8 and 64")` |
| `generate_password("ten")` | raises `ValueError("Length must be an integer")` |
| `len(generate_password(20))` | `20`, and `rate_password` of it is `"strong"` |

`generate_password` output is random, so tests must check properties (length, all four classes present), not exact strings.

---

## 4. Example session

```
$ python pwdtool.py generate 12
aB3!xY9%Qz$k

$ python pwdtool.py check 'aB3!xY9%Qz$k'
strong

$ python pwdtool.py check 'abcdefgh1$'
medium

$ python pwdtool.py check abc
weak

$ python pwdtool.py generate 5
Length must be between 8 and 64

$ python pwdtool.py check
Usage: python pwdtool.py generate <length> | python pwdtool.py check <password>
```

(The generated password in the first command is only an example; real output differs. Error and usage lines go to stderr and the exit code is 1.)