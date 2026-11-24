# Privacy and data-handling summary (local development edition)

**Public-facing developer:** TrueDuck Security (project pseudonym)  
**Brand:** TrueDuck Security (not represented as an incorporated company)  
**Product:** TrueDuck Sentinel Beta (development build)

TrueDuck Sentinel runs automatic rule-based checks on the visible content and link destinations of HTTP(S) webpages where the extension is permitted to run. It also checks text that the user voluntarily pastes into the extension popup. These checks take place in the user's browser.

The extension reads its locally cached list of reported or verified indicators, including email addresses, phone numbers, web domains, URLs and physical addresses. When the user requests a database sync, the extension downloads these records from a local Python server at `http://127.0.0.1:8765`. The extension does **not** transmit scanned webpages, messages or browsing history to the database server, and this starter has no remote analytics or ads.

The extension stores settings, a copy of database records, the date of the most recent synchronization, and a local database access token in browser extension storage. The Python service stores indicator records and their attached notes in a local SQLite database file. The user can add or delete indicators in the dashboard, export a JSON backup, and import a prior JSON backup. Imported records are sent only to the local Python service, not an external website.

This **development notice is not a completed public privacy policy**. Before distributing the extension or hosting any data remotely, review the exact product behavior, data retention, consent, rights to data sources, cross-border issues, user requests and applicable laws. Add developer contact information and a complaint/correction mechanism. Comply with Chrome Web Store's user-data disclosure policies.

A watchlist match or language-pattern caution is not a factual determination that a person or organization committed fraud. An absence of matches does not guarantee safety.

## Version 0.3 additions

The extension analyzes ordinary webpage text, links, and the current webpage URL locally. It sends only alert categories to its extension background service, not full message content. The database access token is stored in trusted extension storage and not exposed to page content scripts; this storage is not encrypted at rest and a compromised local device can still expose it.

Optional recent-alert history is disabled by default. If enabled in Preferences, it stores no more than 50 records of the website hostname (not full URL or page contents), assessment category, and date/time in extension-local storage. You can clear it from the Activity page. Muted-site hostnames are saved in extension-local settings. No external telemetry service is included.

Before publishing beyond your own computer, assess the read-access permission to all HTTP(S) websites, obtain required consents, publish a current privacy policy, and undertake a security review. The local HTTP connection to 127.0.0.1 is not designed to be exposed to the internet.

## Version 0.4: External feed data

You can optionally run a Python script that downloads the URLhaus recent CSV from `urlhaus-api.abuse.ch` using an Auth-Key provided by you. The request sends that Auth-Key to URLhaus; the script does not store it in the SQLite database, extension, or logs. It does not upload scanned webpage content to URLhaus. The user may also import a CSV offline, or load fictional sample records without a network request.

Imported external data is stored in a **separate SQLite table** and cached locally in Edge for on-device detection. It is labeled as external URL intelligence rather than a user-verified scam record. This is a development build, not a comprehensive threat-protection service. The precise usage terms of the external feed and privacy obligations must be reviewed before public or commercial distribution.

## Version 0.5: reports and local review logs

The dashboard can record manual review decisions, notes, and references, and keeps the review events in the local SQLite database. The dashboard shows up to 100 recent events. This log can contain personal data if you type it into an indicator or note, so **do not collect more data than you need**. Removing an indicator also removes its saved review events.

A **Report this site for review** button copies **only the active webpage's hostname** into the dashboard form when you click it. It does not automatically submit any report or collect its text, path, or query-string parameters. If the user deliberately submits the form, that indicator and the user's notes are stored on their own localhost database.

Dismissed records remain stored for review, but are not included in the scanner's locally synchronized active watchlist after a successful sync. The scanner also ignores dismissed entries if they appear in an older cache. A JSON export includes report states and notes; restoring JSON **does not restore the separate event history**. To preserve all data and the audit trail, back up `scamlens.db` while the database server is stopped.

