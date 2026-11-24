# Understanding the TrueDuck Sentinel Python code

All backend Python files have explanatory `#` comments next to the important operations and decision points. This guide explains how they fit together.

## 1. `backend/server.py`: your local web server

- **Imports:** The top of the file imports `sqlite3` for the database, `json` for communication with Edge, and `http.server` for serving HTTP requests.
- **Paths and constants:** `ROOT` is the folder containing `server.py`; `DATA` is `backend/data`; `DB` is the `scamlens.db` file; `TOKEN_FILE` stores your access token.
- **`canonicalize(kind, value)`:** Cleans up an email, phone, domain, URL or physical address so it can be compared consistently and duplicates can be found.
- **`get_db()`:** Opens a SQLite connection, lets code use it inside a `with` block, and closes it automatically when finished.
- **`bootstrap()`:** Creates the private data folder, access token and missing database tables/columns **if they don't already exist**. In v0.5 it adds review fields without replacing existing reports.
- **`class Handler`:** The functions that respond to requests from Edge. Names beginning with `do_` correspond to different kinds of HTTP requests.
  - `do_GET` returns the fictional `/demo` webpage, `/api/indicators`, `/api/reviews` (review history) and `/api/intelligence` (external feed).
  - `do_POST` adds a report, calls `_import_records` to merge JSON, or routes to `_review_record` for a manual review decision.
  - `_review_record` validates a reviewer note and, for approvals, an evidence reference; updates the indicator and records its decision in one database transaction.
  - `do_DELETE` removes a personal indicator and the associated review history by numeric ID.
  - `_authorized` checks your secret access token before allowing access to the API.
  - `_json` sends Python objects as JSON that JavaScript understands.
- **`if __name__ == '__main__'`:** Starts listening on `127.0.0.1:8765`, prints the token and stays running until Ctrl+C.

## 2. SQLite tables (your database)

`indicators` contains your manually entered and JSON-imported watchlist records. `feed_indicators` contains external URLhaus URL matches and deliberately uses the status `external` rather than `verified`. `feed_syncs` stores the date and count of the latest imported URLhaus feed. `review_events` keeps a local trail of manual decisions (including reopening a report). `indicators.review_state` is `pending`, `approved`, or `dismissed`. A dismissed record stays in the table but must be excluded from browser scans. Your old watchlist table is preserved during upgrades.

Python uses SQL commands like `CREATE TABLE`, `INSERT`, `SELECT` and `DELETE`. Parameters are supplied separately using `?` placeholders rather than placing untrusted text directly in SQL strings.

## 3. `backend/urlhaus_feed.py`: process outside intelligence

- **`fetch_csv(auth_key)`:** Makes a request to the fixed official URLhaus HTTPS host using a key you supply. It refuses redirects and limits the download size. The key is not stored.
- **`parse_csv(source, normalize)`:** Reads CSV rows, skips comments, offline URLs, invalid URLs and duplicates, and keeps at most 5,000 online URL indicators.
- **`replace_feed(conn, records)`:** Removes the OLD URLhaus feed and inserts the NEW one in a database transaction. This does **not** modify personal watchlist data.

## 4. `backend/update_urlhaus.py`: run the importer

This is a separate command from `server.py`; the database server does not automatically fetch outside data.

From the main TrueDuck Sentinel-Starter folder, open Command Prompt:

```bat
py -3.12 backend/update_urlhaus.py --sample
```

This loads fictional test data. To use a locally saved CSV:

```bat
py -3.12 backend/update_urlhaus.py --file "C:\Users\You\Downloads\recent.csv"
```

To use URLhaus directly (requires an Auth-Key):

```bat
py -3.12 backend/update_urlhaus.py
```

After importing, open TrueDuck Sentinel Settings in Edge and click **Refresh**.

## 5. Common code symbols

| Python | Meaning |
|---|---|
| `# A comment` | Notes for you; Python ignores it when running. |
| `def function(...):` | Defines reusable instructions that you can call. |
| `return` | Sends a result back to the calling code. |
| `if`, `elif`, `else` | Runs different code depending on a condition. |
| `try` and `except` | Handles errors such as invalid input or failed downloads. |
| `with get_db() as conn:` | Wraps database changes in a commit/rollback context. |
| `for item in records:` | Repeats operations for each record. |
| `self._json(200, data)` | Sends HTTP status 200 (success) and JSON data to Edge. |
| `f"Record: {value}"` | Inserts a variable into a string. |

## 6. How to change Python code

