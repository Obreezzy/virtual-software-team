import os
import json
import io
import unittest
import tempfile
import contextlib
from unittest import mock

import app


class TestTodoApp(unittest.TestCase):
    def test_get_default_path_expands_home(self):
        path = app.get_default_path()
        self.assertTrue(path.startswith(os.path.expanduser("~")))
        self.assertTrue(path.endswith(".todo.json"))

    def test_load_tasks_creates_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "tasks.json")
            self.assertFalse(os.path.exists(path))
            tasks = app.load_tasks(path)
            self.assertEqual(tasks, [])
            self.assertTrue(os.path.isfile(path))
            with open(path, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])

    def test_load_tasks_handles_corrupted_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "tasks.json")
            # write invalid JSON
            with open(path, "w", encoding="utf-8") as f:
                f.write("{ not json")
            bak = path + ".bak"
            tasks = app.load_tasks(path)
            self.assertEqual(tasks, [])
            self.assertTrue(os.path.isfile(bak))
            with open(bak, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "{ not json")
            with open(path, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])

    def test_add_task_and_next_id(self):
        tasks = []
        t1 = app.add_task(tasks, "Buy milk")
        self.assertEqual(t1["id"], 1)
        self.assertEqual(t1["description"], "Buy milk")
        self.assertFalse(t1["completed"])
        self.assertIsInstance(t1["created"], str)
        self.assertTrue(t1["created"])
        self.assertEqual(len(tasks), 1)

        t2 = app.add_task(tasks, "Read book")
        self.assertEqual(t2["id"], 2)
        self.assertEqual(len(tasks), 2)

    def test_add_task_empty_description_raises(self):
        tasks = []
        with self.assertRaisesRegex(ValueError, "Description cannot be empty"):
            app.add_task(tasks, "   ")

    def test_list_tasks_filters_and_invalid_status(self):
        tasks = []
        t1 = app.add_task(tasks, "Buy milk")
        t2 = app.add_task(tasks, "Read book")
        # pending
        pending = app.list_tasks(tasks, status="pending")
        self.assertEqual(pending, [t1, t2])
        # mark one done
        app.mark_done(tasks, 1)
        done = app.list_tasks(tasks, status="done")
        self.assertEqual(done, [t1])
        # invalid status
        with self.assertRaisesRegex(ValueError, "Invalid status filter"):
            app.list_tasks(tasks, status="finished")

    def test_mark_done_not_found(self):
        tasks = []
        app.add_task(tasks, "Buy milk")
        with self.assertRaisesRegex(ValueError, "Task ID not found"):
            app.mark_done(tasks, 99)

    def test_remove_task_not_found(self):
        tasks = []
        app.add_task(tasks, "Buy milk")
        with self.assertRaisesRegex(ValueError, "Task ID not found"):
            app.remove_task(tasks, 99)

    def test_clear_tasks_confirmation_decline(self):
        tasks = []
        t1 = app.add_task(tasks, "Buy milk")
        app.mark_done(tasks, 1)
        with mock.patch.object(app, "confirm", return_value=False):
            removed = app.clear_tasks(tasks, force=False)
        self.assertEqual(removed, [])
        self.assertEqual(len(tasks), 1)  # still present

    def test_clear_tasks_force(self):
        tasks = []
        t1 = app.add_task(tasks, "Buy milk")
        app.mark_done(tasks, 1)
        removed = app.clear_tasks(tasks, force=True)
        self.assertEqual(removed, [t1])
        self.assertEqual(tasks, [])

    def test_format_task_line(self):
        task = {"id": 1, "description": "Buy milk", "completed": False}
        line = app.format_task_line(task)
        self.assertEqual(line, "  1  [ ] Buy milk")
        task["completed"] = True
        line = app.format_task_line(task)
        self.assertEqual(line, "  1  [x] Buy milk")

    def test_print_tasks_output(self):
        tasks = []
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            app.print_tasks(tasks)
        self.assertIn("No tasks.", f.getvalue())

        app.add_task(tasks, "Buy milk")
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            app.print_tasks(tasks)
        self.assertIn("  1  [ ] Buy milk", f.getvalue())

    def test_confirm_yes_and_no(self):
        with mock.patch("builtins.input", return_value="Y"):
            self.assertTrue(app.confirm("Prompt? "))
        with mock.patch("builtins.input", return_value="no"):
            self.assertFalse(app.confirm("Prompt? "))

    def test_parse_args_valid_commands(self):
        self.assertEqual(app.parse_args(["add", "Buy", "milk"]),
                         {"command": "add", "description": "Buy milk"})
        self.assertEqual(app.parse_args(["list", "--pending"]),
                         {"command": "list", "status": "pending"})
        self.assertEqual(app.parse_args(["done", "3"]),
                         {"command": "done", "id": 3})
        self.assertEqual(app.parse_args(["remove", "2"]),
                         {"command": "remove", "id": 2})
        self.assertEqual(app.parse_args(["clear", "--force"]),
                         {"command": "clear", "force": True})
        self.assertEqual(app.parse_args(["clear"]),
                         {"command": "clear", "force": False})
        self.assertEqual(app.parse_args(["-h"]), {"command": "help"})
        self.assertEqual(app.parse_args(["--help"]), {"command": "help"})

    def test_parse_args_unknown_command(self):
        with self.assertRaisesRegex(ValueError, "Unknown command"):
            app.parse_args(["foobar"])

    def test_end_to_end_example_session(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "tasks.json")
            # 1) add "Buy milk"
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                app.main(["add", "Buy milk"], path=path)
            self.assertIn("Added task 1.", f.getvalue())

            # 2) add "Read book"
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                app.main(["add", "Read book"], path=path)
            self.assertIn("Added task 2.", f.getvalue())

            # 3) list --pending
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                app.main(["list", "--pending"], path=path)
            out = f.getvalue()
            self.assertIn("  1  [ ] Buy milk", out)
            self.assertIn("  2  [ ] Read book", out)

            # 4) done 1
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                app.main(["done", "1"], path=path)
            self.assertIn("Marked task 1 as completed.", f.getvalue())

            # 5) list --done
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                app.main(["list", "--done"], path=path)
            out = f.getvalue()
            self.assertIn("  1  [x] Buy milk", out)
            self.assertNotIn("Read book", out)

            # 6) remove 2
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                app.main(["remove", "2"], path=path)
            self.assertIn("Removed task 2.", f.getvalue())

            # 7) clear (confirm y)
            with mock.patch("builtins.input", return_value="y"):
                f = io.StringIO()
                with contextlib.redirect_stdout(f):
                    app.main(["clear"], path=path)
                out = f.getvalue()
                self.assertIn("Cleared 1 completed task(s).", out)

            # 8) list (should be empty)
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                app.main(["list"], path=path)
            self.assertIn("No tasks.", f.getvalue())

            # 9) help
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                with self.assertRaises(SystemExit) as cm:
                    app.main(["--help"], path=path)
                self.assertEqual(cm.exception.code, 0)
            self.assertIn("Usage: todo", f.getvalue())


if __name__ == "__main__":
    unittest.main()
