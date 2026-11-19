import unittest
from copy import deepcopy

import habit_logic as hl
from core import HabitError, HabitData, StreakInfo


class TestHabitLogic(unittest.TestCase):
    def setUp(self):
        # Example data from the design specification
        self.base_data: HabitData = {
            "exercise": ["2023-09-01", "2023-09-02", "2023-09-04"],
            "read": ["2023-09-02", "2023-09-03", "2023-09-04"],
        }

    def test_add_habit_success(self):
        data = deepcopy(self.base_data)
        result = hl.add_habit(data, "meditate")
        expected = {
            "exercise": ["2023-09-01", "2023-09-02", "2023-09-04"],
            "read": ["2023-09-02", "2023-09-03", "2023-09-04"],
            "meditate": [],
        }
        self.assertEqual(result, expected)
        # original data must stay unchanged
        self.assertEqual(data, self.base_data)

    def test_add_habit_errors(self):
        data = deepcopy(self.base_data)
        # empty name
        with self.assertRaisesRegex(
            HabitError, r'^habit name must be a non-empty string$'
        ):
            hl.add_habit(data, "")
        # duplicate habit
        with self.assertRaisesRegex(
            HabitError, r'^habit "exercise" already exists$'
        ):
            hl.add_habit(data, "exercise")

    def test_log_habit_success(self):
        data = deepcopy(self.base_data)
        result = hl.log_habit(data, "exercise", "2023-09-03")
        expected = {
            "exercise": [
                "2023-09-01",
                "2023-09-02",
                "2023-09-03",
                "2023-09-04",
            ],
            "read": ["2023-09-02", "2023-09-03", "2023-09-04"],
        }
        self.assertEqual(result, expected)
        # original data unchanged
        self.assertEqual(data, self.base_data)

    def test_log_habit_errors(self):
        data = deepcopy(self.base_data)
        # duplicate date
        with self.assertRaisesRegex(
            HabitError,
            r'^date "2023-09-02" already logged for habit "exercise"$',
        ):
            hl.log_habit(data, "exercise", "2023-09-02")
        # unknown habit
        with self.assertRaisesRegex(
            HabitError, r'^habit "sleep" does not exist$'
        ):
            hl.log_habit(data, "sleep", "2023-09-01")
        # invalid ISO date
        with self.assertRaisesRegex(
            HabitError,
            r'^date "2023-13-01" is not a valid ISO date \(YYYY-MM-DD\)$',
        ):
            hl.log_habit(data, "exercise", "2023-13-01")

    def test_get_streaks_success(self):
        data = deepcopy(self.base_data)
        result: StreakInfo = hl.get_streaks(data, "read", "2023-09-04")
        expected = {"current": 3, "longest": 3}
        self.assertEqual(result, expected)

    def test_get_streaks_errors(self):
        data = deepcopy(self.base_data)
        # habit does not exist
        with self.assertRaisesRegex(
            HabitError, r'^habit "sleep" does not exist$'
        ):
            hl.get_streaks(data, "sleep", "2023-09-04")
        # invalid today date
        with self.assertRaisesRegex(
            HabitError,
            r'^date "2023-02-30" is not a valid ISO date \(YYYY-MM-DD\)$',
        ):
            hl.get_streaks(data, "read", "2023-02-30")

    def test_get_missed_yesterday_success(self):
        data = deepcopy(self.base_data)
        result = hl.get_missed_yesterday(data, "2023-09-01")
        self.assertEqual(result, ["read"])

    def test_get_missed_yesterday_error(self):
        data = deepcopy(self.base_data)
        with self.assertRaisesRegex(
            HabitError,
            r'^date "2023-13-01" is not a valid ISO date \(YYYY-MM-DD\)$',
        ):
            hl.get_missed_yesterday(data, "2023-13-01")


if __name__ == "__main__":
    unittest.main()
