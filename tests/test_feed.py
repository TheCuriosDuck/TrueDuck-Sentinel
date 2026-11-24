"""Tests for the optional URLhaus importer, using fictional URLs only."""

# These imports let us test the importer without contacting the internet.
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

# Load backend/server.py and urlhaus_feed.py from this project folder.
BACKEND = Path(__file__).resolve().parents[1] / "backend"


def load_module(name, file):
    """Import a Python source file by its exact path for testing."""
    spec = importlib.util.spec_from_file_location(name, BACKEND / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = load_module("scamlens_feed_server_tests", "server.py")
feed = load_module("scamlens_urlhaus_feed_tests", "urlhaus_feed.py")
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "urlhaus_sample.csv"


class FeedTests(unittest.TestCase):
    """Exercise CSV filtering and database isolation with temporary files."""

    def setUp(self):
        # Keep the user's real database safe: all test data lives in a temp folder.
        self.tmp = tempfile.TemporaryDirectory()
        server.DATA = Path(self.tmp.name)
        server.DB = server.DATA / "test.db"
        server.TOKEN_FILE = server.DATA / "token.txt"
        server.bootstrap()

    def tearDown(self):
        # Remove the disposable test data after each test finishes.
        self.tmp.cleanup()

    def sample(self):
        # Read the official-shaped but fictional .test fixture.
        with FIXTURE.open("r", encoding="utf-8", newline="") as file:
            return feed.parse_csv(file, server.canonicalize)

    def test_only_online_urls_are_used(self):
        rows = self.sample()
        self.assertEqual(len(rows), 2)  # Offline fixture is excluded.
        self.assertEqual(rows[0][1], "https://example-malware.test/payload")
        self.assertTrue(rows[0][3].startswith("https://urlhaus.abuse.ch/url/"))

    def test_refresh_keeps_manual_records(self):
        # Save a personal indicator first, then update the external table.
        with server.get_db() as conn:
            now = server.utc_now()
            conn.execute("""INSERT INTO indicators
                (kind,value,canonical,status,reason,source,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                ("email", "alerts@example.test", "alerts@example.test", "reported", "test", "Manual entry", now, now))
            feed.replace_feed(conn, self.sample())
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM feed_indicators").fetchone()[0], 2)
            statuses = [row[0] for row in conn.execute("SELECT status FROM feed_indicators")]
            self.assertEqual(statuses, ["external", "external"])
            # Importing again replaces, rather than appends, the same feed.
            feed.replace_feed(conn, self.sample())
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM feed_indicators").fetchone()[0], 2)

    def test_reject_invalid_download_without_erasing_previous(self):
        with server.get_db() as conn:
            feed.replace_feed(conn, self.sample())
            # Invalid input must fail before the DELETE statement runs.
            with self.assertRaises(ValueError):
                feed.replace_feed(conn, [])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM feed_indicators").fetchone()[0], 2)

    def test_csv_without_online_entries_does_not_replace(self):
        # A feed containing only offline URLs must not erase saved intelligence.
        text = 'id,url,url_status\n1,https://example.test/old,offline\n'
        with self.assertRaises(ValueError):
            feed.parse_csv(io.StringIO(text), server.canonicalize)

    def test_refuse_bad_api_key_before_network(self):
        # A short or malformed key is rejected without a network request.
        with self.assertRaises(ValueError):
            feed.fetch_csv("bad")


if __name__ == "__main__":
    unittest.main()
