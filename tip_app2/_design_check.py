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


import sys
import math
from decimal import Decimal, ROUND_HALF_UP

# ----- Implementation per design -----
def parse_float(arg: str, *, name: str) -> float:
    try:
        value = float(arg)
    except ValueError:
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value

def parse_int(arg: str, *, name: str) -> int:
    try:
        value = int(arg)
    except ValueError:
        raise ValueError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be >= 1")
    return value

def compute_tip(bill: float, percent: float) -> float:
    return bill * (percent / 100)

def compute_total(bill: float, tip: float) -> float:
    return bill + tip

def compute_share(total: float, people: int) -> float:
    return total / people

def round_money(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

def format_money(value: float) -> str:
    return f"${value:0.2f}"

def main() -> None:
    args = sys.argv[1:]
    if len(args) != 3:
        raise ValueError("exactly three arguments required: BILL PERCENT PEOPLE")
    bill = parse_float(args[0], name="BILL")
    percent = parse_float(args[1], name="PERCENT")
    people = parse_int(args[2], name="PEOPLE")

    tip = compute_tip(bill, percent)
    total = compute_total(bill, tip)
    share = compute_share(total, people)

    tip_r = round_money(tip)
    total_r = round_money(total)
    share_r = round_money(share)

    print(f"Tip: {format_money(tip_r)}")
    print(f"Total: {format_money(total_r)}")
    print(f"Each person owes: {format_money(share_r)}")

# ----- Helper for testing main -----
def _run_main(args):
    """Run main() with given argument list, capture stdout and exit code."""
    import io, contextlib
    old_argv = sys.argv
    sys.argv = ["app.py"] + args
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            main()
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1
        except Exception:
            # any unexpected exception propagates as failure in checks
            raise
    output = buf.getvalue()
    sys.argv = old_argv
    return exit_code, output

# ----- Tests (using provided helpers) -----
#
