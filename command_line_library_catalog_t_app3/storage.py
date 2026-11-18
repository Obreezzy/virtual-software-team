from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from lib_common import LibraryError, CatalogData


def _backup_corrupt(path: Path) -> None:
    """Rename a corrupted file to <original>.bak, overwriting any existing backup."""
    backup_path = Path(str(path) + ".bak")
    try:
        # Remove existing backup if present, then replace
        if backup_path.exists():
            backup_path.unlink()
        os.replace(path, backup_path)
    except OSError:
        # If we cannot back up, we still want to continue with an empty catalog.
        # The caller will handle the empty return value.
        pass


def _ensure_catalog_structure(data: Any) -> None:
    """Validate that *data* conforms to the CatalogData schema.

    Raises:
        LibraryError: If the structure is invalid.
    """
    if not isinstance(data, dict):
        raise LibraryError('invalid catalog data structure')
    if set(data.keys()) != {"books", "loans"}:
        raise LibraryError('invalid catalog data structure')
    if not isinstance(data["books"], list) or not isinstance(data["loans"], list):
        raise LibraryError('invalid catalog data structure')
    if any(not isinstance(item, dict) for item in data["books"]):
        raise LibraryError('invalid catalog data structure')
    if any(not isinstance(item, dict) for item in data["loans"]):
        raise LibraryError('invalid catalog data structure')


def load_data(file_path: str) -> CatalogData:
    """Load catalog data from *file_path*.

    Returns an empty catalog if the file does not exist, is malformed,
    or does not match the required schema.  Corrupted files are renamed
    to ``<original>.bak``.
    """
    path = Path(file_path).expanduser()

    if not path.exists():
        return {"books": [], "loans": []}

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except OSError as exc:
        # Propagate as domain error with the original message.
        raise LibraryError(f'cannot read data file: {exc.strerror}') from None
    except json.JSONDecodeError:
        _backup_corrupt(path)
        return {"books": [], "loans": []}

    # Validate the parsed JSON against the expected schema.
    if not isinstance(raw_data, dict):
        _backup_corrupt(path)
        return {"books": [], "loans": []}

    books = raw_data.get("books", [])
    loans = raw_data.get("loans", [])

    if not isinstance(books, list) or not isinstance(loans, list):
        _backup_corrupt(path)
        return {"books": [], "loans": []}

    if any(not isinstance(b, dict) for b in books) or any(not isinstance(l, dict) for l in loans):
        _backup_corrupt(path)
        return {"books": [], "loans": []}

    return {"books": books, "loans": loans}


def save_data(file_path: str, data: CatalogData) -> None:
    """Persist *data* to *file_path* safely.

    The function validates the structure, writes to a temporary file,
    flushes it to disk, and then atomically replaces the target file.
    """
    _ensure_catalog_structure(data)

    target_path = Path(file_path).expanduser()
    parent_dir = target_path.parent

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=str(parent_dir),
            prefix=".tmp_",
            suffix=".json",
            mode="w",
            encoding="utf-8",
        ) as tmp_file:
            json.dump(data, tmp_file, ensure_ascii=False, indent=2, sort_keys=True)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = Path(tmp_file.name)

        # Atomically replace the target file.
        os.replace(tmp_path, target_path)
    except OSError as exc:
        # Clean up the temporary file if it was created.
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise LibraryError(f'cannot write data file: {exc.strerror}') from None
