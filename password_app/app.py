import sys
import string
import secrets
from typing import List, Optional

SYMBOLS: str = "!@#$%^&*()-_=+[]{}|;:,.<>?"


def generate_password(length: int) -> str:
    """Generate a random password of the given length.

    The password will contain at least one lowercase letter, one uppercase
    letter, one digit and one symbol from ``SYMBOLS``.
    """
    if not isinstance(length, int):
        raise ValueError("Length must be an integer")
    if length < 8 or length > 64:
        raise ValueError("Length must be between 8 and 64")

    # one mandatory character from each required class
    lower = secrets.choice(string.ascii_lowercase)
    upper = secrets.choice(string.ascii_uppercase)
    digit = secrets.choice(string.digits)
    symbol = secrets.choice(SYMBOLS)

    # pool of all allowed characters
    pool = (
        string.ascii_lowercase
        + string.ascii_uppercase
        + string.digits
        + SYMBOLS
    )

    # fill the rest of the password
    rest = [secrets.choice(pool) for _ in range(length - 4)]

    # combine and shuffle
    password_chars = [lower, upper, digit, symbol] + rest
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)


def rate_password(password: str) -> str:
    """Rate the strength of a password.

    Returns one of: "weak", "medium", "strong".
    """
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    if password == "":
        raise ValueError("Password may not be empty")

    has_lower = any(ch in string.ascii_lowercase for ch in password)
    has_upper = any(ch in string.ascii_uppercase for ch in password)
    has_digit = any(ch in string.digits for ch in password)
    has_symbol = any(ch in SYMBOLS for ch in password)

    classes_present = sum(
        (has_lower, has_upper, has_digit, has_symbol)
    )

    if len(password) >= 12 and classes_present == 4:
        return "strong"
    if len(password) >= 10 and classes_present >= 3:
        return "medium"
    return "weak"


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the command‑line interface."""
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 2:
        print(
            "Usage: python pwdtool.py generate <length> | python pwdtool.py check <password>",
            file=sys.stderr,
        )
        return 1

    command, argument = argv[0], argv[1]

    if command == "generate":
        try:
            length = int(argument)
        except ValueError:
            print("Length must be an integer", file=sys.stderr)
            return 1
        try:
            pwd = generate_password(length)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(pwd)
        return 0

    if command == "check":
        try:
            rating = rate_password(argument)
        except (ValueError, TypeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(rating)
        return 0

    print("Unknown command", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
