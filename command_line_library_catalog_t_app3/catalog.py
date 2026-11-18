# catalog.py
from __future__ import annotations

from typing import List, Optional

from lib_common import LibraryError, Book, Loan, CatalogData
from validator import (
    validate_isbn,
    validate_nonempty_string,
    parse_date,
    validate_book,
)
from lib_common import LibraryError


# ----------------------------------------------------------------------
# Private helpers (not part of the public API)
# ----------------------------------------------------------------------
def _index_of_book(books: List[Book], isbn: str) -> Optional[int]:
    """Return the list index of the book with *isbn* or ``None`` if absent."""
    for i, b in enumerate(books):
        if b.get("isbn") == isbn:
            return i
    return None


def _index_of_loan(loans: List[Loan], isbn: str) -> Optional[int]:
    """Return the list index of the loan with *isbn* or ``None`` if absent."""
    for i, l in enumerate(loans):
        if l.get("isbn") == isbn:
            return i
    return None


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def add_book(data: CatalogData, book: Book) -> CatalogData:
    """
    Add a new book to the catalog.

    Steps
    -----
    1. ``validate_book(book)`` - raises ``LibraryError`` with the exact
       message from the validator if any field is missing or malformed.
    2. ``validate_isbn(book['isbn'])`` - ensures a 10- or 13-digit numeric
       string.
    3. Scan ``data['books']`` for a matching ``isbn``.
       * If found -> raise ``LibraryError('ISBN already exists in catalog')``.
    4. Return a **new** ``CatalogData`` instance (the original is left
       untouched) where ``book`` is appended to ``books`` and ``loans``
       is copied unchanged.
    """
    # validation
    validate_book(book)
    validate_isbn(book["isbn"])

    # duplicate check
    if _index_of_book(data["books"], book["isbn"]) is not None:
        raise LibraryError("ISBN already exists in catalog")

    # create new catalog
    new_books = list(data["books"])
    new_books.append(book)
    new_loans = list(data["loans"])
    return {"books": new_books, "loans": new_loans}


def lend_book(
    data: CatalogData,
    member_id: str,
    isbn: str,
    due_date: str,
) -> CatalogData:
    """
    Record a loan of a book to a member.

    Validation & rules
    ------------------
    * ``validate_nonempty_string(member_id, 'member_id')`` - raises
      ``LibraryError('member_id must be a non-empty string')``.
    * ``validate_isbn(isbn)`` - raises ``LibraryError('ISBN must be a 10 or 13 digit numeric string')``.
    * ``parse_date(due_date)`` - returns an ISO ``YYYY-MM-DD`` string or
      raises ``LibraryError('due_date must be a valid date in YYYY-MM-DD format')``.
    * The book must exist in ``data['books']``; otherwise raise
      ``LibraryError('Book with ISBN {isbn} not found')``.
    * The book must not already be loaned (no entry in ``data['loans']`` with the same ISBN);
      otherwise raise ``LibraryError('ISBN already loaned')``.
    """
    # validations
    validate_nonempty_string(member_id, "member_id")
    validate_isbn(isbn)
    parsed_due = _parse_date_with_context("due_date", due_date)

    # book existence
    if _index_of_book(data["books"], isbn) is None:
        raise LibraryError(f"Book with ISBN {isbn} not found")

    # loan existence
    if _index_of_loan(data["loans"], isbn) is not None:
        raise LibraryError("ISBN already loaned")

    # create new loan entry
    new_loan: Loan = {"isbn": isbn, "member_id": member_id, "due_date": parsed_due}
    new_loans = list(data["loans"])
    new_loans.append(new_loan)

    # return new catalog (books unchanged)
    new_books = list(data["books"])
    return {"books": new_books, "loans": new_loans}


def return_book(data: CatalogData, isbn: str) -> CatalogData:
    """
    Remove a loan, marking the book as returned.

    Validation & rules
    ------------------
    * ``validate_isbn(isbn)`` - same error message as in ``lend_book``.
    * The loan must exist; otherwise raise
      ``LibraryError('Book with ISBN {isbn} is not currently loaned')``.
    """
    # validation
    validate_isbn(isbn)

    # locate loan
    loan_idx = _index_of_loan(data["loans"], isbn)
    if loan_idx is None:
        raise LibraryError(f"Book with ISBN {isbn} is not currently loaned")

    # remove loan
    new_loans = list(data["loans"])
    del new_loans[loan_idx]

    # return new catalog (books unchanged)
    new_books = list(data["books"])
    return {"books": new_books, "loans": new_loans}


def list_overdue(data: CatalogData, today: str) -> List[Loan]:
    """
    List all loans whose ``due_date`` is earlier than ``today``.

    * ``parse_date(today)`` validates the supplied date string.
    * Comparison is lexical because ISO ``YYYY-MM-DD`` sorts correctly.
    * The function returns a **new list** (no reference to the internal
      ``data['loans']`` list) containing the full ``Loan`` dicts that are
      overdue.
    """
    parsed_today = _parse_date_with_context("today", today)

    overdue: List[Loan] = []
    for loan in data["loans"]:
        if loan["due_date"] < parsed_today:
            overdue.append(loan)
    return overdue


def _parse_date_with_context(field_name: str, date_str: str) -> str:
    """
    Parse a date string using ``validator.parse_date`` but ensure that
    any ``LibraryError`` raised uses the exact wording required by the
    public API for the given *field_name*.

    The underlying validator may use a slightly different message (e.g.
    "must be a valid ISO date").  This helper normalises the message to
    ``"{field_name} must be a valid date in YYYY-MM-DD format"``.
    """
    try:
        return parse_date(date_str)
    except LibraryError as exc:
        # Preserve the original exception type but replace the message.
        raise LibraryError(f"{field_name} must be a valid date in YYYY-MM-DD format") from None
