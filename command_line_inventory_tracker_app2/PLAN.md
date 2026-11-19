Requirements:
- Track inventory items with a name, quantity and unit price.
- Add new items or increase quantity of existing items.
- Remove stock from an item, error if insufficient quantity.
- Report items whose quantity is below a user‑provided threshold.
- Calculate total monetary value of all stock (quantity × price).
- Persist inventory data in a JSON file between runs.
- Invalid input (negative numbers, missing items, malformed file) raises a clear InventoryError.
- The program never crashes; all errors are caught and reported to the user.
Shared data formats (every module must follow these EXACTLY):
* inventory = dict[str, {'quantity': int, 'price': float}]  # mapping item name to its data
* low_stock_item = {'name': str, 'quantity': int, 'price': float}
Modules (in build order; each may import only the ones before it):
1. inventory_core.py - Define shared exception and type alias used by all other modules.
2. inventory_io.py - Load inventory from and save inventory to a JSON file.
   - def load_inventory(path: str) -> dict[str, dict]  # reads JSON, returns inventory dict, raises InventoryError on I/O or format problems
   - def save_inventory(path: str, inventory: dict[str, dict]) -> None  # writes inventory as JSON, raises InventoryError on failure
3. inventory_ops.py - Perform inventory modifications and generate reports.
   - def add_item(inventory: dict[str, dict], name: str, quantity: int, price: float) -> dict[str, dict]  # adds or updates an item, raises InventoryError for non‑positive quantity/price
   - def remove_item(inventory: dict[str, dict], name: str, quantity: int) -> dict[str, dict]  # subtracts quantity, removes entry if zero, raises InventoryError if item missing or not enough stock
   - def total_value(inventory: dict[str, dict]) -> float  # sum of quantity * price for all items
   - def low_stock(inventory: dict[str, dict], threshold: int) -> list[dict]  # list of items with quantity < threshold; each dict has keys name, quantity, price
4. app.py - Command‑line interface that ties together I/O and operations.
   - def main(argv: list[str] | None = None) -> int  # parses arguments, calls inventory_io and inventory_ops, prints user‑friendly messages, returns exit status
