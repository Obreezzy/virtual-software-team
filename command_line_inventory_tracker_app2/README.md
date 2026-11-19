# Inventory Manager  

A tiny command-line tool for keeping a persistent inventory of items.  
Each item has a **name**, a **quantity** (integer) and a **unit price** (float).  
The program can:

* add new items or increase the quantity of an existing one  
* remove stock from an item (fails if there isn't enough)  
* list items whose quantity is below a user-provided threshold  
* compute the total monetary value of all stock  
* automatically save the inventory to a JSON file and reload it on the next run  

All error conditions raise a clear `InventoryError` and are reported to the user
instead of causing a traceback.

---

## Files

| File | Purpose |
|------|---------|
| `inventory_core.py` | Defines the `InventoryError` exception and the type alias used throughout the project. |
| `inventory_io.py`   | Functions to **load** (`load_inventory`) and **save** (`save_inventory`) the inventory JSON file. |
| `inventory_ops.py` | Core operations: `add_item`, `remove_item`, `total_value`, `low_stock`. |
| `app.py`            | Command-line interface that ties I/O and operations together. The entry point is `main()`. |
| `test_inventory_core.py`, `test_inventory_io.py`, `test_inventory_ops.py` | Unit tests for the three modules. |
| `test_app.py`       | Integration tests for the command-line interface. |

---

## How to run the program  

```bash
$ python app.py
```

The script expects sub-commands (see examples below).  
If an unknown option is supplied the program prints an error instead of a help
message, e.g.:

```bash
$ python app.py -h
Error: unknown command '-h'.
```

### Example session

```bash
# Add 15 units of "widget" priced at $2.50 each
$ python app.py add widget 15 2.5
Item "widget" added/updated successfully.

# Remove 5 units of "widget"
$ python app.py remove widget 5
Removed 5 of "widget". Remaining quantity: 10.

# Show items with quantity below 12
$ python app.py lowstock 12
Low stock items (threshold < 12):
- widget: quantity=10, price=2.5

# Show total value of the inventory
$ python app.py total
Total inventory value: $25.00
```

All changes are written to `inventory.json` in the current directory and are
available the next time the program runs.

---

## Running the tests  

The test suite uses the standard library `unittest` framework.

```bash
$ python -m unittest
```

The command discovers and runs all `test_*.py` files, including `test_app.py`.
All tests should pass; any failure will be reported with a clear message.

---

## Installation & requirements  

* Python 3.9 or newer  
* No external dependencies - only the Python standard library is used.

Simply clone/download the repository (or copy the files) and run the commands
shown above. No additional setup is required.