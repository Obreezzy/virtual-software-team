import unittest
import string
import contextlib
import io
from unittest.mock import patch

import app  # the module containing generate_password, rate_password, main


class TestPwdTool(unittest.TestCase):
    # -----------------------------------------------------------------
    # rate_password examples from the design
    # -----------------------------------------------------------------
    def test_rate_password_examples(self):
        examples = [
            ("abcdefgh1$", "medium"),
            ("Abcdefg1$xy", "medium"),
            ("Abcdefghijkl1", "medium"),
            ("Abcdefgh1$Xy", "strong"),
            ("Abcdef12", "weak"),
            ("abcdefghij1", "weak"),
            ("abcDEF", "weak"),
        ]
        for pwd, expected in examples:
            with self.subTest(pwd=pwd):
                self.assertEqual(app.rate_password(pwd), expected)

    def test_rate_password_empty_raises(self):
        with self.assertRaises(ValueError) as cm:
            app.rate_password("")
        self.assertEqual(str(cm.exception), "Password may not be empty")

    # -----------------------------------------------------------------
    # generate_password validation
    # -----------------------------------------------------------------
    def test_generate_password_invalid_type(self):
        with self.assertRaises(ValueError) as cm:
            app.generate_password("ten")
        self.assertEqual(str(cm.exception), "Length must be an integer")

    def test_generate_password_invalid_range(self):
        with self.assertRaises(ValueError) as cm:
            app.generate_password(5)
        self.assertEqual(str(cm.exception), "Length must be between 8 and 64")

    # -----------------------------------------------------------------
    # generate_password functional properties
    # -----------------------------------------------------------------
    def test_generate_password_properties(self):
        pwd = app.generate_password(20)
        self.assertEqual(len(pwd), 20)

        # check presence of each required class
        has_lower = any(ch in string.ascii_lowercase for ch in pwd)
        has_upper = any(ch in string.ascii_uppercase for ch in pwd)
        has_digit = any(ch in string.digits for ch in pwd)
        has_symbol = any(not ch.isalnum() for ch in pwd)

        self.assertTrue(has_lower, "missing lowercase")
        self.assertTrue(has_upper, "missing uppercase")
        self.assertTrue(has_digit, "missing digit")
        self.assertTrue(has_symbol, "missing symbol")

        # rating must be strong according to the design
        self.assertEqual(app.rate_password(pwd), "strong")

    # -----------------------------------------------------------------
    # end‑to‑end tests for main()
    # -----------------------------------------------------------------
    def test_main_generate_success(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ret = app.main(["generate", "12"])
        out = stdout.getvalue().strip()
        self.assertEqual(ret, 0)
        # one line output, length 12, contains all classes
        self.assertEqual(len(out), 12)
        self.assertTrue(any(c in string.ascii_lowercase for c in out))
        self.assertTrue(any(c in string.ascii_uppercase for c in out))
        self.assertTrue(any(c in string.digits for c in out))
        self.assertTrue(any(not c.isalnum() for c in out))

    def test_main_check_strong(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ret = app.main(["check", "aB3!xY9%Qz$k"])
        out = stdout.getvalue()
        self.assertEqual(ret, 0)
        self.assertIn("strong", out)

    def test_main_generate_invalid_length(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            ret = app.main(["generate", "5"])
        err = stderr.getvalue()
        self.assertEqual(ret, 1)
        self.assertIn("Length must be between 8 and 64", err)

    def test_main_missing_arguments_shows_usage(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            ret = app.main([])
        err = stderr.getvalue()
        self.assertEqual(ret, 1)
        self.assertIn(
            "Usage: python pwdtool.py generate <length> | python pwdtool.py check <password>",
            err,
        )


if __name__ == "__main__":
    unittest.main()
