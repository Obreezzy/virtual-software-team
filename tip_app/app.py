import sys
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# ----------------------------------------------------------------------
# Error messages (exact strings as specified)
# ----------------------------------------------------------------------
ERROR_MESSAGES = {
    "arg_count": "Error: exactly three arguments required: BILL PERCENT PEOPLE.",   # 61 chars
    "bill_type": "Error: BILL must be a number.",                                 # 29 chars
    "percent_type": "Error: PERCENT must be a number.",                           # 32 chars
    "people_type": "Error: PEOPLE must be a positive integer.",                  # 41 chars
    "bill_positive": "Error: BILL must be a positive number.",                   # 38 chars
    "percent_positive": "Error: PERCENT must be a positive number.",             # 41 chars
    "people_positive": "Error: PEOPLE must be a positive integer."               # 41 chars
}


# ----------------------------------------------------------------------
# Custom exception
# ----------------------------------------------------------------------
class InputError(Exception):
    """Raised when command-line arguments are missing, malformed, or non-positive."""
    pass


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def parse_args(argv: list[str]) -> tuple[Decimal, Decimal, int]:
    """Parse and validate command‑line arguments.

    Returns:
        (bill, percent, people) where bill and percent are Decimals and people is int.

    Raises:
        InputError: with an appropriate message from ERROR_MESSAGES.
    """
    if len(argv) != 4:
        raise InputError(ERROR_MESSAGES["arg_count"])

    # Bill
    try:
        bill = Decimal(argv[1])
    except InvalidOperation:
        raise InputError(ERROR_MESSAGES["bill_type"])
    if bill <= 0:
        raise InputError(ERROR_MESSAGES["bill_positive"])

    # Percent
    try:
        percent = Decimal(argv[2])
    except InvalidOperation:
        raise InputError(ERROR_MESSAGES["percent_type"])
    if percent <= 0:
        raise InputError(ERROR_MESSAGES["percent_positive"])

    # People
    people_str = argv[3]
    if not re.fullmatch(r"[1-9]\d*", people_str):
        raise InputError(ERROR_MESSAGES["people_type"])
    people = int(people_str)  # regex guarantees positivity

    return bill, percent, people


def calculate_tip(bill: Decimal, percent: Decimal) -> Decimal:
    """Calculate raw tip amount (no rounding)."""
    return bill * (percent / Decimal('100'))


def calculate_total(bill: Decimal, tip: Decimal) -> Decimal:
    """Calculate raw total amount."""
    return bill + tip


def calculate_share(total: Decimal, people: int) -> Decimal:
    """Calculate raw per‑person amount."""
    return total / Decimal(people)


def format_currency(value: Decimal) -> str:
    """Return a string like \"$X.XX\" rounded half‑away‑from‑zero."""
    rounded = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"${rounded:.2f}"


def main() -> None:
    """Entry point: parse arguments, compute values, and print them."""
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


if __name__ == "__main__":
    main()
