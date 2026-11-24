# TrueDuck Sentinel v0.8 — Start here (Microsoft Edge + Windows)

**This ZIP is a complete fresh installation.** You do NOT need v0.7 or any older ZIP.

## What's in the project?

- `extension/`: the Edge popup, local scanning, report shortcut, customizable settings.
- `backend/`: your private local SQLite watchlist, moderation, and optional URLhaus importer, on `127.0.0.1:8765`.
- `cloud_api/`: a **separate** experimental community API and public feed, on `127.0.0.1:8877`.
- `cloud_api/dashboard/`: account login, submit form, moderation queue, metrics and audit log.
- `BACKUP_NOW.cmd`: online SQLite backups outside the downloaded project folder.
- `RUN_DAILY_BACKUP.cmd`: helper for a daily task that YOU choose to schedule in Windows Task Scheduler.
- `tests/`: backend, feed, cloud, community, and backup tests.

## 1. Extract and open the RIGHT folder

Right-click the downloaded ZIP → **Extract All**. Open `TrueDuck Sentinel-v0.8`. You should see `cloud_api`, `backend`, `extension`, `START_DATABASE.cmd` and `START_CLOUD_API.cmd` together. In Windows File Explorer, click the address bar, type `cmd` and press Enter to open Command Prompt in this folder.

## 2. Install the Python packages (one-time)

```bat
py -3.12 -m pip install -r cloud_api\requirements.txt
```

The local private backend only needs the Python standard library. The cloud API uses FastAPI and SQLAlchemy.

## 3. Start two separate servers

Double-click `START_DATABASE.cmd`, then `START_CLOUD_API.cmd`. Keep both black windows open.

- Private server: <http://127.0.0.1:8765/demo> (test webpage)
- Cloud health check: <http://127.0.0.1:8877/health>
- Public feed: <http://127.0.0.1:8877/v1/feed>
- **Community console: <http://127.0.0.1:8877/dashboard>**

If the cloud server says `ModuleNotFoundError: No module named 'cloud_api'`, make sure you are running the v0.8 launcher. This version uses `py -3.12 -m cloud_api.dev_server`.

## 4. Create YOUR owner account

Double-click `CREATE_OWNER.cmd` and choose an owner username and **unique 12+ character password**. The password is hidden while you type. This is NOT your private database token and is NOT the publisher token. If the account already exists, the script does not overwrite it.

Then open <http://127.0.0.1:8877/dashboard> in Edge. Log in with the owner account. You should see **Overview**, **Moderation**, and **Audit history**.

## 5. Test a reporter account

To simulate another user, open the same dashboard in a new **InPrivate** Edge window. In this local demo, reporter registration is enabled. Create a fictional reporter account, sign in and submit a fictional domain:

- Type: **Domain**
- Value: `community-test.example.test`
- Details: `Fictional test: asks for a gift-card payment and urgent reply.`
- Evidence reference: `TEST-V08-1`

Back in the owner's normal Edge window, open **Moderation** and refresh the queue. Select the report, add a review reason, enter evidence reference `TEST-V08-1`, and **Approve**. Approval alone **does not publish**.

Click **Publish indicator**, confirm, then check <http://127.0.0.1:8877/v1/feed>. The record should appear. Click **Retract** and refresh the feed: it should disappear.

## 6. Install the Edge extension

Open `edge://extensions` and enable Developer mode. Remove any stale installation pointing to a deleted v0.7 folder. Choose **Load unpacked** and select **`TrueDuck Sentinel-v0.8\extension`**, which contains `manifest.json`.

To connect your personal watchlist, open TrueDuck Sentinel Settings, copy the private token printed by the `START_DATABASE.cmd` server into **Database connection**, and click **Connect & sync**.

Under **Published intelligence feed**, enter `http://127.0.0.1:8877/v1/feed` and click **Sync published feed**. The community console is available by clicking **Submit community report** in the popup or **Open community console** in Settings.

Important: The community console and Edge extension are **separate** interfaces. The extension never receives the community owner's password or publisher secret.

## 7. Back up your databases

Double-click `BACKUP_NOW.cmd` after your test. Backups save into:

`%LOCALAPPDATA%\TrueDuck Sentinel\Backups\private\` and `%LOCALAPPDATA%\TrueDuck Sentinel\Backups\cloud\`

Backups are also attempted **on every server startup** before either SQLite database is opened. Missing databases are skipped. The 30 newest copies per database are kept. These copies survive deleting the current version folder, but not deleting your entire Windows profile.

**Optional daily backups:** Open Windows **Task Scheduler** → **Create Basic Task** → name it `TrueDuck Sentinel Local Backups` → trigger **Daily** at a suitable time → action **Start a program** → Browse for this version's `RUN_DAILY_BACKUP.cmd`. The PC must be on, and you must update the task path when you install a new version. Use `BACKUP_NOW.cmd` to verify the backup location first.

The backups contain sensitive reports and must be protected. They do **not** contain the separate API-token text files. PostgreSQL hosting requires a different backup tool (`pg_dump` or managed database snapshots).

## 8. Read before public hosting

The cloud demo **only binds to 127.0.0.1**. Do not forward ports 8765 or 8877 or bind the development server directly to the internet. The community system is a locally tested foundation, **not production-ready**. See `SECURITY_NOTES_V08.md` for HTTPS, stronger sessions, email/abuse verification, MFA, persistent distributed rate limits, backup encryption, and operational requirements.

## 9. What to change yourself

- Name and developer: `extension/manifest.json` and footer text.
- Edge appearance: `extension/styles.css`.
- Scam rules: `extension/shared/detector.js`.
- Private local watchlist: `backend/server.py`.
- Community account, moderation, and reporting logic: `cloud_api/community.py`.
- Cloud dashboard appearance: `cloud_api/dashboard/styles.css`.
- Cloud dashboard behavior: `cloud_api/dashboard/app.js`.
- Backups: `cloud_api/backup_databases.py`.

Python modules include explanations using `#` comments, docstrings, and short section notes. Keep the repository private until you have removed placeholder identity/license fields and completed security review.
