import unittest
import core as app


class TestCoreModule(unittest.TestCase):
    # -----------------------------------------------------------------
    # HabitError tests
    # -----------------------------------------------------------------
    def test_habit_error_is_exception_subclass(self):
        """HabitError must inherit from Exception."""
        self.assertTrue(issubclass(app.HabitError, Exception))

    def test_habit_error_message_preserved(self):
        """The message passed to HabitError must be stored unchanged."""
        msg = "habit name cannot be empty"
        err = app.HabitError(msg)
        self.assertEqual(str(err), msg)

    def test_habit_error_can_be_raised_and_caught(self):
        """Raising HabitError should be catchable as its own type."""
        msg = "invalid habit"
        with self.assertRaises(app.HabitError) as cm:
            raise app.HabitError(msg)
        self.assertEqual(str(cm.exception), msg)

    # -----------------------------------------------------------------
    # HabitData tests (type alias behavior)
    # -----------------------------------------------------------------
    def test_habit_data_valid_example(self):
        """A valid HabitData instance as shown in the design works."""
        data: app.HabitData = {"exercise": ["2023-09-01", "2023-09-02"]}
        self.assertIsInstance(data, dict)
        self.assertIn("exercise", data)
        self.assertEqual(data["exercise"], ["2023-09-01", "2023-09-02"])

    def test_habit_data_empty_habit_list(self):
        """HabitData may contain an empty list for a new habit."""
        data: app.HabitData = {"meditate": []}
        self.assertIsInstance(data, dict)
        self.assertIn("meditate", data)
        self.assertEqual(data["meditate"], [])

    def test_habit_data_no_enforced_constraints(self):
        """The module does not enforce key/value constraints."""
        # whitespace-only habit name, duplicate dates, unsorted dates
        data: app.HabitData = {
            "  ": ["2023-09-02", "2023-09-01", "2023-09-01"],
            "reading": ["2023-09-05", "2023-09-04"],
        }
        # No exception should be raised; just verify the structure is a dict.
        self.assertIsInstance(data, dict)
        self.assertIn("  ", data)
        self.assertIn("reading", data)

    # -----------------------------------------------------------------
    # StreakInfo tests (type alias behavior)
    # -----------------------------------------------------------------
    def test_streak_info_valid_example(self):
        """A valid StreakInfo instance as shown in the design works."""
        info: app.StreakInfo = {"current": 3, "longest": 7}
        self.assertIsInstance(info, dict)
        self.assertCountEqual(info.keys(), {"current", "longest"})
        self.assertEqual(info["current"], 3)
        self.assertEqual(info["longest"], 7)

    def test_streak_info_zero_streaks(self):
        """StreakInfo can represent zero streaks."""
        info: app.StreakInfo = {"current": 0, "longest": 0}
        self.assertIsInstance(info, dict)
        self.assertCountEqual(info.keys(), {"current", "longest"})
        self.assertEqual(info["current"], 0)
        self.assertEqual(info["longest"], 0)

    def test_streak_info_missing_key_not_validated(self):
        """The module does not validate presence of required keys."""
        # Even though the design expects both keys, the alias permits any dict.
        info: app.StreakInfo = {"current": 5}
        self.assertIsInstance(info, dict)
        self.assertIn("current", info)
        self.assertNotIn("longest", info)


if __name__ == "__main__":
    unittest.main()