1. Open the folder in VS Code or another text editor.
2. Make a copy of the Python file before major changes.
3. Follow the `#` comments in `server.py`, `urlhaus_feed.py` and `update_urlhaus.py`.
4. After editing the server, press **Ctrl+C** in the old command window and double-click `START_DATABASE.cmd` again.
5. After editing an extension JavaScript or HTML file, go to **`edge://extensions`**, click **Reload** on TrueDuck Sentinel, and refresh the webpage.
6. Run the Python unit tests before relying on new changes:

```bat
py -3.12 -m unittest discover -s tests -p "test_*.py"
```

**Be careful:** Changing the database schema, authentication, or comparison rules can cause compatibility or security issues. Keep backups and use harmless `.test` indicators when experimenting.

## 7. v0.5 review workflow: reading the code

- Find **`bootstrap()`** in `server.py` to see the `ALTER TABLE` migration that preserves your v0.4 records.
- Find **`_review_record()`** to learn input validation (`if`), SQLite `UPDATE` and `INSERT`, transactions, and HTTP response codes.
- The `POST /api/indicators/{id}/review` route calls `_review_record()` when the user clicks **Save decision** in Edge.
- The `GET /api/reviews` route reads the latest 100 review events for the dashboard.
- The JSON import code preserves `review_state` on restored reports so dismissed items do not become active again.
- The Edge source in `extension/options.js` decides which records are copied to its local scanner cache: only reports **not dismissed**, plus the separate URLhaus feed.
- **`extension/shared/detector.js`** also ignores dismissed reports for defense in depth.

Back up the `backend/data` folder (including your secret token) before running a newer server version. Do not post real sensitive scam reports or access tokens in a public repository.


## v0.6: `backend/public_feed.py`

The new file explains imports, why private fields are excluded, how `can_publish()` checks a record, how `build_public_feed()` builds a minimal JSON object, and how `save_public_feed()` atomically writes the result to disk. Every function contains Python `#` comments. Run `py -3.12 backend/public_feed.py` in the main project folder to export a local snapshot. This **does not** upload the file.

In `server.py`, the new `public_share` column starts at 0 (private). The token-protected `/api/indicators/{id}/sharing` endpoint controls opt-in, and `/api/public-preview` returns only the filtered snapshot. Changes to review decisions turn public sharing back off.

## v0.7 Python code you can learn from

- `cloud_api/app.py`: a separate FastAPI application. `public_hostname()` checks that a record is safe to publish; `safe_indicator()` validates type and value; `check_owner_token()` protects publishing; `current_feed()` reads only the public DB; `replace_feed()` transactionally replaces all published indicators.
- `cloud_api/dev_server.py`: generates a local development-only publisher token, stores it in ignored `cloud_api/data/`, and starts the demo at 127.0.0.1:8877. **Never forward the port to the internet.**
- `backend/publish_feed.py`: calls the v0.6 privacy-filtering exporter and only uploads if you explicitly use `--publish`. Remote publishing requires HTTPS and a separate token.

Read the `#` comments in the source files line by line. In `cloud_api/app.py`, the most important security concept is **separating public data from private records at the database and API levels**, not just hiding a button.

## 8. v0.8: community API (`cloud_api/community.py`)

- **`accounts`, `sessions`, `reports`, `review_audit`:** SQLAlchemy table definitions. One account may create many reports; each report starts as pending.
- **`hash_password()`** uses `hashlib.pbkdf2_hmac()` and a separate random salt to avoid storing passwords in plaintext.
- **`get_user()`** checks a short-lived bearer session token. The SQLite database stores only the SHA-256 digest of the token, not the token itself.
- **`throttle()`** implements a sliding-window in-memory rate limit for local development, plus a separate per-account report quota. It is not a substitute for distributed limits in production.
- **`normalize_indicator()`** rejects invalid types and strips or rejects risky URL components before storing community reports. It does not retrieve URLs or open messages.
- **`submit_report()`** creates a pending record, **`review_report()`** records an audited owner decision, and **`publish_community()`** explicitly publishes only eligible reviewed domains/URLs.
- **`retract_community()`** removes a public record. **`owner_metrics()`** counts reports by state/type/day for the dashboard.
- **`community_public_table`** in `cloud_api/app.py` is intentionally separate from the owner's v0.7 uploaded feed, so replacing the private-owner feed does not erase published community records.

## 9. v0.8: backups (`cloud_api/backup_databases.py`)

- **`backup_root()`** chooses a location outside your version folder, by default `%LOCALAPPDATA%\\TrueDuck Sentinel\\Backups` on Windows.
- **`save_one()`** opens an existing SQLite database, uses the SQLite backup API to create a safe snapshot, checks database integrity, and removes old copies beyond the retention limit.
- **`main()`** reads `--database` and `--keep` arguments from the command line. Startup `.cmd` scripts run a backup when an existing database is present.
- Backups are not encrypted. You must guard your Windows account and use a secure location for real private data.
