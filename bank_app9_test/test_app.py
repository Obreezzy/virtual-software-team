import sys
import io
import json
import os
import tempfile
import unittest
from decimal import Decimal
from unittest import mock
from contextlib import redirect_stdout

import app


class TestParseAmount(unittest.TestCase):
    def test_integer(self):
        self.assertEqual(app.parse_amount("10"), Decimal("10.00"))

    def test_two_decimal_places(self):
        self.assertEqual(app.parse_amount("0.99"), Decimal("0.99"))

    def test_whitespace(self):
        self.assertEqual(app.parse_amount(" 5.5 "), Decimal("5.50"))

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            app.parse_amount("-3")

    def test_too_many_dp_raises(self):
        with self.assertRaises(ValueError):
            app.parse_amount("12.345")

    def test_nan_raises(self):
        with self.assertRaises(ValueError):
            app.parse_amount("nan")


class TestValidateNewAccountName(unittest.TestCase):
    def test_valid_name(self):
        self.assertEqual(app.validate_new_account_name("Alice", {}), "alice")

    def test_alphanumeric(self):
        self.assertEqual(app.validate_new_account_name("bob123", {}), "bob123")

    def test_invalid_characters(self):
        with self.assertRaises(ValueError):
            app.validate_new_account_name("Bob_1", {})

    def test_empty_after_strip(self):
        with self.assertRaises(ValueError):
            app.validate_new_account_name("   ", {})

    def test_duplicate_name(self):
        accounts = {"alice": {"name": "Alice", "balance": Decimal("0.00")}}
        with self.assertRaises(ValueError):
            app.validate_new_account_name("Alice", accounts)


class TestValidateExistingAccountName(unittest.TestCase):
    def test_valid_existing(self):
        accounts = {"alice": {"name": "Alice", "balance": Decimal("0.00")}}
        self.assertEqual(app.validate_existing_account_name("Alice", accounts), "alice")

    def test_not_found(self):
        accounts = {"alice": {"name": "Alice", "balance": Decimal("0.00")}}
        with self.assertRaises(ValueError):
            app.validate_existing_account_name("bob123", accounts)

    def test_empty_after_strip(self):
        accounts = {"alice": {"name": "Alice", "balance": Decimal("0.00")}}
        with self.assertRaises(ValueError):
            app.validate_existing_account_name("   ", accounts)


class TestAccountOperations(unittest.TestCase):
    def setUp(self):
        self.accounts = {}

    def test_create_account(self):
        key = app.validate_new_account_name("Alice", self.accounts)
        app.create_account(key, "Alice", self.accounts)
        self.assertIn("alice", self.accounts)
        self.assertEqual(self.accounts["alice"]["name"], "Alice")
        self.assertEqual(self.accounts["alice"]["balance"], Decimal("0.00"))

    def test_deposit(self):
        key = app.validate_new_account_name("Alice", self.accounts)
        app.create_account(key, "Alice", self.accounts)
        app.deposit(key, Decimal("25.00"), self.accounts)
        self.assertEqual(self.accounts["alice"]["balance"], Decimal("25.00"))

    def test_withdraw_success(self):
        key = app.validate_new_account_name("Alice", self.accounts)
        app.create_account(key, "Alice", self.accounts)
        app.deposit(key, Decimal("25.00"), self.accounts)
        app.withdraw(key, Decimal("5.00"), self.accounts)
        self.assertEqual(self.accounts["alice"]["balance"], Decimal("20.00"))

    def test_withdraw_insufficient_funds(self):
        key = app.validate_new_account_name("Alice", self.accounts)
        app.create_account(key, "Alice", self.accounts)
        app.deposit(key, Decimal("20.00"), self.accounts)
        with self.assertRaises(ValueError):
            app.withdraw(key, Decimal("30.00"), self.accounts)

    def test_view_balance(self):
        key = app.validate_new_account_name("Alice", self.accounts)
        app.create_account(key, "Alice", self.accounts)
        app.deposit(key, Decimal("20.00"), self.accounts)
        bal = app.view_balance(key, self.accounts)
        self.assertEqual(bal, Decimal("20.00"))

    def test_list_accounts_sorted(self):
        # create two accounts in unsorted order
        k1 = app.validate_new_account_name("bob", self.accounts)
        app.create_account(k1, "Bob", self.accounts)
        k2 = app.validate_new_account_name("alice", self.accounts)
        app.create_account(k2, "Alice", self.accounts)
        app.deposit(k2, Decimal("20.00"), self.accounts)
        result = app.list_accounts(self.accounts)
        expected = [("Alice", Decimal("20.00")), ("Bob", Decimal("0.00"))]
        self.assertEqual(result, expected)


class TestEndToEndMain(unittest.TestCase):
    def setUp(self):
        # Use a temporary directory for the accounts file
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.accounts_path = os.path.join(self.tmp_dir.name, "accounts.json")
        # Patch the module constant to point to the temp file
        self.patcher = mock.patch.object(app, "ACCOUNTS_FILE", self.accounts_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp_dir.cleanup()

    def run_session(self, user_inputs):
        """Run main() with scripted typed commands and return everything it printed."""
        with mock.patch("builtins.input", side_effect=user_inputs):
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    app.main()
                except SystemExit:
                    pass
            return f.getvalue()

    def test_example_session(self):
        output = self.run_session([
            "create account Alice",
            "create account alice",          # duplicate name
            "create account Bob123",
            "deposit -5 to alice",           # invalid amount
            "deposit 100.00 to alice",
            "balance ALICE",
            "withdraw 150 from alice",       # too much
            "list",
            "exit",
        ])
        self.assertIn("Account 'Alice' created.", output)
        self.assertIn("account name must be unique", output.lower())
        self.assertIn("Account 'Bob123' created.", output)
        self.assertIn("amount must be a positive number", output.lower())
        self.assertIn("Deposited $100.00 to 'Alice'.", output)
        self.assertIn("Balance for 'Alice': $100.00", output)
        self.assertIn("insufficient funds", output.lower())
        self.assertIn("Accounts:", output)
        self.assertIn("Alice - $100.00", output)
        self.assertIn("Bob123 - $0.00", output)
        self.assertIn("Good-bye!", output)

    def test_unknown_command_gets_a_message(self):
        output = self.run_session(["frobnicate", "exit"])
        self.assertIn("unknown command", output.lower())
        self.assertIn("Good-bye!", output)

    def test_bad_amounts_are_rejected(self):
        output = self.run_session([
            "create account Carol",
            "deposit inf to carol",
            "deposit nan to carol",
            "deposit 1e999 to carol",
            "deposit 10.005 to carol",
            "balance carol",
            "exit",
        ])
        self.assertNotIn("Deposited", output)
        self.assertIn("Balance for 'Carol': $0.00", output)


if __name__ == "__main__":
    unittest.main()