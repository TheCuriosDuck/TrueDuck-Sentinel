"""Cloud API tests: authentication, privacy, validation, retraction, and caching."""

# Keep test data outside the user's actual project database.
import importlib
import json
import os
import tempfile
import atexit
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

# These variables must exist BEFORE importing cloud_api.app to select a test DB.
TEST_SPACE = tempfile.TemporaryDirectory(prefix='scamlens-cloud-test-')
os.environ['SCAMLENS_CLOUD_DATABASE_URL'] = 'sqlite:///' + str(Path(TEST_SPACE.name) / 'test.db')
os.environ['SCAMLENS_PUBLISH_TOKEN'] = 'local-testing-secret-is-long-and-random-enough-12345'
api = importlib.import_module('cloud_api.app')


# Windows will not delete an SQLite database while its connection is still open.
# SQLAlchemy keeps database connections in a pool even after a request finishes.
# Dispose of the pool BEFORE Python cleans up the temporary test directory.
def _close_test_cloud_database():
    # Release SQLite file handles opened by FastAPI and SQLAlchemy tests.
    api.engine.dispose()

    # Delete ONLY the temporary test database folder, never the real user database.
    TEST_SPACE.cleanup()


# Runs after the tests finish and before temporary directories are finalized.
atexit.register(_close_test_cloud_database)



class CloudApiTests(unittest.TestCase):
    """Exercise the new cloud-facing API without opening a network port."""

    def setUp(self):
        self.client = TestClient(api.app)
        self.headers = {'Authorization': 'Bearer ' + os.environ['SCAMLENS_PUBLISH_TOKEN']}
        self.client.put('/v1/admin/feed', headers=self.headers,
                        json={'schema': 'scamlens.public-feed.v1', 'indicators': []})

    def sample(self, indicators):
        return {'schema': 'scamlens.public-feed.v1', 'generated_at': 'ignored',
                'indicators': indicators}

    def test_health_and_empty_feed(self):
        self.assertEqual(self.client.get('/health').json()['status'], 'ok')
        feed = self.client.get('/v1/feed').json()
        self.assertEqual(feed['count'], 0)
        self.assertEqual(feed['indicators'], [])

    def test_token_required_and_invalid_rejected(self):
        record = self.sample([])
        self.assertEqual(self.client.put('/v1/admin/feed', json=record).status_code, 401)
        self.assertEqual(self.client.put('/v1/admin/feed', headers={'Authorization': 'Bearer wrong'}, json=record).status_code, 401)

    def test_accepted_records_are_minimized(self):
        item = {'kind': 'domain', 'value': 'review-feed.example.test',
                'classification': 'reviewed_report', 'review_note': 'secret note', 'email': 'private@example.test'}
        response = self.client.put('/v1/admin/feed', headers=self.headers, json=self.sample([item]))
        self.assertEqual(response.status_code, 200, response.text)
        feed = self.client.get('/v1/feed').json()
        self.assertEqual(feed['count'], 1)
        self.assertEqual(feed['indicators'], [{'kind':'domain', 'value':'review-feed.example.test', 'classification':'reviewed_report'}])
        self.assertNotIn('secret note', json.dumps(feed))
        self.assertNotIn('private@example.test', json.dumps(feed))
        self.assertNotIn(os.environ['SCAMLENS_PUBLISH_TOKEN'], json.dumps(feed))

    def test_retraction_replaces_entire_feed(self):
        item = {'kind': 'url', 'value': 'https://review-feed.example.test/path', 'classification': 'reviewed_report'}
        one = self.client.put('/v1/admin/feed', headers=self.headers, json=self.sample([item])).json()
        two = self.client.put('/v1/admin/feed', headers=self.headers, json=self.sample([])).json()
        self.assertGreater(two['revision'], one['revision'])
        self.assertEqual(self.client.get('/v1/feed').json()['count'], 0)

    def test_etag_304_when_unchanged(self):
        first = self.client.get('/v1/feed')
        unchanged = self.client.get('/v1/feed', headers={'If-None-Match': first.headers['etag']})
        self.assertEqual(unchanged.status_code, 304)

    def test_rejects_private_types_and_local_urls(self):
        invalid = [
            {'kind':'email', 'value':'private@example.test', 'classification':'reviewed_report'},
            {'kind':'domain', 'value':'localhost', 'classification':'reviewed_report'},
            {'kind':'domain', 'value':'192.168.1.5', 'classification':'reviewed_report'},
            {'kind':'url', 'value':'http://127.0.0.1/page', 'classification':'reviewed_report'},
            {'kind':'url', 'value':'https://review-feed.example.test/path?token=private', 'classification':'reviewed_report'},
            {'kind':'url', 'value':'https://name:secret@review-feed.example.test/path', 'classification':'reviewed_report'},
            {'kind':'url', 'value':'https://review-feed.example.test/path#private', 'classification':'reviewed_report'},
            {'kind':'domain', 'value':'REVIEW-feed.example.test', 'classification':'reviewed_report'},
            {'kind':'domain', 'value':'review-feed.example.test', 'classification':'reported'},
        ]
        for entry in invalid:
            with self.subTest(entry=entry):
                response = self.client.put('/v1/admin/feed', headers=self.headers, json=self.sample([entry]))
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get('/v1/feed').json()['count'], 0)

    def test_duplicates_are_rejected(self):
        item = {'kind':'domain', 'value':'review-feed.example.test', 'classification':'reviewed_report'}
        response = self.client.put('/v1/admin/feed', headers=self.headers, json=self.sample([item, item]))
        self.assertEqual(response.status_code, 422)

    def test_limits_upload(self):
        response = self.client.put('/v1/admin/feed', headers={**self.headers, 'Content-Type':'application/json'}, content=b'a'*700_001)
        self.assertEqual(response.status_code, 413)

    def test_no_public_write_route(self):
        self.assertEqual(self.client.post('/v1/reports', json={'kind':'domain','value':'test.example'}).status_code, 401)
        self.assertEqual(self.client.post('/v1/admin/feed', headers=self.headers).status_code, 405)


if __name__ == '__main__':
    unittest.main()
