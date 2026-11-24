"""Regression tests for the release safety rules and static manifest review."""

# importlib loads our small checker without starting any web servers.
import importlib
import unittest

from security_check import inspect

production = importlib.import_module('cloud_api.production')


class ReleaseSafetyTests(unittest.TestCase):
    """Detect accidental removal of important deployment guardrails."""

    def test_static_security_check_passes(self):
        failures, _warnings = inspect()
        self.assertEqual(failures, [])

    def test_local_mode_is_allowed_for_testing(self):
        self.assertEqual(production.validate_production_config({'SCAMLENS_ENV': 'development'}), [])

    def test_missing_production_secrets_block_launch(self):
        issues = production.validate_production_config({'SCAMLENS_ENV': 'production'})
        self.assertGreaterEqual(len(issues), 3)

    def safe_production_example(self):
        return {
            'SCAMLENS_ENV': 'production',
            'SCAMLENS_CLOUD_DATABASE_URL': 'postgresql+psycopg://service:example@db/scamlens',
            'SCAMLENS_PUBLIC_ORIGIN': 'https://api.example.org',
            'SCAMLENS_ALLOWED_HOSTS': 'api.example.org',
            'SCAMLENS_ALLOW_SIGNUP': '0',
        }

    def test_safe_synthetic_config_passes_config_only(self):
        # Passing these limited checks does NOT establish production readiness.
        self.assertEqual(production.validate_production_config(self.safe_production_example()), [])

    def test_production_registration_is_disabled(self):
        config = self.safe_production_example()
        config['SCAMLENS_ALLOW_SIGNUP'] = '1'
        self.assertTrue(any('signup' in issue for issue in production.validate_production_config(config)))

    def test_production_requires_matching_host(self):
        config = self.safe_production_example()
        config['SCAMLENS_ALLOWED_HOSTS'] = 'another.example.org'
        self.assertTrue(any('hostname' in issue for issue in production.validate_production_config(config)))

    def test_production_rejects_plain_http_origin(self):
        config = self.safe_production_example()
        config['SCAMLENS_PUBLIC_ORIGIN'] = 'http://api.example.org'
        self.assertTrue(any('HTTPS' in issue for issue in production.validate_production_config(config)))


if __name__ == '__main__':
    unittest.main()
