# lib_common.py
from __future__ import annotations

from typing import TypedDict, List


class LibraryError(Exception):
    """Base class for all library-domain errors.

    All higher-level modules raise this (or a subclass) with a clear,
    user-friendly message, e.g. ``raise LibraryError('ISBN already exists')``.
    """
    pass


class Book(TypedDict):
    """A single book record.

    Fields:
        isbn   - 10- or 13-digit numeric string (validated elsewhere)
        title  - non-empty string
        author - non-empty string
    """
    isbn: str
    title: str
    author: str


class Loan(TypedDict):
    """A loan of a book to a member.

    Fields:
        isbn       - ISBN of the loaned book (must match a Book)
        member_id  - non-empty string identifying the member
        due_date   - ISO-8601 date string ``YYYY-MM-DD`` (validated elsewhere)
    """
    isbn: str
    member_id: str
    due_date: str


class CatalogData(TypedDict):
    """Complete persisted catalogue.

    Fields:
        books - list of all `Book` entries
        loans - list of all active `Loan` entries
    """
    books: List[Book]
    loans: List[Loan]


__all__ = [
    "LibraryError",
    "Book",
    "Loan",
    "CatalogData",
]
