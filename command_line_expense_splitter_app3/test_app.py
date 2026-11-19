import sys
import io
import os
import tempfile
import unittest
import contextlib
from unittest import mock

import app
import common


class TestApp(unittest.TestCase):
    def setUp(self):
        # Patch storage I/O functions
        self.patcher_load = mock.patch('storage.load_ledger')
        self.mock_load = self.patcher_load.start()
        self.patcher_save = mock.patch('storage.save_ledger')
        self.mock_save = self.patcher_save.start()
        self.patcher_backup = mock.patch('storage._backup_corrupt_file')
        self.mock_backup = self.patcher_backup.start()

        # In‑memory ledger used by the mocked storage functions
        self.ledger = {"people": [], "expenses": []}
        self.mock_load.side_effect = lambda path: self.ledger
        self.mock_save.side_effect = lambda path, ledger: None

        # Ensure DEFAULT_LEDGER_PATH points to a temporary file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        app.DEFAULT_LEDGER_PATH = os.path.join(self.temp_dir.name, "ledger.json")

    def tearDown(self):
        mock.patch.stopall()

    # --------------------------------------------------------------------- #
    # _cmd_add_person tests
    # --------------------------------------------------------------------- #
    def test_cmd_add_person_success(self):
        with mock.patch('people.add_person') as mock_add, \
                mock.patch('common.validate_name') as mock_validate, \
                mock.patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            ledger = {"people": [], "expenses": []}
            result = app._cmd_add_person(ledger=ledger, args=["Alice"])
            self.assertTrue(result)
            self.assertIn("Added person: Alice", mock_out.getvalue())
            mock_validate.assert_called_once_with(name="Alice")
            mock_add.assert_called_once_with(ledger=ledger, name="Alice")

    def test_cmd_add_person_invalid_name(self):
        with mock.patch(
            'common.validate_name',
            side_effect=common.ExpenseError("person name cannot be empty")
        ):
            ledger = {"people": [], "expenses": []}
            with self.assertRaises(common.ExpenseError) as cm:
                app._cmd_add_person(ledger=ledger, args=[""])
            self.assertEqual(str(cm.exception), "person name cannot be empty")

    # --------------------------------------------------------------------- #
    # _cmd_add_expense tests
    # --------------------------------------------------------------------- #
    def test_cmd_add_expense_success(self):
        with mock.patch('expenses.add_expense') as mock_add_exp, \
                mock.patch('common.validate_name'), \
                mock.patch('common.validate_payer'), \
                mock.patch('common.validate_amount'), \
                mock.patch('common.validate_participants'), \
                mock.patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            ledger = {"people": ["Alice", "Bob"], "expenses": []}
            args = ["Alice", "30.00", "Bob,Alice", "Dinner"]
            result = app._cmd_add_expense(ledger=ledger, args=args)
            self.assertTrue(result)
            self.assertIn("Expense recorded.", mock_out.getvalue())
            mock_add_exp.assert_called_once()
            call_kwargs = mock_add_exp.call_args.kwargs
            self.assertEqual(call_kwargs["payer"], "Alice")
            self.assertAlmostEqual(call_kwargs["amount"], 30.0, delta=0.01)
            self.assertEqual(call_kwargs["participants"], ["Bob", "Alice"])
            self.assertEqual(call_kwargs["description"], "Dinner")

    def test_cmd_add_expense_invalid_amount(self):
        ledger = {"people": ["Alice"], "expenses": []}
        args = ["Alice", "nan", "Alice", "Lunch"]
        with self.assertRaises(common.ExpenseError) as cm:
            app._cmd_add_expense(ledger=ledger, args=args)
        self.assertEqual(str(cm.exception), "amount must be a finite positive number")

    def test_cmd_add_expense_unknown_participant(self):
        with mock.patch(
            'common.validate_participants',
            side_effect=common.ExpenseError("unknown participant(s): ['Bob']")
        ):
            ledger = {"people": ["Alice"], "expenses": []}
            args = ["Alice", "10", "Bob", "Snack"]
            with self.assertRaises(common.ExpenseError) as cm:
                app._cmd_add_expense(ledger=ledger, args=args)
            self.assertEqual(str(cm.exception), "unknown participant(s): ['Bob']")

    # --------------------------------------------------------------------- #
    # _cmd_settle tests
    # --------------------------------------------------------------------- #
    def test_cmd_settle_success(self):
        payments = [{"from": "Bob", "to": "Alice", "amount": 15.0}]
        with mock.patch('settlement.compute_settlements', return_value=payments), \
                mock.patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            ledger = {"people": [], "expenses": []}
            result = app._cmd_settle(ledger=ledger, args=[])
            self.assertFalse(result)
            self.assertIn("Bob pays Alice: $15.00", mock_out.getvalue())

    def test_cmd_settle_invalid_args(self):
        ledger = {"people": [], "expenses": []}
        with self.assertRaises(common.ExpenseError) as cm:
            app._cmd_settle(ledger=ledger, args=["extra"])
        self.assertEqual(str(cm.exception), "settlement impossible")

    # --------------------------------------------------------------------- #
    # _dispatch tests
    # --------------------------------------------------------------------- #
    def test_dispatch_unknown_command(self):
        ledger = {"people": [], "expenses": []}
        with self.assertRaises(common.ExpenseError) as cm:
            app._dispatch(ledger=ledger, argv=["foobar"])
        self.assertEqual(str(cm.exception), "unknown command: foobar")

    # --------------------------------------------------------------------- #
    # End‑to‑end example session (via main)
    # --------------------------------------------------------------------- #
    def test_end_to_end_example_session(self):
        # Patch validation functions to be no‑ops and settlement to deterministic output
        with mock.patch('common.validate_name'), \
             mock.patch('common.validate_payer'), \
             mock.patch('common.validate_amount'), \
             mock.patch('common.validate_participants'), \
             mock.patch(
                 'settlement.compute_settlements',
                 return_value=[{"from": "Bob", "to": "Alice", "amount": 15.0}]
             ):

            def run_main(argv):
                out_buf = io.StringIO()
                err_buf = io.StringIO()
                with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
                    try:
                        app.main(argv)
                    except SystemExit:
                        pass
                return out_buf.getvalue(), err_buf.getvalue()

            # 1. add-person Alice
            out, err = run_main(['add-person', 'Alice'])
            self.assertIn("Added person: Alice", out)
            self.assertEqual(err, "")

            # 2. add-person Bob
            out, err = run_main(['add-person', 'Bob'])
            self.assertIn("Added person: Bob", out)

            # 3. add-expense Alice 30.00 Bob,Alice Dinner
            out, err = run_main(['add-expense', 'Alice', '30.00', 'Bob,Alice', 'Dinner'])
            self.assertIn("Expense recorded.", out)

            # 4. settle
            out, err = run_main(['settle'])
            self.assertIn("Bob pays Alice: $15.00", out)

            # 5. list-people
            out, err = run_main(['list-people'])
            self.assertIn("Alice", out)
            self.assertIn("Bob", out)

            # 6. list-expenses
            out, err = run_main(['list-expenses'])
            self.assertIn("Alice paid $30.00 for Dinner", out)
