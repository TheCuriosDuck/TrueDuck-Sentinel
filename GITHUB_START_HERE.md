# TrueDuck Sentinel — upload to GitHub (Windows)

**Repository:** `trueduck-sentinel`  
**Brand:** TrueDuck Security  
**Release:** 0.9.3 Beta (developer preview)  
**License:** Apache-2.0, subject to contributor rights and third-party licenses.

## 1. Clone the empty private repository

Open GitHub Desktop → **File → Clone repository** → select the existing private `trueduck-sentinel` repository → **Clone**.

## 2. Copy the source into the cloned repository root

Extract `TrueDuck-Sentinel-GitHub-Ready-v0.9.3-beta.zip` to a regular folder outside the GitHub clone. Open its inner **trueduck-sentinel** folder, select **everything inside it** (including `.gitignore` and `.dockerignore`), then copy the selection. In GitHub Desktop choose **Repository → Show in Explorer** and paste into the repository directory that opens.

Do **not** paste the entire `trueduck-sentinel` folder inside the cloned `trueduck-sentinel` directory. The main repository page must list `extension/`, `backend/`, `cloud_api/`, `tests/`, `README.md`, and `LICENSE` directly.

## 3. Check the files before committing

Verify that GitHub Desktop is **not** showing `.env`, private credentials, database records, backup files, API tokens, or personal data. `.gitignore` helps but does not prevent all leaks. Make sure your Git commit author/email settings won't expose details you wish to keep private.

## 4. Verify and upload

In the cloned project directory run `CHECK_SECURITY.cmd`. Install dependencies first with `py -3.12 -m pip install -r cloud_api\requirements.txt` if necessary. If tests pass, in GitHub Desktop choose **Commit to main**, summary `Initial TrueDuck Sentinel Beta source`, then **Push origin**. Refresh the private GitHub repo homepage.

## 5. Test the beta in Edge

Edge → `edge://extensions` → Developer mode → **Load unpacked** → select the cloned repository's `extension` directory. The extension can scan ordinary sites and perform offline warnings without logging in. A production live feed is **not** available until `https://api.trueducksecurity.com` is securely deployed. See `TEST_PUBLIC_USER_V093.md` for local testing with fictional data.

## Important before public release

Do **not** make the repository public just because the tests pass. Review code dependencies, repository history, author attribution, the draft privacy policy, extension permissions and external data handling. See `PUBLIC_RELEASE_CHECKLIST.md` and `SECURITY.md`.

### Compatibility note

The product was previously developed under the internal name ScamLens. Some internal identifiers (`SCAMLENS_` environment variables, `scamlens.public-feed.v1` schema, cache keys, and Python database filename) intentionally remain unchanged in v0.9.3 for compatibility. They are not user-facing branding. Do not blindly rename them; doing so could break publishing and detection.
