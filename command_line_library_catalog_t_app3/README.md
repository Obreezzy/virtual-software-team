# Library Catalog CLI

A tiny command-line tool that keeps a catalog of books and tracks active loans.
All data is stored in a single JSON file that is updated after every successful
operation.

## Files

| File | Purpose |
|------|---------|
| `lib_common.py` | Defines the base `LibraryError` exception and type aliases used across the project. |
| `validator.py` | Helper functions that validate ISBNs, non-empty strings, and parse ISO dates. |
| `storage.py` | Load and save the JSON catalog (`CatalogData`). |
| `catalog.py` | Core business logic: add books, lend books, return books, list overdue loans. |
| `app.py` | Command-line interface that wires everything together. |
| `test_*.py` | Unit tests for each module. Run with `python -m unittest`. |

## Data format

The JSON file always follows the same schema:

```json
{
  "books": [
    {"isbn": "string", "title": "string", "author": "string"}
  ],
  "loans": [
    {"isbn": "string", "member_id": "string", "due_date": "YYYY-MM-DD"}
  ]
}
```

* `Book` - a dictionary with keys `isbn`, `title`, `author`.
* `Loan` - a dictionary with keys `isbn`, `member_id`, `due_date` (ISO date).

## Installation

The program uses only the Python standard library. No external packages are required.

```bash
# Clone / copy the repository containing the files
# (the files are already in the current directory)
python -V   # must be Python 3.8 or newer
```

## Usage

Run the program with:

```bash
python app.py <subcommand> [options]
```

### Subcommands

| Subcommand | Description | Required arguments |
|------------|-------------|--------------------|
| `add-book` | Add a new book to the catalog. | `--isbn ISBN --title TITLE --author AUTHOR` |
| `lend`      | Lend a book to a member. | `--isbn ISBN --member-id MEMBER_ID --due DATE` |
| `return`    | Return a previously lent book. | `--isbn ISBN` |
| `overdue`   | List all loans that are overdue relative to a given date. | `--today DATE` |

All subcommands also accept `--data-path PATH` (default: `catalog.json`) to specify where the JSON file is stored.

### Example session

```bash
# 1. Add a book
python app.py add-book \
    --isbn 9780132350884 \
    --title "Clean Code" \
    --author "Robert C. Martin"

# 2. Lend the book to member M123, due in 7 days
python app.py lend \
    --isbn 9780132350884 \
    --member-id M123 \
    --due 2024-12-01

# 3. Check for overdue loans as of 2024-12-02
python app.py overdue --today 2024-12-02
# Output (example):
# ISBN: 9780132350884, Member: M123, Due: 2024-12-01

# 4. Return the book
python app.py return --isbn 9780132350884
```

All commands print a short success message or, in case of an error, a clear
message without a Python traceback.

## Running the tests

Unit tests are provided for every module. Execute them with the standard
unittest runner:

```bash
python -m unittest
```

The test suite will automatically discover all files named `test_*.py` and
report any failures.

## Error handling

All user-visible errors raise `LibraryError` and are caught by `app.py`. The
program prints only the error message, e.g.:

```
Error: ISBN must be a 10 or 13 digit numeric string.
```

No traceback is shown to the end user, and the JSON file is never left in a
corrupted state.

## License

This project is released into the public domain. Feel free to copy, modify,
or redistribute it.