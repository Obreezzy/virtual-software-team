import sys
import math
from decimal import Decimal, ROUND_HALF_UP


def fail(msg: object) -> None:
    """Print an error message to stderr and exit with a non-zero status."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_float(arg: str, *, name: str, allow_zero: bool = False) -> float:
    """Parse a command-line token as a finite float (> 0, or >= 0 if allow_zero)."""
    try:
        value = float(arg)
    except ValueError:
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if allow_zero:
        if value < 0:
            raise ValueError(f"{name} must be >= 0")
    elif value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def parse_int(arg: str, *, name: str) -> int:
    """Parse a command-line token as an integer >= 1."""
    try:
        value = int(arg)
    except ValueError:
        raise ValueError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be >= 1")
    return value


def compute_tip(bill: float, percent: float) -> float:
    """Exact tip amount (no rounding)."""
    return bill * (percent / 100.0)


def compute_total(bill: float, tip: float) -> float:
    """Exact total amount (no rounding)."""
    return bill + tip


def compute_share(total: float, people: int) -> float:
    """Exact per-person share (no rounding)."""
    return total / people


def round_money(value: float) -> float:
    """Round to two decimal places using half-away-from-zero."""
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def format_money(value: float) -> str:
    """Format a rounded monetary value as $X.XX."""
    return f"${value:0.2f}"


def main() -> None:
    args = sys.argv[1:]
    try:
        if len(args) != 3:
            raise ValueError("exactly three arguments required: BILL PERCENT PEOPLE")
        bill_str, percent_str, people_str = args

        bill = parse_float(bill_str, name="BILL")
        percent = parse_float(percent_str, name="PERCENT", allow_zero=True)
        people = parse_int(people_str, name="PEOPLE")

        tip = compute_tip(bill, percent)
        total = compute_total(bill, tip)
        share = compute_share(total, people)

        # Very large inputs can overflow to inf during the math above
        if not all(math.isfinite(v) for v in (tip, total, share)):
            raise ValueError("amounts are too large to calculate")

        tip_r = round_money(tip)
        total_r = round_money(total)
        share_r = round_money(share)

        print(f"Tip: {format_money(tip_r)}")
        print(f"Total: {format_money(total_r)}")
        print(f"Each person owes: {format_money(share_r)}")
    except ValueError as exc:
        fail(exc)
    except ArithmeticError:
        # Decimal raises InvalidOperation (an ArithmeticError) for huge values
        fail("amounts are too large to calculate")


if __name__ == "__main__":
    main()