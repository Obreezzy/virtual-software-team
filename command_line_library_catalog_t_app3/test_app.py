import unittest
import os
import json
import sys
import contextlib
import io
import tempfile
from unittest import mock

import app
from lib_common import LibraryError


class TestApp(unittest.TestCase):
    def setUp(self):
        # Patches common to many tests
        self.patcher_load = mock.patch('app.storage.load_data')
        self.mock_load = self.patcher_load.start()
        self.patcher_save = mock.patch('app.storage.save_data')
        self.mock_save = self.patcher_save.start()
        self.patcher_validate_isbn = mock.patch('app.validator.validate_isbn')
        self.mock_validate_isbn = self.patcher_validate_isbn.start()
        self.patcher_validate_str = mock.patch('app.validator.validate_nonempty_string')
        self.mock_validate_str = self.patcher_validate_str.start()
        self.patcher_parse_date = mock.patch('app.validator.parse_date')
        self.mock_parse_date = self.patcher_parse_date.start()
        self.patcher_add_book = mock.patch('app.catalog.add_book')
        self.mock_add_book = self.patcher_add_book.start()
        self.patcher_lend_book = mock.patch('app.catalog.lend_book')
        self.mock_lend_book = self.patcher_lend_book.start()
        self.patcher_return_book = mock.patch('app.catalog.return_book')
        self.mock_return_book = self.patcher_return_book.start()
        self.patcher_list_overdue = mock.patch('app.catalog.list_overdue')
        self.mock_list_overdue = self.patcher_list_overdue.start()

        # Default behaviours
        self.mock_load.return_value = {"books": [], "loans": []}
        self.mock_save.return_value = None
        self.mock_validate_isbn.side_effect = None
        self.mock_validate_str.side_effect = None
        self.mock_parse_date.side_effect = lambda d: d
        self.mock_add_book.side_effect = lambda data, book: {"books": [book], "loans": []}
        self.mock_lend_book.side_effect = lambda data, member_id, isbn, due_date: {
            "books": data["books"],
            "loans": [{"isbn": isbn, "member_id": member_id, "due_date": due_date}],
        }
        self.mock_return_book.side_effect = lambda data, isbn: {"books": data["books"], "loans": []}
        self.mock_list_overdue.side_effect = lambda data, today: []

    def tearDown(self):
        mock.patch.stopall()

    # ---- Success cases -------------------------------------------------

    def test_cmd_add_book_success(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app._cmd_add_book('1234567890', 'The Hobbit', 'J.R.R. Tolkien', '/tmp/catalog.json')
        self.assertIn('Book added.', out.getvalue())
        self.mock_validate_isbn.assert_called_once_with('1234567890')
        self.mock_validate_str.assert_any_call('The Hobbit', 'title')
        self.mock_validate_str.assert_any_call('J.R.R. Tolkien', 'author')
        self.mock_add_book.assert_called()
        self.mock_save.assert_called()

    def test_cmd_lend_success(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app._cmd_lend('1234567890', 'M001', '2024-05-01', '/tmp/catalog.json')
        self.assertIn('Book lent to M001, due 2024-05-01.', out.getvalue())
        self.mock_validate_isbn.assert_called_once_with('1234567890')
        self.mock_validate_str.assert_called_once_with('M001', 'member_id')
        self.mock_parse_date.assert_called_once_with('2024-05-01')
        self.mock_lend_book.assert_called()
        self.mock_save.assert_called()

    def test_cmd_return_success(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app._cmd_return('1234567890', '/tmp/catalog.json')
        self.assertIn('Book returned.', out.getvalue())
        self.mock_validate_isbn.assert_called_once_with('1234567890')
        self.mock_return_book.assert_called()
        self.mock_save.assert_called()

    def test_cmd_overdue_none(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app._cmd_overdue('2024-06-01', '/tmp/catalog.json')
        self.assertIn('No overdue loans.', out.getvalue())
        self.mock_parse_date.assert_called_once_with('2024-06-01')
        self.mock_list_overdue.assert_called()

    def test_cmd_overdue_with_loans(self):
        # Make list_overdue return a loan
        self.mock_list_overdue.side_effect = lambda data, today: [
            {"isbn": "9876543210", "member_id": "M002", "due_date": "2024-04-15"}
        ]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app._cmd_overdue('2024-06-01', '/tmp/catalog.json')
        output = out.getvalue()
        self.assertIn('Overdue loans:', output)
        self.assertIn('ISBN: 9876543210, Member: M002, Due: 2024-04-15', output)

    # ---- Error handling ------------------------------------------------

    def test_cmd_add_book_invalid_isbn(self):
        self.mock_validate_isbn.side_effect = LibraryError('ISBN must be a 10 or 13 digit numeric string')
        with self.assertRaises(LibraryError) as cm:
            app._cmd_add_book('badisbn', 'Title', 'Author', '/tmp/catalog.json')
        self.assertEqual(str(cm.exception), 'ISBN must be a 10 or 13 digit numeric string')

    def test_cmd_lend_invalid_date(self):
        self.mock_parse_date.side_effect = LibraryError('date must be in ISO YYYY-MM-DD format')
        with self.assertRaises(LibraryError) as cm:
            app._cmd_lend('1234567890', 'M001', 'invalid-date', '/tmp/catalog.json')
        self.assertEqual(str(cm.exception), 'date must be in ISO YYYY-MM-DD format')

    def test_cmd_lend_empty_member_id(self):
        self.mock_validate_str.side_effect = LibraryError('member_id must be a non-empty string')
        with self.assertRaises(LibraryError) as cm:
            app._cmd_lend('1234567890', '   ', '2024-05-01', '/tmp/catalog.json')
        self.assertEqual(str(cm.exception), 'member_id must be a non-empty string')

    # ---- Endâ€‘toâ€‘end test of main ---------------------------------------

    def test_main_add_book_end_to_end(self):
        # Use a temporary directory for the catalog file path
        with tempfile.TemporaryDirectory() as td:
            catalog_path = os.path.join(td, 'catalog.json')
            os.environ['LIBRARY_CATALOG'] = catalog_path

            # Ensure storage.load_data sees an empty catalog
            self.mock_load.return_value = {"books": [], "loans": []}
            # Run main
            with contextlib.redirect_stdout(io.StringIO()) as out, \
                 contextlib.redirect_stderr(io.StringIO()) as err:
                app.main(['add-book', '1234567890123', 'Dune', 'Frank Herbert'])
            # Verify output
            self.assertIn('Book added.', out.getvalue())
            self.assertEqual(err.getvalue(), '')

            # Clean up env var
            del os.environ['LIBRARY_CATALOG']


if __name__ == '__main__':
    unittest.main()


