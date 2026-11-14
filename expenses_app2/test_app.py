import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

import app


class TestApp(unittest.TestCase):
    # 1. validate_date – success and failures
    def test_validate_date(self):
        # success
        self.assertIsNone(app.validate_date("2022-12-31"))
        # invalid day
        with self.assertRaises(ValueError) as cm:
            app.validate_date("2022-02-30")
        self.assertEqual(
            str(cm.exception),
            "Date must be in YYYY-MM-DD format and a real calendar day.",
        )
        # wrong format
        with self.assertRaises(ValueError) as cm:
            app.validate_date("2022-5-1")
        self.assertEqual(
            str(cm.exception),
            "Date must be in YYYY-MM-DD format and a real calendar day.",
        )

    # 2. validate_amount – success and failures
    def test_validate_amount(self):
        self.assertAlmostEqual(app.validate_amount("  42.5  "), 42.5, delta=0.01)
        for bad in ["-3", "abc", "inf"]:
            with self.assertRaises(ValueError) as cm:
                app.validate_amount(bad)
            self.assertEqual(str(cm.exception), "Amount must be a positive number.")

    # 3. normalise_category – success and failure
    def test_normalise_category(self):
        self.assertEqual(app.normalise_category("food"), "Food")
        self.assertEqual(app.normalise_category("  TRANSPORT "), "Transport")
        with self.assertRaises(ValueError) as cm:
            app.normalise_category("   ")
        self.assertEqual(str(cm.exception), "Category cannot be empty.")

    # 4. make_entry – exact dict structure
    def test_make_entry(self):
        entry = app.make_entry("2023-05-12", "food", 12.5, "Lunch at cafe")
        expected = {
            "date": "2023-05-12",
            "category": "Food",
            "amount": 12.5,
            "note": "Lunch at cafe",
        }
        self.assertEqual(entry, expected)

    # 5. format_report – both worked examples
    def test_format_report_examples(self):
        # example 1
        totals = {"Food": 123.45, "Transport": 67.89, "Utilities": 200.0}
        report = app.format_report("2023-05", totals)
        expected = (
            "Expenses for 2023-05\n"
            "Food            123.45    31.55%\n"
            "Transport        67.89    17.35%\n"
            "Utilities       200.00    51.11%\n"
            "Overall total: 391.34"
        )
        self.assertEqual(report, expected)

        # example 2
        report2 = app.format_report("2023-06", {})
        expected2 = "Expenses for 2023-06\nOverall total: 0.00"
        self.assertEqual(report2, expected2)

    # 6. load_entries with malformed rows – warnings to stderr
    def test_load_entries_malformed(self):
        csv_content = """date,category,amount,note
2023-05-01,Food,10.00,Lunch
2023-05-02,Food,abc,Bad amount
2023-13-01,Food,5.00,Bad date
2023-05-04,,3.00,No category
"""
        with tempfile.NamedTemporaryFile("w+", delete=False, newline="", encoding="utf-8") as tf:
            tf.write(csv_content)
            tf_path = tf.name

        try:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                entries = app.load_entries(tf_path)

            # only the first row should be loaded
            self.assertEqual(
                entries,
                [{"date": "2023-05-01", "category": "Food", "amount": 10.0, "note": "Lunch"}],
            )

            # warnings should be printed in order
            warning_output = stderr.getvalue().strip().splitlines()
            self.assertIn("Warning: skipping malformed row 3: invalid amount", warning_output)
            self.assertIn("Warning: skipping malformed row 4: invalid date", warning_output)
            self.assertIn("Warning: skipping malformed row 5: missing value", warning_output)
        finally:
            os.remove(tf_path)

    # 7. end‑to‑end add + report using a temporary CSV file
    def test_end_to_end_add_and_report(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            path = tf.name
        try:
            # add two entries
            self.assertEqual(app.main(["add", "2023-05-12", "Food", "12.50", "Lunch at cafe"], path), 0)
            self.assertEqual(app.main(["add", "2023-05-20", "transport", "30", "Bus pass"], path), 0)

            # capture report output
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                ret = app.main(["report", "2023-05"], path)
            self.assertEqual(ret, 0)

            output = stdout.getvalue().strip().splitlines()
            # check each expected line appears
            self.assertIn("Expenses for 2023-05", output)
            self.assertIn("Food             12.50    29.41%", output)
            self.assertIn("Transport        30.00    70.59%", output)
            self.assertIn("Overall total: 42.50", output)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
