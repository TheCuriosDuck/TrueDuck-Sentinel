# TrueDuck Sentinel v0.9 — start here (Windows + Microsoft Edge)

This is a **complete replacement** for v0.8.1. It includes the entire browser extension, your local database server, the community report/review dashboard, and an optional read-only published feed. You do not need earlier version folders.

## 1 — Unpack and install

1. Extract the ZIP to a normal folder such as `Documents\TrueDuck Sentinel-v0.9`.
2. Open that folder in File Explorer, click the address bar, type `cmd` and press Enter.
3. Run:

   ```bat
   py -3.12 -m pip install -r cloud_api\requirements.txt
   ```

4. Do not disable Microsoft Defender or the Windows firewall. A downloaded `.cmd` file may show an unsigned-publisher warning. Open it in Notepad first if you want to review its exact commands.

## 2 — Start both local servers

Double-click these **in separate windows**, keeping the windows open:

- `START_DATABASE.cmd` — personal SQLite database, `http://127.0.0.1:8765`.
- `START_CLOUD_API.cmd` — separate community API and dashboard, `http://127.0.0.1:8877`.

If this is a **fresh** folder, run `CREATE_OWNER.cmd` one time to create your administrator username and passphrase. The owner account and database tokens must remain private. In Edge open `http://127.0.0.1:8877/dashboard`. The `/health` endpoint returns `{"status":"ok",...}` when the cloud service is working.

The word "cloud" refers to the API's **design**. These servers are still on **your PC**, not publicly hosted.

## 3 — Install in Edge

1. Go to `edge://extensions` and turn on Developer mode.
2. Remove the extension installation that points at a previously deleted project folder.
3. Click **Load unpacked**, then select the new `extension` folder containing `manifest.json`.
4. Open TrueDuck Sentinel > **Settings**, enter the *private database* token from the `START_DATABASE.cmd` console and click **Connect & sync**.
5. Optional: in **Published intelligence feed** enter `http://127.0.0.1:8877/v1/feed` and click **Sync published feed**. Accept the browser's permission prompt if shown.

The extension requests webpage access for automatic local scanning. You can turn **Automatic webpage scanning** off in Settings, and use the popup's manual Quick Check for pasted text. Turning it off does **not** revoke extension site access in Edge; for that use Edge's extension site-access controls.

## 4 — Check that your protections still work

1. Run `CHECK_SECURITY.cmd` in the main folder. It runs a **limited static preflight** and the Python/API tests. Review any warnings.
2. Run `node tests/detector.test.js` if Node.js is installed (optional).
3. Go to `http://127.0.0.1:8765/demo` in Edge and confirm a fictional message triggers a caution banner.
4. Open the community console, submit fictional domain `community-test.example.test` from a test reporter account, moderate and explicitly publish it, then read `http://127.0.0.1:8877/v1/feed`.
5. In TrueDuck Sentinel Settings, sync the feed and use Quick Check on `community-test.example.test`. Retract it and sync again to confirm the warning goes away.

## 5 — Where your files live

- `extension/` — editable Edge extension source, popup, detector, and settings.
- `backend/` — local SQLite server, URLhaus importer, publish tools.
- `cloud_api/` — account-based API, dashboard, production guardrails, and example HTTPS proxy configuration.
- `backend/data/` and `cloud_api/data/` — generated databases and local secrets, **excluded from the ZIP**. If you have real data later, stop deleting these without backups.
- `BACKUP_NOW.cmd` — copies SQLite databases to `%LOCALAPPDATA%\TrueDuck Sentinel\Backups` (separate from your version folder). This does not encrypt the backups.

## 6 — Before any real online launch

Read `SECURITY_REVIEW_V09.md` and `PUBLIC_RELEASE_CHECKLIST.md`.

Do **not** open ports 8765 or 8877 in your router. Do **not** deploy this unchanged for public accounts or collect real community submissions. Developer-mode testing and clean automated tests are not a production security review.
