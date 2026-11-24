> HISTORICAL SETUP NOTES — these may reference older releases. Current licensing is Apache-2.0; see top-level README.md and LICENSE.

# TrueDuck Sentinel v0.8 — Complete Microsoft Edge project

**Begin with [`START_V08_HERE.md`](START_V08_HERE.md).** This ZIP is a full fresh install with no older version required.

New features: account roles, community scam-report submission, moderation, explicit publication/retraction, real report-count dashboard, audit log, abuse controls and SQLite backups.

Security warning: runs locally for testing; not ready for public internet deployment. See [`SECURITY_NOTES_V08.md`](SECURITY_NOTES_V08.md).

---

## Prior project notes (v0.7 and earlier)

# START HERE: See `START_V07_HERE.md` for the complete Microsoft Edge v0.7 installation.

# TrueDuck Sentinel v0.6 — private database + controlled public-feed export

**Upgrading from v0.5?** Read [UPGRADE_TO_V06.md](UPGRADE_TO_V06.md) and preserve your original `backend/data` folder.

Version 0.6 introduces an opt-in **public intelligence feed preview**. Only manually approved domains/URLs that you explicitly mark for sharing may appear in an exported JSON snapshot. All existing records remain private. This does **not** publish an API or host a database online. For a future hosted architecture, see [PUBLIC_API_PLAN.md](PUBLIC_API_PLAN.md).

The Python code is commented to explain each piece: see `backend/public_feed.py` and `PYTHON_CODE_GUIDE.md`. No third-party installation is required for v0.6.

# TrueDuck Sentinel v0.5 for Microsoft Edge — local security research build

**Upgrading from v0.4? Read [UPGRADE_TO_V05.md](UPGRADE_TO_V05.md) first.** Do not overwrite your original `backend/data` folder. The new Python source files have extensive `#` comments; start with [PYTHON_CODE_GUIDE.md](PYTHON_CODE_GUIDE.md).

Version 0.5 adds an editable report-review queue, a reviewer decision log, and a one-click **Report this site** shortcut. Read [TEST_V05.md](TEST_V05.md) to test the new workflow safely. The Python code includes detailed `#` comments.

The optional URLhaus importer provides outside **malware URL** indicators, not a comprehensive list of scams. External matches use a separate label, cannot be edited as personal verified reports, and require your own URLhaus Auth-Key for real downloads. For a safe demo, run `py -3.12 backend/update_urlhaus.py --sample` from this folder, then press Refresh in Settings.

# TrueDuck Sentinel — personal browser extension + private indicator database

**A real, editable starter project.** For Edge on Windows, start with `EDGE_START_HERE.md`. Public-facing developer: **TrueDuck Security** (project brand and author pseudonym). Working title “TrueDuck Sentinel” is not trademark-cleared.

The extension supports **Google Chrome and Microsoft Edge**, using Manifest V3. The database uses **SQLite**, through a Python server that runs **only on your computer**. No npm or third-party libraries are required.

## What it actually does

- Detects exact matches against your own records for **email, US/Canada phone, domains, URL, physical addresses**.
- Shows a small on-page warning for a watchlist match, or several suspicious language patterns.
- Includes a professional popup for scanning the current page or manually pasted text.
- Includes a full dashboard for submitting reports, approving/dismissing/reopening them with notes, reviewing the audit trail, adding/deleting records, exporting/importing JSON, and customizing scanning and styling.
- Stores watchlist records in a real SQLite file: `backend/data/scamlens.db`.
- Syncs a copy of your own watchlist into the extension's local storage so scans continue while the server is stopped.
- Scans page content on the device. **It does not upload webpage text to the server.**

It **does not** connect to national fraud reports, verify accusations, analyze browser-native SMS apps, scan all messages in a mail account, or guarantee that an item is safe or unsafe. It is an educational prototype, **not yet vetted for broad public distribution**. Avoid collecting or publishing sensitive information without reviewing applicable privacy and consumer-protection rules.

