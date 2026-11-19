Requirements:
- Record people who share expenses.
- Add an expense with payer, amount, participants and description.
- Persist data in a JSON file between runs.
- Compute a minimal set of payments that settles all debts.
- Handle invalid input by raising a clear exception, never crashing.
- Command‑line interface supports adding people, adding expenses, and showing settlements.
- Data is never lost; file is written atomically.
- All library modules are pure and produce no console output.
Shared data formats (every module must follow these EXACTLY):
* Ledger = {'people': List[str], 'expenses': List[Expense]}
* Expense = {'payer': str, 'amount': float, 'participants': List[str], 'description': str}
* Payment = {'from': str, 'to': str, 'amount': float}
Modules (in build order; each may import only the ones before it):
1. common.py - Defines shared exception and simple validation helpers.
   - def validate_amount(amount: float) -> None  # raises ExpenseError if amount <= 0
2. storage.py - Load and save the ledger JSON file.
   - def load_ledger(path: str) -> dict  # returns Ledger, raises ExpenseError on I/O or malformed JSON
   - def save_ledger(path: str, ledger: dict) -> None  # writes Ledger atomically, raises ExpenseError on failure
3. people.py - Manage the list of participants in the ledger.
   - def add_person(ledger: dict, name: str) -> None  # adds name to ledger['people'], raises ExpenseError on duplicate or empty
   - def list_people(ledger: dict) -> List[str]  # returns a sorted copy of ledger['people']
4. expenses.py - Add and list expense records.
   - def add_expense(ledger: dict, payer: str, amount: float, participants: List[str], description: str) -> None  # validates and appends an Expense, raises ExpenseError on errors
   - def list_expenses(ledger: dict) -> List[dict]  # returns a shallow copy of ledger['expenses']
5. settlement.py - Calculate the minimal payment plan to settle all debts.
   - def compute_settlements(ledger: dict) -> List[dict]  # returns a list of Payments, raises ExpenseError if settlement impossible
6. app.py - Command‑line interface, argument parsing and user interaction.
   - def main(argv: List[str] | None = None) -> None  # parses commands, uses other modules, prints results, handles ExpenseError
