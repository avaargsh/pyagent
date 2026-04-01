from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.skills.loader import load_skills


ROOT = Path(__file__).resolve().parents[3]


class SkillsLoaderTest(unittest.TestCase):
    def test_loads_customer_followup_skill(self) -> None:
        skills = load_skills(ROOT)
        self.assertIn("customer-followup", skills)
        self.assertEqual(skills["customer-followup"]["display_name"], "Customer Follow-Up")


if __name__ == "__main__":
    unittest.main()
