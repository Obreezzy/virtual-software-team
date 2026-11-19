import sys
import os
import math
from decimal import Decimal, InvalidOperation, getcontext
from typing import List, Dict, Any

import inventory_core
import inventory_io
import inventory_ops

# Set Decimal precision high enough for money calculations
getcontext().prec = 28

DEFAULT_PATH: str = os.path.expanduser('~/.inventory.json')
USAGE: str = """Usage: app <command> [options]

Commands:
  add <name> <quantity> <price>   Add or increase an item.
  remove <name> <quantity>        Remove stock from an item.
  low <threshold>                 List items below a quantity threshold.
  total                           Show total inventory value.
  help                            Show this help message.
"""

def _inventory_path() -> str:
    """Return the absolute path used for persistence."""
    return DEFAULT_PATH


def _print_error(msg: str) -> None:
    """Write an error message to stderr."""
    sys.stderr.write(msg + "\n")


def _load() -> Dict[str, Dict[str, Any]]:
    """Load the inventory, handling missing or corrupted files.

    If the inventory file is missing, start with an empty inventory silently.
    For any other InventoryError, report the problem and return an empty dict.
    """
    try:
        return inventory_io.load_inventory(path=_inventory_path())
    except inventory_core.InventoryError as e:
        # Suppress the “file not found” message – start with empty inventory quietly.
        msg = e.args[0] if e.args else ""
        if "not found" in msg.lower():
            return {}
        _print_error(f"Error: {msg}")
        return {}


def _save(inv: Dict[str, Dict[str, Any]]) -> None:
    """Persist the inventory, handling I/O problems."""
    try:
        inventory_io.save_inventory(path=_inventory_path(), inventory=inv)
    except inventory_core.InventoryError as e:
        _print_error(f"Error: {e.args[0]}")


def main(argv: List[str] | None = None) -> int:
    """Command‑line entry point."""
    args = argv if argv is not None else sys.argv[1:]

    # Help / no command
    if not args or args[0] == "help":
        print(USAGE)
        return 0

    cmd = args[0]

    # Load inventory (even for read‑only commands)
    inventory = _load()

    try:
        if cmd == "add":
            if len(args) != 4:
                _print_error("Invalid option")
                return 1
            name = args[1].strip()
            if not name:
                _print_error("Error: item name must be non-empty.")
                return 1
            # quantity validation
            try:
                qty = int(args[2])
                if qty <= 0:
                    raise ValueError
            except ValueError:
                _print_error("Error: quantity must be a positive integer.")
                return 1
            # price validation (float, positive, finite)
            try:
                price = float(args[3])
                if not math.isfinite(price) or price <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                _print_error("Error: price must be a positive number.")
                return 1

            inventory_ops.add_item(
                inventory=inventory,
                name=name,
                quantity=qty,
                price=price,
            )
            # format price with two decimal places as required by the spec
            print(f'Added {qty} of "{name}" at ${price:.2f} each.')
            _save(inventory)
            return 0

        elif cmd == "remove":
            if len(args) != 3:
                _print_error("Invalid option")
                return 1
            name = args[1].strip()
            if not name:
                _print_error("Error: item name must be non-empty.")
                return 1
            try:
                qty = int(args[2])
                if qty <= 0:
                    raise ValueError
            except ValueError:
                _print_error("Error: quantity must be a positive integer.")
                return 1

            inventory_ops.remove_item(
                inventory=inventory,
                name=name,
                quantity=qty,
            )
            print(f'Removed {qty} of "{name}".')
            _save(inventory)
            return 0

        elif cmd == "low":
            if len(args) != 2:
                _print_error("Invalid option")
                return 1
            try:
                threshold = int(args[1])
                if threshold < 0:
                    raise ValueError
            except ValueError:
                _print_error("Error: threshold must be a non-negative integer.")
                return 1

            low_items = inventory_ops.low_stock(
                inventory=inventory,
                threshold=threshold,
            )
            for item in low_items:
                # Expected keys: 'name', 'quantity', 'price'
                print(f"- {item['name']}: {item['quantity']} @ ${item['price']}")
            return 0

        elif cmd == "total":
            if len(args) != 1:
                _print_error("Invalid option")
                return 1
            total = inventory_ops.total_value(inventory=inventory)
            # Ensure we have a Decimal for formatting to two decimal places
            try:
                total_dec = Decimal(str(total))
            except (InvalidOperation, ValueError):
                _print_error("Error: total value could not be interpreted as a number.")
                return 1
            if not total_dec.is_finite():
                _print_error("Error: total value is not a finite number.")
                return 1
            total_dec = total_dec.quantize(Decimal('0.01'))
            print(f"Total inventory value: ${total_dec}")
            return 0

        else:
            # Unknown command handling per specification
            _print_error(f"Error: unknown command '{cmd}'.")
            return 1

    except inventory_core.InventoryError as e:
        _print_error(f"Error: {e.args[0]}")
        return 1
    except (KeyboardInterrupt, EOFError):
        # Graceful termination without traceback
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (EOFError, KeyboardInterrupt):
        # Clean exit on user interrupt or EOF
        sys.exit(0)
