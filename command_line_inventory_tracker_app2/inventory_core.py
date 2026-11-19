"""inventory_core.py

Library module providing core types and the base exception for the inventory system.
It defines no executable code, only data structures and the InventoryError
exception as specified in the design document.
"""

from __future__ import annotations

from typing import TypedDict, Dict

__all__ = ["InventoryError", "ItemData", "Inventory", "LowStockItem"]


class InventoryError(Exception):
    """Base exception for all inventory‑related problems.

    The exception stores a single error message and returns it unchanged
    when converted to a string.
    """

    def __init__(self, message: str) -> None:
        # Store the message exactly as provided.
        super().__init__(message)


class ItemData(TypedDict):
    """Data for a single inventory entry.

    Attributes
    ----------
    quantity: int
        Must be a non‑negative integer (>= 0).
    price: float
        Must be a non‑negative float (>= 0.0).
    """
    quantity: int
    price: float


# Mapping from item name to its data.
Inventory = Dict[str, ItemData]


class LowStockItem(TypedDict):
    """Record returned by inventory_ops.low_stock.

    Attributes
    ----------
    name: str
        The item name (key from the inventory mapping).
    quantity: int
        Must be a non‑negative integer (>= 0).
    price: float
        Must be a non‑negative float (>= 0.0).
    """
    name: str
    quantity: int
    price: float
