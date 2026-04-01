from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from digital_employee.infra.config.loader import load_app_config
from digital_employee.infra.config.validate import validate_loaded_config


ROOT = Path(__file__).resolve().parents[4]


class ConfigValidateTest(unittest.TestCase):
    def test_repo_config_is_valid(self) -> None:
        config = load_app_config(ROOT)
        self.assertEqual(validate_loaded_config(config), [])


if __name__ == "__main__":
    unittest.main()
