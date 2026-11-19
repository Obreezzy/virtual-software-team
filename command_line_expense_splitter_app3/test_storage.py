import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import storage as app  # the storage module implementation is in app.py


class TestStorage(unittest.TestCase):
    def setUp(self):
        # Patch validation helpers to keep tests focused on storage logic.
        patch_people = mock.patch('storage.validate_people_list', autospec=True)
        patch_expense = mock.patch('storage.validate_expense_dict', autospec=True)

        self.mock_validate_people = patch_people.start()
        self.mock_validate_expense = patch_expense.start()
        self.addCleanup(patch_people.stop)
        self.addCleanup(patch_expense.stop)

        # By default, validation succeeds.
        self.mock_validate_people.return_value = None
        self.mock_validate_expense.return_value = None

        # Temporary directory for all file operations.
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    # ---------- load_ledger tests ----------
    def test_load_nonexistent_returns_empty(self):
        path = os.path.join(self.tmp_dir.name, "does_not_exist.json")
        result = app.load_ledger(path)
        self.assertEqual(result, app.EMPTY_LEDGER)

    def test_load_well_formed_file(self):
        path = os.path.join(self.tmp_dir.name, "good.json")
        ledger = {"people": ["Alice", "Bob"], "expenses": []}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ledger, f)
        result = app.load_ledger(path)
        self.assertEqual(result, ledger)

    def test_load_malformed_json_creates_backup_and_raises(self):
        path = os.path.join(self.tmp_dir.name, "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ not a valid json }")
        with self.assertRaisesRegex(app.ExpenseError, r"ledger file is corrupted, backup created"):
            app.load_ledger(path)
        # backup should exist
        self.assertTrue(os.path.exists(path + ".bak"))
        # original file should have been moved (i.e., no longer at original location)
        self.assertFalse(os.path.exists(path))

    def test_load_invalid_structure_creates_backup_and_raises(self):
        # Simulate a ledger where an expense references an unknown participant.
        path = os.path.join(self.tmp_dir.name, "invalid.json")
        ledger = {
            "people": ["Alice"],
            "expenses": [
                {"payer": "Alice", "amount": 10.0, "participants": ["Bob"], "description": "Lunch"}
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ledger, f)

        # Force validate_expense_dict to raise the expected error.
        self.mock_validate_expense.side_effect = app.ExpenseError('participant "Bob" is not a known person')

        with self.assertRaisesRegex(app.ExpenseError, r"ledger file is corrupted, backup created"):
            app.load_ledger(path)
        self.assertTrue(os.path.exists(path + ".bak"))
        self.assertFalse(os.path.exists(path))

    def test_load_empty_path_raises(self):
        with self.assertRaisesRegex(app.ExpenseError, r"path must be a non-empty string"):
            app.load_ledger("   ")

    def test_load_unreadable_file_raises(self):
        # Create a directory and try to load it as a file.
        path = os.path.join(self.tmp_dir.name, "dir_as_file")
        os.mkdir(path)
        with self.assertRaisesRegex(app.ExpenseError, r"cannot read ledger file:"):
            app.load_ledger(path)

    # ---------- save_ledger tests ----------
    def test_save_valid_ledger_and_load_back(self):
        path = os.path.join(self.tmp_dir.name, "saved.json")
        ledger = {"people": ["Alice"], "expenses": []}
        app.save_ledger(path, ledger)
        # Ensure file exists and can be read back correctly.
        loaded = app.load_ledger(path)
        self.assertEqual(loaded, ledger)

    def test_save_invalid_ledger_unknown_participant_raises(self):
        path = os.path.join(self.tmp_dir.name, "bad_save.json")
        bad_ledger = {
            "people": ["Alice"],
            "expenses": [
                {"payer": "Alice", "amount": 10.0, "participants": ["Bob"], "description": "Lunch"}
            ],
        }
        # Mock validation to raise the specific error expected by the design.
        self.mock_validate_expense.side_effect = app.ExpenseError('participant "Bob" is not a known person')
        with self.assertRaisesRegex(
            app.ExpenseError,
            r'ledger structure invalid: participant "Bob" is not a known person',
        ):
            app.save_ledger(path, bad_ledger)

    def test_save_empty_path_raises(self):
        with self.assertRaisesRegex(app.ExpenseError, r"path must be a non-empty string"):
            app.save_ledger("   ", {"people": [], "expenses": []})

    def test_save_non_dict_ledger_raises(self):
        path = os.path.join(self.tmp_dir.name, "notadict.json")
        with self.assertRaisesRegex(app.ExpenseError, r"ledger must be a dict"):
            app.save_ledger(path, ["not", "a", "dict"])


if __name__ == "__main__":
    unittest.main()
