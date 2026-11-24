"""Prepare a privacy-filtered public feed from individually approved records.

This does NOT run a public web server. It builds a JSON snapshot which the owner
may later choose to upload to a separate, secure HTTPS host. No third-party feed
entries, emails, phone numbers, addresses, evidence, or reporter notes are copied.
"""

# --- Standard-library modules; no packages need to be installed. ---
import argparse             # Read the command-line options in Windows Command Prompt.
import json                 # Serialize Python dictionaries as a JSON document.
import os                   # Replace the completed export atomically.
import sqlite3              # Read reviewed indicators from the local database.
import tempfile             # Create an incomplete output file safely.
from datetime import datetime, timezone  # Timestamp the snapshot using UTC.
from pathlib import Path   # Locate files without hardcoded Windows paths.
from urllib.parse import urlsplit  # Check if a URL contains credentials or query data.
import ipaddress            # Reject local, private, or loopback IP addresses.

# This folder always points at backend/, wherever the project is extracted.
BACKEND_DIR = Path(__file__).resolve().parent
# By default the export is stored beneath backend/data (excluded from Git).
DEFAULT_OUTPUT = BACKEND_DIR / "data" / "public-feed.json"
# Top-level field documenting the JSON structure for future extension clients.
SCHEMA = "scamlens.public-feed.v1"


def utc_now() -> str:
    """Return the time in UTC so other systems understand the feed timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def can_publish(record: sqlite3.Row | dict) -> bool:
    """Verify a record is reviewed, explicitly shared, and safe to describe.

    This function is also used by the ADMIN API before it sets public_share=1.
    In particular, full URLs with query strings are excluded because queries
    can contain session tokens, email addresses, or other private information.
    """
    if record["kind"] not in ("domain", "url"):
        return False  # Never publish email addresses, phone numbers or addresses.
    if record["status"] != "verified" or record["review_state"] != "approved":
        return False  # Reported or dismissed is NOT an approved intelligence entry.

    # The canonical value was already validated when added to the database.
    # Recheck it here as defense in depth before making a public export.
    value = record["canonical"]
    if record["kind"] == "url":
        try:
            parsed = urlsplit(value)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                return False
            # Check BOTH the canonical form and the original raw URL: the
            # canonicalizer may remove a fragment or embedded credentials.
            # Publishing the path of a URL requires an extra privacy check.
            original = urlsplit(record["value"])
            if (parsed.username or parsed.password or parsed.query or parsed.fragment
                    or original.username or original.password or original.query or original.fragment):
                return False  # URL parameters and credentials can leak secrets.
            hostname = parsed.hostname
        except ValueError:
            return False
    else:
        hostname = value.lower().rstrip(".")

    # Local/private network targets should never be distributed as threat labels.
    if hostname in {"localhost"} or hostname.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        address = ipaddress.ip_address(hostname)
        if not address.is_global:
            return False
    except ValueError:
        pass  # Ordinary domain names are not IP addresses, which is fine.
    return True


def build_public_feed(conn: sqlite3.Connection) -> dict:
    """Produce a minimal, public-safe feed from an existing SQLite connection."""
    # Sharing is opt-in, not inferred from reviewed status.
    rows = conn.execute("""SELECT kind, value, canonical, status, review_state, public_share
                           FROM indicators
                           WHERE public_share=1 AND review_state='approved'
                           AND status='verified' AND kind IN ('domain','url')
                           ORDER BY kind, canonical""").fetchall()

    # A second validation step protects against database edits made outside the UI.
    indicators = [
        {"kind": row["kind"], "value": row["canonical"], "classification": "reviewed_report"}
        for row in rows if can_publish(row)
    ]
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "description": "Opt-in, manually reviewed indicators. Not proof of fraud.",
        "count": len(indicators),
        "indicators": indicators,
    }


def save_public_feed(destination: Path, feed: dict) -> None:
    """Write the snapshot atomically so interruptions cannot leave partial JSON."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    # A temporary file in the same folder keeps os.replace on one filesystem.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                     prefix=".scamlens-", suffix=".tmp", delete=False) as temp:
        temp_path = Path(temp.name)
        json.dump(feed, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
    try:
        os.replace(temp_path, destination)  # Rename only when writing succeeds.
    finally:
        temp_path.unlink(missing_ok=True)   # Clean up if an error occurred.


def main() -> None:
    """Export an approved-feed snapshot when you run this file directly."""
    parser = argparse.ArgumentParser(description="Create a public-safe TrueDuck Sentinel feed snapshot")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Path to write JSON (default: backend/data/public-feed.json)")
    args = parser.parse_args()

    # Import here, after parsing, to avoid a circular import with server.py.
    from server import bootstrap, get_db
    bootstrap()  # Preserve existing database records and add missing v0.6 columns.
    with get_db() as conn:
        feed = build_public_feed(conn)
    save_public_feed(args.output, feed)
    print(f"Exported {feed['count']} opted-in approved domains/URLs to: {args.output}")
    print("Nothing was uploaded. Inspect this file before publishing it anywhere.")


if __name__ == "__main__":
    main()  # Only run the export when called from Command Prompt.
