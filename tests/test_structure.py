from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class ProjectStructureTests(unittest.TestCase):
    def test_required_endpoints_are_implemented(self):
        expected = {
            "apps/frontend-api/app/main.py": '/checkout',
            "apps/orders-api/app/main.py": '/orders/process',
            "apps/payment-api/app/main.py": '/payment/process',
        }
        for relative_path, endpoint in expected.items():
            self.assertIn(endpoint, (ROOT / relative_path).read_text())

    def test_payment_has_slow_path(self):
        source = (ROOT / "apps/payment-api/app/main.py").read_text()
        self.assertIn("slow: bool", source)
        self.assertIn("random.uniform(1.0, 2.0)", source)


if __name__ == "__main__":
    unittest.main()
