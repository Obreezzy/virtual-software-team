import unittest
from people import add_person, list_people
from common import ExpenseError


class TestPeople(unittest.TestCase):
    def setUp(self):
        # Fresh ledger for each test
        self.ledger = {"people": [], "expenses": []}

    def test_add_person_success(self):
        add_person(self.ledger, "Alice")
        self.assertIn("Alice", self.ledger["people"])
        self.assertEqual(self.ledger["people"], ["Alice"])

    def test_add_multiple_and_list_sorted(self):
        add_person(self.ledger, "Bob")
        add_person(self.ledger, "Alice")
        # Ledger order reflects insertion order
        self.assertEqual(self.ledger["people"], ["Bob", "Alice"])
        # list_people should return a new sorted list
        sorted_people = list_people(self.ledger)
        self.assertEqual(sorted_people, ["Alice", "Bob"])
        # Ensure a new list is returned (not the same object)
        self.assertIsNot(sorted_people, self.ledger["people"])

    def test_duplicate_person_error(self):
        add_person(self.ledger, "Alice")
        with self.assertRaises(ExpenseError) as cm:
            add_person(self.ledger, "Alice")
        self.assertEqual(str(cm.exception), "person already exists: Alice")

    def test_empty_name_error(self):
        with self.assertRaises(ExpenseError) as cm:
            add_person(self.ledger, "")
        self.assertEqual(str(cm.exception), "person name cannot be empty")

    def test_whitespace_name_error(self):
        with self.assertRaises(ExpenseError) as cm:
            add_person(self.ledger, "   ")
        self.assertEqual(str(cm.exception), "person name cannot be empty")

    def test_validate_name_non_string_error(self):
        # validate_name should raise for non‑string inputs
        with self.assertRaises(ExpenseError) as cm:
            add_person(self.ledger, None)  # type: ignore[arg-type]
        self.assertEqual(str(cm.exception), "name must be a non-empty string")

    def test_list_people_empty(self):
        empty_ledger = {"people": [], "expenses": []}
        result = list_people(empty_ledger)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
