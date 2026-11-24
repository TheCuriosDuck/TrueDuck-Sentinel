"""TrueDuck Sentinel's local database and HTTP API.

This is a beginner-friendly, commented Python backend. It uses only the Python
standard library (Python 3.10 or newer); there is no need to install Flask.

The server stays on YOUR computer at 127.0.0.1. It serves the optional demo
page, stores YOUR indicators in SQLite, and lets the Edge extension retrieve
both your indicators and optional outside malware URL intelligence.
"""

from __future__ import annotations

# --- Imports: built-in Python tools used by the database and web server. ---
import json                     # Convert between Python dictionaries and JSON for the extension.
import os                       # Restrict the access-token file where the OS supports it.
import re                       # Check input formats with regular expressions.
import secrets                  # Generate and compare the private access token securely.
import sqlite3                  # Open and update the local SQLite database file.
from datetime import datetime, timezone  # Record dates consistently in UTC.
from contextlib import contextmanager # Close database connections reliably after use.
from typing import Iterator          # Type hint for the managed SQLite connection.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # HTTP API.
from pathlib import Path        # Safely find folders relative to this Python file.
from urllib.parse import urlsplit  # Read components of a website URL.
# Load the public-feed helper relative to this file. This works both when you run
# server.py directly and when automated tests load it by its filesystem path.
import importlib.util
_feed_spec = importlib.util.spec_from_file_location("scamlens_public_feed", Path(__file__).resolve().parent / "public_feed.py")
_feed_module = importlib.util.module_from_spec(_feed_spec)
_feed_spec.loader.exec_module(_feed_module)
build_public_feed = _feed_module.build_public_feed  # Build minimal opt-in exports.
can_publish = _feed_module.can_publish          # Enforce type/status/privacy checks.

# --- Local configuration: these paths are inside the backend folder. ---
ROOT = Path(__file__).resolve().parent   # Folder containing server.py.
DATA = ROOT / "data"                      # Private folder for persistent data.
DB = DATA / "scamlens.db"                # Your SQLite database (do not overwrite when upgrading).
TOKEN_FILE = DATA / "access_token.txt"   # Secret needed to edit/read your local database API.
HOST, PORT = "127.0.0.1", 8765           # Local computer only; NEVER change to 0.0.0.0.

# Allowed indicator types and the statuses you can assign to YOUR records.
KINDS = {"domain", "url", "email", "phone", "address"}
STATUSES = {"reported", "verified"}


def utc_now() -> str:
    """Return a timestamp in UTC for a record's creation/update time."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonicalize(kind: str, value: str) -> str:
    """Put an indicator into a predictable form so duplicates can be recognized."""
    value = value.strip()  # Remove accidental spaces at the beginning and end.
    if not value or len(value) > 500:
        raise ValueError("Enter a value between 1 and 500 characters")

    if kind == "email":
        # Require a plausible email shape and ignore case during matching.
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value.lower()

    if kind == "phone":
        # Keep digits only; remove the optional US/Canada country code (1).
        number = re.sub(r"\D", "", value)
        if len(number) == 11 and number[0] == "1":
            number = number[1:]
        if len(number) != 10:
            raise ValueError("Use a 10-digit US/Canada phone number")
        return number

    if kind == "address":
        # Make addresses comparable despite capitalization or punctuation.
        normalized = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()
        if len(normalized) < 8:
            raise ValueError("Enter a more complete street address")
        return normalized

    if kind in {"url", "domain"}:
        # Domain entries may be written as example.org without https://.
        parsed = urlsplit(value if "://" in value else "https://" + value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only normal HTTP(S) URLs or domains are supported")
        hostname = parsed.hostname.rstrip(".").lower()
        try:
            hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError as ex:
            raise ValueError("Invalid domain name") from ex
        if not re.fullmatch(r"[a-z0-9.-]+", hostname) or "." not in hostname:
            raise ValueError("Enter a valid domain name")
        if kind == "domain":
            # Ignore paths when a user wants to track a whole domain.
            return hostname

        # For an exact URL, retain the path and query but ignore #fragments.
        # A malformed port will raise ValueError and be rejected by the API.
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or "/"
        return f"{parsed.scheme}://{hostname}{port}{path}" + (f"?{parsed.query}" if parsed.query else "")

    raise ValueError("Unsupported indicator type")


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Open, commit/rollback, and ALWAYS close a SQLite database connection."""
    conn = sqlite3.connect(DB, timeout=5)  # Open the local database file.
    conn.row_factory = sqlite3.Row        # Allow row["kind"] as well as row[0].
    try:
        with conn:                       # Commit on success, roll back on an error.
            yield conn                   # Give the calling `with` block this connection.
    finally:
        conn.close()                     # Release the file and its system resources.


