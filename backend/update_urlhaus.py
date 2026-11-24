"""Update TrueDuck Sentinel's optional malware URL feed without changing personal reports.

Beginner commands (from the main TrueDuck Sentinel-Starter folder):
  py -3.12 backend/update_urlhaus.py --sample       # Safe fictional records.
  py -3.12 backend/update_urlhaus.py --file feed.csv # Previously downloaded CSV.
  py -3.12 backend/update_urlhaus.py                # Real URLhaus Auth-Key.

NOTE: You can run this while the database server is up, but refresh the Edge
extension's database cache afterwards to see the new records.
"""

from __future__ import annotations

# --- Built-in Python modules for command-line input and file handling. ---
import argparse     # Parse the --sample and --file switches.
import getpass      # Ask for an API key without showing it on screen.
import os           # Optionally read a key from an environment variable.
import sys          # Write errors and return a nonzero exit status.
from pathlib import Path  # Find the sample CSV and a user-selected file.

# Import your own program's database and the separate feed helper functions.
import server
from urlhaus_feed import fetch_csv, parse_csv, replace_feed


def main() -> int:
    """Choose a CSV source, validate its URLs, and safely refresh the feed."""
    parser = argparse.ArgumentParser(
        description="Import exact online URLhaus malware URLs into your local database"
    )
    group = parser.add_mutually_exclusive_group()  # Prevent two sources at once.
    group.add_argument("--sample", action="store_true", help="Import fictional URLs for testing (no API key needed)")
    group.add_argument("--file", type=Path, help="Import a previously downloaded URLhaus recent.csv file")
    args = parser.parse_args()

    server.bootstrap()  # Create missing tables, but preserve all existing data.
    try:
        if args.sample:
            # Safe offline testing using made-up .test domain names.
            path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "urlhaus_sample.csv"
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                parsed = parse_csv(file, server.canonicalize)
        elif args.file:
            # Import a CSV you downloaded yourself; no network access here.
            with args.file.open("r", encoding="utf-8-sig", newline="") as file:
                parsed = parse_csv(file, server.canonicalize)
        else:
            # Live mode: URLhaus currently needs a free API Auth-Key.
            print("Get a URLhaus Auth-Key at https://urlhaus.abuse.ch/api/")
            print("This script never saves the key in the database or Edge extension.")
            key = os.environ.get("URLHAUS_AUTH_KEY") or getpass.getpass("URLhaus Auth-Key (hidden input): ")
            parsed = parse_csv(fetch_csv(key), server.canonicalize)

        # Insert feed rows in a transaction without modifying user indicators.
        with server.get_db() as conn:
            count = replace_feed(conn, parsed)
        print(f"Imported {count} external exact-URL indicators into your local database.")
        print("External URL reports remain separate from your personal reports.")
        print("In Edge, open TrueDuck Sentinel Settings and click Refresh to sync.")
        return 0  # Exit status zero means success.
    except (ValueError, OSError) as exc:
        # Failed downloads and invalid CSV data must leave the old feed unchanged.
        print(f"Update failed: {exc}", file=sys.stderr)
        print("Your personal indicators and previous feed were left unchanged.", file=sys.stderr)
        return 1  # Nonzero exit code means the update failed.


if __name__ == "__main__":
    # Python calls main() only when running this file directly.
    raise SystemExit(main())
