from __future__ import annotations

from typing import List, Dict, Any

from common import ExpenseError, validate_expense_dict


def compute_settlements(ledger: dict) -> List[dict]:
    """
    Compute the minimal list of payments that settles all debts in the given ledger.

    Args:
        ledger: A dictionary following the Ledger format.

    Returns:
        A list of payment dictionaries, each with keys "from", "to", and "amount".

    Raises:
        ExpenseError: If the ledger is malformed or settlement is impossible.
    """
    _validate_ledger(ledger)
    balances = _net_balances(ledger)
    payments = _greedy_payments(balances)
    # Ensure required ordering: debtor alphabetically, then creditor alphabetically
    payments.sort(key=lambda p: (p["from"], p["to"]))
    return payments


def _validate_ledger(ledger: dict) -> None:
    """
    Validate the structure of a ledger.

    Raises:
        ExpenseError: If any validation rule is violated.
    """
    if not isinstance(ledger, dict):
        raise ExpenseError('ledger is malformed')
    if "people" not in ledger or "expenses" not in ledger:
        raise ExpenseError('ledger is malformed')

    people = ledger["people"]
    expenses = ledger["expenses"]

    if not isinstance(people, list) or len(people) == 0:
        raise ExpenseError('ledger is malformed')
    for name in people:
        if not isinstance(name, str) or not name.strip():
            raise ExpenseError('ledger is malformed')

    if not isinstance(expenses, list):
        raise ExpenseError('ledger is malformed')
    for exp in expenses:
        try:
            validate_expense_dict(exp, people)  # may raise ExpenseError
        except ExpenseError:
            raise ExpenseError('ledger is malformed')


def _net_balances(ledger: dict) -> Dict[str, float]:
    """
    Compute each person's net balance.

    Returns:
        A dict mapping person name to their rounded net balance.
    """
    people = ledger["people"]
    balances: Dict[str, float] = {p: 0.0 for p in people}

    for exp in ledger["expenses"]:
        amount = float(exp["amount"])
        payer = exp["payer"]
        participants = exp["participants"]
        share = amount / len(participants)

        # Add full amount to payer
        balances[payer] += amount

        # Subtract share from each participant
        for participant in participants:
            balances[participant] -= share

    # Round to 2 decimal places
    for p in balances:
        balances[p] = round(balances[p], 2)

    # Rounding each balance on its own can leave a stray cent; give it to the
    # person with the largest balance so the balances always add up to zero.
    residual = round(-sum(balances.values()), 2)
    if residual != 0.0 and balances:
        biggest = max(balances, key=lambda k: (abs(balances[k]), k))
        balances[biggest] = round(balances[biggest] + residual, 2)

    return balances


def _greedy_payments(balances: Dict[str, float]) -> List[dict]:
    """
    Generate a minimal set of payments to settle the balances.

    Assumes the sum of balances is zero within tolerance.

    Returns:
        List of payment dictionaries.
    """
    total = sum(balances.values())
    if abs(total) >= 0.01:
        raise ExpenseError('settlement impossible: balances do not sum to zero')

    # Prepare creditors and debtors
    creditors: List[tuple[str, float]] = [
        (p, b) for p, b in balances.items() if b > 0
    ]
    debtors: List[tuple[str, float]] = [
        (p, -b) for p, b in balances.items() if b < 0
    ]

    # Sort descending by amount
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    payments: List[dict] = []

    while creditors and debtors:
        cred_name, cred_amount = creditors[0]
        debt_name, debt_amount = debtors[0]

        pay = min(cred_amount, debt_amount)
        payments.append({
            "from": debt_name,
            "to": cred_name,
            "amount": round(pay, 2)
        })

        cred_amount -= pay
        debt_amount -= pay

        # Update lists
        if round(cred_amount, 2) == 0.0:
            creditors.pop(0)
        else:
            creditors[0] = (cred_name, round(cred_amount, 2))

        if round(debt_amount, 2) == 0.0:
            debtors.pop(0)
        else:
            debtors[0] = (debt_name, round(debt_amount, 2))

    return payments
