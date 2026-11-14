import io
import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock
from contextlib import redirect_stdout, redirect_stderr

import app


class TestHabitTracker(unittest.TestCase):
    def test_validate_habit_name(self):
        # valid name
        self.assertIsNone(app.validate_habit_name("exercise"))

        # invalid names
        cases = [
            ("", "Habit name must be non-empty"),
            ("my habit", "Habit name may contain only letters, digits and underscores"),
            ("read-books", "Habit name may contain only letters, digits and underscores"),
            ("exercise\n", "Habit name may contain only letters, digits and underscores"),
            ("bad-name", "Habit name may contain only letters, digits and underscores"),
        ]
        for name, msg in cases:
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as cm:
                    app.validate_habit_name(name)
                self.assertEqual(str(cm.exception), msg)

    def test_checkin_behavior(self):
        today = date(2023, 10, 5)

        # 6. new habit
        data = {}
        result = app.checkin("exercise", data, today)
        expected = {"exercise": {"last_date": "2023-10-05", "streak": 1}}
        self.assertIs(result, data)
        self.assertEqual(data, expected)

        # 7. consecutive day
        data = {"exercise": {"last_date": "2023-10-04", "streak": 5}}
        result = app.checkin("exercise", data, today)
        expected = {"exercise": {"last_date": "2023-10-05", "streak": 6}}
        self.assertEqual(data, expected)

        # 8. missed day
        data = {"exercise": {"last_date": "2023-10-03", "streak": 3}}
        result = app.checkin("exercise", data, today)
        expected = {"exercise": {"last_date": "2023-10-05", "streak": 1}}
        self.assertEqual(data, expected)

        # 9. already checked in today
        data = {"exercise": {"last_date": "2023-10-05", "streak": 1}}
        with self.assertRaises(ValueError) as cm:
            app.checkin("exercise", data, today)
        self.assertEqual(str(cm.exception), "Already checked in today")

        # 10. future date
        data = {"exercise": {"last_date": "2023-10-06", "streak": 2}}
        with self.assertRaises(ValueError) as cm:
            app.checkin("exercise", data, today)
        self.assertEqual(str(cm.exception), "Last check-in is dated in the future")

        # 11. add new habit alongside existing
        data = {"exercise": {"last_date": "2023-10-05", "streak": 6}}
        result = app.checkin("meditate", data, today)
        expected = {
            "exercise": {"last_date": "2023-10-05", "streak": 6},
            "meditate": {"last_date": "2023-10-05", "streak": 1},
        }
        self.assertEqual(data, expected)

    def test_compute_streak(self):
        today = date(2023, 10, 5)

        cases = [
            ({"last_date": "2023-10-05", "streak": 6}, (6, False)),
            ({"last_date": "2023-10-04", "streak": 5}, (5, True)),
            ({"last_date": "2023-10-02", "streak": 4}, (0, True)),
            ({"last_date": "2023-10-06", "streak": 2}, (2, False)),
        ]
        for record, expected in cases:
            with self.subTest(record=record):
                self.assertEqual(app.compute_streak(record, today), expected)

    def test_status_and_list_habits(self):
        today = date(2023, 10, 5)
        data = {
            "exercise": {"last_date": "2023-10-05", "streak": 6},
            "meditate": {"last_date": "2023-10-04", "streak": 3},
            "read": {"last_date": "2023-09-30", "streak": 2},
        }

        # 18. status
        expected_status = [
            ("exercise", 6, False),
            ("meditate", 3, True),
            ("read", 0, True),
        ]
        self.assertEqual(app.status(data, today), expected_status)

        # 19. empty status
        self.assertEqual(app.status({}, today), [])

        # 20. list_habits
        self.assertEqual(app.list_habits(data), ["exercise", "meditate", "read"])

    def test_format_status_line(self):
        self.assertEqual(
            app.format_status_line("exercise", 6, False), "exercise      6  done"
        )
        self.assertEqual(
            app.format_status_line("read", 0, True), "read          0  pending"
        )

    def test_load_and_save_data(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "habits.json"

            # 23. load non‑existent file
            self.assertEqual(app.load_data(str(path)), {})

            # 24. save and load back
            data_to_save = {
                "exercise": {"last_date": "2023-10-05", "streak": 6},
                "read": {"last_date": "2023-09-30", "streak": 2},
            }
            app.save_data(str(path), data_to_save)
            # check file content exactly
            with path.open(encoding="utf-8") as f:
                content = f.read()
            expected_content = """{
  "exercise": {
    "last_date": "2023-10-05",
    "streak": 6
  },
  "read": {
    "last_date": "2023-09-30",
    "streak": 2
  }
}
"""
            self.assertEqual(content, expected_content)
            # load back
            loaded = app.load_data(str(path))
            self.assertEqual(loaded, data_to_save)

            # 25. unreadable JSON handling
            bad_path = Path(td) / "bad.json"
            bad_path.write_text("{not json", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = app.load_data(str(bad_path))
            self.assertEqual(result, {})
            # backup file exists with original bad content
            bak_path = bad_path.with_name(bad_path.name + ".bak")
            self.assertTrue(bak_path.is_file())
            self.assertEqual(bak_path.read_text(encoding="utf-8"), "{not json")
            self.assertIn(
                "Warning: the habit file was unreadable; it was renamed to .bak and a new one will be started.",
                stderr.getvalue(),
            )

    def test_main_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "habits.json"

            # Helper to run main and capture output
            def run(argv, today):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    ret = app.main(argv, path=str(path), today=today)
                return ret, stdout.getvalue(), stderr.getvalue()

            # 1. status with no habits
            ret, out, err = run(["status"], date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("No habits yet.", out)

            # 2. checkin exercise
            ret, out, err = run(["checkin", "exercise"], date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("Checked in: exercise (streak: 1)", out)

            # 3. checkin meditate
            ret, out, err = run(["checkin", "meditate"], date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("Checked in: meditate (streak: 1)", out)

            # 4. status shows both done
            ret, out, err = run(["status"], date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("exercise      1  done", out)
            self.assertIn("meditate      1  done", out)

            # 5. duplicate checkin error
            ret, out, err = run(["checkin", "exercise"], date(2023, 10, 5))
            self.assertEqual(ret, 1)
            self.assertIn("Error: Already checked in today", err)

            # 6. next day pending status
            ret, out, err = run(["status"], date(2023, 10, 6))
            self.assertEqual(ret, 0)
            self.assertIn("exercise      1  pending", out)
            self.assertIn("meditate      1  pending", out)

            # 7. checkin exercise next day (streak 2)
            ret, out, err = run(["checkin", "exercise"], date(2023, 10, 6))
            self.assertEqual(ret, 0)
            self.assertIn("Checked in: exercise (streak: 2)", out)

            # 8. later date with missed days (streak broken)
            ret, out, err = run(["status"], date(2023, 10, 9))
            self.assertEqual(ret, 0)
            self.assertIn("exercise      0  pending", out)
            self.assertIn("meditate      0  pending", out)

            # 9. list habits
            ret, out, err = run(["list"], date(2023, 10, 9))
            self
