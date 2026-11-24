"""Test v0.5 report moderation using only disposable SQLite files.

These tests do not modify your actual TrueDuck Sentinel database or contact the internet.
"""

from contextlib import closing  # Ensure SQLite files are released on Windows.
import importlib.util
import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# Load the same server.py used by START_DATABASE.cmd, without starting it.
FILE = Path(__file__).resolve().parents[1] / "backend" / "server.py"
spec = importlib.util.spec_from_file_location("scamlens_review_api", FILE)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        # All database writes go to this short-lived temporary directory.
        self.temp = tempfile.TemporaryDirectory()
        api.DATA = Path(self.temp.name)
        api.DB = api.DATA / "test.db"
        api.TOKEN_FILE = api.DATA / "token.txt"
        self.token = api.bootstrap()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, payload=None, valid_token=True):
        # Simulate the HTTP requests sent by an Edge extension page.
        req = Request(
            self.base + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method,
            headers={
                "Authorization": "Bearer " + (self.token if valid_token else "wrong"),
                "Content-Type": "application/json",
                "Origin": "chrome-extension://" + "a" * 32,
            },
        )
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as failure:
            return failure.code, json.loads(failure.read())

    def create_report(self):
        status, result = self.request("POST", "/api/indicators", {
            "kind": "email", "value": "case@example.test",
            "source": "Fictional report", "reason": "Test scenario only",
        })
        self.assertEqual(status, 201)
        return result["id"]

    def test_pending_then_approve_writes_audit_log(self):
        report_id = self.create_report()
        status, response = self.request("GET", "/api/indicators")
        self.assertEqual(response["records"][0]["review_state"], "pending")
        self.assertEqual(response["records"][0]["status"], "reported")

        # Approval without evidence is rejected, so it cannot turn a report into an assertion.
        status, _ = self.request("POST", f"/api/indicators/{report_id}/review", {
            "decision": "approved", "note": "Reviewed this report", "evidence_reference": ""
        })
        self.assertEqual(status, 400)
        status, result = self.request("POST", f"/api/indicators/{report_id}/review", {
            "decision": "approved", "note": "Reviewed fictional case details",
            "evidence_reference": "Case TEST-001",
        })
        self.assertEqual(status, 200)
        self.assertEqual(result["review_state"], "approved")
        _, list_result = self.request("GET", "/api/indicators")
        self.assertEqual(list_result["records"][0]["status"], "verified")
        self.assertEqual(list_result["records"][0]["review_state"], "approved")
        _, events = self.request("GET", "/api/reviews")
        self.assertEqual(events["records"][0]["decision"], "approved")
        self.assertEqual(events["records"][0]["indicator_id"], report_id)

    def test_dismiss_and_reopen(self):
        report_id = self.create_report()
        status, _ = self.request("POST", f"/api/indicators/{report_id}/review", {
            "decision": "dismissed", "note": "Not enough evidence", "evidence_reference": ""
        })
        self.assertEqual(status, 200)
        _, data = self.request("GET", "/api/indicators")
        self.assertEqual(data["records"][0]["review_state"], "dismissed")
        self.assertEqual(data["records"][0]["status"], "reported")

        status, _ = self.request("POST", f"/api/indicators/{report_id}/review", {
            "decision": "pending", "note": "New evidence arrived", "evidence_reference": ""
        })
        self.assertEqual(status, 200)
        _, data = self.request("GET", "/api/indicators")
        self.assertEqual(data["records"][0]["review_state"], "pending")
        _, log = self.request("GET", "/api/reviews")
        self.assertEqual([e["decision"] for e in log["records"]], ["pending", "dismissed"])

    def test_delete_erases_review_log(self):
        report_id = self.create_report()
        self.request("POST", f"/api/indicators/{report_id}/review", {
            "decision": "dismissed", "note": "Fictional case closed"
        })
        status, data = self.request("DELETE", f"/api/indicators/{report_id}")
        self.assertEqual(status, 200)
        self.assertTrue(data["deleted"])
        _, events = self.request("GET", "/api/reviews")
        self.assertEqual(events["records"], [])

    def test_json_restore_keeps_dismissed_report_dismissed(self):
        # Simulate a JSON export restored into a newly created database.
        payload = {"records": [{
            "kind": "email", "value": "dismissed@example.test", "status": "reported",
            "review_state": "dismissed", "review_note": "Test case is closed",
            "evidence_reference": "Case TEST-002", "reason": "Fictional test data",
            "source": "Local case reference",
        }]}
        status, summary = self.request("POST", "/api/import", payload)
        self.assertEqual(status, 200)
        self.assertEqual(summary["added"], 1)
        _, result = self.request("GET", "/api/indicators")
        self.assertEqual(result["records"][0]["review_state"], "dismissed")
        self.assertEqual(result["records"][0]["review_note"], "Test case is closed")

    def test_json_restore_rejects_conflicting_review_status(self):
        status, _ = self.request("POST", "/api/import", {"records": [{
            "kind": "email", "value": "contradiction@example.test",
            "status": "verified", "review_state": "dismissed",
            "reason": "Reviewed test record", "source": "Case TEST-004"
        }]})
        self.assertEqual(status, 400)
        _, result = self.request("GET", "/api/indicators")
        self.assertEqual(result["records"], [])

    def test_reviews_require_token(self):
        report_id = self.create_report()
        status, _ = self.request("POST", f"/api/indicators/{report_id}/review", {
            "decision": "approved", "note": "Reviewed case details",
            "evidence_reference": "Case TEST-001",
        }, valid_token=False)
        self.assertEqual(status, 401)
        status, _ = self.request("GET", "/api/reviews", valid_token=False)
        self.assertEqual(status, 401)

    def test_rejects_bad_review_decisions(self):
        report_id = self.create_report()
        for payload in [
            {"decision": "approved", "note": "tiny", "evidence_reference": "source"},
            {"decision": "deleted", "note": "Reasonable explanation"},
            {"decision": "dismissed", "note": ""},
        ]:
            status, _ = self.request("POST", f"/api/indicators/{report_id}/review", payload)
            self.assertEqual(status, 400)
        _, events = self.request("GET", "/api/reviews")
        self.assertEqual(events["records"], [])


class LegacyMigrationTests(unittest.TestCase):
    def test_upgrades_legacy_schema_without_losing_records(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            api.DATA = root
            api.DB = root / "legacy.db"
            api.TOKEN_FILE = root / "token.txt"
            # Create a table as it existed in v0.4, before review columns existed.
            with closing(sqlite3.connect(api.DB)) as conn, conn:
                conn.execute("""CREATE TABLE indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL, value TEXT NOT NULL, canonical TEXT NOT NULL,
                    status TEXT NOT NULL, reason TEXT NOT NULL, source TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    UNIQUE(kind, canonical))""")
                conn.execute("""INSERT INTO indicators(kind,value,canonical,status,reason,source,created_at,updated_at)
                    VALUES ('email','legacy@example.test','legacy@example.test','verified',
                    'Legacy test case','Case REF-123','2026-01-01','2026-01-01')""")
            api.bootstrap()
            # Re-running bootstrap should be safe and preserve the old record.
            api.bootstrap()
            with api.get_db() as conn:
                row = conn.execute("SELECT * FROM indicators").fetchone()
                self.assertEqual(row["value"], "legacy@example.test")
                self.assertEqual(row["status"], "verified")
                self.assertEqual(row["review_state"], "approved")
                self.assertIsNotNone(conn.execute("SELECT name FROM sqlite_master WHERE name='review_events'").fetchone())


if __name__ == "__main__":
    unittest.main()
