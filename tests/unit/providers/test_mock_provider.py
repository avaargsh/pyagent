from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.providers.mock_provider import MockProvider
from digital_employee.providers.models import CompletionRequest


class MockProviderTest(unittest.TestCase):
    def test_mock_provider_returns_summary(self) -> None:
        provider = MockProvider()
        result = asyncio.run(
            provider.complete(
                CompletionRequest(
                    system="Employee Sales Assistant",
                    prompt="Follow up with the customer",
                    metadata={"employee_id": "sales-assistant", "allowed_tools": ["send-email"]},
                )
            )
        )
        self.assertIn("sales-assistant", result.text)
        self.assertIn("send-email", result.text)


if __name__ == "__main__":
    unittest.main()
