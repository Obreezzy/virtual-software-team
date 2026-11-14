import unittest
import tempfile
import os
import json
import datetime
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

import app


class TestHabitTracker(unittest.TestCase):
    def test_validate_habit_name(self):
        # valid name
        self.assertIsNone(app.validate_habit_name("exercise"))
        # empty name
        with self.assertRaises(ValueError) as cm:
            app.validate_habit_name("")
        self.assertEqual(str(cm.exception), "Habit name must be non-empty")
        # invalid characters
        for bad in ["my habit", "read-books", "exercise\n"]:
            with self.assertRaises(ValueError) as cm:
                app.validate_habit_name(bad)
            self.assertEqual(
                str(cm.exception),
                "Habit name may contain only letters, digits and underscores",
            )

    def test_checkin_behaviour(self):
        today = datetime.date(2023, 10, 5)
        # 6. new habit
        data = {}
        res = app.checkin("exercise", data, today)
        self.assertEqual(
            res,
            {"exercise": {"last_date": "2023-10-05", "streak": 1}},
        )
        # 7. consecutive day
        data = {"exercise": {"last_date": "2023-10-04", "streak": 5}}
        res = app.checkin("exercise", data, today)
        self.assertEqual(
            res,
            {"exercise": {"last_date": "2023-10-05", "streak": 6}},
        )
        # 8. missed day
        data = {"exercise": {"last_date": "2023-10-03", "streak": 3}}
        res = app.checkin("exercise", data, today)
        self.assertEqual(
            res,
            {"exercise": {"last_date": "2023-10-05", "streak": 1}},
        )
        # 9. already checked today
        data = {"exercise": {"last_date": "2023-10-05", "streak": 1}}
        with self.assertRaises(ValueError) as cm:
            app.checkin("exercise", data, today)
        self.assertEqual(str(cm.exception), "Already checked in today")
        # 10. future date
        data = {"exercise": {"last_date": "2023-10-06", "streak": 2}}
        with self.assertRaises(ValueError) as cm:
            app.checkin("exercise", data, today)
        self.assertEqual(str(cm.exception), "Last check-in is dated in the future")
        # 12. bad habit name
        with self.assertRaises(ValueError) as cm:
            app.checkin("bad-name", {}, today)
        self.assertEqual(
            str(cm.exception),
            "Habit name may contain only letters, digits and underscores",
        )
        # 13. dict is mutated (already covered by previous checks)

    def test_compute_streak(self):
        today = datetime.date(2023, 10, 5)
        # 14.
        rec = {"last_date": "2023-10-05", "streak": 6}
        self.assertEqual(app.compute_streak(rec, today), (6, False))
        # 15.
        rec = {"last_date": "2023-10-04", "streak": 5}
        self.assertEqual(app.compute_streak(rec, today), (5, True))
        # 16.
        rec = {"last_date": "2023-10-02", "streak": 4}
        self.assertEqual(app.compute_streak(rec, today), (0, True))
        # 17.
        rec = {"last_date": "2023-10-06", "streak": 2}
        self.assertEqual(app.compute_streak(rec, today), (2, False))

    def test_status_and_format(self):
        today = datetime.date(2023, 10, 5)
        data = {
            "exercise": {"last_date": "2023-10-05", "streak": 6},
            "meditate": {"last_date": "2023-10-04", "streak": 3},
            "read": {"last_date": "2023-09-30", "streak": 2},
        }
        # 18.
        expected_status = [
            ("exercise", 6, False),
            ("meditate", 3, True),
            ("read", 0, True),
        ]
        self.assertEqual(app.status(data, today), expected_status)
        # 21.
        line = app.format_status_line("exercise", 6, False)
        self.assertEqual(line, "exercise      6  done")
        # 22.
        line = app.format_status_line("read", 0, True)
        self.assertEqual(line, "read          0  pending")

    def test_load_save_and_corrupt_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "habits.json")
            # 24. save and load round‑trip
            data_to_save = {
                "exercise": {"last_date": "2023-10-05", "streak": 6},
                "read": {"last_date": "2023-09-30", "streak": 2},
            }
            app.save_data(path, data_to_save)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            expected_content = (
                "{\n"
                "  \"exercise\": {\n"
                "    \"last_date\": \"2023-10-05\",\n"
                "    \"streak\": 6\n"
                "  },\n"
                "  \"read\": {\n"
                "    \"last_date\": \"2023-09-30\",\n"
                "    \"streak\": 2\n"
                "  }\n"
                "}"
            )
            self.assertEqual(content.strip(), expected_content.strip())
            loaded = app.load_data(path)
            self.assertEqual(loaded, data_to_save)

            # 25. corrupt file handling
            bad_path = os.path.join(td, "bad.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                f.write("{not json")
            stderr = StringIO()
            with redirect_stderr(stderr):
                result = app.load_data(bad_path)
            self.assertEqual(result, {})
            # backup exists with same bad content
            bak_path = bad_path + ".bak"
            self.assertTrue(os.path.isfile(bak_path))
            with open(bak_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "{not json")
            self.assertIn(
                "Warning: the habit file was unreadable; it was renamed to .bak and a new one will be started.",
                stderr.getvalue(),
            )

    def test_end_to_end_example_session(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "habits.json")
            # Helper to run main and capture output
            def run(argv, today):
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    ret = app.main(argv, path=path, today=today)
                return ret, stdout.getvalue(), stderr.getvalue()

            # 1) status with no habits
            ret, out, err = run(["status"], datetime.date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("No habits yet.", out)

            # 2) checkin exercise
            ret, out, err = run(["checkin", "exercise"], datetime.date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("Checked in: exercise (streak: 1)", out)

            # 3) checkin meditate
            ret, out, err = run(["checkin", "meditate"], datetime.date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("Checked in: meditate (streak: 1)", out)

            # 4) status shows both done
            ret, out, err = run(["status"], datetime.date(2023, 10, 5))
            self.assertEqual(ret, 0)
            self.assertIn("exercise      1  done", out)
            self.assertIn("meditate      1  done", out)

            # 5) duplicate checkin error
            ret, out, err = run(["checkin", "exercise"], datetime.date(2023, 10, 5))
            self.assertEqual(ret, 1)
            self.assertIn("Error: Already checked in today", err)

            # 6) next day status pending
            ret, out, err = run(["status"], datetime.date(2023, 10, 6))
            self.assertEqual(ret, 0)
            self.assertIn("exercise      1  pending", out)
            self.assertIn("meditate      1  pending", out)

            # 7) checkin exercise on 2023-10-06
            ret, out, err = run(["checkin", "exercise"], datetime.date(2023, 10, 6))
            self.assertEqual(ret, 0)
            self.assertIn("Checked in: exercise (streak: 2)", out)

            # 8) status on 2023-10-09 (missed days)
            ret, out, err = run(["status"], datetime.date(2023, 10, 9))
            self.assertEqual(ret, 0)
            self.assertIn("exercise      0  pending", out)
            self.assertIn("meditate      0  pending", out)

            # 9) list habits
            ret, out, err = run(["list"], datetime.date(2023, 10, 9))
            self.assertEqual(ret, 0)
            self.assertIn("exercise", out)
            self.assertIn("meditate", out)

            # 10) bad habit name error
            ret, out, err = run(["checkin", "Bad-Name"], datetime.date(2023, 10, 9))
            self.assertEqual(ret, 1)
            self.assertIn(
                "Error: Habit name may contain only letters, digits and underscores",
                err,
            )


if __name__ == "__main__":
    unittest.main()
