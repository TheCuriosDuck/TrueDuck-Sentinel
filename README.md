# TrueDuck Sentinel Beta by TrueDuck Security

**Open-source Microsoft Edge scam-awareness extension, published under the TrueDuck Security project brand.**

- **Version:** 0.9.3 Beta (developer preview; suggested first tag `v0.9.3-beta.1`)
- **Software license:** Apache License, Version 2.0 — see [`LICENSE`](LICENSE)
- **Public developer:** TrueDuck Security (brand / public author pseudonym; not an incorporated company)  
- **Brand website:** https://trueducksecurity.com/
- **Trademark / brand guidelines:** [`TRADEMARKS.md`](TRADEMARKS.md)
- **Community contributions:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Security reporting:** [`SECURITY.md`](SECURITY.md)

To the extent the project contributors have rights to license their contributions, the code is available to view, modify, redistribute, and use commercially under Apache-2.0. Branding is distinct from the code license: a fork can describe where the project came from but should not impersonate TrueDuck Security or imply endorsement. The included generic placeholder shield icons are part of this source release; **no official company logo has been provided or included**.

## Easy installation for everyday users (v0.9.3 Beta)

- **No account or Python installation is needed** for browser scanning and manual email/phone lookup.
- Load `extension/` with Edge's `edge://extensions` → Developer mode → Load unpacked. After eventual Edge Add-ons publication, installation will be one click.
- Automatic scanning runs locally on permitted HTTP(S) webpages; it looks for suspicious phrases and indicators. It can show cautions even offline. A warning is not proof of fraud.
- The extension automatically attempts to download a **read-only** approved domain/URL feed from `https://api.trueducksecurity.com/v1/feed`, and refreshes periodically. This endpoint **is not deployed yet**. If unreachable, scanning falls back to locally cached indicators and text heuristics. Do not claim real-time known-scam protection until the API is hosted and checked.
- The popup has an **Email / Phone lookup**. After the user explicitly clicks Look up, it first checks locally cached matches and then sends that one exact contact indicator over HTTPS to `https://api.trueducksecurity.com/v1/lookup` if available. No accounts or administrator token are used. If the API is unavailable, it says so and does not claim the contact is safe.
- The administrator signs in to the separate dashboard to review community reports and can **explicitly opt in** individual reviewed email/phone indicators for anonymous exact-match queries. These contact values are **not distributed in the public feed**. Unapproved, private, and rejected reports are not searchable.
- To test the hosted API behavior on Windows before deployment, read [`TEST_PUBLIC_USER_V093.md`](TEST_PUBLIC_USER_V093.md).

**Status:** This is a local developer Beta; production deployment, abuse-rate limits, privacy/legal review, and an independent security audit are outstanding. Opening a webpage with an extension is not an assurance of protection against fraud.

## What it includes

- `extension/` — Edge extension for risk signals, watched indicators, and explanations
- `backend/` — Python service, your own SQLite indicator database and review/export tools
- `cloud_api/` — community reporting, moderation dashboard, published feed API, and future hosting scaffolding
- `tests/` — Python and JavaScript tests
- `CHECK_SECURITY.cmd` — static preflight checks
- `START_V09_HERE.md` and `BRAND_AND_DOMAIN.md` — Windows setup and customizations

## Local Windows setup (development only)

1. Extract the project. Open Command Prompt in the top-level folder.
2. Install prerequisites: `py -3.12 -m pip install -r cloud_api\requirements.txt`
3. Run `START_DATABASE.cmd` for the local watchlist API.
4. Run `START_CLOUD_API.cmd` for the local community API.
5. Run `CREATE_OWNER.cmd` to create the local admin account, if one has not already been created.
6. Open `edge://extensions` > **Developer mode** > **Load unpacked**, selecting the `extension` folder.
7. Configure local connections in extension Settings and check `http://127.0.0.1:8877/health`.

**Do not host the development servers directly on the internet.** `api.trueducksecurity.com` is a planned production endpoint, not a deployed service. Read [`PUBLIC_RELEASE_CHECKLIST.md`](PUBLIC_RELEASE_CHECKLIST.md) before any public launch.

## Privacy and data

The public repository should contain **source only**. Never commit `backend/data/`, `cloud_api/data/`, SQLite files, API tokens, credentials, backups, real scam reports, or personal data. See `.gitignore` and `SECURITY.md`. Real-world reports may contain sensitive information and are not covered by the code license just because the code is open source.

TrueDuck Sentinel offers **educational scam awareness**, not a guarantee that any site is safe or that reported individuals have committed fraud. This development build has not undergone independent security testing; local tests do not establish production safety. `PRIVACY.md` is a draft, not a published policy.

## Attribution and ownership

The public author attribution uses **TrueDuck Security** as a project pseudonym; no personal name is included. This does not itself establish legal copyright ownership or rights to license someone else’s code. Review the copyright eligibility of AI-assisted material, third-party code, assets, and data licenses before a public release. See [`OWNERSHIP.md`](OWNERSHIP.md).

Built as **TrueDuck Sentinel by TrueDuck Security**; extensions and forks may use the code under Apache-2.0, while brand/trademark rights remain separate.
