# TrueDuck Sentinel (Beta)

Open-source browser scam awareness, anonymous reports, and administrator-reviewed intelligence. No account is needed to use the extension. Local suspicious-language warnings are available without a server; reviewed website and contact matches require a configured intelligence API.

## Install and run

1. Stop both old Python servers with Ctrl+C. Back up `cloud_api/data` and `backend/data` outside the repository. Preserve both data folders and `.git` when updating source files.
2. From the project root, install dependencies: `py -3.12 -m pip install -r cloud_api\requirements.txt`.
3. Run `RUN_LOCAL.cmd`. It now starts **only the community API** on port 8877. The private 8765 server is retired; its old database remains on disk for reference.
4. If you already have an admin in `cloud_api/data/cloud-dev.db`, keep using it. Otherwise run `py -3.12 -m cloud_api.manage_owner` in the project root.
5. Open `edge://extensions` and reload TrueDuck Sentinel, or select **Load unpacked** and choose `extension`.
6. In extension Settings, enter `http://127.0.0.1:8877/v1/feed` and click **Sync published feed**. No admin token is needed. The upgrade discards old extension private records and clears the previously downloaded public cache; re-sync to get the current approved feed. Only configure an API you trust.

## One report queue, one Admin Center (v0.9.8)

- Users click **Report a scam anonymously**, complete the form and submit. Reports are stored in `cloud_api/data/cloud-dev.db` and start pending. Public users cannot review, publish, retract, enable contact lookup or read private reports.
- Administrator: open `http://127.0.0.1:8877/dashboard`, sign in, choose **Moderation**, and refresh. Review evidence and record your decision. To expose an approved domain or URL, click **Publish indicator**. To make an approved email or phone searchable, click **Enable contact lookup**. Public review summaries are optional and must not contain personal details, raw evidence or unsupported claims.
- The extension only downloads public approved domain/URL records. Exact email and phone lookup is performed on demand by the community API. Physical addresses remain private. Re-review and retraction remove publication; website warnings update after the next successful feed sync. Suspicious-language warnings are independent of the review queue and are not claims of verified fraud.
- There is no longer a private local database management section, administrator token or local review queue in the extension. The old bulk publishing endpoint returns HTTP 410, even for old publisher credentials. Legacy private records and old bulk feed rows are retained for reference but no longer distributed. If you want a legacy indicator reviewed, submit it through the anonymous report form and review it in the Admin Center. No automatic migration or deletion of the old database is performed. The legacy `backend/` files remain for archive compatibility and tests; the private server cannot be started through its old direct command.

## Test locally

Health: `http://127.0.0.1:8877/health`. Reporting: `http://127.0.0.1:8877/report`. Admin: `http://127.0.0.1:8877/dashboard`.

Submit `alerts@example.test` anonymously with a fictional description. Before approval and explicit contact lookup access, the email must not return a reviewed match. Open the Admin Center, approve with a fictional reference and a public summary, then enable contact lookup. Look it up again in the extension: the summary should appear. Retract the report and repeat the lookup: it should no longer match. Repeat for `test-scam.example.test` as a domain, publishing it and syncing the feed before testing Quick Check. Do not navigate to real malicious websites.

The public intake has basic in-memory rate limits and duplicate detection. Server or hosting logs may record IP addresses. This is not production-grade abuse protection.

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
- **Never commit** `backend/data` (legacy archive), `cloud_api/data`, `.env`, tokens, API credentials, database backups, or real users' reports. `.gitignore` and `.dockerignore` help but don't replace manual review.
- This code is not ready for public hosting: HTTPS, production authentication, privacy notice, rate limiting, ongoing maintenance, and independent review are still required.
- Imported threat feeds may have their **own licenses and terms**, separate from this repository's license.
- Removing authorship from files does not erase Git commit authors, account ownership, or previously published history. If anonymity is important, create a new neutral repository and review its metadata before making it public.
