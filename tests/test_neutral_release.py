"""Check the neutral build and permission boundaries."""
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class NeutralReleaseTests(unittest.TestCase):
    def test_manifest_is_anonymous_and_account_free(self):
        m = json.loads((ROOT / 'extension/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(m['name'], 'TrueDuck Sentinel (Beta)')
        self.assertNotIn('author', m)
        self.assertNotIn('homepage_url', m)
        self.assertEqual(m['host_permissions'], [])
        self.assertEqual(set(m['optional_host_permissions']), {'https://*/*', 'http://127.0.0.1:8877/*'})
        self.assertIn('alarms', m['permissions'])

    def test_code_has_no_previous_company_brand(self):
        for path in (ROOT / 'extension').rglob('*'):
            if path.suffix in ('.html', '.js', '.json', '.css'):
                source = path.read_text(encoding='utf-8').lower()
                self.assertNotIn('trueducksecurity.com', source, str(path))
                self.assertNotIn('trueduck security', source, str(path))
        self.assertIn("url.protocol === 'https:'", (ROOT / 'extension/options.js').read_text(encoding='utf-8'))

    def test_consumer_has_no_private_moderation_controls(self):
        for name in ('options.html','options.js','popup.html','popup.js'):
            source = (ROOT / 'extension' / name).read_text(encoding='utf-8')
            for forbidden in ('/api/indicators','/api/review','/v1/admin/', 'id="apiToken"', 'id="reviewForm"', 'id="addForm"', 'Private local indicator database'):
                self.assertNotIn(forbidden, source)
        bg = (ROOT / 'extension/background.js').read_text(encoding='utf-8')
        self.assertIn("remove(['apiToken', 'dbCache'", bg)
        self.assertNotIn('saved.dbCache', bg)
        self.assertNotIn('backend\\server.py', (ROOT / 'RUN_LOCAL.cmd').read_text())

    def test_warning_is_advisory(self):
        self.assertIn('not proof', (ROOT / 'extension/popup.html').read_text(encoding='utf-8').lower())

if __name__ == '__main__':
    unittest.main()
