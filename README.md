# TrueDuck Sentinel (Beta)

An independent, open-source browser extension for detecting suspicious language and matching known risk indicators on webpages. Includes manual email/phone checks, an optional local database, and an optional community-reporting API.

**No sign-in is required to use the extension.** Automatic scans work locally. A live shared intelligence feed and online email/phone reputation checks require the user or project maintainers to configure and host an API.

## Features

- Automatic local website warnings for suspicious wording and downloaded indicators
- Popup: quick message check and email / phone exact-match lookup
- Clear distinction between reviewed records, unverified reports, and suspicious patterns
- Optional Python SQLite database and reviewed public JSON feed
- Optional FastAPI community submission and moderation server

## Installation in Microsoft Edge

1. Open `edge://extensions`, enable Developer mode, and choose **Load unpacked**.
2. Select the **`extension`** directory, which contains `manifest.json`.
3. Visit ordinary websites or use the popup to check text, emails, and phone numbers.
4. Local pattern scanning works with **no account, no server, and no Python**. A missing online lookup is shown as *unavailable*, not *safe*.

## Optional local API development

Install Python 3.12 and run, from the project root:

```powershell
py -3.12 -m pip install -r cloud_api\requirements.txt
py -3.12 backend\server.py
```

Start the community API in a **second** terminal:

```powershell
py -3.12 -m cloud_api.dev_server
```

Health check: `http://127.0.0.1:8877/health`  |  Admin console: `http://127.0.0.1:8877/dashboard` | Anonymous report form: `http://127.0.0.1:8877/report`.

Only administrators have accounts. Public signup is disabled; old reporter accounts cannot sign in. To create the first administrator account (skip if you already have one in the same database):

```powershell
py -3.12 -m cloud_api.manage_owner
```

The extension's **Settings** page can connect to the localhost APIs. Manual public-feed sync accepts a user-approved HTTPS endpoint ending in `/v1/feed`, or the local development URL `http://127.0.0.1:8877/v1/feed`. Grant network permission only to an API you trust. The popup’s **Report a scam anonymously** opens that service’s `/report` page. If no service is configured, the popup offers to open the localhost test form. Submit the form and wait for the receipt; merely opening the form does not submit it. In the admin console, choose **Moderation → Refresh reports**, with the filter set to Pending or All. Private indicators added in extension Settings remain in the separate local database and do not appear in the community queue. Re-submit old fictional test indicators via the anonymous form if needed.

Anonymous reports are private and pending until an administrator reviews them. Approval and publishing are separate actions. There is no public report history or account creation. Pending duplicates are merged without revealing queue membership. The local API limits intake to 10 attempts per socket IP per day and 200 per hour globally, in memory. These limits reset on restart and are not production-grade. Report records do not store visitor account details or IPs; the server/hosting access logs may still record IPs.

## Public review summaries (v0.9.7)

In Moderation, click **Review**, select Approve, add an evidence reference and private review reason, then enter a separate **Public review summary** (up to 240 characters). Do not include personal information, private evidence, or unsupported claims. Save the decision. For domains/URLs, click **Publish indicator** and sync the extension feed. The popup and webpage warning show the public summary when a published entry matches. For emails/phones, click **Enable contact lookup** and then use the popup lookup. The public API returns the summary only for an exact opted-in approved contact. Physical addresses remain private. Previously published reports have no public summary until re-reviewed and explicitly republished. Re-review or retraction removes publication; downloaded website records change on the next successful sync. Cached copies may persist until then.

For an upgrade, stop both servers, back up both data directories, and keep `backend/data` and `cloud_api/data` when replacing source files. Existing databases gain the separate summary table automatically on startup; no data migration or new admin account is required if you use the same database. Restart `RUN_LOCAL.cmd`, hard-refresh the dashboard, reload the Edge extension, and sync `http://127.0.0.1:8877/v1/feed` in Settings.

## Checks

```powershell
py -3.12 security_check.py
py -3.12 -m unittest discover -s tests -p "test_*.py"
```

With Node installed, run JS tests via `node tests/detector.test.js`, `node tests/feed.test.js`, `node tests/lookup.test.js`.

## License and project name

**The Unlicense:** to the extent contributors have the rights to release their contributions, the original code is dedicated to the public domain where possible, with a permissive fallback. Anyone may copy, modify, distribute, and use it commercially, without attribution. The software is supplied as-is.

**No project trademark is asserted.** The project name is intended for free community use; this statement grants no rights held by third parties. However, a source-code license cannot stop all third-party trademark claims or guarantee exclusive rights will never arise. No participant is authorized to claim they represent all contributors without permission. See the `LICENSE` file.

TrueDuck Sentinel is the project name; no personal author, company publisher, or company API is specified in this release. The name is not trademark-cleared and does not imply endorsement by any company. The project's use of old internal identifiers such as `SCAMLENS_` or `scamlens.public-feed.v1` is only for backward protocol compatibility.

## Privacy and release limitations

- This is a **developer Beta**, not a fully audited security product. Warnings are not proof of fraud; absence of a warning does not mean safe.
- Scanning of permitted webpage content occurs locally. Optional scan history is off by default.
- Manual contact lookup can send the entered email or phone number to the **user-configured** API only after the user clicks **Look up**. Do not connect a service that you don't trust.
- Content-script permissions are broad because automatic warnings work on ordinary websites; consider an on-demand edition for more restricted access.
- **Never commit** `backend/data`, `cloud_api/data`, `.env`, tokens, API credentials, database backups, or real users' reports. `.gitignore` and `.dockerignore` help but don't replace manual review.
- This code is not ready for public hosting: HTTPS, production authentication, privacy notice, rate limiting, ongoing maintenance, and independent review are still required.
- Imported threat feeds may have their **own licenses and terms**, separate from this repository's license.
- Removing authorship from files does not erase Git commit authors, account ownership, or previously published history. If anonymity is important, create a new neutral repository and review its metadata before making it public.
