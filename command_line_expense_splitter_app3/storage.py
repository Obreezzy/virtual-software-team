import json
import os
import tempfile
from typing import List, Dict, Any

from common import ExpenseError, validate_people_list, validate_expense_dict

EMPTY_LEDGER: Dict[str, Any] = {"people": [], "expenses": []}


def _validate_ledger(ledger: dict) -> None:
    """
    Ensures the ledger matches the shared format:
        {'people': List[str], 'expenses': List[Expense]}
    * 'people' must be a list of non-empty strings (validated via
      validate_people_list).
    * 'expenses' must be a list; each element is validated with
      validate_expense_dict using the current people list.
    Raises:
        ExpenseError('ledger structure invalid: <detail>')
    """
    if not isinstance(ledger, dict):
        raise ExpenseError("ledger structure invalid: ledger must be a dict")
    expected_keys = {"people", "expenses"}
    actual_keys = set(ledger.keys())
    if actual_keys != expected_keys:
        raise ExpenseError(
            f"ledger structure invalid: expected keys {sorted(expected_keys)}, got {sorted(actual_keys)}"
        )

    # Validate people list
    try:
        validate_people_list(ledger["people"])
    except ExpenseError as e:
        raise ExpenseError(f"ledger structure invalid: {e.args[0]}")

    # Validate each expense
    for expense in ledger["expenses"]:
        try:
            validate_expense_dict(expense, ledger["people"])
        except ExpenseError as e:
            raise ExpenseError(f"ledger structure invalid: {e.args[0]}")


def load_ledger(path: str) -> dict:
    """
    Reads the JSON file at *path* and returns a Ledger dict.
    - If the file does not exist -> returns EMPTY_LEDGER.
    - If the file cannot be opened -> raises ExpenseError('cannot read ledger file: <reason>').
    - If the JSON is malformed or the resulting object does not conform to the Ledger schema
      -> the original file is renamed to <path>.bak (over‑writing any existing backup) and raises
      ExpenseError('ledger file is corrupted, backup created').
    """
    if not isinstance(path, str) or not path.strip():
        raise ExpenseError("path must be a non-empty string")

    if not os.path.exists(path):
        return EMPTY_LEDGER

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except OSError as e:
        raise ExpenseError(f"cannot read ledger file: {e.strerror}")
    except json.JSONDecodeError:
        # Corrupted JSON – back up and raise
        _backup_corrupt_file(path)
        raise ExpenseError("ledger file is corrupted, backup created")

    try:
        _validate_ledger(data)
    except ExpenseError:
        _backup_corrupt_file(path)
        raise ExpenseError("ledger file is corrupted, backup created")

    return data


def _backup_corrupt_file(path: str) -> None:
    """Rename a corrupt ledger file to <path>.bak, overwriting any existing backup."""
    backup_path = f"{path}.bak"
    try:
        os.replace(path, backup_path)
    except OSError:
        # If we cannot rename, there is nothing safe to do; let the original exception propagate.
        pass


def save_ledger(path: str, ledger: dict) -> None:
    """
    Persists *ledger* atomically.
    1. Validates *ledger* with _validate_ledger.
    2. Serialises to JSON with indent=2 and sort_keys=True.
    3. Writes to a temporary file in the same directory (<path>.tmp).
    4. Calls os.replace(tmp, path) for an atomic rename.
    5. If any step fails, the temporary file is removed and an ExpenseError is raised.
    """
    if not isinstance(path, str) or not path.strip():
        raise ExpenseError("path must be a non-empty string")
    if not isinstance(ledger, dict):
        raise ExpenseError("ledger must be a dict")

    # Validate ledger structure
    try:
        _validate_ledger(ledger)
    except ExpenseError as e:
        raise ExpenseError(f"ledger structure invalid: {e.args[0]}")

    # Prepare JSON string
    try:
        json_text = json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ExpenseError(f"ledger structure invalid: {e}")

    dir_name = os.path.dirname(os.path.abspath(path)) or "."
    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=dir_name,
            prefix=os.path.basename(path) + ".",
            suffix=".tmp",
        ) as tmp:
            tmp_file = tmp.name
            tmp.write(json_text)
            tmp.flush()
            os.fsync(tmp.fileno())
    except OSError as e:
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass
        raise ExpenseError(f"cannot write temporary ledger file: {e.strerror}")

    try:
        os.replace(tmp_file, path)
    except OSError as e:
        # Clean up temp file if replace failed
        try:
            os.remove(tmp_file)
        except OSError:
            pass
        raise ExpenseError(f"cannot replace ledger file atomically: {e.strerror}")
