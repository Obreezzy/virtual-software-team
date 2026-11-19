import unittest
import sys
import io
import contextlib
from unittest import mock
from types import SimpleNamespace, ModuleType


# Now import the application and core modules.
import app
import core


class TestApp(unittest.TestCase):
    def setUp(self):
        # Inâ€‘memory dict acting as the habit JSON store.
        self._storage_data = {}

        # Patch storage functions used by `app.main`.
        self.patcher_path = mock.patch('storage.get_default_path')
        self.mock_path = self.patcher_path.start()
        self.mock_path.return_value = '/nonexistent/path.json'  # irrelevant value

        self.patcher_load = mock.patch('storage.load_data')
        self.mock_load = self.patcher_load.start()
        self.mock_load.side_effect = lambda _: self._storage_data

        self.patcher_save = mock.patch('storage.save_data')
        self.mock_save = self.patcher_save.start()
        self.mock_save.side_effect = lambda _, data: self._storage_data.update(data)

    def tearDown(self):
        mock.patch.stopall()

    # ---------- success paths ----------
    def test_add_success(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app.main(['add', 'exercise'])
        self.assertIn('Added habit "exercise"', out.getvalue())
        self.assertIn('exercise', self._storage_data)

    def test_log_success(self):
        # Preâ€‘populate a habit so that logging succeeds.
        self._storage_data['exercise'] = []
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app.main(['log', 'exercise', '2023-09-15'])
        self.assertIn('Logged "exercise" for 2023-09-15', out.getvalue())

    def test_streak_success(self):
        streak_info = {"current": 3, "longest": 5}
        with mock.patch('habit_logic.get_streaks', return_value=streak_info):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                app.main(['streak', 'exercise', '2023-09-20'])
        self.assertIn('Current streak: 3 days, Longest streak: 5 days', out.getvalue())

    def test_missed_none(self):
        with mock.patch('habit_logic.get_missed_yesterday', return_value=[]):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                app.main(['missed'])
        self.assertIn('No missed habits', out.getvalue())

    def test_missed_some(self):
        with mock.patch('habit_logic.get_missed_yesterday', return_value=['reading', 'exercise']):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                app.main(['missed'])
        output = out.getvalue().splitlines()
        self.assertEqual(sorted(output), ['exercise', 'reading'])

    def test_list_no_habits(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app.main(['list'])
        self.assertIn('No habits defined', out.getvalue())

    def test_list_with_habits(self):
        self._storage_data.update({'reading': [], 'exercise': []})
        with contextlib.redirect_stdout(io.StringIO()) as out:
            app.main(['list'])
        output = out.getvalue().splitlines()
        self.assertEqual(output, ['exercise', 'reading'])  # alphabetical

    # ---------- error handling ----------
    def test_empty_command_error(self):
        stderr = io.StringIO()
        with mock.patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as cm:
                app.main([])
        self.assertEqual(cm.exception.code, 1)
        self.assertIn('no command supplied', stderr.getvalue())

    def test_invalid_date_error(self):
        stderr = io.StringIO()
        with mock.patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as cm:
                app.main(['log', 'exercise', '2023-02-30'])
        self.assertEqual(cm.exception.code, 1)
        self.assertIn('date must be a valid ISO date (YYYY-MM-DD)', stderr.getvalue())

    def test_duplicate_habit_error(self):
        # First add succeeds.
        app.main(['add', 'exercise'])
        # Second add should raise from habit_logic.
        with mock.patch('habit_logic.add_habit',
                        side_effect=core.HabitError('habit "exercise" already exists')):
            stderr = io.StringIO()
            with mock.patch('sys.stderr', stderr):
                with self.assertRaises(SystemExit) as cm:
                    app.main(['add', 'exercise'])
        self.assertEqual(cm.exception.code, 1)
        self.assertIn('habit "exercise" already exists', stderr.getvalue())

    def test_unknown_command_error(self):
        stderr = io.StringIO()
        with mock.patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as cm:
                app.main(['foobar'])
        self.assertEqual(cm.exception.code, 1)
        # Design does not prescribe the exact message; ensure something was printed.
        self.assertTrue(stderr.getvalue().strip())

    # ---------- endâ€‘toâ€‘end example session ----------
    def test_example_session_end_to_end(self):
        # Mock habit_logic to provide deterministic responses.
        with mock.patch('habit_logic.add_habit',
                        side_effect=lambda data, name: {**data, name: []}), \
             mock.patch('habit_logic.log_habit',
                        side_effect=lambda data, name, iso_date: {
                            **data,
                            name: data.get(name, []) + [iso_date]
                        }), \
             mock.patch('habit_logic.get_streaks',
                        return_value={"current": 1, "longest": 1}), \
             mock.patch('habit_logic.get_missed_yesterday', return_value=[]):
            commands = [
                (['add', 'reading'], 'Added habit "reading"'),
                (['log', 'reading', '2023-09-01'], 'Logged "reading" for 2023-09-01'),
                (['streak', 'reading'], 'Current streak: 1 days, Longest streak: 1 days'),
                (['missed'], 'No missed habits'),
                (['list'], 'reading')
            ]
            for argv, expected in commands:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    app.main(argv)
                self.assertIn(expected, out.getvalue())


