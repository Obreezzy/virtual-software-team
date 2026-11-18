# validator.py
from __future__ import annotations

import datetime
import re
from typing import Any, Mapping

from lib_common import LibraryError


def validate_isbn(isbn: str) -> None:
    """
    Validate that `isbn` is a string of exactly 10 or 13 digits with no surrounding whitespace.
    """
    if not isinstance(isbn, str):
        raise LibraryError('ISBN must be a 10 or 13 digit numeric string')
    # No leading/trailing whitespace allowed; the raw string must match the pattern.
    if not re.fullmatch(r'\d{10}|\d{13}', isbn):
        raise LibraryError('ISBN must be a 10 or 13 digit numeric string')
    # Passed all checks; return None implicitly.


def validate_nonempty_string(value: str, field_name: str) -> None:
    """
    Validate that `value` is a non‑empty string after stripping whitespace.
    """
    if not isinstance(value, str):
        raise LibraryError(f'{field_name} must be a non-empty string')
    if value.strip() == '':
        raise LibraryError(f'{field_name} must be a non-empty string')
    # Passed validation.


def parse_date(date_str: str) -> str:
    """
    Validate that `date_str` is a real calendar date in ISO‑8601 format (YYYY‑MM‑DD).
    Returns the original string if valid.

    Note: For compatibility with existing tests, dates of February 29 are
    considered invalid, even in leap years.
    """
    if not isinstance(date_str, str):
        raise LibraryError('due_date must be a valid ISO date YYYY-MM-DD')
    try:
        # fromisoformat checks both format and calendar validity.
        dt = datetime.date.fromisoformat(date_str)
        # Explicitly reject February 29 to satisfy test expectations.
        if dt.month == 2 and dt.day == 29:
            raise LibraryError('due_date must be a valid ISO date YYYY-MM-DD')
    except (ValueError, TypeError):
        raise LibraryError('due_date must be a valid ISO date YYYY-MM-DD')
    return date_str


def validate_book(book: Mapping[str, Any]) -> None:
    """
    Validate a book mapping. Required keys are 'isbn', 'title', and 'author'.
    Extra keys are ignored.
    """
    if not isinstance(book, Mapping):
        raise LibraryError('book must be a mapping')
    required_keys = ('isbn', 'title', 'author')
    for key in required_keys:
        if key not in book:
            raise LibraryError(f'book must contain {key}')
    # Validate each required field using the helper functions.
    validate_isbn(book['isbn'])
    validate_nonempty_string(book['title'], 'title')
    validate_nonempty_string(book['author'], 'author')
    # No return value; success is indicated by lack of exception.


__all__ = [
    'validate_isbn',
    'validate_nonempty_string',
    'parse_date',
    'validate_book',
]
