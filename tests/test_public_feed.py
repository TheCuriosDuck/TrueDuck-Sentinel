"""Tests for v0.6 public-feed controls using TEMPORARY data only.

No test publishes a real URL, contacts a website, or touches the owner's DB.
"""

# The tests use only Python's standard library.
from contextlib import closing  # Ensure SQLite files are released on Windows.
import importlib.util  # Load the actual backend file without starting a permanent server.
import json            # Encode and decode the request/response bodies.
import sqlite3         # Create an old database for the migration test.
import tempfile        # Isolate every test from the user's saved data.
import threading       # Run a disposable localhost HTTP server during tests.
import unittest        # Check results automatically.
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Locate the same server.py the Windows launcher uses.
FILE = Path(__file__).resolve().parents[1] / 'backend' / 'server.py'
spec = importlib.util.spec_from_file_location('scamlens_public_tests', FILE)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class PublicFeedTests(unittest.TestCase):
    def setUp(self):
        # All records go to this disposable folder rather than backend/data/.
        self.temp = tempfile.TemporaryDirectory()
        api.DATA = Path(self.temp.name)
        api.DB = api.DATA / 'test.db'
        api.TOKEN_FILE = api.DATA / 'token.txt'
        self.token = api.bootstrap()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), api.Handler)
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        # Shut down the server and remove the temporary SQLite database.
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, body=None, valid_token=True, origin=None):
        # Simulate a browser request without using a real Edge installation.
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + (self.token if valid_token else 'incorrect')}
        if origin is not None:
            headers['Origin'] = origin
        req = Request(self.base + path, method=method, headers=headers,
                      data=json.dumps(body).encode() if body is not None else None)
        try:
            with urlopen(req, timeout=4) as response:
                return response.status, json.load(response)
        except HTTPError as err:
            return err.code, json.loads(err.read())

    def create(self, kind, value):
        status, result = self.request('POST', '/api/indicators', {
            'kind': kind, 'value': value, 'source': 'Fictional source only',
            'reason': 'Temporary test record, not a real scam'
        })
        self.assertEqual(status, 201)
        return result['id']

    def approve(self, record_id):
        # These fabricated references satisfy the existing manual-review API.
        status, _ = self.request('POST', f'/api/indicators/{record_id}/review', {
            'decision': 'approved', 'note': 'Reviewed fictional test indicator',
            'evidence_reference': 'TEST-FEED-006'
        })
        self.assertEqual(status, 200)

    def share(self, record_id, enabled=True, valid_token=True):
        return self.request('POST', f'/api/indicators/{record_id}/sharing',
                            {'enabled': enabled}, valid_token=valid_token)

    def test_pending_report_cannot_be_shared(self):
        item = self.create('domain', 'test-domain.example.test')
        status, _ = self.share(item)
        self.assertEqual(status, 400)
        _, feed = self.request('GET', '/api/public-preview')
        self.assertEqual(feed['count'], 0)

    def test_sharing_requires_token_and_never_exposes_private_notes(self):
        item = self.create('domain', 'reviewed.example.test')
        self.approve(item)
        self.assertEqual(self.share(item, valid_token=False)[0], 401)
        self.assertEqual(self.share(item)[0], 200)
        _, feed = self.request('GET', '/api/public-preview')
        self.assertEqual(feed['count'], 1)
        self.assertEqual(feed['indicators'][0], {
            'kind': 'domain', 'value': 'reviewed.example.test',
            'classification': 'reviewed_report'
        })
        serialized = json.dumps(feed)
        for forbidden in ['TEST-FEED-006', 'Fictional source', 'review_note', 'evidence_reference', self.token]:
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(self.request('GET', '/api/public-preview', valid_token=False)[0], 401)

    def test_only_domain_or_url_and_no_query_credentials(self):
        email_id = self.create('email', 'test@example.test')
        self.approve(email_id)
        self.assertEqual(self.share(email_id)[0], 400)
        url_with_query = self.create('url', 'https://test-site.example.test/pay?token=private')
        self.approve(url_with_query)
        self.assertEqual(self.share(url_with_query)[0], 400)
        url_with_userinfo = self.create('url', 'https://user:password@test-site.example.test/pay')
        self.approve(url_with_userinfo)
        self.assertEqual(self.share(url_with_userinfo)[0], 400)
        clean_url = self.create('url', 'https://test-site.example.test/clean')
        self.approve(clean_url)
        self.assertEqual(self.share(clean_url)[0], 200)
        _, feed = self.request('GET', '/api/public-preview')
        self.assertEqual(feed['count'], 1)

    def test_dismiss_revokes_sharing_and_reapproval_does_not_restore(self):
        item = self.create('domain', 'reviewed.example.test')
        self.approve(item)
        self.share(item)
        status, _ = self.request('POST', f'/api/indicators/{item}/review', {
            'decision': 'dismissed', 'note': 'Retracted for testing'
        })
        self.assertEqual(status, 200)
        _, result = self.request('GET', '/api/public-preview')
        self.assertEqual(result['count'], 0)
        self.approve(item)
        _, result = self.request('GET', '/api/public-preview')
        self.assertEqual(result['count'], 0)

    def test_unsharing_removes_from_feed(self):
        item = self.create('domain', 'reviewed.example.test')
        self.approve(item)
        self.share(item)
        self.assertEqual(self.share(item, False)[0], 200)
        _, feed = self.request('GET', '/api/public-preview')
        self.assertEqual(feed['count'], 0)

    def test_json_import_does_not_import_publishing_permission(self):
        # A copied JSON file must NEVER silently opt a record into public sharing.
        status, result = self.request('POST', '/api/import', {'records': [{
            'kind': 'domain', 'value': 'imported.example.test',
            'status': 'verified', 'review_state': 'approved', 'public_share': 1,
            'source': 'TEST-FEED-006', 'reason': 'Reviewed fictional test entry'
        }]})
        self.assertEqual(status, 200)
        self.assertEqual(result['added'], 1)
        _, feed = self.request('GET', '/api/public-preview')
        self.assertEqual(feed['count'], 0)

    def test_request_origin_is_checked(self):
        item = self.create('domain', 'reviewed.example.test')
        self.approve(item)
        status, _ = self.request('POST', f'/api/indicators/{item}/sharing',
                                  {'enabled': True}, origin='https://not-the-extension.example')
        self.assertEqual(status, 403)

    def test_export_file_uses_same_safe_records(self):
        # Check the exporter writes valid JSON and does not alter the database.
        item = self.create('domain', 'reviewed.example.test')
        self.approve(item)
        self.share(item)
        _, feed = self.request('GET', '/api/public-preview')
        import sys
        sys.path.insert(0, str(FILE.parent))
        from public_feed import save_public_feed
        destination = Path(self.temp.name) / 'exports' / 'feed.json'
        save_public_feed(destination, feed)
        exported = json.loads(destination.read_text(encoding='utf-8'))
        self.assertEqual(exported, feed)


