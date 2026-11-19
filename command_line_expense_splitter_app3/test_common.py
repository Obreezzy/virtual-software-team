import unittest
import math
from unittest import mock

import common as app  # the module containing the validation functions


class TestCommonValidators(unittest.TestCase):
    # ---------- validate_amount ----------
    def test_validate_amount_success(self):
        # Worked example: should succeed without exception
        try:
            app.validate_amount(25.0)
        except Exception as e:
            self.fail(f"validate_amount raised an unexpected exception: {e}")

    def test_validate_amount_invalid(self):
        # Zero, negative, NaN, and infinities must raise the exact message
        invalid_values = [0, -3.5, float('nan'), float('inf'), float('-inf')]
        for val in invalid_values:
            with self.subTest(val=val):
                with self.assertRaises(app.ExpenseError) as cm:
                    app.validate_amount(val)
                self.assertEqual(str(cm.exception),
                                 'amount must be a positive finite number')

    # ---------- validate_name ----------
    def test_validate_name_success_and_failure(self):
        # Success case (whitespace ignored for emptiness test)
        app.validate_name(' Alice ')
        # Failure cases: empty after stripping and non‑string
        for bad in ['', '   ', 123]:
            with self.subTest(bad=bad):
                with self.assertRaises(app.ExpenseError) as cm:
                    app.validate_name(bad)  # type: ignore[arg-type]
                self.assertEqual(str(cm.exception),
                                 'name must be a non-empty string')

    # ---------- validate_people_list ----------
    def test_validate_people_list_success_and_errors(self):
        # Success
        app.validate_people_list(['Alice', 'Bob', 'Carol'])
        # Empty list
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_people_list([])
        self.assertEqual(str(cm.exception), 'people list cannot be empty')
        # Duplicate (after stripping)
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_people_list(['Bob', '  Bob  '])
        self.assertEqual(str(cm.exception), 'duplicate person "Bob"')
        # Invalid name inside list
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_people_list(['Alice', '   '])
        self.assertEqual(str(cm.exception), 'name must be a non-empty string')

    # ---------- validate_participants ----------
    def test_validate_participants_success_and_errors(self):
        known = ['Alice', 'Bob', 'Carol']
        # Success
        app.validate_participants(['Bob', 'Carol'], known)
        # Empty participants list
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_participants([], known)
        self.assertEqual(str(cm.exception), 'participants list cannot be empty')
        # Duplicate participant
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_participants(['Bob', 'Bob'], known)
        self.assertEqual(str(cm.exception), 'duplicate participant "Bob"')
        # Unknown participant
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_participants(['Dave'], known)
        self.assertEqual(str(cm.exception), 'participant "Dave" is not a known person')
        # Invalid name inside participants
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_participants(['   '], known)
        self.assertEqual(str(cm.exception), 'name must be a non-empty string')

    # ---------- validate_payer ----------
    def test_validate_payer_success_and_error(self):
        known = ['Alice', 'Bob']
        # Success
        app.validate_payer(' Alice ', known)
        # Unknown payer
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_payer('Carol', known)
        self.assertEqual(str(cm.exception), 'payer "Carol" is not a known person')
        # Invalid name
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_payer('   ', known)
        self.assertEqual(str(cm.exception), 'name must be a non-empty string')

    # ---------- validate_expense_dict ----------
    def test_validate_expense_dict_success_and_key_errors(self):
        known = ['Alice', 'Bob', 'Carol']
        expense = {
            'payer': 'Alice',
            'amount': 30.0,
            'participants': ['Bob', 'Carol'],
            'description': 'Dinner'
        }
        # Success
        app.validate_expense_dict(expense, known)

        # Missing key
        bad_expense = expense.copy()
        del bad_expense['description']
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad_expense, known)
        self.assertEqual(str(cm.exception),
                         'expense must contain keys payer, amount, participants, description')

        # Extra key
        bad_expense = expense.copy()
        bad_expense['extra'] = 1
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad_expense, known)
        self.assertEqual(str(cm.exception),
                         'expense must contain keys payer, amount, participants, description')

    def test_validate_expense_dict_subvalidation_errors(self):
        known = ['Alice', 'Bob', 'Carol']
        base = {
            'payer': 'Alice',
            'amount': 30.0,
            'participants': ['Bob'],
            'description': 'Lunch'
        }

        # Invalid payer
        bad = base.copy()
        bad['payer'] = 'Dave'
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad, known)
        self.assertEqual(str(cm.exception), 'payer "Dave" is not a known person')

        # Invalid amount
        bad = base.copy()
        bad['amount'] = -5
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad, known)
        self.assertEqual(str(cm.exception), 'amount must be a positive finite number')

        # Invalid participants (unknown)
        bad = base.copy()
        bad['participants'] = ['Eve']
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad, known)
        self.assertEqual(str(cm.exception), 'participant "Eve" is not a known person')

        # Invalid participants (duplicate)
        bad = base.copy()
        bad['participants'] = ['Bob', 'Bob']
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad, known)
        self.assertEqual(str(cm.exception), 'duplicate participant "Bob"')

        # Invalid participants (empty list)
        bad = base.copy()
        bad['participants'] = []
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad, known)
        self.assertEqual(str(cm.exception), 'participants list cannot be empty')

        # Invalid description type
        bad = base.copy()
        bad['description'] = 123
        with self.assertRaises(app.ExpenseError) as cm:
            app.validate_expense_dict(bad, known)
        self.assertEqual(str(cm.exception), 'description must be a string')


if __name__ == '__main__':
    unittest.main()
