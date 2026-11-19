import unittest
from unittest import mock
import contextlib
import io

import settlement as app  # the settlement module under test


class TestSettlement(unittest.TestCase):
    def setUp(self):
        # Patch the expense validator so that all expense dicts in our tests are accepted.
        patcher = mock.patch('settlement.validate_expense_dict', autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_validate = patcher.start()
        self.mock_validate.side_effect = lambda exp, people: None

    def test_simple_two_person_split(self):
        ledger = {
            "people": ["Alice", "Bob"],
            "expenses": [
                {
                    "payer": "Alice",
                    "amount": 30.0,
                    "participants": ["Alice", "Bob"],
                    "description": "Dinner",
                }
            ],
        }
        expected = [{"from": "Bob", "to": "Alice", "amount": 15.0}]
        result = app.compute_settlements(ledger)
        self.assertEqual(result, expected)

    def test_three_people_uneven_shares(self):
        ledger = {
            "people": ["A", "B", "C"],
            "expenses": [
                {
                    "payer": "A",
                    "amount": 60.0,
                    "participants": ["A", "B", "C"],
                    "description": "Trip",
                },
                {
                    "payer": "B",
                    "amount": 30.0,
                    "participants": ["B", "C"],
                    "description": "Museum",
                },
            ],
        }
        # After alphabetical ordering of debtors then creditors
        expected = [
            {"from": "B", "to": "A", "amount": 5.0},
            {"from": "C", "to": "A", "amount": 35.0},
        ]
        result = app.compute_settlements(ledger)
        self.assertEqual(result, expected)

    def test_already_settled(self):
        ledger = {
            "people": ["X", "Y"],
            "expenses": [
                {
                    "payer": "X",
                    "amount": 20.0,
                    "participants": ["X"],
                    "description": "Solo",
                },
                {
                    "payer": "Y",
                    "amount": 20.0,
                    "participants": ["Y"],
                    "description": "Solo",
                },
            ],
        }
        result = app.compute_settlements(ledger)
        self.assertEqual(result, [])

    def test_malformed_missing_people_key(self):
        ledger = {"expenses": []}
        with self.assertRaises(app.ExpenseError) as cm:
            app.compute_settlements(ledger)
        self.assertEqual(str(cm.exception), "ledger is malformed")

    def test_malformed_invalid_expense(self):
        # Make the validator raise an ExpenseError for a specific expense
        def side_effect(exp, people):
            if exp.get("description") == "Bad":
                raise app.ExpenseError("bad expense")
        self.mock_validate.side_effect = side_effect

        ledger = {
            "people": ["Alice"],
            "expenses": [
                {
                    "payer": "Alice",
                    "amount": 10.0,
                    "participants": ["Alice"],
                    "description": "Bad",
                }
            ],
        }
        with self.assertRaises(app.ExpenseError) as cm:
            app.compute_settlements(ledger)
        self.assertEqual(str(cm.exception), "ledger is malformed")

    def test_greedy_payments_impossible_settlement(self):
        # Directly test the private helper that checks the total balance tolerance.
        balances = {"A": 1.00, "B": -0.98}  # sum = 0.02 > 0.01 tolerance
        with self.assertRaises(app.ExpenseError) as cm:
            app._greedy_payments(balances)
        self.assertEqual(
            str(cm.exception),
            "settlement impossible: balances do not sum to zero",
        )

    def test_payment_ordering_alphabetical(self):
        # Ledger that yields two payments; we verify ordering by debtor then creditor.
        ledger = {
            "people": ["Bob", "Carol", "Alice"],
            "expenses": [
                {
                    "payer": "Alice",
                    "amount": 90.0,
                    "participants": ["Alice", "Bob", "Carol"],
                    "description": "Trip",
                }
            ],
        }
        # Net balances: Alice +60, Bob -30, Carol -30
        expected = [
            {"from": "Bob", "to": "Alice", "amount": 30.0},
            {"from": "Carol", "to": "Alice", "amount": 30.0},
        ]
        result = app.compute_settlements(ledger)
        self.assertEqual(result, expected)

    def test_end_to_end_example_session(self):
        # Simulate a simple interactive session that would call compute_settlements.
        # Here we just call the function and capture its printed representation.
        ledger = {
            "people": ["Alice", "Bob"],
            "expenses": [
                {
                    "payer": "Alice",
                    "amount": 30.0,
                    "participants": ["Alice", "Bob"],
                    "description": "Dinner",
                }
            ],
        }
        with contextlib.redirect_stdout(io.StringIO()) as fake_out:
            payments = app.compute_settlements(ledger)
            for p in payments:
                print(f"{p['from']} pays {p['to']}: ${p['amount']:.2f}")

        output = fake_out.getvalue()
        self.assertIn("Bob pays Alice: $15.00", output)


if __name__ == "__main__":
    unittest.main()
