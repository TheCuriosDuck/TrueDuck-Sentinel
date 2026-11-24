# Open-source repository preparation checklist

- [x] Set public author display to **TrueDuck Security** (pseudonym) in the manifest, UI, and `NOTICE`.
- [ ] Confirm the author has rights to license the software and artwork; pseudonymous branding does not establish legal ownership.
- [ ] Ensure you have the right to license all included works and generic artwork.
- [ ] Remove `backend/data/`, `cloud_api/data/`, backups, secrets, report exports, `.env`, account information, and all `.pyc` files.
- [ ] Scan the entire Git history for secrets if this repository has ever been public or contained credentials.
- [ ] Check third-party dependencies and URLhaus redistribution/commercial licensing requirements.
- [ ] Upload source to a **private** `scamlens` repository first and manually review all files and history, then consider public visibility.
- [ ] Add `LICENSE`, `NOTICE`, `TRADEMARKS.md`, `CONTRIBUTING.md`, `SECURITY.md`.
- [ ] Enable GitHub secret scanning and private vulnerability reporting if available.
- [ ] Set GitHub description to “TrueDuck Sentinel — open-source scam-awareness extension by TrueDuck Security.”
- [ ] Create a GitHub **pre-release** (`v0.9.2-beta.1`) and label the extension developer preview.
- [ ] Do not publish a public API or solicit real user reports until the production security/privacy checklist is complete.
