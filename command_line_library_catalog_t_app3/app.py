import argparse
import json
import os
import sys
from pathlib import Path

import catalog
import lib_common
import storage
import validator
from typing import Any, cast


def _print_error(msg: str) -> None:
    """Write an error message to stderr."""
    sys.stderr.write(msg + "\n")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse commandâ€‘line arguments."""
    parser = argparse.ArgumentParser(prog="library-catalog")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add-book
    add_parser = subparsers.add_parser("add-book", help="Add a new book")
    add_parser.add_argument("isbn", type=str, help="ISBN of the book")
    add_parser.add_argument("title", type=str, help="Title of the book")
    add_parser.add_argument("author", type=str, help="Author of the book")

    # lend
    lend_parser = subparsers.add_parser("lend", help="Lend a book")
    lend_parser.add_argument("isbn", type=str, help="ISBN of the book")
    lend_parser.add_argument("member_id", type=str, help="Member identifier")
    lend_parser.add_argument("due", type=str, help="Due date (YYYYâ€‘MMâ€‘DD)")

    # return
    return_parser = subparsers.add_parser("return", help="Return a book")
    return_parser.add_argument("isbn", type=str, help="ISBN of the book")

    # overdue
    overdue_parser = subparsers.add_parser("overdue", help="List overdue loans")
    overdue_parser.add_argument("today", type=str, help="Today's date (YYYYâ€‘MMâ€‘DD)")

    return parser.parse_args(argv)


def _load_catalog(data_path: str) -> lib_common.CatalogData:
    """Load the catalog, converting I/O/JSON errors to LibraryError.
    If the file does not exist, start with an empty catalog structure.
    """
    try:
        return storage.load_data(data_path)
    except FileNotFoundError:
        # No existing file â€“ start with a clean catalog.
        empty: lib_common.CatalogData = {"books": [], "loans": []}
        return empty
    except (OSError, json.JSONDecodeError):
        # Attempt to back up the corrupt file; if that fails, surface a clear message.
        try:
            storage._backup_corrupt(Path(data_path))
        except Exception:
            raise lib_common.LibraryError(
                "Failed to load catalog data; could not back up corrupt file"
            ) from None
        raise lib_common.LibraryError("Failed to load catalog data") from None
    except lib_common.LibraryError:
        # Propagate libraryâ€‘level errors unchanged.
        raise


def _cmd_add_book(isbn: str, title: str, author: str, data_path: str) -> None:
    """Add a new book to the catalog."""
    _validate_call(validator.validate_isbn, isbn)
    _validate_call(validator.validate_nonempty_string, title, "title")
    _validate_call(validator.validate_nonempty_string, author, "author")

    catalog_data = _load_catalog(data_path)
    book: lib_common.Book = {"isbn": isbn, "title": title, "author": author}
    new_data = catalog.add_book(catalog_data, book)

    _ensure_parent_dir(data_path)
    try:
        storage.save_data(data_path, new_data)
    except OSError:
        raise lib_common.LibraryError("Failed to save catalog data") from None

    print("Book added.")


def _cmd_lend(isbn: str, member_id: str, due: str, data_path: str) -> None:
    """Lend a book to a member."""
    _validate_call(validator.validate_isbn, isbn)
    _validate_call(validator.validate_nonempty_string, member_id, "member_id")
    try:
        due_date = validator.parse_date(due)
    except lib_common.LibraryError as exc:
        # Normalise validator dateâ€‘format errors to the designâ€‘specified message.
        msg = str(exc)
        if "ISO" in msg or "date" in msg:
            raise lib_common.LibraryError("date must be in ISO YYYY-MM-DD format") from None
        raise
    catalog_data = _load_catalog(data_path)
    new_data = catalog.lend_book(catalog_data, member_id=member_id, isbn=isbn, due_date=due_date)

    _ensure_parent_dir(data_path)
    try:
        storage.save_data(data_path, new_data)
    except OSError:
        raise lib_common.LibraryError("Failed to save catalog data") from None

    print(f"Book lent to {member_id}, due {due_date}.")


def _cmd_return(isbn: str, data_path: str) -> None:
    """Return a previously lent book."""
    _validate_call(validator.validate_isbn, isbn)

    catalog_data = _load_catalog(data_path)
    new_data = catalog.return_book(catalog_data, isbn)

    _ensure_parent_dir(data_path)
    try:
        storage.save_data(data_path, new_data)
    except OSError:
        raise lib_common.LibraryError("Failed to save catalog data") from None

    print("Book returned.")


def _cmd_overdue(today: str, data_path: str) -> None:
    """List all overdue loans as of today."""
    try:
        today_date = validator.parse_date(today)
    except lib_common.LibraryError as exc:
        msg = str(exc)
        if "ISO" in msg or "date" in msg:
            raise lib_common.LibraryError("date must be in ISO YYYY-MM-DD format") from None
        raise
    catalog_data = _load_catalog(data_path)
    overdue_loans = catalog.list_overdue(catalog_data, today_date)

    if not overdue_loans:
        print("No overdue loans.")
        return

    print("Overdue loans:")
    for loan in overdue_loans:
        print(
            f"ISBN: {loan['isbn']}, Member: {loan['member_id']}, Due: {loan['due_date']}"
        )


def main(argv: list[str] | None = None) -> None:
    """Entry point for the libraryâ€‘catalog command line program."""
    if argv is None:
        argv = sys.argv[1:]

    args = _parse_args(argv)

    # Determine data file location
    env_path = os.getenv("LIBRARY_CATALOG")
    if env_path:
        data_path = env_path
    else:
        data_path = str(Path.home() / ".library_catalog.json")

    try:
        if args.command == "add-book":
            _cmd_add_book(args.isbn, args.title, args.author, data_path)
        elif args.command == "lend":
            _cmd_lend(args.isbn, args.member_id, args.due, data_path)
        elif args.command == "return":
            _cmd_return(args.isbn, data_path)
        elif args.command == "overdue":
            _cmd_overdue(args.today, data_path)
        else:
            _print_error("Invalid option")
            sys.exit(1)
    except lib_common.LibraryError as e:
        _print_error(str(e))
        sys.exit(1)




def _ensure_parent_dir(data_path: str) -> None:
    """Create the parent directory for the catalog file if it does not exist."""
    Path(data_path).parent.mkdir(parents=True, exist_ok=True)


def _validate_call(func, *args) -> None:
    """Run a validator function, converting any nonâ€‘LibraryError exception to LibraryError."""
    try:
        func(*args)
    except lib_common.LibraryError:
        raise
    except Exception as exc:
        raise lib_common.LibraryError(str(exc))

if __name__ == "__main__":
    main()