def bootstrap() -> str:
    """Create missing files/tables without deleting any existing user records."""
    DATA.mkdir(parents=True, exist_ok=True)  # First run: create backend/data.
    if not TOKEN_FILE.exists():
        # First run: create a random secret to authorize extension requests.
        TOKEN_FILE.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        try:
            os.chmod(TOKEN_FILE, 0o600)  # Reduce access on compatible systems.
        except OSError:
            pass  # Windows file permissions work differently from Unix chmod.

    with get_db() as conn:
        # Personal records: only your manual entries/imports are stored here.
        # UNIQUE prevents duplicate values for the same indicator type.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('domain','url','email','phone','address')),
                value TEXT NOT NULL,
                canonical TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'reported' CHECK(status IN ('reported','verified')),
                reason TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'Manual entry',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(kind, canonical)
            )
        """)
        # External records are intentionally stored in a DIFFERENT table.
        # They must not silently become "verified" or overwrite your reports.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind = 'url'),
                value TEXT NOT NULL,
                canonical TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status = 'external'),
                reason TEXT NOT NULL,
                source TEXT NOT NULL,
                reference TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE(feed, canonical)
            )
        """)
        # A small metadata table lets the dashboard show the feed's last refresh.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_syncs (
                feed TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                record_count INTEGER NOT NULL
            )
        """)

        # v0.5 database migration: add review fields to the EXISTING indicator table.
        # PRAGMA table_info tells us which columns are already present so an upgrade
        # won't erase reports you created with older versions of TrueDuck Sentinel.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(indicators)")}
        if "review_state" not in columns:
            conn.execute("ALTER TABLE indicators ADD COLUMN review_state TEXT NOT NULL DEFAULT 'pending'")
            # Keep older reviewed reports reviewed; don't change their status.
            conn.execute("UPDATE indicators SET review_state='approved' WHERE status='verified'")
        if "review_note" not in columns:
            conn.execute("ALTER TABLE indicators ADD COLUMN review_note TEXT NOT NULL DEFAULT ''")
        if "evidence_reference" not in columns:
            conn.execute("ALTER TABLE indicators ADD COLUMN evidence_reference TEXT NOT NULL DEFAULT ''")
        if "reviewed_at" not in columns:
            conn.execute("ALTER TABLE indicators ADD COLUMN reviewed_at TEXT")

        # v0.6: Public-feed sharing is OPT-IN for each reviewed domain/URL.
        # Existing records are private after migration, regardless of their review status.
        if "public_share" not in columns:
            conn.execute("ALTER TABLE indicators ADD COLUMN public_share INTEGER NOT NULL DEFAULT 0")

        # Keep a history of human decisions. This is NOT a record of detections
        # and contains only manual review events, not webpage text.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_id INTEGER NOT NULL,
                indicator_value TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('approved','dismissed','pending')),
                note TEXT NOT NULL,
                evidence_reference TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT NOT NULL
            )
        """)

    # Reuse the same token every time the server starts.
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


