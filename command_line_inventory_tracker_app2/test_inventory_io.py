import json
import os
import tempfile
import unittest
from unittest import mock

import inventory_io as inventory_io  
from inventory_core import InventoryError


class TestInventoryIO(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for all file operations
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def _temp_path(self, filename: str) -> str:
        return os.path.join(self.tmp_dir.name, filename)

    # 1. Loading a well‑formed file
    def test_load_inventory_success(self):
        path = self._temp_path('good.json')
        data = {
            "apple": {"quantity": 10, "price": 0.5},
            "banana": {"quantity": 5, "price": 0.30}
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        result = inventory_io.load_inventory(path)
        self.assertEqual(result, data)

    # 2. Loading a missing file
    def test_load_inventory_missing_file(self):
        path = self._temp_path('does_not_exist.json')
        with self.assertRaises(InventoryError) as cm:
            inventory_io.load_inventory(path)
        self.assertEqual(str(cm.exception),
                         'inventory file not found - starting with empty inventory')

    # 3. Loading a file with invalid JSON
    def test_load_inventory_invalid_json(self):
        path = self._temp_path('bad_json.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{"apple": {"quantity": 10, "price": 0.5},')  # truncated JSON

        with self.assertRaises(InventoryError) as cm:
            inventory_io.load_inventory(path)
        self.assertEqual(str(cm.exception), 'inventory file is not valid JSON')

    # 4. Loading a file that violates the schema (negative quantity)
    def test_load_inventory_corrupted_schema(self):
        path = self._temp_path('negative_qty.json')
        corrupted = {"orange": {"quantity": -3, "price": 0.8}}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(corrupted, f)

        with self.assertRaises(InventoryError) as cm:
            inventory_io.load_inventory(path)
        self.assertEqual(str(cm.exception),
                         'inventory file is corrupted - backup created')

        # backup file should exist
        backup_path = f'{path}.bak'
        self.assertTrue(os.path.isfile(backup_path))

        # original file should have been moved (i.e., no longer present)
        self.assertFalse(os.path.isfile(path))

    # 5. Saving a correct inventory
    def test_save_inventory_success(self):
        path = self._temp_path('out.json')
        inventory = {"milk": {"quantity": 3, "price": 1.25}}
        inventory_io.save_inventory(path, inventory)

        # Verify file exists and content matches expected JSON
        with open(path, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        self.assertEqual(saved, inventory)

    # 6. Saving an inventory with a non‑finite price
    def test_save_inventory_invalid_price(self):
        path = self._temp_path('invalid_price.json')
        inventory = {"water": {"quantity": 1, "price": float('nan')}}
        with self.assertRaises(InventoryError) as cm:
            inventory_io.save_inventory(path, inventory)
        self.assertEqual(str(cm.exception),
                         'inventory data contains invalid values')

    # 7. Path validation – empty string
    def test_path_validation_empty_string(self):
        with self.assertRaises(InventoryError) as cm:
            inventory_io.load_inventory('   ')
        self.assertEqual(str(cm.exception),
                         'inventory file path must be a non-empty string')

        with self.assertRaises(InventoryError) as cm2:
            inventory_io.save_inventory('', {"a": {"quantity": 1, "price": 0.1}})
        self.assertEqual(str(cm2.exception),
                         'inventory file path must be a non-empty string')

    # 8. Path validation – non‑string type
    def test_path_validation_non_string(self):
        with self.assertRaises(InventoryError) as cm:
            inventory_io.load_inventory(123)  # type: ignore[arg-type]
        self.assertEqual(str(cm.exception),
                         'inventory file path must be a non-empty string')

        with self.assertRaises(InventoryError) as cm2:
            inventory_io.save_inventory(None, {"a": {"quantity": 1, "price": 0.1}})  # type: ignore[arg-type]
        self.assertEqual(str(cm2.exception),
                         'inventory file path must be a non-empty string')


if __name__ == '__main__':
    unittest.main()
