# Pre-release checklist — Microsoft Edge Add-ons

**TrueDuck Sentinel v0.9 is a local development preview. This is a checklist, not a claim that the work is done.** Do not publish until a competent security and privacy review resolves the blockers.

- [x] Manifest V3 extension source and packaged scripts (no remote JavaScript).
- [x] Local private database token is restricted to trusted extension storage contexts.
- [x] Browser warning and community dashboard use safe text rendering.
- [x] Public feed is owner-reviewed, opt-in, and domain/URL-only.
- [x] Public HTTPS feed enforcement (localhost exception for testing).
- [x] Production configuration guardrails and basic static checks.
- [ ] Restrict public feed optional host permissions to your **actual owned HTTPS API hostname**.
- [ ] Decide whether broad automatic webpage scanning is necessary; justify it accurately in the store listing or offer a manual-only edition.
- [ ] Deploy behind HTTPS with non-public app port, managed DB, monitored logs, and independent backups.
- [ ] Implement distributed rate limits, bot defense, account verification, secure recovery, real session-security controls and appropriate admin authorization review.
- [ ] Run dependency audit, browser E2E tests, security review and penetration tests.
- [ ] Create a public privacy policy describing automatic local page inspection, optional alert history, reported personal data, cookies/session handling, retention, deletion and sharing.
- [ ] Decide your real legal publisher/developer name and verify you may use the TrueDuck Sentinel product name.
- [ ] Protect your Microsoft developer account with multi-factor authentication.
- [ ] Prepare the Edge Add-ons package, screenshots, description, permission explanations and truthful security claims.
- [ ] Test that a report retraction propagates to deployed extension clients reliably.

The current code is a foundation for this work; Microsoft Edge Add-ons review and update signing happen **after submission**. Publishing under your own name and owning source code are separate from copyrightability and trademark clearance.