## 1. Start your database on Windows

1. Download this folder and **extract the ZIP** into an ordinary folder, e.g. `Documents\TrueDuck Sentinel`.
2. Install **Python 3.10 or newer** from https://www.python.org/downloads/ if it is not installed. During Windows setup, choose **Add Python to PATH**.
3. Open the extracted folder, open `backend`, click the File Explorer address bar, type `cmd`, press Enter.
4. Double-click **`START_DATABASE.cmd`** in the main project folder (recommended on Windows), or in the Command Prompt type:

   ```bat
   py -3.12 server.py
   ```

   If `py` isn't recognized, try `python server.py`.
5. The command window will print **Access token: ...**. Keep it private. Leave the window open while you manage records.
6. You can test the example webpage at http://127.0.0.1:8765/demo

**Your database file is created automatically**, and remains after closing the server. It is *not* uploaded to a cloud service. For a full backup including review history, copy the `.db` file **after stopping the server** or use **Export JSON** in the dashboard. Use **Import JSON** later to restore or merge your exported records; existing duplicates are skipped.

## 2. Install your extension in Microsoft Edge (or Chrome)

1. Open **Microsoft Edge** and navigate to `edge://extensions` (Chrome users: `chrome://extensions`).
2. Switch on **Developer mode** (top right).
3. Click **Load unpacked**.
4. Choose the extracted `TrueDuck Sentinel-Starter\extension` folder — the one containing `manifest.json`.
5. Pin **TrueDuck Sentinel** using the extensions puzzle icon. Click the shield icon to open its popup.
6. Click the settings gear, enter the access token shown in the database console, and click **Connect & sync**.

See **`EDGE_START_HERE.md`** for a detailed Microsoft Edge walkthrough and access-token instructions.

Chrome and Edge may show a browser warning that the extension can read webpage data. Automatic detection requires access to webpage content. See `PRIVACY.md` and the manifest. It does **not** run on `chrome://`, `edge://`, Chrome Web Store pages, or some restricted sites.

## 3. Try a safe demo

1. While your Python database server is running, open http://127.0.0.1:8765/demo in Edge.
2. The fake page contains suspicious wording and **fictional** email, phone, and domain examples. Your extension should show a *caution* banner from wording even before you add any watchlist entries.
3. Open **TrueDuck Sentinel → Settings**, and add an **email** record with value `alerts@example.test`, status **Reported**, and note “Fictional test entry”.
4. Click **Connect & sync** if needed, then reload the demo page.
5. The extension should now show a **watchlist match**. You can remove the demo record when finished. For testing report approval and dismissal, see [TEST_V05.md](TEST_V05.md).

Another test value is phone number `(202) 555-0199`, reserved for fictitious use. These are **not real scam reports**.

## 4. Files you can edit

| File | Purpose |
|---|---|
| `extension/manifest.json` | Extension name, version, author, permissions |
| `extension/styles.css` | Popup and dashboard visual design |
| `extension/popup.html` and `popup.js` | Browser-toolbar interface and manual scanner |
| `extension/options.html` and `options.js` | Database manager, visual preferences |
| `extension/shared/detector.js` | Detection patterns and matching algorithms |
| `extension/content.js` | On-page scanning and warning banner |
| `extension/background.js` | Toolbar badge and initialization |
| `backend/server.py` | Your commented SQLite database, review history, and private local API |
| `backend/data/scamlens.db` | Database file (generated on first run; excluded from project ZIP) |
| `LICENSE` | Open-source Apache License 2.0; see `NOTICE` for copyright holder placeholder |
| `OWNERSHIP.md` | Ownership and publication steps |

After editing extension files, open **`edge://extensions`** (or `chrome://extensions` on Chrome) and click **Reload** on TrueDuck Sentinel. After editing `backend/server.py`, stop and restart Python with `Ctrl+C`, `py -3.12 server.py`.

