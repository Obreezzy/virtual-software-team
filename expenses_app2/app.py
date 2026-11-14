import csv
import sys
import os
import re
from datetime import datetime
from math import isfinite

# ---------- Validation ----------

def validate_date(date_str: str) -> None:
    if len(date_str) != 10:
        raise ValueError("Date must be in YYYY-MM-DD format and a real calendar day.")
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        raise ValueError("Date must be in YYYY-MM-DD format and a real calendar day.")


def validate_amount(amount_str: str) -> float:
    txt = amount_str.strip()
    try:
        val = float(txt)
    except Exception:
        raise ValueError("Amount must be a positive number.")
    if not isfinite(val) or val <= 0:
        raise ValueError("Amount must be a positive number.")
    return val


def normalise_category(category: str) -> str:
    cat = category.strip()
    if not cat:
        raise ValueError("Category cannot be empty.")
    return cat.title()


# ---------- Entry handling ----------

def make_entry(date: str, category: str, amount: float, note: str) -> dict:
    return {
        "date": date,
        "category": normalise_category(category),
        "amount": round(amount, 2),
        "note": note,
    }


def ensure_csv_exists(path: str) -> None:
    """
    Ensure the CSV file exists and contains the header row.
    If the file does not exist or is empty, write the header.
    """
    need_header = not os.path.exists(path) or os.path.getsize(path) == 0
    if need_header:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "category", "amount", "note"])


def append_entry(path: str, entry: dict) -> None:
    ensure_csv_exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                entry["date"],
                entry["category"],
                f"{entry['amount']:.2f}",
                entry["note"],
            ]
        )


def load_entries(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            line_no = reader.line_num
            # check missing/blank values for required fields
            date_raw = row.get("date", "").strip()
            cat_raw = row.get("category", "").strip()
            amt_raw = row.get("amount", "").strip()
            note_raw = row.get("note", "")
            if not date_raw or not cat_raw or not amt_raw:
                print(
                    f"Warning: skipping malformed row {line_no}: missing value",
                    file=sys.stderr,
                )
                continue
            # validate amount
            try:
                amount_val = validate_amount(amt_raw)
            except ValueError:
                print(
                    f"Warning: skipping malformed row {line_no}: invalid amount",
                    file=sys.stderr,
                )
                continue
            # validate date
            try:
                validate_date(date_raw)
            except ValueError:
                print(
                    f"Warning: skipping malformed row {line_no}: invalid date",
                    file=sys.stderr,
                )
                continue
            # build entry
            entry = make_entry(date_raw, cat_raw, amount_val, note_raw)
            entries.append(entry)
    return entries


# ---------- Filtering & aggregation ----------

def filter_by_month(entries: list[dict], year_month: str) -> list[dict]:
    return [e for e in entries if e["date"][:7] == year_month]


def aggregate_by_category(entries: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for e in entries:
        cat = normalise_category(e["category"])
        totals[cat] = totals.get(cat, 0.0) + e["amount"]
    # round each total to 2 decimals
    for cat in list(totals):
        totals[cat] = round(totals[cat], 2)
    return totals


# ---------- Reporting ----------

def format_report(year_month: str, totals: dict[str, float]) -> str:
    overall = round(sum(totals.values()), 2)
    lines = [f"Expenses for {year_month}"]
    if totals:
        for cat in sorted(totals):
            total = totals[cat]
            pct = 0.0 if overall == 0 else 100 * total / overall
            lines.append(f"{cat:<12}{total:>10.2f}{pct:>9.2f}%")
    lines.append(f"Overall total: {overall:.2f}")
    return "\n".join(lines)


def print_error(message: str) -> None:
    print(message, file=sys.stderr)


# ---------- Command handlers ----------

def handle_add(args: list[str], path: str) -> None:
    if len(args) != 4:
        raise ValueError("Usage: add <date> <category> <amount> <note>")
    date_str, cat_str, amt_str, note = args
    validate_date(date_str)
    amount = validate_amount(amt_str)
    entry = make_entry(date_str, cat_str, amount, note)
    append_entry(path, entry)
    print("Entry added.")


def handle_report(args: list[str], path: str) -> None:
    if len(args) != 1 or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args[0]):
        raise ValueError("Usage: report <year-month> (format YYYY-MM)")
    year_month = args[0]
    entries = load_entries(path)
    month_entries = filter_by_month(entries, year_month)
    totals = aggregate_by_category(month_entries)
    report = format_report(year_month, totals)
    print(report)


# ---------- Main entry point ----------

def main(argv: list[str] | None = None, path: str = "expenses.csv") -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print_error("Unknown command. Use: add, report")
        return 1
    command, *rest = argv
    try:
        if command == "add":
            handle_add(rest, path)
        elif command == "report":
            handle_report(rest, path)
        else:
            print_error("Unknown command. Use: add, report")
            return 1
        return 0
    except ValueError as ve:
        print_error(str(ve))
        return 1
    except OSError as oe:
        print_error(f"I/O error: {oe}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
