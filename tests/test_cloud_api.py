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
    """Legacy publishing cannot bypass community moderation."""
    def setUp(self):
        self.client = TestClient(api.app)
        from sqlalchemy import delete
        with api.engine.begin() as conn:
            conn.execute(delete(api.community_public_table))
            conn.execute(delete(api.indicators_table))

    def test_health_and_empty_feed(self):
        self.assertEqual(self.client.get('/health').json()['status'], 'ok')
        self.assertEqual(self.client.get('/v1/feed').json()['indicators'], [])

    def test_legacy_upload_rejected(self):
        item = {'kind':'domain','value':'bypass.example.test','classification':'reviewed_report'}
        for headers in ({}, {'Authorization':'Bearer '+os.environ['SCAMLENS_PUBLISH_TOKEN']}, {'Authorization':'Bearer wrong'}):
            result = self.client.put('/v1/admin/feed', headers=headers, json={'schema':'scamlens.public-feed.v1','indicators':[item]})
            self.assertEqual(result.status_code, 410)
        self.assertEqual(self.client.get('/v1/feed').json()['count'], 0)

    def test_old_private_uploads_are_not_distributed(self):
        with api.engine.begin() as conn:
            conn.execute(api.indicators_table.insert().values(kind='domain', value='old.example.test', classification='reviewed_report'))
        self.assertEqual(self.client.get('/v1/feed').json()['indicators'], [])
        with api.engine.connect() as conn:
            self.assertEqual(len(conn.execute(api.indicators_table.select()).all()), 1)

    def test_etag_304_when_unchanged(self):
        first = self.client.get('/v1/feed')
        self.assertEqual(self.client.get('/v1/feed', headers={'If-None-Match':first.headers['etag']}).status_code, 304)

    def test_publishable_indicator_validation(self):
        for kind, value in [('email','private@example.test'), ('domain','localhost'), ('domain','192.168.1.5'), ('url','http://127.0.0.1/page'), ('url','https://example.test/path?token=secret'), ('url','https://user:secret@example.test/path'), ('url','https://example.test/path#private'), ('domain','UPPER.example.test')]:
            with self.subTest(kind=kind, value=value):
                with self.assertRaises(ValueError):
                    api.safe_indicator({'kind':kind,'value':value,'classification':'reviewed_report'})
        self.assertEqual(api.safe_indicator({'kind':'domain','value':'valid.example.test','classification':'reviewed_report'})['value'],'valid.example.test')

    def test_no_public_publishing_route(self):
        self.assertEqual(self.client.post('/v1/admin/feed').status_code, 405)

if __name__ == '__main__':
    unittest.main()
