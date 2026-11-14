def check(label, actual, expected):
    try:
        got = actual() if callable(actual) else actual
    except Exception as e:
        print(f"MISMATCH {label}: the rules raise {type(e).__name__}: {e}")
        return
    try:
        if isinstance(got, float) or isinstance(expected, float):
            ok = abs(float(got) - float(expected)) <= 0.006
        else:
            ok = got == expected
    except Exception:
        ok = got == expected
    print(("OK " if ok else "MISMATCH ") + f"{label}: design says {expected!r}, rules give {got!r}")


def check_raises(label, func, exc, message=None):
    try:
        func()
    except exc as e:
        if message is not None and str(e) != message:
            print(f"MISMATCH {label}: design says message {message!r}, rules give {str(e)!r}")
        else:
            print(f"OK {label}")
    except Exception as e:
        print(f"MISMATCH {label}: design says {exc.__name__}, rules raise {type(e).__name__}: {e}")
    else:
        print(f"MISMATCH {label}: design says {exc.__name__} is raised, but the rules do not raise")


# -*- coding: utf-8 -*-
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import re
import sys

# ---------- Exceptions ----------
class InputError(Exception):
    """Raised when command-line arguments are missing, malformed, or non-positive."""
    pass

# ---------- Error messages ----------
ERROR_MESSAGES = {
    "arg_count": "Error: exactly three arguments required: BILL PERCENT PEOPLE.",   # 61 chars
    "bill_type": "Error: BILL must be a number.",                                 # 29 chars
    "percent_type": "Error: PERCENT must be a number.",                           # 32 chars
    "people_type": "Error: PEOPLE must be a positive integer.",                  # 41 chars
    "bill_positive": "Error: BILL must be a positive number.",                   # 38 chars
    "percent_positive": "Error: PERCENT must be a positive number.",             # 41 chars
    "people_positive": "Error: PEOPLE must be a positive integer."               # 41 chars
}

# ---------- Core functions ----------
def parse_args(argv: list[str]) -> tuple[Decimal, Decimal, int]:
    # Argument count
    if len(argv) != 4:
        raise InputError(ERROR_MESSAGES["arg_count"])

    # Bill conversion
    try:
        bill = Decimal(argv[1])
    except InvalidOperation:
        raise InputError(ERROR_MESSAGES["bill_type"])
    if bill <= 0:
        raise InputError(ERROR_MESSAGES["bill_positive"])

    # Percent conversion
    try:
        percent = Decimal(argv[2])
    except InvalidOperation:
        raise InputError(ERROR_MESSAGES["percent_type"])
    if percent <= 0:
        raise InputError(ERROR_MESSAGES["percent_positive"])

    # People validation
    people_str = argv[3]
    if not re.fullmatch(r'^[1-9]\d*$', people_str):
        raise InputError(ERROR_MESSAGES["people_type"])
    people = int(people_str)

    return bill, percent, people

def calculate_tip(bill: Decimal, percent: Decimal) -> Decimal:
    return bill * (percent / Decimal('100'))

def calculate_total(bill: Decimal, tip: Decimal) -> Decimal:
    return bill + tip

def calculate_share(total: Decimal, people: int) -> Decimal:
    return total / Decimal(people)

def format_currency(value: Decimal) -> str:
    rounded = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"${rounded:.2f}"

def main() -> None:
    try:
        bill, percent, people = parse_args(sys.argv)
        tip = calculate_tip(bill, percent)
        total = calculate_total(bill, tip)
        share = calculate_share(total, people)

        print(f"Tip: {format_currency(tip)}")
        print(f"Total: {format_currency(total)}")
        print(f"Each person pays: {format_currency(share)}")
    except InputError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

# ---------- Checks ----------
# Helpers are assumed to be provided in the execution environment:
#   check(label, actual, expected)
#   check_raises(label, lambda_that_should_raise, ExceptionType, expected_message_or_None)

# Worked‑example checks
check("calc_tip 100 15", lambda: calculate_tip(Decimal('100'), Decimal('15')), Decimal('15'))
check("calc_total 100 15", lambda: calculate_total(Decimal('100'), Decimal('15')), Decimal('115'))
check("calc_share 115 3", lambda: calculate_share(Decimal('115'), 3),
      Decimal('38.33333333333333333333333333'))
check("format_currency share", lambda: format_currency(Decimal('38.3333333333333333')),
      "$38.33")

check("trickiest tip", lambda: calculate_tip(Decimal('57.25'), Decimal('18')),
      Decimal('10.305'))
check("trickiest total", lambda: calculate_total(Decimal('57.25'), Decimal('10.305')),
      Decimal('67.555'))
check("trickiest share", lambda: calculate_share(Decimal('67.555'), 2),
      Decimal('33.7775'))
check("trickiest format", lambda: format_currency(Decimal('33.7775')),
      "$33.78")

check("tie‑breaking tip", lambda: calculate_tip(Decimal('0.05'), Decimal('10')),
      Decimal('0.005'))
check("tie‑breaking format", lambda: format_currency(Decimal('0.005')),
      "$0.01")

check("parse_args normal 1", lambda: parse_args(['app.py', '100', '15', '3']),
      (Decimal('100'), Decimal('15'), 3))
check("parse_args normal 2", lambda: parse_args(['app.py', '0.01', '0.5', '1']),
      (Decimal('0.01'), Decimal('0.5'), 1))

# Error‑case checks
check_raises("parse_args negative bill",
             lambda: parse_args(['app.py', '-50', '10', '2']),
             InputError,
             ERROR_MESSAGES["bill_positive"])
check_raises("parse_args non‑numeric percent",
             lambda: parse_args(['app.py', '100', 'abc', '2']),
             InputError,
             ERROR_MESSAGES["percent_type"])
check_raises("parse_args zero people",
             lambda: parse_args(['app.py', '100', '10', '0']),
             InputError,
             ERROR_MESSAGES["people_type"])
check_raises("parse_args non‑int people",
             lambda: parse_args(['app.py', '100', '10', '2.5']),
             InputError,
             ERROR_MESSAGES["people_type"])
check_raises("parse_args missing arg",
             lambda: parse_args(['app.py', '100', '10']),
             InputError,
             ERROR_MESSAGES["arg_count"])

# Character‑count claims
check("arg_count length", lambda: len(ERROR_MESSAGES["arg_count"]), 61)
check("bill_type length", lambda: len(ERROR_MESSAGES["bill_type"]), 29)
check("percent_type length", lambda: len(ERROR_MESSAGES["percent_type"]), 32)
check("people_type length", lambda: len(ERROR_MESSAGES["people_type"]), 41)
check("bill_positive length", lambda: len(ERROR_MESSAGES["bill_positive"]), 38)
check("percent_positive length", lambda: len(ERROR_MESSAGES["percent_positive"]), 41)
check("people_positive length", lambda: len(ERROR_MESSAGES["people_positive"]), 41)
