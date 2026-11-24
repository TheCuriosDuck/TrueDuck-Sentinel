# TrueDuck Sentinel v0.9 — security review and explicit tradeoffs

This note implements part of the guidance in the **Chrome extension security and privacy docs**, **Microsoft Edge Add-ons policies**, and the **OWASP Browser Extension Vulnerabilities Cheat Sheet**. The Chrome guidance is useful because modern Edge extensions use the Chromium extension platform. There are remaining items that require manual review and a hosted deployment design.

## Permissions (what users grant)

`extension/manifest.json` requests exactly `storage` and `activeTab` as named required APIs. It requires one network host, `http://127.0.0.1:8765/*`, for the owner-only local database. A second local demo host (`http://127.0.0.1:8877/*`) and HTTPS feed endpoints are **optional permissions**: the extension requests permission for the particular feed origin **only after** a user chooses Sync published feed.

**Important tradeoff:** The automatic detection feature installs `content.js` into normal HTTP(S) webpages through `content_scripts.matches`. This is **broad website access**, even though `<all_urls>` does not appear in `host_permissions`. `activeTab` alone would only support scans after a click, not continuous scanning as users browse. Edge users must see an accurate explanation that the extension reads visible page text locally. A future *manual-scan-only* product edition could avoid the broad script match and instead use `activeTab` + `scripting` after a click.

The optional permission declaration `https://*/*` supports user-chosen public feed services; actual runtime requests target only the chosen origin. This is still a broad declaration and should be **replaced by an owned API hostname** before store release, with a proper UX for that service. Never add `cookies`, `history`, `webRequest`, `debugger`, or other powerful permissions without a specific feature and justification.

## Communications

- The installed extension sends **no website text** to our Python services. Its local detector looks at page text and links in memory.
- The private owner API listens only on `127.0.0.1:8765`, and the second local demo listens only on `127.0.0.1:8877`. Unencrypted HTTP is permitted **only for the local development setup**, never across the public internet.
- User-configured public intelligence feeds must use **HTTPS**, except the exact `127.0.0.1:8877/v1/feed` test endpoint.
- The public feed transfers only reviewed, explicitly published domains / URLs. It never transfers owner API tokens, evidence notes, emails, phone numbers, physical addresses, or webpage text.
- The optional community-report console can receive **what a reporter deliberately enters**. A production privacy policy must disclose report fields, retention, review access and deletion rights.

## XSS, scripts, and message boundaries

- The extension's `content_security_policy.extension_pages` allows packaged scripts, denies plugins and inline scripts, and constrains outbound connections. Manifest V3 does not allow remotely hosted executable code.
- The in-page warning uses `document.createElement` and `textContent`, and the community dashboard renders submitted report values using `textContent` rather than interpreting them as HTML.
- Content scripts run in an isolated world (the Chromium default). They request settings through the extension background worker. The worker permits only the top-level extension content script and sends **minimal detection fields** instead of private review notes and tokens.
- `chrome.storage.local.setAccessLevel({ accessLevel: 'TRUSTED_CONTEXTS' })` restricts access to the private token and caches from content scripts; it does **not** encrypt local disk storage. An attacker who compromises the Windows profile or extension itself may access this data.
- A malicious webpage may contain crafted or unusually large input; the detector limits scanned text and the extension banner does not interpolate page text into HTML.

## Update and dependency integrity

- Keep releases signed and distributed through **Microsoft Edge Add-ons** after acceptance. No extension JavaScript should be loaded or updated from an arbitrary third-party URL.
- Protect the eventual Microsoft Partner Center developer account with **multi-factor authentication** and least privilege; use distinct unique credentials and a secure repository.
- Review `cloud_api/requirements.txt` and dependency changelogs. Run `python -m pip list --outdated` and a vulnerability scanner such as `pip-audit` in a separate controlled environment. This ZIP does **not** claim dependencies have been audited or cryptographically pinned.
- `CHECK_SECURITY.cmd` is a limited code-pattern/manifest checker and Python test runner; it is not a dependency/SCA scan or independent security audit.

## Before allowing public reports (BLOCKERS)

1. Use a real owned domain with TLS termination and HTTPS everywhere, a managed PostgreSQL database, non-public backend networking, and proper secret management. Never port-forward local developer ports.
2. Replace per-process in-memory rate limiting with **shared** abuse controls (e.g. at the edge and API), monitor abuse and audit logs, and plan incident response and account recovery.
3. Reconsider the browser console's `sessionStorage` bearer-session handling for production. Implement a robust session and CSRF threat model; test XSS and session fixation/expiry under your target hosting architecture.
4. Add email verification and anti-bot controls before opening self-registration. **Production mode currently refuses public signup** until reviewed.
5. Add database migrations, tested encrypted backups and restoration drills, secrets rotation, server and permission monitoring, reporter removal/correction rights and lawful data-retention policies.
6. Perform threat modeling, static analysis, dependency audit, automated browser tests, penetration testing, and a legal/privacy review. Exercise false positive retractions and dispute handling before calling any report 'known scam'.
7. Ensure your URLhaus agreement permits the intended redistribution and commercial use.

The cloud API's `cloud_api/production.py` rejects a number of obviously dangerous settings when `SCAMLENS_ENV=production`, but **passing those checks does not mean that deployment is approved or secure**. The example `cloud_api/Caddyfile.example` is a learning/reference template, not a turnkey public deployment.

## Primary references

- Chrome extension guidance: https://developer.chrome.com/docs/extensions/develop/security-privacy/stay-secure
- Chrome privacy and permission advice: https://developer.chrome.com/docs/extensions/develop/security-privacy/user-privacy
- OWASP extension cheat sheet: https://cheatsheetseries.owasp.org/cheatsheets/Browser_Extension_Vulnerabilities_Cheat_Sheet.html
- Microsoft Edge Add-ons developer policies: https://learn.microsoft.com/en-us/legal/microsoft-edge/extensions/developer-policies
- Microsoft Edge CSP: https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/developer-guide/csp