class Handler(BaseHTTPRequestHandler):
    """Handle HTTP requests sent by Microsoft Edge or local test programs."""

    server_version = "TrueDuckSentinelLocal/0.6"

    def log_message(self, format, *args):
        # Avoid logging URL indicator values and authentication details.
        pass

    def _origin_allowed(self) -> bool:
        """Refuse normal websites trying to call the extension's private API."""
        origin = self.headers.get("Origin", "")
        # Command-line tools usually send no Origin; extension pages use this URL format.
        return not origin or bool(re.fullmatch(r"chrome-extension://[a-z]{32}", origin))

    def _headers(self, status: int, content_type="application/json; charset=utf-8"):
        """Send response headers for requests that have no response body (OPTIONS)."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")  # Avoid browser/proxy caching.
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin", "")
        if origin and self._origin_allowed():
            # Allow extension pages to read the response across origins (CORS).
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def _json(self, status: int, value: dict | list):
        """Convert a Python object into JSON and return it to the extension."""
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin", "")
        if origin and self._origin_allowed():
            # Browsers require this before extension code can read the response.
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(payload)  # Write response bytes to the browser connection.

    def _authorized(self) -> bool:
        """Check both the request Origin and the Bearer token."""
        if not self._origin_allowed():
            self._json(403, {"error": "Unsupported request origin"})
            return False
        stored = TOKEN_FILE.read_text(encoding="utf-8").strip()
        provided = self.headers.get("Authorization", "")
        # Constant-time comparison helps protect against timing-based guessing.
        if not secrets.compare_digest(provided, f"Bearer {stored}"):
            self._json(401, {"error": "Invalid database access token"})
            return False
        return True

    def do_OPTIONS(self):
        """Answer the CORS preflight that Edge may send before a JSON request."""
        if not self._origin_allowed():
            self._json(403, {"error": "Unsupported request origin"})
            return
        self._headers(204)

    def do_GET(self):
        """Return the demo, your watchlist, or outside threat feed records."""
        if self.path == "/demo":
            # Demonstration only: the following strings are FICTIONAL indicators.
            # This page never sends real messages or contacts example.test.
            page = b'''<!doctype html><html lang="en"><meta charset="utf-8"><title>TrueDuck Sentinel test page</title>
<style>body{font:16px system-ui;max-width:680px;margin:65px auto;color:#26364b}article{padding:25px;background:#f2f5fa;border-radius:12px}</style>
<h1>TrueDuck Sentinel test page</h1><p>This is a fictional message to help you test your own extension. No actual account is at risk.</p>
<article><h2>Fake message for testing</h2><p>URGENT PAYMENT: Act now, pay using a gift card or your account will be suspended.</p>
<p>Send details to alerts@example.test or call (202) 555-0199.</p><p>Learn more at <a href="https://example-scam.test">example-scam.test</a>.</p>
<p>External feed test URL: <a href="https://example-malware.test/payload">example-malware.test/payload</a> (fictional, only matches after a --sample import).</p></article>
<p>Add any of the example email, phone or domain values to your own database as <b>reported</b> entries, then reload to test watchlist matching.</p>
</html>'''
            # Return this demo as HTML instead of JSON.
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)
            return

        # All database API routes require the private token.
        if not self._authorized():
            return
        if self.path == "/api/health":
            # Lightweight connection check for Settings.
            self._json(200, {"ok": True, "service": "TrueDuck Sentinel local database", "version": "0.6"})
        elif self.path == "/api/public-preview":
            # Preview only user-opted-in approved domain/URL entries.
            # This remains a PRIVATE token-protected endpoint: it is NOT online hosting.
            with get_db() as conn:
                feed = build_public_feed(conn)
            self._json(200, feed)
        elif self.path == "/api/indicators":
            # Return only user-managed records, so the Remove button is safe.
            with get_db() as conn:
                rows = conn.execute("SELECT * FROM indicators ORDER BY id DESC").fetchall()
            self._json(200, {"records": [dict(row) for row in rows]})
        elif self.path == "/api/reviews":
            # Show the last 100 review decisions in the private dashboard.
            # Values are only from manually entered records, never webpage bodies.
            with get_db() as conn:
                rows = conn.execute("""SELECT * FROM review_events
                                       ORDER BY id DESC LIMIT 100""").fetchall()
            self._json(200, {"records": [dict(row) for row in rows]})
        elif self.path == "/api/intelligence":
            # Return external exact URLs separately, with attribution and last-sync time.
            with get_db() as conn:
                rows = conn.execute("""SELECT kind, value, canonical, status, reason, source, reference
                                       FROM feed_indicators WHERE feed='urlhaus' ORDER BY id DESC""").fetchall()
                last = conn.execute("SELECT updated_at FROM feed_syncs WHERE feed='urlhaus'").fetchone()
            self._json(200, {
                "feed": "urlhaus",
                "updatedAt": last["updated_at"] if last else None,
                "count": len(rows),
                "records": [dict(row) for row in rows],
            })
        else:
            self._json(404, {"error": "Unknown endpoint"})

    def do_POST(self):
        """Add one personal report or import a batch of personal records."""
        if not self._authorized():
            return
        # Per-record publishing preference. This is a private ADMIN action, not a
        # public write API. Never allow a webpage to approve or publish a record.
        publish_match = re.fullmatch(r"/api/indicators/(\d+)/sharing", self.path)
        if publish_match:
            self._set_public_sharing(int(publish_match.group(1)))
            return
        if self.path == "/api/import":
            self._import_records()  # Bulk import has its own validation logic.
            return
        # Review decisions have a separate endpoint from new report submissions.
        # This makes approving or dismissing a report an explicit manual action.
        review_match = re.fullmatch(r"/api/indicators/(\d+)/review", self.path)
        if review_match:
            self._review_record(int(review_match.group(1)))
            return
        if self.path != "/api/indicators":
            self._json(404, {"error": "Unknown endpoint"})
            return
        try:
            # Limit request size so a local website cannot overload the server.
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 10000:
                self._json(413, {"error": "Request must be between 1 and 10000 bytes"})
                return
            data = json.loads(self.rfile.read(size))  # Read incoming JSON into a dict.
            if not isinstance(data, dict):
                raise ValueError("Record must be an object")
            kind = str(data.get("kind", "")).lower()
            if kind not in KINDS:
                raise ValueError("Choose a valid indicator type")
            status = str(data.get("status", "reported"))
            if status not in STATUSES:
                raise ValueError("Status must be reported or verified")
            value = str(data.get("value", "")).strip()
            canonical = canonicalize(kind, value)
            reason = str(data.get("reason", "")).strip()[:500]
            source = str(data.get("source", "Manual entry")).strip()[:200] or "Manual entry"
            # A reviewed entry needs evidence; never treat a blank report as verified.
            if status == "verified" and (len(reason) < 10 or source.lower() in ("manual entry", "imported file") or len(source) < 5):
                raise ValueError("Reviewed records need an explanation (10+ characters) and an evidence source/reference")
            now = utc_now()
            with get_db() as conn:
                # Parameter placeholders (?) protect SQL from injected input.
                # New submissions are pending by default. Legacy direct verified
                # submissions are accepted only with an explanation and source.
                state = "approved" if status == "verified" else "pending"
                cursor = conn.execute("""
                    INSERT INTO indicators(kind,value,canonical,status,reason,source,
                                           created_at,updated_at,review_state,reviewed_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (kind, value, canonical, status, reason, source, now, now,
                      state, now if state == "approved" else None))
                if state == "approved":
                    # Even legacy approvals should appear in the audit log.
                    conn.execute("""INSERT INTO review_events
                        (indicator_id, indicator_value, decision, note, evidence_reference, reviewed_at)
                        VALUES (?, ?, 'approved', ?, ?, ?)""",
                        (cursor.lastrowid, value, reason, source, now))
            self._json(201, {"id": cursor.lastrowid, "message": "Indicator added"})
        except sqlite3.IntegrityError:
            self._json(409, {"error": "This indicator is already in your database"})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})

    def _set_public_sharing(self, record_id: int):
        """Opt a specific reviewed domain or URL into or out of a future public feed.

        Only the owner can call this endpoint using the private API token. Sharing
        does not automatically upload any data, and the original evidence stays
        inside the private SQLite database.
        """
        try:
            # Reject oversized or missing JSON bodies before reading from the socket.
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 256:
                self._json(413, {"error": "Publishing request must be 1–256 bytes"})
                return
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or type(data.get("enabled")) is not bool:
                raise ValueError("Send an enabled field containing true or false")
            enabled = data["enabled"]

            # Check the current status inside a transaction to prevent publishing
            # a record which has since been dismissed or returned to review.
            with get_db() as conn:
                record = conn.execute("SELECT * FROM indicators WHERE id=?", (record_id,)).fetchone()
                if record is None:
                    self._json(404, {"error": "Record not found"})
                    return
                if enabled and not can_publish(record):
                    self._json(400, {"error": "Only approved domains or URLs without query strings, credentials or private hosts can be shared"})
                    return
                conn.execute("UPDATE indicators SET public_share=?, updated_at=? WHERE id=?",
                             (1 if enabled else 0, utc_now(), record_id))
            self._json(200, {"id": record_id, "public_share": bool(enabled)})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})

    def _import_records(self):
        """Validate and merge up to 100 personal records per request."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 120000:
                self._json(413, {"error": "Import request must be 1–120000 bytes"})
                return
            data = json.loads(self.rfile.read(size))
            batch = data.get("records") if isinstance(data, dict) else None
            if not isinstance(batch, list) or not 1 <= len(batch) <= 100:
                raise ValueError("Send 1 to 100 records in an import batch")
            prepared = []  # Gather everything first so a bad entry rejects the whole batch.
            now = utc_now()
            for index, item in enumerate(batch, start=1):
                if not isinstance(item, dict):
                    raise ValueError(f"Record {index}: expected a record object")
                kind = str(item.get("kind", "")).lower()
                status = str(item.get("status", "reported")).lower()
                if kind not in KINDS or status not in STATUSES:
                    raise ValueError(f"Record {index}: invalid type or status")
                value = str(item.get("value", "")).strip()
                canonical = canonicalize(kind, value)
                reason = str(item.get("reason", ""))[:500]
                source = str(item.get("source", "Imported file"))[:200] or "Imported file"
                if status == "verified" and (len(reason) < 10 or source.lower() in ("manual entry", "imported file") or len(source) < 5):
                    raise ValueError(f"Record {index}: reviewed records require an explanation and source")

                # An exported v0.5 record includes its current review_state.
                # Preserve 'dismissed' on restore or it would begin alerting again.
                # Old v0.4 JSON files have no review_state; infer their state.
                state = str(item.get("review_state") or ("approved" if status == "verified" else "pending"))
                if state not in {"approved", "pending", "dismissed"}:
                    raise ValueError(f"Record {index}: invalid review state")
                if (state == "approved") != (status == "verified"):
                    raise ValueError(f"Record {index}: review state and status disagree")
                note = str(item.get("review_note", ""))[:500]
                evidence = str(item.get("evidence_reference", ""))[:300]
                reviewed_at = str(item.get("reviewed_at") or "")[:40] or None
                prepared.append((kind, value, canonical, status, reason, source, now, now,
                                 state, note, evidence, reviewed_at))
            with get_db() as conn:
                before = conn.total_changes
                # INSERT OR IGNORE preserves existing entries, including previous
                # review decisions, rather than overwriting them during an import.
                # Import never sets public_share; it defaults to 0 for every new row.
                # Even a backup containing public_share=1 cannot publish itself.
                conn.executemany("""
                    INSERT OR IGNORE INTO indicators
                    (kind, value, canonical, status, reason, source, created_at,
                     updated_at, review_state, review_note, evidence_reference, reviewed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, prepared)
                added = conn.total_changes - before
            self._json(200, {"added": added, "skipped": len(batch) - added})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})

    def _review_record(self, record_id: int):
        """Approve, dismiss, or reopen one report and log that decision.

        A reviewer must supply a meaningful note. Approval also needs a
        supporting reference. This is a manual review workflow; it cannot
        independently establish whether a real person committed fraud.
        """
        try:
            # Restrict body sizes so a mistaken or malicious client cannot
            # send huge logs or webpage contents into the local database.
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 5000:
                self._json(413, {"error": "Review request must be 1–5000 bytes"})
                return
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Review request must be an object")
            decision = str(data.get("decision", "")).strip().lower()
            note = str(data.get("note", "")).strip()
            evidence = str(data.get("evidence_reference", "")).strip()
            if decision not in {"approved", "dismissed", "pending"}:
                raise ValueError("Choose approve, dismiss, or reopen")
            if not 5 <= len(note) <= 500:
                raise ValueError("Write a review note between 5 and 500 characters")
            if len(evidence) > 300:
                raise ValueError("Evidence reference must be 300 characters or less")
            if decision == "approved" and (len(note) < 10 or len(evidence) < 5 or
                                           evidence.lower() in {"manual entry", "imported file", "none"}):
                raise ValueError("Approval requires a 10+ character note and a specific evidence reference")

            # Use one transaction: changing the status and writing the event
            # either both succeed or both roll back.
            now = utc_now()
            with get_db() as conn:
                item = conn.execute("SELECT id, value FROM indicators WHERE id=?", (record_id,)).fetchone()
                if item is None:
                    self._json(404, {"error": "Report not found"})
                    return
                # Dismissed reports stay in the SQLite database but MUST NOT
                # be included in the synced browser watchlist.
                status = "verified" if decision == "approved" else "reported"
                # A new review decision revokes prior public-feed consent.
                # The owner must explicitly opt in again after re-approval.
                conn.execute("""UPDATE indicators SET review_state=?, status=?,
                    review_note=?, evidence_reference=?, reviewed_at=?, updated_at=?, public_share=0
                    WHERE id=?""", (decision, status, note, evidence, now, now, record_id))
                conn.execute("""INSERT INTO review_events
                    (indicator_id, indicator_value, decision, note, evidence_reference, reviewed_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (record_id, item["value"], decision, note, evidence, now))
            self._json(200, {"updated": True, "review_state": decision})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})

    def do_DELETE(self):
        """Delete a user-managed indicator when the Remove button is pressed."""
        if not self._authorized():
            return
        # Only allow a numeric ID for the manual-indicators table.
        match = re.fullmatch(r"/api/indicators/(\d+)", self.path)
        if not match:
            self._json(404, {"error": "Unknown endpoint"})
            return
        with get_db() as conn:
            record_id = int(match.group(1))
            deleted = conn.execute("DELETE FROM indicators WHERE id=?", (record_id,)).rowcount
            if deleted:
                # Erase associated review history as well when the owner
                # deletes a report; no hidden copy of its value is kept.
                conn.execute("DELETE FROM review_events WHERE indicator_id=?", (record_id,))
        self._json(200 if deleted else 404, {"deleted": bool(deleted)})


if __name__ == "__main__":
    # This block runs ONLY when you launch server.py directly.
    token = bootstrap()  # Open the existing database, creating missing tables.
    server = ThreadingHTTPServer((HOST, PORT), Handler)  # Start a local HTTP listener.
    print("TrueDuck Sentinel database is running locally.")
    print(f"API: http://{HOST}:{PORT}/api/health")
    print(f"Access token: {token}")
    print("Keep this token private. Paste it into the extension's Settings page.")
    print("Stop with Ctrl+C. Your database remains in backend/data/scamlens.db")
    try:
        server.serve_forever()  # Keep running while Edge accesses the database.
    except KeyboardInterrupt:
        print("\nDatabase server stopped.")  # Printed when you press Ctrl+C.
    finally:
        server.server_close()  # Release port 8765 cleanly when exiting.
