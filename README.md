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

Health check: `http://127.0.0.1:8877/health`  |  Admin console: `http://127.0.0.1:8877/dashboard`.

To create the first administrator account:

```powershell
py -3.12 -m cloud_api.manage_owner
```

The extension's **Settings** page can connect to the localhost APIs. Manual public-feed sync accepts a user-approved HTTPS endpoint ending in `/v1/feed`, or the local development URL `http://127.0.0.1:8877/v1/feed`. Grant network permission only to an API you trust.

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
