import unittest
from validator import (
    validate_isbn,
    validate_nonempty_string,
    parse_date,
    validate_book,
)
from lib_common import LibraryError


class TestValidator(unittest.TestCase):
    # ---------- validate_isbn ----------
    def test_validate_isbn_accepts_valid_10(self):
        # Worked example: passes for a 10‑digit numeric string
        try:
            validate_isbn('0123456789')
        except LibraryError:
            self.fail("validate_isbn raised LibraryError on a valid 10‑digit ISBN")

    def test_validate_isbn_accepts_valid_13(self):
        # Worked example: passes for a 13‑digit numeric string
        try:
            validate_isbn('9780123456786')
        except LibraryError:
            self.fail("validate_isbn raised LibraryError on a valid 13‑digit ISBN")

    def test_validate_isbn_rejects_invalid(self):
        # Worked example: too short raises the exact message
        with self.assertRaises(LibraryError) as cm:
            validate_isbn('12345')
        self.assertEqual(str(cm.exception),
                         'ISBN must be a 10 or 13 digit numeric string')

    # ---------- validate_nonempty_string ----------
    def test_validate_nonempty_string_pass(self):
        # Worked example: string with surrounding whitespace passes after strip
        try:
            validate_nonempty_string('  Great  ', 'title')
        except LibraryError:
            self.fail("validate_nonempty_string raised LibraryError on a non‑empty string")

    def test_validate_nonempty_string_rejects_empty(self):
        # Worked example: only whitespace raises the exact message
        with self.assertRaises(LibraryError) as cm:
            validate_nonempty_string('   ', 'author')
        self.assertEqual(str(cm.exception), 'author must be a non-empty string')

    # ---------- parse_date ----------
    def test_parse_date_valid(self):
        # Worked example: a correct ISO date returns the same string
        result = parse_date('2023-12-01')
        self.assertEqual(result, '2023-12-01')

    def test_parse_date_invalid(self):
        # Worked example: an impossible calendar day raises the exact message
        with self.assertRaises(LibraryError) as cm:
            parse_date('2024-02-29')
        self.assertEqual(str(cm.exception),
                         'due_date must be a valid ISO date YYYY-MM-DD')

    # ---------- validate_book ----------
    def test_validate_book_cases(self):
        # Valid book – should pass without exception
        valid_book = {
            'isbn': '9780123456786',
            'title': 'Python 101',
            'author': 'A. B.'
        }
        try:
            validate_book(valid_book)
        except LibraryError:
            self.fail("validate_book raised LibraryError on a valid book")

        # Missing key – should raise the exact missing‑key message
        missing_key_book = {'isbn': '9780123456786', 'title': 'X'}
        with self.assertRaises(LibraryError) as cm_missing:
            validate_book(missing_key_book)
        self.assertEqual(str(cm_missing.exception), 'book must contain author')

        # Invalid ISBN – helper error should propagate unchanged
        invalid_isbn_book = {'isbn': '123', 'title': 'X', 'author': 'Y'}
        with self.assertRaises(LibraryError) as cm_isbn:
            validate_book(invalid_isbn_book)
        self.assertEqual(str(cm_isbn.exception),
                         'ISBN must be a 10 or 13 digit numeric string')


if __name__ == '__main__':
    unittest.main()
