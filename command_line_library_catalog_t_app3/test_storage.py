import json
import os
import unittest
import tempfile
from pathlib import Path
from unittest import mock

from lib_common import LibraryError
import storage as storage  # the module under test


class TestStorage(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary directory for each test.
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.dir_path = Path(self.tmp_dir.name)

    # 1. load_data missing file -> empty catalog
    def test_load_missing_file_returns_empty(self):
        missing_path = self.dir_path / "nonexistent.json"
        result = storage.load_data(str(missing_path))
        self.assertEqual(result, {"books": [], "loans": []})

    # 2. load_data well‑formed file returns exact data
    def test_load_well_formed_file(self):
        data = {
            "books": [{"isbn": "1234567890", "title": "Sample Book", "author": "A. Writer"}],
            "loans": [{"isbn": "1234567890", "member_id": "M001", "due_date": "2024-12-31"}],
        }
        file_path = self.dir_path / "library.json"
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        result = storage.load_data(str(file_path))
        self.assertEqual(result, data)

    # 3. load_data corrupted JSON creates backup and returns empty catalog
    def test_load_corrupted_json_creates_backup(self):
        corrupt_path = self.dir_path / "corrupt.json"
        corrupt_path.write_text("{ this is not valid JSON")
        result = storage.load_data(str(corrupt_path))
        self.assertEqual(result, {"books": [], "loans": []})
        backup_path = Path(str(corrupt_path) + ".bak")
        self.assertTrue(backup_path.is_file())
        # backup should contain the original (invalid) content
        self.assertEqual(backup_path.read_text(), "{ this is not valid JSON")

    # 4. load_data schema mismatch (wrong types) creates backup and returns empty catalog
    def test_load_schema_mismatch_creates_backup(self):
        bad_schema_path = self.dir_path / "bad.json"
        bad_schema_path.write_text(json.dumps({"books": "not a list", "loans": []}))
        result = storage.load_data(str(bad_schema_path))
        self.assertEqual(result, {"books": [], "loans": []})
        backup_path = Path(str(bad_schema_path) + ".bak")
        self.assertTrue(backup_path.is_file())

    # 5. load_data unreadable file propagates LibraryError with exact message
    def test_load_unreadable_file_raises_library_error(self):
        unreadable_path = self.dir_path / "unreadable.json"
        unreadable_path.write_text("{}")
        # Patch Path.open to raise OSError with a known strerror
        with mock.patch.object(storage.Path, "open", side_effect=OSError(13, "Permission denied")):
            with self.assertRaises(LibraryError) as cm:
                storage.load_data(str(unreadable_path))
            self.assertEqual(str(cm.exception), "cannot read data file: Permission denied")

    # 6. save_data with valid catalog writes file correctly
    def test_save_valid_catalog_writes_file(self):
        data = {"books": [], "loans": []}
        target_path = self.dir_path / "library.json"
        storage.save_data(str(target_path), data)
        # Verify file exists and content matches expected JSON (sorted keys, indent)
        with target_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded, data)

    # 7. save_data with invalid structure raises LibraryError with exact message
    def test_save_invalid_structure_raises_error(self):
        bad_data = {"books": "not a list", "loans": []}
        target_path = self.dir_path / "library.json"
        with self.assertRaises(LibraryError) as cm:
            storage.save_data(str(target_path), bad_data)
        self.assertEqual(str(cm.exception), "invalid catalog data structure")

    # 8. save_data I/O error (e.g., permission) raises LibraryError with exact message
    def test_save_io_error_raises_library_error(self):
        data = {"books": [], "loans": []}
        target_path = self.dir_path / "protected.json"
        # Ensure the directory is writable but patch os.replace to simulate a permission error
        with mock.patch("storage.os.replace", side_effect=OSError(13, "Permission denied")):
            with self.assertRaises(LibraryError) as cm:
                storage.save_data(str(target_path), data)
            self.assertEqual(str(cm.exception), "cannot write data file: Permission denied")


if __name__ == "__main__":
    unittest.main()
