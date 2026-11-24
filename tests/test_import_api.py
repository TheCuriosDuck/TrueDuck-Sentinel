"""Exercise JSON import and access-token protection with temporary data files."""
# The tests start a temporary local HTTP server, not your normal TrueDuck Sentinel server.
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

path = Path(__file__).resolve().parents[1] / 'backend' / 'server.py'
spec = importlib.util.spec_from_file_location('scamlens_local_api_tests', path)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


# Verify that imports preserve data and reject unsafe or unauthorized requests.
class ImportApiTests(unittest.TestCase):
    def setUp(self):
        # Create a disposable database so tests never alter your saved watchlist.
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        api.DATA = root
        api.DB = root / 'test.db'
        api.TOKEN_FILE = root / 'token.txt'
        self.token = api.bootstrap()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), api.Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        # Stop the test server and remove the temporary database files.
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, method, path, payload=None, valid_token=True):
        data = json.dumps(payload).encode() if payload is not None else None
        token = self.token if valid_token else 'wrong'
        req = Request(self.url + path, data=data, method=method, headers={
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'Origin': 'chrome-extension://' + 'a' * 32,
        })
        try:
            with urlopen(req, timeout=3) as resp:
                return resp.status, json.load(resp)
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_import_merges_and_skips_duplicates(self):
        example = {'kind': 'email', 'value': 'ALERTS@EXAMPLE.TEST', 'status': 'reported', 'reason': 'demo'}
        status, response = self.request('POST', '/api/import', {'records': [example, example]})
        self.assertEqual(status, 200)
        self.assertEqual(response, {'added': 1, 'skipped': 1})
        status, response = self.request('GET', '/api/indicators')
        self.assertEqual(status, 200)
        self.assertEqual(len(response['records']), 1)
        self.assertEqual(response['records'][0]['canonical'], 'alerts@example.test')
        self.assertEqual(response['records'][0]['status'], 'reported')
        status, response = self.request('POST', '/api/import', {'records': [example]})
        self.assertEqual(status, 200)
        self.assertEqual(response['added'], 0)

    def test_invalid_batch_is_not_imported(self):
        status, response = self.request('POST', '/api/import', {'records': [
            {'kind': 'domain', 'value': 'example.test'},
            {'kind': 'phone', 'value': '123'},
        ]})
        self.assertEqual(status, 400)
        status, response = self.request('GET', '/api/indicators')
        self.assertEqual(response['records'], [])

    def test_reviewed_requires_evidence_source_and_explanation(self):
        base = {'kind':'email','value':'example@test.invalid','status':'verified'}
        status, data = self.request('POST','/api/indicators',base)
        self.assertEqual(status,400)
        status, data = self.request('POST','/api/indicators',{
            **base, 'reason': 'Recorded in an internal test case.',
            'source': 'Case reference #TEST-001'
        })
        self.assertEqual(status,201)
        status, data = self.request('POST','/api/import',{'records':[
            {'kind':'domain', 'value':'phish.invalid', 'status':'verified', 'reason':'', 'source':'Manual entry'}
        ]})
        self.assertEqual(status,400)

    def test_external_endpoint_remains_separate(self):
        # On a fresh install, the feed endpoint should have no records.
        status, data = self.request('GET', '/api/intelligence')
        self.assertEqual(status, 200)
        self.assertEqual(data['feed'], 'urlhaus')
        self.assertEqual(data['records'], [])
        self.assertIsNone(data['updatedAt'])

        # The outside-feed endpoint also needs the secret token.
        status, data = self.request('GET', '/api/intelligence', valid_token=False)
        self.assertEqual(status, 401)

    def test_auth_required(self):
        status, response = self.request('POST', '/api/import', {'records': [{'kind': 'domain', 'value': 'example.test'}]}, valid_token=False)
        self.assertEqual(status, 401)


if __name__ == '__main__':
    unittest.main()
