import unittest
from inventory_core import (
    InventoryError,
    ItemData,
    LowStockItem,
    Inventory,
    __all__,
)


class TestInventoryCore(unittest.TestCase):
    def test_inventory_error_message(self):
        """InventoryError must return the exact message passed at construction."""
        msg = "quantity must be positive"
        err = InventoryError(msg)
        self.assertIsInstance(err, Exception)
        self.assertEqual(str(err), msg)

    def test_inventory_error_is_subclass(self):
        """InventoryError must be a subclass of Exception."""
        self.assertTrue(issubclass(InventoryError, Exception))

    def test_all_exports(self):
        """The module's __all__ must contain exactly the public symbols."""
        expected = {"InventoryError", "ItemData", "Inventory", "LowStockItem"}
        self.assertEqual(set(__all__), expected)

    def test_item_data_structure(self):
        """ItemData TypedDict should accept the required fields with correct types."""
        item: ItemData = {"quantity": 3, "price": 1.99}
        self.assertIsInstance(item["quantity"], int)
        self.assertGreaterEqual(item["quantity"], 0)
        self.assertIsInstance(item["price"], float)
        self.assertGreaterEqual(item["price"], 0.0)

    def test_low_stock_item_structure(self):
        """LowStockItem TypedDict must contain name, quantity and price with proper types."""
        low: LowStockItem = {"name": "apple", "quantity": 5, "price": 0.5}
        self.assertIsInstance(low["name"], str)
        self.assertIsInstance(low["quantity"], int)
        self.assertGreaterEqual(low["quantity"], 0)
        self.assertIsInstance(low["price"], float)
        self.assertGreaterEqual(low["price"], 0.0)

    def test_inventory_type_alias(self):
        """Inventory alias should behave like a dict mapping names to ItemData."""
        inv: Inventory = {
            "apple": {"quantity": 10, "price": 0.5},
            "banana": {"quantity": 0, "price": 0.3},
        }
        self.assertIsInstance(inv, dict)
        for name, data in inv.items():
            self.assertIsInstance(name, str)
            self.assertTrue(name.strip())  # non‑empty after strip
            self.assertIsInstance(data, dict)
            self.assertIn("quantity", data)
            self.assertIn("price", data)

    def test_error_message_catalog_examples(self):
        """Each catalog message must be reproduced exactly when raised."""
        examples = [
            ("quantity must be positive", InventoryError("quantity must be positive")),
            ("price must be positive", InventoryError("price must be positive")),
            ('item "orange" not found', InventoryError('item "orange" not found')),
            ('insufficient stock for "banana"', InventoryError('insufficient stock for "banana"')),
            ("item name must be non-empty", InventoryError("item name must be non-empty")),
            ("threshold must be a positive integer", InventoryError("threshold must be a positive integer")),
        ]
        for expected_msg, exc in examples:
            with self.subTest(msg=expected_msg):
                self.assertEqual(str(exc), expected_msg)


if __name__ == "__main__":
    unittest.main()
