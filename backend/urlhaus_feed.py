"""Safely import optional URLhaus malware-URL intelligence.

This file NEVER sends emails or SMS messages. It downloads a CSV file containing
URL indicators, filters it, and puts exact ONLINE malware URLs in a separate
SQLite table. It needs an Auth-Key for live downloads.
"""

from __future__ import annotations

# --- Python standard-library imports; no extra packages are needed. ---
import csv               # Read rows and columns from URLhaus's CSV export.
import io                # Turn downloaded CSV text into a file-like object.
import re                # Check references and the access-key format.
import sqlite3           # Store external indicators in your local database.
import urllib.error      # Handle network and HTTP errors cleanly.
import urllib.request    # Download HTTPS content from URLhaus.
from datetime import datetime, timezone  # Save the time the feed was updated.
from typing import TextIO                 # Describe the expected file-like input.

# --- Safety limits and official feed identifiers. ---
MAX_URLS = 5000                  # Limit the number of URLs saved and sent to Edge.
MAX_DOWNLOAD_BYTES = 20_000_000 # Avoid unexpectedly large remote downloads.
FEED = "urlhaus"                # Internal name for this one data source.
FEED_HOST = "urlhaus-api.abuse.ch"  # The ONLY remote host the downloader contacts.


def _is_valid_ref(value: str) -> bool:
    """Accept only official URLhaus evidence-page links, not arbitrary URLs."""
    return bool(re.fullmatch(r"https://urlhaus\.abuse\.ch/url/\d+/", value))


def parse_csv(source: TextIO, normalize, limit: int = MAX_URLS) -> list[tuple[str, str, str, str]]:
    """Extract exact online malware URLs from a URLhaus CSV export.

    Each return value contains: original URL, normalized URL, explanation,
    and optional official reference link. The `normalize` argument comes from
    server.canonicalize, ensuring the feed and your own records match the same way.
    """
    if not 1 <= limit <= MAX_URLS:
        raise ValueError("Choose a limit between 1 and 5000 URLs")

    def lines():
        """Discard CSV comments, but keep its commented column-header line."""
        for line in source:
            if not line.strip():
                continue  # Skip blank lines.
            if line.lstrip().startswith("#"):
                if re.match(r"^\s*#\s*id\s*,", line, flags=re.I):
                    # URLhaus commonly prefixes the real CSV heading with '#'.
                    yield re.sub(r"^\s*#\s*", "", line, count=1)
                continue  # Skip other comment lines.
            yield line

    reader = csv.DictReader(lines())  # Access each column by its heading.
    names = {name.strip() for name in (reader.fieldnames or []) if name}
    if not {"url", "url_status"}.issubset(names):
        raise ValueError("Invalid URLhaus CSV: expected url and url_status columns")

    found = []  # Valid URL indicators collected so far.
    seen = set()  # Normalized URLs already found; avoid duplicates.
    for item in reader:
        if not item or str(item.get("url_status", "")).strip().lower() != "online":
            continue  # Offline URLs might have been cleaned; don't flag as current.
        raw = str(item.get("url", "")).strip()
        try:
            canonical = normalize("url", raw)
        except (ValueError, TypeError):
            continue  # Reject broken/malformed URLs without stopping the import.
        if canonical in seen:
            continue
        seen.add(canonical)

        # Include an explanation rather than simply declaring the host a scam.
        threat = str(item.get("threat", "malware_download")).strip().replace("_", " ")[:100]
        ref = str(item.get("urlhaus_link", "")).strip()
        ref = ref if _is_valid_ref(ref) else ""  # Do not store untrusted evidence URLs.
        found.append((raw, canonical, f'URLhaus lists this exact URL as online ({threat or "malware distribution"}).', ref))
        if len(found) >= limit:
            break  # Stop after the configured number of recent online URLs.

    if not found:
        # Never delete the existing feed if a new download contains no usable URLs.
        raise ValueError("No valid online URLs found; existing intelligence was left unchanged")
    return found


def replace_feed(conn: sqlite3.Connection, records: list[tuple[str, str, str, str]]) -> int:
    """Atomically replace URLhaus rows; do not change your personal reports."""
    if not records or len(records) > MAX_URLS:
        raise ValueError("Expected 1 to 5000 normalized URL records")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # A transaction means an error rolls back this refresh, keeping old records.
    with conn:
        conn.execute("DELETE FROM feed_indicators WHERE feed=?", (FEED,))
        conn.executemany("""
            INSERT INTO feed_indicators
            (feed,kind,value,canonical,status,reason,source,reference,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, [
            (FEED, "url", raw, canonical, "external", reason,
             "URLhaus (abuse.ch) — external malware URL intelligence", ref, now)
            for raw, canonical, reason, ref in records
        ])
        # Save date and size so users know how old the feed is.
        conn.execute("""
            INSERT INTO feed_syncs(feed,updated_at,record_count)
            VALUES(?,?,?) ON CONFLICT(feed) DO UPDATE SET
            updated_at=excluded.updated_at, record_count=excluded.record_count
        """, (FEED, now, len(records)))
    return len(records)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent redirects that could leak an API key from its original URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("URLhaus export redirected unexpectedly; refusing to forward the key")


def fetch_csv(auth_key: str) -> io.StringIO:
    """Download URLhaus recent.csv without saving or printing the secret key."""
    key = auth_key.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{12,200}", key):
        raise ValueError("Invalid API key format; use the Auth-Key from URLhaus")

    # Use a fixed official HTTPS endpoint. Never accept a custom hostname here.
    address = f"https://{FEED_HOST}/v2/files/exports/{key}/recent.csv"
    req = urllib.request.Request(address, headers={
        "User-Agent": "TrueDuckSentinel-Local/0.4",
        "Accept": "text/csv",
    })
    opener = urllib.request.build_opener(NoRedirect())  # Disable HTTP redirects.
    try:
        with opener.open(req, timeout=25) as response:
            if response.geturl() != address:
                raise ValueError("Unexpected response URL")
            content = response.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.HTTPError as exc:
        # Do not include the request URL in the exception (it contains the key).
        raise ValueError(f"URLhaus HTTP {exc.code}. Check your Auth-Key and service status.") from None
    except urllib.error.URLError:
        raise ValueError("Could not reach URLhaus. Check your internet connection.") from None

    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Feed download exceeds 20 MB safety limit; existing records were preserved")
    try:
        text = content.decode("utf-8-sig")  # Handle UTF-8 files with optional BOM.
    except UnicodeError:
        raise ValueError("Feed contains invalid text encoding") from None
    return io.StringIO(text)  # parse_csv can read this just like an open file.
