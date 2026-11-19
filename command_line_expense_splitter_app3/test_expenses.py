import unittest
from expenses import add_expense, list_expenses, ExpenseError

class TestExpenses(unittest.TestCase):
    def setUp(self):
        # Base ledger used in all tests
        self.ledger = {'people': ['Alice', 'Bob', 'Carol'], 'expenses': []}

    def test_add_expense_success(self):
        # Worked example 1
        add_expense(self.ledger, 'Alice', 30.0, ['Bob', 'Carol'], 'Dinner')
        expected = [
            {
                'payer': 'Alice',
                'amount': 30.0,
                'participants': ['Bob', 'Carol'],
                'description': 'Dinner',
            }
        ]
        self.assertEqual(self.ledger['expenses'], expected)

    def test_list_expenses_shallow_copy(self):
        # Populate ledger first
        add_expense(self.ledger, 'Alice', 30.0, ['Bob', 'Carol'], 'Dinner')
        expenses_copy = list_expenses(self.ledger)

        # The returned list must be a new object
        self.assertIsNot(expenses_copy, self.ledger['expenses'])
        # The dicts inside must be the same objects (shallow copy)
        self.assertIs(expenses_copy[0], self.ledger['expenses'][0])

        # Mutating the copy's list should not affect the ledger
        expenses_copy.append({'payer': 'Bob', 'amount': 10.0,
                             'participants': ['Alice'], 'description': 'Snack'})
        self.assertEqual(len(self.ledger['expenses']), 1)
        self.assertEqual(len(expenses_copy), 2)

    def test_add_expense_invalid_payer(self):
        # Worked example 3
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, 'Dave', 10.0, ['Alice'], 'Snack')
        self.assertEqual(str(cm.exception), 'payer must be an existing person')

    def test_add_expense_negative_amount(self):
        # Worked example 4
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, 'Alice', -5.0, ['Bob'], 'Refund')
        self.assertEqual(str(cm.exception), 'amount must be positive')

    def test_add_expense_nan_amount(self):
        import math
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, 'Alice', math.nan, ['Bob'], 'Weird')
        self.assertEqual(str(cm.exception), 'amount must be positive')

    def test_add_expense_empty_participants(self):
        # Worked example 5
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, 'Alice', 10.0, [], 'Coffee')
        self.assertEqual(str(cm.exception),
                         'participants must be non-empty list of existing people')

    def test_add_expense_participant_not_in_people(self):
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, 'Alice', 10.0, ['Dave'], 'Lunch')
        self.assertEqual(str(cm.exception),
                         'participants must be non-empty list of existing people')

    def test_add_expense_empty_description(self):
        # Worked example 6
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, 'Alice', 10.0, ['Bob'], '   ')
        self.assertEqual(str(cm.exception), 'description must not be empty')

    def test_add_expense_empty_payer_name(self):
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, '   ', 10.0, ['Bob'], 'Snack')
        self.assertEqual(str(cm.exception), 'payer must be an existing person')

    def test_add_expense_participant_empty_name(self):
        with self.assertRaises(ExpenseError) as cm:
            add_expense(self.ledger, 'Alice', 10.0, ['   '], 'Snack')
        self.assertEqual(str(cm.exception),
                         'participants must be non-empty list of existing people')


if __name__ == '__main__':
    unittest.main()
