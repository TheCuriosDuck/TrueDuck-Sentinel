# TrueDuck Sentinel v0.8 — security and privacy boundaries

This release is a **local, educational prototype** designed for Windows/Edge. Do not describe it as a security-audited or publicly hosted production service.

## Implemented in v0.8

- Private and public databases are separate, using two distinct local services.
- Reporter and owner roles; account registration defaults **off** except in the local demonstration launcher.
- User passwords use random per-account salts and PBKDF2-HMAC-SHA256, with a configurable migration path to Argon2id later.
- Sessions use high-entropy bearer tokens; only their SHA-256 verifiers are stored in SQLite. Tokens expire after 8 hours and can be revoked on logout.
- Local in-memory sliding-window limits on login, signup, and reports; additional per-reporter report quotas.
- Input type/size checking and exact duplicate checks per reporter.
- Submission is private and pending by default. Review evidence is required for approval. Only the owner can publish.
- Re-review or retraction removes community entries from the public feed and bumps its revision.
- Email addresses, phone numbers, street addresses, notes and evidence references are never published by the community feed.
- Dashboard uses local JavaScript/CSS assets, CSP, and text nodes instead of inserting report HTML.
- On-startup SQLite backups outside the version directory; optional Windows Task Scheduler daily run.

## Not yet production-ready

- No HTTPS termination, hardened reverse proxy, secure-cookie session flow, or deployed identity provider.
- No multifactor authentication / passkeys for the owner account; implement before exposing a real moderator account.
- Local rate limiting is per Python process. A hosted deployment needs shared Redis/proxy/WAF limits, abuse signals, and monitoring.
- No email confirmation, verified identities, account recovery, password breach screening, spam classification or bot challenges.
- Backups are NOT encrypted and restore procedures have only been tested with SQLite backups; hosted Postgres requires separate PITR/pg_dump policy, disaster recovery, and retention controls.
- No formal vulnerability assessment, penetration test, external code audit, or production observability.
- Avoid storing highly sensitive information in report notes; add retention/deletion workflows and a legally reviewed privacy notice before accepting real submissions.
- Do not expose `START_DATABASE.cmd`'s API, `START_CLOUD_API.cmd`, or `CREATE_OWNER.cmd` to the public internet.

## Publishing and rights

Indicator values may contain personal data. Legitimate reports are not evidence of wrongdoing by themselves. Treat community submissions as unverified until reviewed and preserve retraction/dispute mechanisms. Never publish identifying information about private persons. Ensure external-feed license compliance if you redistribute third-party data. Use the public project byline TrueDuck Security; ensure the actual author has rights to grant the license before publication.

## External references (as of November 2026)

- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP Bot Management / Anti-Automation: https://cheatsheetseries.owasp.org/cheatsheets/Bot_Management_and_Anti-Automation_Cheat_Sheet.html
