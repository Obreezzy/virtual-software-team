import unittest
import math
from inventory_core import InventoryError
import inventory_ops as app  


class TestInventoryOps(unittest.TestCase):
    def setUp(self):
        # start each test with a fresh inventory
        self.inv = {}

    # ---- successful operation tests ----
    def test_add_item_new_and_existing(self):
        # add new apple
        app.add_item(self.inv, "apple", 10, 0.30)
        self.assertEqual(
            self.inv,
            {"apple": {"quantity": 10, "price": 0.30}},
        )
        # add new banana
        app.add_item(self.inv, "banana", 5, 0.50)
        self.assertEqual(
            self.inv,
            {
                "apple": {"quantity": 10, "price": 0.30},
                "banana": {"quantity": 5, "price": 0.50},
            },
        )
        # increase existing apple
        app.add_item(self.inv, "apple", 5, 0.30)
        self.assertEqual(
            self.inv,
            {
                "apple": {"quantity": 15, "price": 0.30},
                "banana": {"quantity": 5, "price": 0.50},
            },
        )

    def test_remove_item_decrement_and_delete(self):
        # set up inventory
        app.add_item(self.inv, "apple", 15, 0.30)
        app.add_item(self.inv, "banana", 5, 0.50)

        # decrement banana
        app.remove_item(self.inv, "banana", 3)
        self.assertEqual(
            self.inv,
            {
                "apple": {"quantity": 15, "price": 0.30},
                "banana": {"quantity": 2, "price": 0.50},
            },
        )
        # remove banana completely
        app.remove_item(self.inv, "banana", 2)
        self.assertEqual(
            self.inv,
            {"apple": {"quantity": 15, "price": 0.30}},
        )

    def test_total_value(self):
        app.add_item(self.inv, "apple", 15, 0.30)
        self.assertAlmostEqual(app.total_value(self.inv), 4.50, delta=0.01)

    def test_low_stock(self):
        app.add_item(self.inv, "apple", 15, 0.30)
        low = app.low_stock(self.inv, 20)
        self.assertEqual(
            low,
            [{"name": "apple", "quantity": 15, "price": 0.30}],
        )

    # ---- error handling tests ----
    def test_add_item_invalid_name(self):
        with self.assertRaises(InventoryError) as cm:
            app.add_item(self.inv, "", 5, 1.00)
        self.assertEqual(str(cm.exception), 'item name must be a non-empty string')

    def test_add_item_invalid_quantity(self):
        with self.assertRaises(InventoryError) as cm:
            app.add_item(self.inv, "pear", -3, 0.40)
        self.assertEqual(str(cm.exception), 'quantity must be a positive integer')

    def test_add_item_invalid_price(self):
        with self.assertRaises(InventoryError) as cm:
            app.add_item(self.inv, "pear", 3, float('nan'))
        self.assertEqual(str(cm.exception), 'price must be a positive finite number')

    def test_add_item_price_mismatch(self):
        app.add_item(self.inv, "apple", 10, 0.30)
        with self.assertRaises(InventoryError) as cm:
            app.add_item(self.inv, "apple", 5, 0.31)
        self.assertEqual(
            str(cm.exception),
            'price mismatch for existing item "apple"',
        )

    def test_remove_item_nonexistent(self):
        with self.assertRaises(InventoryError) as cm:
            app.remove_item(self.inv, "orange", 1)
        self.assertEqual(
            str(cm.exception),
            'item "orange" does not exist in inventory',
        )

    def test_remove_item_insufficient_stock(self):
        app.add_item(self.inv, "apple", 5, 0.30)
        with self.assertRaises(InventoryError) as cm:
            app.remove_item(self.inv, "apple", 10)
        self.assertEqual(
            str(cm.exception),
            'insufficient stock for item "apple"',
        )

    def test_low_stock_invalid_threshold(self):
        with self.assertRaises(InventoryError) as cm:
            app.low_stock(self.inv, -1)
        self.assertEqual(
            str(cm.exception),
            'threshold must be a non-negative integer',
        )


if __name__ == "__main__":
    unittest.main()