class MigrationTests(unittest.TestCase):
    def test_v05_data_defaults_to_private(self):
        # Create a minimal original table WITHOUT the public_share column.
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            api.DATA = root
            api.DB = root / 'legacy.db'
            api.TOKEN_FILE = root / 'token.txt'
            with closing(sqlite3.connect(api.DB)) as conn, conn:
                conn.execute('''CREATE TABLE indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                    value TEXT NOT NULL, canonical TEXT NOT NULL, status TEXT NOT NULL,
                    reason TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, review_state TEXT NOT NULL DEFAULT 'pending',
                    review_note TEXT NOT NULL DEFAULT '', evidence_reference TEXT NOT NULL DEFAULT '',
                    reviewed_at TEXT, UNIQUE(kind, canonical))''')
                conn.execute('''INSERT INTO indicators (kind,value,canonical,status,reason,source,
                    created_at,updated_at,review_state) VALUES
                    ('domain','old.example.test','old.example.test','verified',
                     'Reviewed old test','TEST-FEED-006','2026-01-01','2026-01-01','approved')''')
            api.bootstrap()  # Add v0.6 column without overwriting the report.
            with api.get_db() as conn:
                row = conn.execute('SELECT * FROM indicators').fetchone()
                self.assertEqual(row['value'], 'old.example.test')
                self.assertEqual(row['public_share'], 0)
                self.assertEqual(api.build_public_feed(conn)['count'], 0)


if __name__ == '__main__':
    unittest.main()
