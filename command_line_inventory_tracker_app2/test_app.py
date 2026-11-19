import unittest
import io
import sys
import contextlib
from decimal import Decimal
from unittest.mock import patch

import app


class TestApp(unittest.TestCase):
    def setUp(self):
        # a simple in‑memory inventory that survives across calls in a test
        self._inventory_store = {}

        # patch the persistence helpers to use the in‑memory store
        self.patcher_load = patch.object(app, "_load", side_effect=self._fake_load)
        self.patcher_save = patch.object(app, "_save", side_effect=self._fake_save)
        self.mock_load = self.patcher_load.start()
        self.mock_save = self.patcher_save.start()

        # provide very small stubs for the operation functions
        self.patcher_add = patch.object(
            app.inventory_ops,
            "add_item",
            side_effect=self._fake_add_item,
        )
        self.patcher_remove = patch.object(
            app.inventory_ops,
            "remove_item",
            side_effect=self._fake_remove_item,
        )
        self.patcher_low = patch.object(
            app.inventory_ops,
            "low_stock",
            side_effect=self._fake_low_stock,
        )
        self.patcher_total = patch.object(
            app.inventory_ops,
            "total_value",
            side_effect=self._fake_total_value,
        )
        self.patcher_add.start()
        self.patcher_remove.start()
        self.patcher_low.start()
        self.patcher_total.start()

    def tearDown(self):
        patch.stopall()

    # ----- fake helpers -------------------------------------------------
    def _fake_load(self):
        # return a *copy* so the app can modify it
        return dict(self._inventory_store)

    def _fake_save(self, inv):
        # replace the stored inventory with the new one
        self._inventory_store.clear()
        self._inventory_store.update(inv)

    def _fake_add_item(self, *, inventory, name, quantity, price):
        # price is a Decimal in the real code; keep it as Decimal here
        if name in inventory:
            inventory[name]["quantity"] += quantity
        else:
            inventory[name] = {"quantity": quantity, "price": price}

    def _fake_remove_item(self, *, inventory, name, quantity):
        if name not in inventory:
            raise app.inventory_core.InventoryError("item not found")
        new_qty = inventory[name]["quantity"] - quantity
        if new_qty < 0:
            raise app.inventory_core.InventoryError("not enough stock")
        if new_qty == 0:
            del inventory[name]
        else:
            inventory[name]["quantity"] = new_qty

    def _fake_low_stock(self, *, inventory, threshold):
        result = []
        for n, rec in inventory.items():
            if rec["quantity"] < threshold:
                result.append(
                    {"name": n, "quantity": rec["quantity"], "price": rec["price"]}
                )
        return result

    def _fake_total_value(self, inventory):
        total = Decimal("0")
        for rec in inventory.values():
            total += Decimal(rec["quantity"]) * Decimal(rec["price"])
        return total

    # ----- individual behaviour tests ---------------------------------
    def test_add_success(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = app.main(["add", "apple", "10", "0.55"])
        self.assertEqual(rc, 0)
        self.assertIn('Added 10 of "apple" at $0.55 each.', out.getvalue())
        self.assertIn("apple", self._inventory_store)
        self.assertEqual(self._inventory_store["apple"]["quantity"], 10)

    def test_remove_success(self):
        # pre‑populate inventory
        self._inventory_store["apple"] = {"quantity": 10, "price": Decimal("0.55")}
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = app.main(["remove", "apple", "5"])
        self.assertEqual(rc, 0)
        self.assertIn('Removed 5 of "apple".', out.getvalue())
        self.assertEqual(self._inventory_store["apple"]["quantity"], 5)

    def test_low_stock_report(self):
        self._inventory_store["banana"] = {"quantity": 2, "price": Decimal("0.75")}
        self._inventory_store["orange"] = {"quantity": 15, "price": Decimal("0.60")}
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = app.main(["low", "5"])
        self.assertEqual(rc, 0)
        self.assertIn("- banana: 2 @ $0.75", out.getvalue())
        self.assertNotIn("orange", out.getvalue())

    def test_total_value_report(self):
        self._inventory_store["banana"] = {"quantity": 10, "price": Decimal("0.75")}
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = app.main(["total"])
        self.assertEqual(rc, 0)
        self.assertIn("Total inventory value: $7.50", out.getvalue())

    def test_unknown_command(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = app.main(["foobar"])
        self.assertEqual(rc, 1)
        self.assertIn("Error: unknown command 'foobar'.", err.getvalue())

    def test_malformed_quantity(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = app.main(["add", "pear", "-2", "1.20"])
        self.assertEqual(rc, 1)
        self.assertIn("Error: quantity must be a positive integer.", err.getvalue())

    def test_invalid_name_empty(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = app.main(["add", "   ", "5", "1.00"])
        self.assertEqual(rc, 1)
        self.assertIn("Error: item name must be non-empty.", err.getvalue())

    def test_invalid_price_nan(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = app.main(["add", "grape", "5", "nan"])
        self.assertEqual(rc, 1)
        self
