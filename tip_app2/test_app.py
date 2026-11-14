"""Edge-case tester for app.py (usage: python app.py BILL TIP_PERCENT PEOPLE).

Put this file in the same folder as app.py and run:
    python test_app.py

Each case is run as a subprocess. "reject" means the app should print an error
and exit with a non-zero code. "accept" means it should succeed (exit code 0).
Adjust the expectations below if your app treats a case differently.
"""
import subprocess
import sys

APP = "app.py"

# (arguments, expected behaviour, description)
CASES = [
    (["inf", "10", "2"], "reject", "BILL is inf"),
    (["nan", "10", "2"], "reject", "BILL is nan"),
    (["-inf", "10", "2"], "reject", "BILL is -inf"),
    (["-nan", "10", "2"], "reject", "BILL is -nan"),
    (["1e999", "10", "2"], "reject", "BILL overflows to inf"),
    (["1e30", "10", "2"], "reject", "amounts too large to calculate"),
    (["50", "inf", "2"], "reject", "TIP is inf"),
    (["50", "nan", "2"], "reject", "TIP is nan"),
    (["50", "10", "inf"], "reject", "PEOPLE is inf"),
    (["50", "10", "nan"], "reject", "PEOPLE is nan"),
    (["-5", "10", "2"], "reject", "negative bill"),
    (["0", "10", "2"], "reject", "zero bill"),
    (["50", "-10", "2"], "reject", "negative tip percent"),
    (["50", "10", "0"], "reject", "zero people (divide by zero)"),
    (["50", "10", "-2"], "reject", "negative people"),
    (["50", "10", "2.5"], "reject", "non-integer people"),
    (["abc", "10", "2"], "reject", "non-numeric bill"),
    (["50", "abc", "2"], "reject", "non-numeric tip"),
    (["50", "10", "abc"], "reject", "non-numeric people"),
    (["50", "10"], "reject", "missing argument"),
    ([], "reject", "no arguments"),
    (["50", "10", "2", "extra"], "reject", "too many arguments"),
    (["50", "0", "2"], "accept", "zero tip percent"),
    (["100", "15", "1"], "accept", "normal case, one person"),
    (["100", "15", "4"], "accept", "normal case, split four ways"),
    (["0.1", "15", "3"], "accept", "small amount, check cent rounding"),
    (["1234567.89", "18", "7"], "accept", "large amount"),
]


def run_case(args):
    return subprocess.run(
        [sys.executable, APP, *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def main():
    passed = 0
    for args, expected, description in CASES:
        result = run_case(args)
        failed_run = result.returncode != 0
        ok = failed_run if expected == "reject" else not failed_run
        passed += ok

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {description}")
        print(f"        command : python {APP} {' '.join(args)}")
        print(f"        exit    : {result.returncode}")
        if result.stdout.strip():
            print(f"        stdout  : {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"        stderr  : {result.stderr.strip()}")

        # Extra checks
        if expected == "reject":
            if "Traceback" in result.stderr:
                print("        WARNING : raw traceback shown; catch the exception "
                      "and print a friendly error instead")
            if not result.stderr.strip() and result.stdout.strip():
                print("        NOTE    : error went to stdout; consider printing "
                      "errors to stderr")
        else:
            out = result.stdout.lower()
            if "nan" in out or "inf" in out:
                print("        WARNING : output contains nan/inf")
        print()

    print(f"{passed}/{len(CASES)} cases behaved as expected.")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()