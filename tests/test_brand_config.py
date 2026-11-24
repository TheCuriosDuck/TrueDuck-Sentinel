"""TrueDuck brand regression tests. Run with the normal project test suite."""

import json  # Parse the extension metadata exactly as Edge does.
import unittest  # Use the same simple test runner as the other backend checks.
from pathlib import Path  # Resolve the project location without hardcoding Windows paths.

ROOT = Path(__file__).resolve().parents[1]


class TrueDuckBrandTests(unittest.TestCase):
    """Verify the branded build cannot silently restore arbitrary feed servers."""

    def test_manifest_brand_and_domain(self):
        manifest = json.loads((ROOT / "extension/manifest.json").read_text(encoding="utf-8"))
        self.assertIn("TrueDuck Sentinel", manifest["name"])
        self.assertIn("TrueDuck Security", manifest["name"])
        self.assertEqual(manifest["host_permissions"], ["https://api.trueducksecurity.com/*"])
        self.assertIn("alarms", manifest["permissions"])
        self.assertEqual(manifest["homepage_url"], "https://trueducksecurity.com/")
        self.assertEqual(set(manifest["optional_host_permissions"]), {
            "http://127.0.0.1:8765/*",
            "http://127.0.0.1:8877/*",
        })

    def test_beta_author_display(self):
        manifest = json.loads((ROOT / "extension/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["author"], "TrueDuck Security")
        self.assertEqual(manifest["version_name"], "0.9.3 Beta")
        self.assertIn("Beta", manifest["name"])
        self.assertEqual(manifest["short_name"], "Sentinel")

    def test_extension_explicitly_restricts_cloud_host(self):
        source = (ROOT / "extension/options.js").read_text(encoding="utf-8")
        self.assertIn("url.hostname === 'api.trueducksecurity.com'", source)
        self.assertIn("url.hostname === '127.0.0.1'", source)

    def test_branding_and_disclaimer_visible(self):
        for page in ("extension/popup.html", "extension/options.html"):
            content = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn("TrueDuck Security", content)
        self.assertIn("educational", (ROOT / "extension/popup.html").read_text(encoding="utf-8"))


if __name__ == '__main__':
    unittest.main()
