import json
import os
import unittest
import tempfile
from unittest import mock

from storage import (
    get_default_path,
    load_data,
    save_data,
    DEFAULT_FILENAME,
)
from core import HabitError


class TestStorage(unittest.TestCase):
    def test_get_default_path(self):
        path = get_default_path()
        self.assertTrue(path.endswith(f"/{DEFAULT_FILENAME}"))
        self.assertTrue(os.path.isabs(path))

    def test_load_data_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            missing = os.path.join(td, "does_not_exist.json")
            self.assertFalse(os.path.exists(missing))
            result = load_data(missing)
            self.assertEqual(result, {})

    def test_load_data_unreadable_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            file_path = os.path.join(td, "unreadable.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            # Simulate unreadable file by patching os.access to return False
            with mock.patch("os.access", return_value=False):
                with self.assertRaises(HabitError) as cm:
                    load_data(file_path)
                self.assertEqual(str(cm.exception), "cannot read habit file")

    def test_load_data_malformed_json_raises(self):
        with tempfile.TemporaryDirectory() as td:
            bad_json = os.path.join(td, "bad.json")
            with open(bad_json, "w", encoding="utf-8") as f:
                f.write("not a json")
            with self.assertRaises(HabitError) as cm:
                load_data(bad_json)
            self.assertEqual(str(cm.exception), "malformed JSON file")

    def test_load_data_malformed_structure_raises(self):
        with tempfile.TemporaryDirectory() as td:
            malformed = os.path.join(td, "malformed.json")
            # value is a string instead of list
            with open(malformed, "w", encoding="utf-8") as f:
                json.dump({"exercise": "2023-09-01"}, f)
            with self.assertRaises(HabitError) as cm:
                load_data(malformed)
            self.assertEqual(str(cm.exception), "malformed habit data")

    def test_load_data_valid(self):
        with tempfile.TemporaryDirectory() as td:
            good = os.path.join(td, "good.json")
            data = {"exercise": ["2023-09-01", "2023-09-02"]}
            with open(good, "w", encoding="utf-8") as f:
                json.dump(data, f)
            result = load_data(good)
            self.assertEqual(result, data)

    def test_save_data_successful(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "out.json")
            data = {"read": ["2023-01-01"]}
            save_data(out_path, data)
            with open(out_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, data)

    def test_save_data_malformed_data_raises(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "out.json")
            malformed = {"": ["2023-01-01"]}  # empty habit name
            with self.assertRaises(HabitError) as cm:
                save_data(out_path, malformed)
            self.assertEqual(str(cm.exception), "malformed habit data")

    def test_save_data_unwritable_directory_raises(self):
        with tempfile.TemporaryDirectory() as td:
            unwritable_dir = os.path.join(td, "no_write")
            os.mkdir(unwritable_dir)
            out_path = os.path.join(unwritable_dir, "out.json")
            data = {"read": []}
            # Simulate unwritable directory by patching os.access to return False
            with mock.patch("os.access", return_value=False):
                with self.assertRaises(HabitError) as cm:
                    save_data(out_path, data)
                self.assertEqual(str(cm.exception), "cannot write habit file")

    def test_save_data_rename_failure_raises(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "out.json")
            data = {"read": []}
            # Patch os.replace to raise OSError after the temp file is written
            with mock.patch("os.replace", side_effect=OSError):
                with self.assertRaises(HabitError) as cm:
                    save_data(out_path, data)
                self.assertEqual(str(cm.exception), "cannot replace habit file")


if __name__ == "__main__":
    unittest.main()
