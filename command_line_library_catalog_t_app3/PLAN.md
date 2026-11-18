Requirements:
- Persist a catalog of books and active loans in a JSON file.
- Add a new book (ISBN, title, author) to the catalog.
- Lend a book to a member, recording member ID and due date.
- Return a previously lent book.
- List all loans that are overdue relative to a given date.
- Validate all user input and raise clear, user‑friendly errors.
- Update the JSON file after each successful modification.
- Provide a command‑line interface with subcommands: add-book, lend, return, overdue.
Shared data formats (every module must follow these EXACTLY):
* Book = {'isbn': str, 'title': str, 'author': str}
* Loan = {'isbn': str, 'member_id': str, 'due_date': str}  # due_date is ISO YYYY‑MM‑DD
* CatalogData = {'books': list[Book], 'loans': list[Loan]}
Modules (in build order; each may import only the ones before it):
1. lib_common.py - Shared exception type and data‑format type aliases.
   - class LibraryError(Exception): pass  # base class for all domain errors
2. validator.py - Validate input values and parse dates.
   - def validate_isbn(isbn: str) -> None  # raises LibraryError if not 10 or 13 digit numeric string
   - def validate_nonempty_string(value: str, field_name: str) -> None  # raises LibraryError if empty
   - def parse_date(date_str: str) -> str  # returns ISO YYYY‑MM‑DD string or raises LibraryError
   - def validate_book(book: dict) -> None  # checks required fields using above helpers, raises LibraryError
3. storage.py - Load and save the catalog JSON file.
   - def load_data(file_path: str) -> dict  # returns CatalogData, raises LibraryError on I/O or JSON errors
   - def save_data(file_path: str, data: dict) -> None  # writes CatalogData to file, raises LibraryError on failure
4. catalog.py - Business logic for books and loans.
   - def add_book(data: dict, book: dict) -> dict  # returns new CatalogData, raises LibraryError if ISBN exists
   - def lend_book(data: dict, member_id: str, isbn: str, due_date: str) -> dict  # adds a loan, raises LibraryError if book unavailable
   - def return_book(data: dict, isbn: str) -> dict  # removes loan, raises LibraryError if not currently loaned
   - def list_overdue(data: dict, today: str) -> list[dict]  # returns list of Loan dicts with due_date < today
5. app.py - Command‑line interface and program entry point.
   - def main(argv: list[str] | None = None) -> None  # parses arguments, invokes catalog functions, prints results, handles LibraryError
