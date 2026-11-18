import unittest
from copy import deepcopy

from catalog import (
    add_book,
    lend_book,
    return_book,
    list_overdue,
    _index_of_book,
    _index_of_loan,
)
from lib_common import LibraryError


class TestCatalog(unittest.TestCase):
    # ------------------------------------------------------------------
    # add_book
    # ------------------------------------------------------------------
    def test_add_book_success(self):
        data = {"books": [], "loans": []}
        book = {"isbn": "1234567890", "title": "Python 101", "author": "Guido"}
        result = add_book(data, book)
        expected = {
            "books": [book],
            "loans": [],
        }
        self.assertEqual(result, expected)
        # original data must stay unchanged (purity)
        self.assertEqual(data, {"books": [], "loans": []})

    def test_add_book_duplicate_isbn(self):
        data = {
            "books": [{"isbn": "1234567890", "title": "X", "author": "Y"}],
            "loans": [],
        }
        book = {"isbn": "1234567890", "title": "New", "author": "Z"}
        with self.assertRaises(LibraryError) as cm:
            add_book(data, book)
        self.assertEqual(str(cm.exception), "ISBN already exists in catalog")

    # ------------------------------------------------------------------
    # lend_book
    # ------------------------------------------------------------------
    def test_lend_book_success(self):
        data = {
            "books": [{"isbn": "1111111111", "title": "A", "author": "B"}],
            "loans": [],
        }
        result = lend_book(data, member_id="M001", isbn="1111111111", due_date="2025-01-15")
        expected = {
            "books": [{"isbn": "1111111111", "title": "A", "author": "B"}],
            "loans": [
                {"isbn": "1111111111", "member_id": "M001", "due_date": "2025-01-15"}
            ],
        }
        self.assertEqual(result, expected)
        # ensure original data unchanged
        self.assertEqual(
            data,
            {
                "books": [{"isbn": "1111111111", "title": "A", "author": "B"}],
                "loans": [],
            },
        )

    def test_lend_book_already_loaned(self):
        data = {
            "books": [{"isbn": "1111111111", "title": "A", "author": "B"}],
            "loans": [
                {"isbn": "1111111111", "member_id": "M001", "due_date": "2025-01-15"}
            ],
        }
        with self.assertRaises(LibraryError) as cm:
            lend_book(data, member_id="M002", isbn="1111111111", due_date="2025-02-01")
        self.assertEqual(str(cm.exception), "ISBN already loaned")

    def test_lend_book_invalid_member_id(self):
        data = {"books": [], "loans": []}
        with self.assertRaises(LibraryError) as cm:
            lend_book(data, member_id="", isbn="1234567890", due_date="2025-01-01")
        self.assertEqual(str(cm.exception), "member_id must be a non-empty string")

    def test_lend_book_invalid_isbn(self):
        data = {"books": [], "loans": []}
        with self.assertRaises(LibraryError) as cm:
            lend_book(data, member_id="M001", isbn="abc", due_date="2025-01-01")
        self.assertEqual(str(cm.exception), "ISBN must be a 10 or 13 digit numeric string")

    def test_lend_book_invalid_due_date(self):
        data = {"books": [], "loans": []}
        with self.assertRaises(LibraryError) as cm:
            lend_book(data, member_id="M001", isbn="1234567890", due_date="2025-02-30")
        self.assertEqual(str(cm.exception), "due_date must be a valid date in YYYY-MM-DD format")

    # ------------------------------------------------------------------
    # return_book
    # ------------------------------------------------------------------
    def test_return_book_success(self):
        data = {
            "books": [{"isbn": "2222222222", "title": "C", "author": "D"}],
            "loans": [
                {"isbn": "2222222222", "member_id": "M003", "due_date": "2024-12-01"}
            ],
        }
        result = return_book(data, isbn="2222222222")
        expected = {"books": [{"isbn": "2222222222", "title": "C", "author": "D"}], "loans": []}
        self.assertEqual(result, expected)

    def test_return_book_not_loaned(self):
        data = {
            "books": [{"isbn": "3333333333", "title": "E", "author": "F"}],
            "loans": [],
        }
        with self.assertRaises(LibraryError) as cm:
            return_book(data, isbn="3333333333")
        self.assertEqual(str(cm.exception), "Book with ISBN 3333333333 is not currently loaned")

    def test_return_book_invalid_isbn(self):
        data = {"books": [], "loans": []}
        with self.assertRaises(LibraryError) as cm:
            return_book(data, isbn="not-an-isbn")
        self.assertEqual(str(cm.exception), "ISBN must be a 10 or 13 digit numeric string")

    # ------------------------------------------------------------------
    # list_overdue
    # ------------------------------------------------------------------
    def test_list_overdue_success(self):
        data = {
            "books": [],
            "loans": [
                {"isbn": "4444444444", "member_id": "M004", "due_date": "2025-02-28"},
                {"isbn": "5555555555", "member_id": "M005", "due_date": "2025-03-02"},
            ],
        }
        result = list_overdue(data, today="2025-03-01")
        expected = [
            {"isbn": "4444444444", "member_id": "M004", "due_date": "2025-02-28"}
        ]
        self.assertEqual(result, expected)
        # ensure a new list is returned
        self.assertIsNot(result, data["loans"])

    def test_list_overdue_invalid_today(self):
        data = {"books": [], "loans": []}
        with self.assertRaises(LibraryError) as cm:
            list_overdue(data, today="2025-02-30")
        self.assertEqual(str(cm.exception), "today must be a valid date in YYYY-MM-DD format")

    # ------------------------------------------------------------------
    # private helpers (basic sanity)
    # ------------------------------------------------------------------
    def test_index_helpers(self):
        books = [
            {"isbn": "111", "title": "A", "author": "B"},
            {"isbn": "222", "title": "C", "author": "D"},
        ]
        loans = [
            {"isbn": "111", "member_id": "M1", "due_date": "2025-01-01"},
        ]
        self.assertEqual(_index_of_book(books, "222"), 1)
        self.assertIsNone(_index_of_book(books, "999"))
        self.assertEqual(_index_of_loan(loans, "111"), 0)
        self.assertIsNone(_index_of_loan(loans, "222"))


if __name__ == "__main__":
    unittest.main()
