import unittest
import types
import sys
import importlib

# Import the module under test
lib_common = importlib.import_module("lib_common")


class TestLibCommon(unittest.TestCase):
    def test_all_exports(self):
        """__all__ should contain exactly the public symbols."""
        expected = ["LibraryError", "Book", "Loan", "CatalogData"]
        self.assertListEqual(lib_common.__all__, expected)
        # Ensure each exported name exists in the module namespace
        for name in expected:
            self.assertTrue(hasattr(lib_common, name), f"{name} missing from lib_common")

    def test_library_error_message(self):
        """LibraryError should preserve the message passed at raise time."""
        msg = "ISBN already exists"
        with self.assertRaises(lib_common.LibraryError) as cm:
            raise lib_common.LibraryError(msg)
        self.assertEqual(str(cm.exception), msg)

    def test_library_error_is_exception_subclass(self):
        """LibraryError must be a subclass of Exception."""
        self.assertTrue(issubclass(lib_common.LibraryError, Exception))

    def test_book_structure(self):
        """A Book TypedDict should match the example shape."""
        example_book = {
            "isbn": "9780306406157",
            "title": "The Art of Computer Programming",
            "author": "Donald Knuth",
        }
        # TypedDicts are just dicts at runtime; instantiate directly
        book: lib_common.Book = example_book
        self.assertDictEqual(book, example_book)

    def test_loan_structure(self):
        """A Loan TypedDict should match the example shape."""
        example_loan = {
            "isbn": "9780306406157",
            "member_id": "M001",
            "due_date": "2024-12-01",
        }
        loan: lib_common.Loan = example_loan
        self.assertDictEqual(loan, example_loan)

    def test_catalogdata_empty(self):
        """An empty catalogue should match the example empty state."""
        empty_catalog = {"books": [], "loans": []}
        catalog: lib_common.CatalogData = empty_catalog
        self.assertDictEqual(catalog, empty_catalog)

    def test_catalogdata_with_one_entry(self):
        """A catalogue with one book and one loan should match the example."""
        example_catalog = {
            "books": [
                {
                    "isbn": "9780306406157",
                    "title": "The Art of Computer Programming",
                    "author": "Donald Knuth",
                }
            ],
            "loans": [
                {
                    "isbn": "9780306406157",
                    "member_id": "M001",
                    "due_date": "2024-12-01",
                }
            ],
        }
        catalog: lib_common.CatalogData = example_catalog
        self.assertDictEqual(catalog, example_catalog)


if __name__ == "__main__":
    unittest.main()
