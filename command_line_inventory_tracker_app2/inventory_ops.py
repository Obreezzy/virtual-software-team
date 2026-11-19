from __future__ import annotations

import math
from typing import Dict, List

from inventory_core import InventoryError, ItemData, LowStockItem


def _validate_name(name: str) -> None:
    if not isinstance(name, str) or not name.strip():
        raise InventoryError('item name must be a non-empty string')


def _validate_quantity(quantity: int) -> None:
    if not isinstance(quantity, int) or quantity < 1:
        raise InventoryError('quantity must be a positive integer')


def _validate_price(price: float) -> None:
    if not isinstance(price, (int, float)):
        raise InventoryError('price must be a positive finite number')
    if not math.isfinite(price) or price <= 0.0:
        raise InventoryError('price must be a positive finite number')


def _validate_threshold(threshold: int) -> None:
    if not isinstance(threshold, int) or threshold < 0:
        raise InventoryError('threshold must be a non-negative integer')


def add_item(
    inventory: Dict[str, ItemData],
    name: str,
    quantity: int,
    price: float,
) -> Dict[str, ItemData]:
    """Insert a new item or increase the quantity of an existing one."""
    _validate_name(name)
    _validate_quantity(quantity)
    _validate_price(price)

    if name in inventory:
        stored_price = inventory[name]["price"]
        if round(stored_price, 2) != round(price, 2):
            raise InventoryError(f'price mismatch for existing item "{name}"')
        inventory[name]["quantity"] += quantity
    else:
        inventory[name] = {"quantity": quantity, "price": price}
    return inventory


def remove_item(
    inventory: Dict[str, ItemData],
    name: str,
    quantity: int,
) -> Dict[str, ItemData]:
    """Decrease the quantity of an existing item; delete if quantity reaches zero."""
    _validate_name(name)
    _validate_quantity(quantity)

    if name not in inventory:
        raise InventoryError(f'item "{name}" does not exist in inventory')
    current_qty = inventory[name]["quantity"]
    if quantity > current_qty:
        raise InventoryError(f'insufficient stock for item "{name}"')
    new_qty = current_qty - quantity
    if new_qty == 0:
        del inventory[name]
    else:
        inventory[name]["quantity"] = new_qty
    return inventory


def total_value(inventory: Dict[str, ItemData]) -> float:
    """Compute the total monetary value of the inventory."""
    total = 0.0
    for data in inventory.values():
        total += data["quantity"] * data["price"]
    if not math.isfinite(total):
        raise InventoryError('total value overflow')
    return round(total, 2)


def low_stock(
    inventory: Dict[str, ItemData],
    threshold: int,
) -> List[LowStockItem]:
    """Return items whose quantity is strictly less than the given threshold."""
    _validate_threshold(threshold)
    return [
        {"name": name, "quantity": data["quantity"], "price": data["price"]}
        for name, data in inventory.items()
        if data["quantity"] < threshold
    ]
