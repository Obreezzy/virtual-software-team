# Requested changes (not applied)

CHANGES NEEDED
- Unhandled exceptions (e.g., from `storage.load_data`, `storage.save_data`, or logic functions) will bubble up and produce a traceback, violating the “never show a traceback to its user” rule. Add a generic `except Exception` block that reports a user‑friendly error and exits cleanly.
- No validation of the data structure returned by `storage.load_data`. If the file is corrupted and the data is not a dict, later code will raise a `TypeError`. Verify the loaded data’s type and shape before using it.
- Errors from `storage.save_data` are not caught, so a failure to write the file could abort the program with a traceback and potentially leave data unsaved. Wrap the save calls in a try/except and report a clear error.
- The helper `_ensure_iso_date` returns the original string even after parsing; while functional, it silently accepts dates like `"2023-02-30"` (which `fromisoformat` would reject, but any further date‑related logic might expect a `datetime.date`). Consider returning a `datetime.date` object to avoid downstream misuse.
- The `except (KeyboardInterrupt, EOFError)` block exits with status 0 in non‑interactive mode, which may mask an intentional interruption as a successful run. Use a distinct non‑zero exit code for user‑initiated aborts.
