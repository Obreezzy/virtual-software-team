import io
import sys
import unittest
from decimal import Decimal
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr

import app


class TestApp(unittest.TestCase):
    # ---------- parse_args ----------
    def test_parse_args_success(self):
        argv = ['app.py', '100', '15', '3']
        bill, percent, people = app.parse_args(argv)
        self.assertEqual(bill, Decimal('100'))
        self.assertEqual(percent, Decimal('15'))
        self.assertEqual(people, 3)

    def test_parse_args_negative_bill(self):
        argv = ['app.py', '-50', '10', '2']
        with self.assertRaises(app.InputError) as cm:
            app.parse_args(argv)
        self.assertEqual(str(cm.exception),
                         app.ERROR_MESSAGES["bill_positive"])

    def test_parse_args_invalid_percent(self):
        argv = ['app.py', '100', 'abc', '2']
        with self.assertRaises(app.InputError) as cm:
            app.parse_args(argv)
        self.assertEqual(str(cm.exception),
                         app.ERROR_MESSAGES["percent_type"])

    def test_parse_args_invalid_people(self):
        argv = ['app.py', '100', '10', '2.5']
        with self.assertRaises(app.InputError) as cm:
            app.parse_args(argv)
        self.assertEqual(str(cm.exception),
                         app.ERROR_MESSAGES["people_type"])

    # ---------- calculation helpers ----------
    def test_calculate_tip_trickiest_rule(self):
        tip = app.calculate_tip(Decimal('57.25'), Decimal('18'))
        self.assertEqual(tip, Decimal('10.305'))

    def test_format_currency_rounding(self):
        # tie‑breaking example: 0.005 -> $0.01
        formatted = app.format_currency(Decimal('0.005'))
        self.assertEqual(formatted, "$0.01")
        # regular rounding example from worked examples
        formatted2 = app.format_currency(Decimal('33.7775'))
        self.assertEqual(formatted2, "$33.78")

    # ---------- end‑to‑end ----------
    def test_main_successful_run(self):
        test_argv = ['app.py', '57.25', '18', '2']
        with patch.object(sys, 'argv', test_argv):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                app.main()
        output = stdout.getvalue()
        self.assertIn("Tip: $10.31", output)
        self.assertIn("Total: $67.56", output)
        self.assertIn("Each person pays: $33.78", output)

    def test_main_error_negative_bill(self):
        test_argv = ['app.py', '-20', '10', '2']
        with patch.object(sys, 'argv', test_argv):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as cm:
                    app.main()
            # exit code should be 1 per spec
            self.assertEqual(cm.exception.code, 1)
        err_output = stderr.getvalue()
        self.assertIn(app.ERROR_MESSAGES["bill_positive"], err_output)


if __name__ == '__main__':
    unittest.main()