This local, single-owner prototype does not provide identity verification, public reporting, contact removal requests, or independent fact-checking. It is not ready for public user-submitted allegations or commercial distribution without additional privacy controls and security review.


## v0.6: optional public-feed export

Downloading or generating a public-feed snapshot is a local action. Nothing is uploaded by the extension or backend. Public-feed JSON includes only opted-in approved **domains and URL values** plus a review classification and generation time. It intentionally excludes emails, phone numbers, addresses, reviewers’ private notes, evidence references, other personally identifying report data, and imported URLhaus intelligence. All existing records default to private after migration. A domain/URL is not automatically published simply because a reviewer approved it.

If you later upload a snapshot to the internet, the selected domains and URLs become visible to others and may be retained in caches or copies. Do not share a feed without reviewing its accuracy, licensing, privacy implications, correction process, and applicable law.

## v0.7 optional published-intelligence feed

The extension may fetch the approved TrueDuck Security HTTPS feed (or localhost during development) containing manually reviewed and individually opted-in domain/URL indicators. It requests access to that origin from the user. This request does not contain the website they are viewing, message text, local reports, or the private database token. Only the downloaded minimal public indicators and synchronization metadata are saved in the extension's local storage. The new feed is **disabled until connected by the user**. The owner-only publication API is separate and requires a different publisher secret. This is a development privacy description, not a complete policy for a deployed public service.

## Version 0.8: Community accounts and reports (local-only demo)

The optional community reporting console at `127.0.0.1:8877/dashboard` is a **separate** service from the private database. It collects a chosen username, password verifier (a salted PBKDF2 hash; not the raw password), account role, report indicators, notes, evidence reference text, status, and moderation decisions. It stores session-token hashes and expiry dates. It does not require an email address for testing.

Reporter accounts can retrieve only their own reports. Owner accounts can see the moderation queue and audit history. Community reports stay in the cloud demo's separate private database unless an owner deliberately approves and then publishes a domain or URL. Email addresses, phone numbers, physical addresses, original notes, evidence references, and reporter identity are not included in the public feed. No report is submitted automatically when a user clicks the Edge community shortcut: it only opens a form and pre-fills a website hostname. Nothing is sent until the signed-in user submits it.

The dashboard uses no third-party analytics. This demo has no live public hosting, production privacy notice, deletion/export workflow for reporter accounts, or verified identity system. Do not accept real sensitive reports or publish the service until these are addressed. Local SQLite backups stored in the Windows profile contain sensitive report information and are not encrypted by this release.

## v0.9.3: Consumer no-account mode and contact lookups (draft)

An ordinary extension user does not need a username, password, Python server, or admin token. The extension scans content locally and attempts to retrieve the approved TrueDuck Security domain/URL feed from `https://api.trueducksecurity.com/v1/feed` at install/startup and periodically thereafter. The feed GET does not contain visited URLs, webpage text, or messages. The API operator may still receive network metadata such as the user's IP address and request time. The official API address is configured but is **not yet hosted**, so unavailable service responses are normal during development.

**When the user deliberately clicks Look up for an email address or phone number**, the extension checks local data, then sends the exact entered value and indicator type in an HTTPS JSON POST to `https://api.trueducksecurity.com/v1/lookup` (or to explicitly configured localhost for testing). The lookup request does not include the current website or page text, and the client does not save a lookup history. The server returns only whether an exact, individually approved, owner-opted-in contact report is present; it does not return the contact, source, evidence or reporter identity. Server-side logging, retention, incident response, removal/appeal policy and rate limits still need production review. Contact values are potentially personal information: real-world public deployment needs a privacy notice, appropriate legal basis, a dispute/correction process, and anti-enumeration measures.

**Important distinction:** Community reporter accounts remain optional for *submitting* a report; there is no account required for consumers to scan pages or look up contacts. Locally run administrator scripts and SQLite files are not distributed to everyday users in the future Add-ons store build.

No match or a network failure is not evidence that a site, sender, or phone number is safe. No database review establishes legal wrongdoing. Automatic page scanning requires site-read permissions, which should be justified in the Edge listing.
