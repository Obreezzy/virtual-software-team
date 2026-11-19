# inventory_io.py
"""
Library module for loading and saving an inventory JSON file.

Provides:
    load_inventory(path: str) -> dict[str, dict[str, Any]]
    save_inventory(path: str, inventory: dict[str, dict[str, Any]]) -> None

All errors are raised as InventoryError with exact messages defined in the design.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict

from inventory_core import InventoryError


def _validate_path(path: str) -> str:
    """Return a cleaned, expanded path or raise InventoryError."""
    if not isinstance(path, str):
        raise InventoryError('inventory file path must be a non-empty string')
    cleaned = path.strip()
    if not cleaned:
        raise InventoryError('inventory file path must be a non-empty string')
    # Expand user (~) and environment variables
    return os.path.expandvars(os.path.expanduser(cleaned))


def _validate_structure(
    data: Any,
    *,
    corrupted_msg: str = 'inventory file is corrupted - backup created',
    invalid_msg: str = 'inventory data contains invalid values',
) -> None:
    """
    Validate that *data* conforms to the shared inventory format.

    Raises InventoryError with *corrupted_msg* for load validation,
    or with *invalid_msg* for save validation.
    """
    if not isinstance(data, dict):
        raise InventoryError(corrupted_msg)

    for key, value in data.items():
        # key checks
        if not isinstance(key, str) or not key:
            raise InventoryError(corrupted_msg)

        # value must be dict with exactly two keys
        if not isinstance(value, dict):
            raise InventoryError(corrupted_msg)
        if set(value.keys()) != {'quantity', 'price'}:
            raise InventoryError(corrupted_msg)

        # quantity checks
        qty = value['quantity']
        if not isinstance(qty, int) or qty < 0:
            raise InventoryError(corrupted_msg)

        # price checks
        price = value['price']
        if not isinstance(price, float):
            raise InventoryError(corrupted_msg)
        if not math.isfinite(price) or price < 0.0:
            raise InventoryError(corrupted_msg)


def load_inventory(path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load the inventory JSON file located at *path*.

    Returns
    -------
    dict[str, dict]  # exactly the shared format:
        {
            "item-name": {"quantity": int, "price": float},
            ...
        }

    Raises
    ------
    InventoryError('inventory file not found - starting with empty inventory')
        if the file does not exist.

    InventoryError('inventory file is not valid JSON')
        if the file cannot be parsed as JSON.

    InventoryError('inventory file is corrupted - backup created')
        if the JSON structure does not conform to the shared format
        (wrong types, missing keys, negative numbers, non-finite price).

    InventoryError('cannot read inventory file: <OS-error-message>')
        for any other I/O problem.
    """
    expanded_path = _validate_path(path)

    if not os.path.exists(expanded_path):
        raise InventoryError('inventory file not found - starting with empty inventory')

    try:
        with open(expanded_path, 'r', encoding='utf-8-sig') as f:
            raw = f.read()
    except OSError as e:
        raise InventoryError(f'cannot read inventory file: {e.strerror}') from None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise InventoryError('inventory file is not valid JSON') from None

    try:
        _validate_structure(data)
    except InventoryError:
        # backup corrupted file
        backup_path = f'{expanded_path}.bak'
        try:
            os.replace(expanded_path, backup_path)
        except OSError as e:
            # If we cannot backup, still raise the original error
            raise InventoryError('inventory file is corrupted - backup created') from None
        raise InventoryError('inventory file is corrupted - backup created') from None

    # At this point data is validated
    return data  # type: ignore[return-value]


def save_inventory(path: str, inventory: Dict[str, Dict[str, Any]]) -> None:
    """
    Persist *inventory* to *path* as pretty-printed JSON.

    The write is performed atomically:
        1. JSON is written to a temporary file `<path>.tmp`.
        2. The temporary file is renamed to *path*.

    Raises
    ------
    InventoryError('cannot write inventory file: <OS-error-message>')
        if any step of the atomic write fails.

    InventoryError('inventory data contains invalid values')
        if *inventory* does not follow the shared format
        (e.g. negative quantity, non-finite price, missing keys).
    """
    expanded_path = _validate_path(path)

    # Validate inventory before any file operation
    try:
        _validate_structure(inventory, corrupted_msg='inventory data contains invalid values')
    except InventoryError:
        raise InventoryError('inventory data contains invalid values') from None

    tmp_path = f'{expanded_path}.tmp'

    # Serialize JSON string first to avoid partial writes on encoding errors
    try:
        json_str = json.dumps(inventory, indent=2, sort_keys=True)
    except (TypeError, ValueError):
        raise InventoryError('inventory data contains invalid values') from None

    # Write atomically (plain UTF-8, no BOM)
    try:
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as tmp_file:
            tmp_file.write(json_str)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
    except OSError as e:
        raise InventoryError(f'cannot write inventory file: {e.strerror}') from None

    try:
        os.replace(tmp_path, expanded_path)
    except OSError as e:
        # Attempt to clean up the temp file before raising
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise InventoryError(f'cannot write inventory file: {e.strerror}') from None
