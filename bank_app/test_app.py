import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout
import io
from decimal import Decimal

import app


class TestBankApp(unittest.TestCase):
    def setUp(self):
        # Use a temporary directory for the accounts file
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.account_path = pathlib.Path(self.tmp_dir.name) / "accounts.json"
        # Patch the module constant so all file ops use the temp file
        self.patcher = mock.patch.object(app, "ACCOUNT_FILE", self.account_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp_dir.cleanup()

    # ---- validation tests -------------------------------------------------
    def test_validate_name_strips_and_accepts(self):
        self.assertEqual(app.validate_name("  Alice  "), "Alice")

    def test_validate_name_rejects_empty(self):
        with self.assertRaises(ValueError) as cm:
            app.validate_name("   ")
        self.assertEqual(str(cm.exception), "account name must be non-empty")

    def test_validate_amount_parses_and_rounds(self):
        amt = app.validate_amount("12.345")
        self.assertIsInstance(amt, Decimal)
        # 12.345 rounded half up to two places -> 12.35
        self.assertEqual(amt, Decimal("12.35"))

    def test_validate_amount_invalid_string(self):
        with self.assertRaises(ValueError) as cm:
            app.validate_amount("12.3a")
        self.assertEqual(str(cm.exception), "amount must be a number")

    def test_validate_amount_nonfinite(self):
        with self.assertRaises(ValueError) as cm:
            app.validate_amount("NaN")
        self.assertEqual(str(cm.exception), "amount must be a number")

    def test_validate_amount_nonpositive(self):
        for txt in ("0", "-5"):
            with self.assertRaises(ValueError) as cm:
                app.validate_amount(txt)
            self.assertEqual(str(cm.exception), "amount must be positive")

    # ---- account operations ------------------------------------------------
    def test_create_account_and_duplicate_error(self):
        accounts = {}
        app.create_account(accounts, "Bob", Decimal("0.00"))
        self.assertEqual(accounts, {"Bob": "0.00"})
        with self.assertRaises(ValueError) as cm:
            app.create_account(accounts, "Bob", Decimal("10.00"))
        self.assertEqual(str(cm.exception), "account already exists")

    def test_deposit_and_withdraw(self):
        accounts = {"Bob": "25.00"}
        new_bal = app.deposit(accounts, "Bob", Decimal("10.00"))
        self.assertEqual(new_bal, Decimal("35.00"))
        self.assertEqual(accounts["Bob"], "35.00")

        new_bal = app.withdraw(accounts, "Bob", Decimal("5.00"))
        self.assertEqual(new_bal, Decimal("30.00"))
        self.assertEqual(accounts["Bob"], "30.00")

    def test_withdraw_insufficient_funds(self):
        accounts = {"Bob": "5.00"}
        with self.assertRaises(ValueError) as cm:
            app.withdraw(accounts, "Bob", Decimal("10.00"))
        self.assertEqual(str(cm.exception), "insufficient funds")

    def test_list_accounts_sorted(self):
        accounts = {"Charlie": "0.00", "Bob": "20.50"}
        lst = app.list_accounts(accounts)
        expected = [("Bob", Decimal("20.50")), ("Charlie", Decimal("0.00"))]
        self.assertEqual(lst, expected)

    # ---- end‑to‑end interactive session ------------------------------------
    def test_example_session_end_to_end(self):
        # Sequence of inputs matching the Example Session in the design
        user_inputs = [
            "1",            # Create account
            "   Alice   ",  # name (with surrounding spaces)
            "100.00",       # initial balance
            "4",            # Deposit
            "Alice",
            "25.50",
            "5",            # Withdraw (insufficient)
            "Alice",
            "130.00",
            "2",            # List accounts
            "6"             # Quit
        ]

        with mock.patch("builtins.input", side_effect=user_inputs):
            captured = io.StringIO()
            with redirect_stdout(captured):
                app.main()

        output = captured.getvalue()

        # Check that each expected line appears somewhere in the output
        self.assertIn("Account 'Alice' created.", output)
        self.assertIn("Deposited 25.50. New balance: 125.50", output)
        self.assertIn("Error: insufficient funds", output)
        self.assertIn("Accounts:", output)
        self.assertIn("Alice : 125.50", output)
        self.assertIn("Good-bye!", output)


if __name__ == "__main__":
    unittest.main()