## 5. Privacy and security notes

- The server binds to **127.0.0.1**, not all network interfaces, and requires a randomly generated API access token.
- The token is stored in the browser's local extension storage to connect to the database. This is not an enterprise secrets vault; do not install untrusted extensions or share computer accounts.
- **The extension automatically reads visible content on HTTP(S) websites** when auto-scan is enabled. It performs local matching; webpage contents are *not* submitted to the Python server.
- The server is not designed to be exposed on a public network. **Do not forward port 8765** or change the server bind address to `0.0.0.0`. A public service would need HTTPS, real user accounts, access controls, abuse prevention, backups and legal review.
- The database is not encrypted at rest. Protect your Windows user account and disk, and avoid storing personal data you do not need.
- The analyzer is rule-based and incomplete. A match is **not proof of fraud** and a clean scan is **not proof of safety**.

## 6. Future development paths

- Add **source link, review date, status history and an appeal/correction process** for reported items.
- Allow opt-in public reporting with spam controls and evidence review rather than treating every report as fact.
- Migrate to PostgreSQL on your own secure host after designing a multi-user API, authentication, and data-retention rules.
- Add reputation feeds, only under licenses that permit storage and redistribution.
- Write real automated browser tests and have a security review before publishing.

## Developer tests

If Node.js is installed: `node tests/detector.test.js` from the project root.

For the database: `python -m unittest discover -s tests -p 'test_*.py'`.

## Publishing reminder

For Chrome Web Store publication you will need a developer account and truthful product declarations, including what web content your extension can access and why. A privacy policy may be required. Publication is separate from copyright ownership. Read `PRIVACY.md` before distributing.

## Version 0.3: local security review upgrade

If you already installed v0.2, **read `UPGRADE_FROM_V02.md` before extracting over your files**. Your SQLite database and access token live in the existing `backend/data` folder, which must be preserved.

New: separate reviewed vs unverified findings, trusted-only extension storage for the database token, per-site scanning pause, and opt-in local alert history. See `UPGRADE_FROM_V02.md` for testing and limitations.

**Development-stage notice:** This local build has been tested at the detector and database API level, not validated end-to-end in every Edge version or against real scam samples. Do not advertise it as a fully operational phishing protection or a real-time intelligence feed. Extension host permissions allow it to read ordinary HTTP(S) webpage text; keep its privacy disclosures accurate and review Microsoft Edge Add-ons policies before publishing.

## Version 0.4: Optional external malware-URL feed

- `backend/update_urlhaus.py`: safe sample import, offline CSV import, or authenticated URLhaus download.
- `backend/urlhaus_feed.py`: filters online exact HTTP(S) URLs from the CSV; no domain-wide verdicts.
- `/api/intelligence`: separate read-only endpoint that the extension fetches alongside your personal watchlist.
- Edge Settings shows the number of external records and last imported date.
- **The feed is not real-time:** manually re-import and press Refresh.
- Commercial use of URLhaus intelligence may require separate permissions or a paid product; review URLhaus usage conditions.
- Your manual JSON import/export contains **only your personal indicators**, not third-party feed data.

---

## Version 0.7 — Separate cloud API and optional Edge published-feed sync

**New users:** follow `START_V07_HERE.md` first. It is a complete install; older versions are not required.

The public API implementation is in `cloud_api/app.py`. It can use a separate local development SQLite database or a managed PostgreSQL database via `SCAMLENS_CLOUD_DATABASE_URL`. A new `backend/publish_feed.py` lets the owner explicitly upload approved opt-in records using a **different publisher token**. Edge Settings has a new opt-in public feed URL and **Sync published feed** button. Public records are stored separately from your local reports and expire from detection after seven days without successful re-sync.

No cloud service has been deployed for you. No public report submission endpoint is enabled. See `HOSTING_V07.md` for production requirements. All new Python source files have detailed beginner-readable `#` comments.
