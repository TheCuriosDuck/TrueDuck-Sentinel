# TrueDuck Sentinel — brand and domain configuration

**Product name:** TrueDuck Sentinel Beta  
**Public developer:** TrueDuck Security  
**Repository:** `trueduck-sentinel`  
**Website:** https://trueducksecurity.com/  
**Planned HTTPS API:** https://api.trueducksecurity.com/

This is a renamed beta based on the account-free extension build v0.9.3. It does not require an account to scan public websites or check text locally. A user chooses to submit an email/phone number to the HTTPS lookup service; this service is **not deployed** yet. The name change does not add live online reputation coverage.

## Editable branding

- Product name and publisher: `extension/manifest.json`
- Popup: `extension/popup.html`, `extension/styles.css`
- Settings: `extension/options.html`
- On-page warning: `extension/content.js`
- Community dashboard: `cloud_api/dashboard/index.html`
- Temporary shield icons: `extension/assets/icon16.png`, `icon32.png`, `icon48.png`, `icon128.png`

The included icon is a **placeholder**, not the official TrueDuck Security logo. Replace it only with artwork you own or are authorized to distribute.

## Keep these internal names until an explicit migration

- `SCAMLENS_*` Python environment variable names
- `scamlens.public-feed.v1` JSON feed schema
- `ScamLensDetector`, `ScamLensFeed`, `ScamLensLookup` JavaScript interfaces
- `scamlens.db` local SQLite filename and local storage names

These are protocol and backward-compatibility details, not product branding. Changing them without a migration may break your existing database, cached feeds, and tests.

## Hosting and publication

The API domain is a planned endpoint, not an active hosted service. Do not expose development servers on ports 8765 or 8877 to the internet. Before public distribution complete HTTPS hosting, abuse defenses for lookup, permission disclosures, privacy/legal review, dependency checks, and independent security assessment. See `PUBLIC_RELEASE_CHECKLIST.md`.
