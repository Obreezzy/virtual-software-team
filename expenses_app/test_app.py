import unittest
import tempfile
import os
import io
import sys
import contextlib
from unittest import mock

import app


class TestApp(unittest.TestCase):
    def test_validate_date(self):
        # valid date
        self.assertIsNone(app.validate_date("2022-12-31"))
        # invalid dates
        with self.assertRaises(ValueError) as cm:
            app.validate_date("2022-02-30")
        self.assertEqual(str(cm.exception),
                         "Date must be in YYYY-MM-DD format and a real calendar day.")
        with self.assertRaises(ValueError) as cm:
            app.validate_date("2022-5-1")
        self.assertEqual(str(cm.exception),
                         "Date must be in YYYY-MM-DD format and a real calendar day.")

    def test_validate_amount(self):
        self.assertAlmostEqual(app.validate_amount("  42.5  "), 42.5, delta=0.01)
        for bad in ["-3", "abc", "inf"]:
            with self.assertRaises(ValueError) as cm:
                app.validate_amount(bad)
            self.assertEqual(str(cm.exception), "Amount must be a positive number.")

    def test_normalise_category(self):
        self.assertEqual(app.normalise_category("food"), "Food")
        self.assertEqual(app.normalise_category("  TRANSPORT "), "Transport")
        with self.assertRaises(ValueError) as cm:
            app.normalise_category("   ")
        self.assertEqual(str(cm.exception), "Category cannot be empty.")

    def test_make_entry(self):
        entry = app.make_entry("2023-05-12", "food", 12.5, "Lunch at cafe")
        expected = {
            "date": "2023-05-12",
            "category": "Food",
            "amount": 12.5,
            "note": "Lunch at cafe",
        }
        self.assertEqual(entry, expected)

    def test_filter_and_aggregate(self):
        entries = [
            {"date": "2023-05-01", "category": "Food", "amount": 10.0, "note": ""},
            {"date": "2023-05-02", "category": "food", "amount": 20.0, "note": ""},
            {"date": "2023-05-03", "category": "Transport", "amount": 15.5, "note": ""},
            {"date": "2023-06-01", "category": "Food", "amount": 5.0, "note": ""},
        ]
        may = app.filter_by_month(entries, "2023-05")
        self.assertEqual(may, entries[:3])
        agg = app.aggregate_by_category(may)
        self.assertEqual(agg, {"Food": 30.0, "Transport": 15.5})

    def test_load_entries_nonexistent(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "does_not_exist.csv")
            self.assertEqual(app.load_entries(path), [])

    def test_append_and_load_entries(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "expenses.csv")
            entry = app.make_entry("2023-05-12", "food", 12.5,
                                   "Lunch, with colleague")
            app.append_entry(path, entry)

            # Verify file content
            with open(path, "r", newline="", encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual(lines[0], "date,category,amount,note")
            self.assertEqual(lines[1],
                             '2023-05-12,Food,12.50,"Lunch, with colleague"')

            # Verify load_entries returns the same entry
            loaded = app.load_entries(path)
            self.assertEqual(loaded, [entry])

    def test_load_entries_malformed(self):
        csv_content = """date,category,amount,note
2023-05-01,Food,10.00,Lunch
2023-05-02,Food,abc,Bad amount
2023-13-01,Food,5.00,Bad date
2023-05-04,,3.00,No category
"""
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "bad.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_content)

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                loaded = app.load_entries(path)

            self.assertEqual(loaded,
                             [{'date': '2023-05-01', 'category': 'Food',
                               'amount': 10.0, 'note': 'Lunch'}])

            err_output = stderr.getvalue().strip().splitlines()
            self.assertIn("Warning: skipping malformed row 3: invalid amount", err_output)
            self.assertIn("Warning: skipping malformed row 4: invalid date", err_output)
            self.assertIn("Warning: skipping malformed row 5: missing value", err_output)

    def test_format_report_examples(self):
        # Example 1
        totals1 = {'Food': 123.45, 'Transport': 67.89, 'Utilities': 200.0}
        report1 = app.format_report("2023-05", totals1)
        expected1 = """Expenses for 2023-05
Food            123.45    31.55%
Transport        67.89    17.35%
Utilities       200.00    51.11%
Overall total: 391.34"""
        self.assertEqual(report1, expected1)

        # Example 2
        report2 = app.format_report("2023-06", {})
        expected2 = "Expenses for 2023-06\nOverall total: 0.00"
        self.assertEqual(report2, expected2)

    def test_end_to_end_example_session(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "expenses.csv")
            # sequence of commands from the example session
            commands = [
                ["add", "2023-05-12", "Food", "12.50", "Lunch at cafe"],
                ["add", "2023-05-20", "transport", "30", "Bus pass"],
                ["add", "2023-06-02", "Food", "8", "Snack"],
                ["report", "2023-05"],
                ["report", "2023-07"],
                ["add", "2023-02-30", "Food", "5", "Bad date"],
                ["add", "2023-05-21", "Food", "-5", "Refund"],
                ["report", "2023-5"],
                ["delete"],
            ]

            for cmd in commands:
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), \
                     contextlib.redirect_stderr(stderr):
                    ret = app.main(cmd, path=path)
                out = stdout.getvalue()
                err = stderr.getvalue()

                # Check return codes for error cases
                if cmd[0] == "add" and cmd[1] == "2023-02-30":
                    self.assertEqual(ret, 1)
                    self.assertIn("Date must be in YYYY-MM-DD format and a real calendar day.", err)
                elif cmd[0] == "add" and cmd[2] == "-5":
                    self.assertEqual(ret, 1)
                    self.assertIn("Amount must be a positive number.", err)
                elif cmd[0] == "report" and cmd[1] == "2023-5":
                    self.assertEqual(ret, 1)
                    self.assertIn("Usage: report <year-month> (format YYYY-MM)", err)
                elif cmd[0] == "delete":
                    self.assertEqual(ret, 1)
                    self.assertIn("Unknown command. Use: add, report", err)
                else:
                    # successful commands
                    self.assertEqual(ret, 0)

                # Verify expected stdout fragments
                if cmd == ["add", "2023-05-12", "Food", "12.50", "Lunch at cafe"]:
                    self.assertIn("Entry added.", out)
                if cmd == ["report", "2023-05"]:
                    self.assertIn("Expenses for 2023-05", out)
                    self.assertIn("Food             12.50    29.41%", out)
                    self.assertIn("Transport        30.00    70.59%", out)
                    self.assertIn("Overall total: 42.50", out)
                if cmd == ["report", "2023-07"]:
                    self.assertIn("Expenses for 2023-07", out)
                    self.assertIn("Overall total: 0.00", out)


if __name__ == "__main__":
    unittest.main()
