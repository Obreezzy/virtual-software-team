# Requested changes (not applied)

CHANGES NEEDED
- Use `Decimal` (not `float`) for all monetary values, including input validation and storage, to avoid rounding errors.
- Validate and sanitize the inventory file contents after loading (e.g., type checks, range checks) to prevent crashes on corrupted data.
- Catch broader I/O/parsing errors (e.g., `json.JSONDecodeError`, `OSError`) when loading/saving and handle them gracefully instead of letting a traceback escape.
- Impose reasonable limits on numeric inputs (e.g., maximum quantity/price) to avoid absurdly large values that could cause overflow or performance issues.
- Ensure that all user‑visible error paths return a clean message without exposing internal exception details.
