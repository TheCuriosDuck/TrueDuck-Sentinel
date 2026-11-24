"""Preview or publish the owner's APPROVED, opt-in domains and URLs.

Usage (from trueduck-sentinel):
    py -3.12 backend/publish_feed.py             # Save preview only (no upload).
    py -3.12 backend/publish_feed.py --publish --local
    py -3.12 backend/publish_feed.py --publish --endpoint https://your-api.example/v1/admin/feed

Publishing REPLACES the cloud list; that way dismissed/unshared records are
retracted on the next publication. This file NEVER sends your private
scamlens.db file, emails, phone numbers, addresses or review notes.
"""

# --- Standard-library imports ---
import argparse                  # Read explicit publish options from Command Prompt.
import json                      # Encode the minimal published feed as JSON.
import os                        # Read your cloud publisher token from the environment.
from pathlib import Path         # Find directories regardless of where Windows extracts ZIP.
from urllib.error import HTTPError, URLError  # Give useful upload errors.
from urllib.parse import urlsplit              # Reject insecure remote publishing URLs.
from urllib.request import Request, urlopen    # Use HTTP PUT; no external package needed.

# --- Files supplied by the previous TrueDuck Sentinel versions ---
from public_feed import build_public_feed, save_public_feed, DEFAULT_OUTPUT
from server import bootstrap, get_db

ROOT = Path(__file__).resolve().parent.parent
LOCAL_ENDPOINT = 'http://127.0.0.1:8877/v1/admin/feed'
LOCAL_TOKEN_FILE = ROOT / 'cloud_api' / 'data' / 'publisher_token.txt'


def publish(endpoint: str, feed: dict, token: str, local: bool = False) -> dict:
    """Replace the public list only after the owner explicitly requests upload."""
    parsed = urlsplit(endpoint)
    # Production publication must use HTTPS. Localhost HTTP is only for demos.
    if (parsed.scheme != 'https' and not (local and endpoint == LOCAL_ENDPOINT)):
        raise ValueError('Publishing remotely requires an HTTPS API endpoint')
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != '/v1/admin/feed':
        raise ValueError('Unexpected publishing endpoint path or URL parameters')
    if len(token) < 32:
        raise ValueError('Set a long, random SCAMLENS_PUBLISH_TOKEN in your environment')
    # Only the filtered export generated from approved records is transmitted.
    body = json.dumps(feed, separators=(',', ':')).encode('utf-8')
    request = Request(endpoint, data=body, method='PUT', headers={
        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
        'User-Agent': 'TrueDuckSentinel-Owner-Publisher/0.7',
    })
    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'Cloud API refused publication (HTTP {exc.code}); check credentials and feed') from exc
    except URLError as exc:
        raise RuntimeError('Cannot reach the chosen cloud API. Is it running?') from exc
    return result


def main() -> None:
    """Run one preview or one owner-requested publication."""
    parser = argparse.ArgumentParser(description='Preview or publish your reviewed scam-indicator feed')
    parser.add_argument('--publish', action='store_true', help='Actually upload the filtered snapshot')
    parser.add_argument('--local', action='store_true', help='Use your local cloud API demo on port 8877')
    parser.add_argument('--endpoint', help='Production HTTPS endpoint ending in /v1/admin/feed')
    args = parser.parse_args()
    if args.local and args.endpoint:
        parser.error('Choose either --local or --endpoint, not both')

    # Only approved and individually shared entries survive this export.
    bootstrap()
    with get_db() as conn:
        feed = build_public_feed(conn)
    save_public_feed(DEFAULT_OUTPUT, feed)
    print(f'Preview saved: {DEFAULT_OUTPUT} ({feed["count"]} reviewed, opt-in entries)')

    # Running this file with no flags does NOT send data anywhere.
    if not args.publish:
        print('Not uploaded. Use --publish --local for the local demo or --publish --endpoint ... for HTTPS.')
        return
    if args.local:
        if not LOCAL_TOKEN_FILE.exists():
            parser.error('Run RUN_LOCAL.cmd first to create the local demonstration token')
        token = LOCAL_TOKEN_FILE.read_text(encoding='utf-8').strip()
        endpoint = LOCAL_ENDPOINT
    else:
        if not args.endpoint:
            parser.error('Specify --endpoint for a real upload, or --local for the demo')
        token = os.environ.get('SCAMLENS_PUBLISH_TOKEN', '')
        endpoint = args.endpoint
    result = publish(endpoint, feed, token, local=args.local)
    print(f'Published {result["published"]} records; cloud revision {result["revision"]}.')
    print('Publishing was explicit. The owner database and review notes were never sent.')


if __name__ == '__main__':
    main()
