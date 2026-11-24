"""Tests normalization without touching your real database."""
# These checks use fictional values, not real scam reports.
import importlib.util
import unittest
from pathlib import Path

# Locate the backend file relative to this test file.
path = Path(__file__).resolve().parents[1] / 'backend' / 'server.py'
spec = importlib.util.spec_from_file_location('scamlens_server', path)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


# Verify that different forms of the same indicator normalize consistently.
class CanonicalizationTests(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(server.canonicalize('phone', '+1 (202) 555-0199'), '2025550199')

    def test_email(self):
        self.assertEqual(server.canonicalize('email', 'ALERTS@EXAMPLE.TEST'), 'alerts@example.test')

    def test_domain(self):
        self.assertEqual(server.canonicalize('domain', 'https://Example-Scam.Test/pay'), 'example-scam.test')

    def test_url(self):
        self.assertEqual(server.canonicalize('url', 'https://EXAMPLE.test/pay?q=1#section'), 'https://example.test/pay?q=1')

    def test_address(self):
        self.assertEqual(server.canonicalize('address', '123 Example Road, Testville'), '123 example road testville')

    def test_invalid(self):
        with self.assertRaises(ValueError):
            server.canonicalize('phone', '123')


if __name__ == '__main__':
    unittest.main()
