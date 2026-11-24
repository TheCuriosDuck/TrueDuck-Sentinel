# TrueDuck Sentinel v0.9.3 Beta — test as an ordinary Edge user

No account or Python setup is required for the **consumer extension**. Python is needed only to test the developer's optional local API and administration functions.

## A. Install / test offline (no servers)

1. Open `edge://extensions` in Microsoft Edge, enable Developer mode, remove the old TrueDuck Sentinel development extension if it points to an old folder, and choose **Load unpacked** → `scamlens\extension`.
2. You do not need to sign in, connect to the private database, or start either Python server. TrueDuck Sentinel scans ordinary HTTP(S) pages by default.
3. Open the popup and paste `URGENT PAYMENT: Act now or your account will be suspended. Pay using a gift card.` into **Quick Check**; press **Check text**. Expect a **suspicious language** caution.
4. For the **on-page warning test** (developer only), open Command Prompt in the repo root and run `py -3.12 -m http.server 8888 --directory tests`, then visit `http://127.0.0.1:8888/scamlens_demo.html`. You should see a dismissible suspicious-language warning. Neither TrueDuck Sentinel database server nor admin account is required; Python only serves this test HTML page. Content scripts do not run on `file://` by default.
5. Open **Look up email or phone** and enter `reviewed@example.test` or `202-555-0177`. Without a cached match or a reachable public API, expect **Unable to verify online**. Do NOT treat that as clean or safe.

## B. Test true server-side contact lookup locally (developer only)

1. In Command Prompt from project root run `py -3.12 -m pip install -r cloud_api\requirements.txt` if dependencies are missing.
2. Start `START_CLOUD_API.cmd` (port `8877`). The separate owner admin account is created by `CREATE_OWNER.cmd` if needed. You do not need to start `START_DATABASE.cmd` for this test.
3. Visit `http://127.0.0.1:8877/dashboard`; sign in as owner. Submit a **fictional** `email` report `reviewed@example.test` or a `phone` report `2025550177` under Submit report. Provide a fictional case reference. As owner, approve it with an evidence reference (such as `TEST-001`), and in Moderation click **Enable contact lookup**. This is separate from approving the report.
4. Open TrueDuck Sentinel extension Settings, scroll to **Published intelligence feed**, enter `http://127.0.0.1:8877/v1/feed`, choose **Sync published feed** and approve the optional localhost host permission.
5. Open the extension popup → **Look up email or phone**, enter the exact fictional contact, and click **Look up indicator**. Expect **Reviewed contact indicator match**. No user login required.
6. In Moderation click **Disable public lookup**, then repeat step 5. The result should no longer return a reviewed contact match from the server. There is never a publicly downloadable list of contact values.

## C. Test public website intelligence (developer only)

Approve and publish a fictional domain `review-feed.example.test` in your owner dashboard. Use Settings → Published intelligence feed → local `http://127.0.0.1:8877/v1/feed` and **Sync published feed**; Quick Check `Visit review-feed.example.test` should show a **published intelligence match**. The production HTTPS feed is not live until you deploy it.

## Caveats before public release

- The owner-managed API currently uses **local** development rate limits. An internet-facing lookup API can be enumerated. Use centralized throttles, abuse monitoring, independent testing, privacy review, correction/appeals and a clear retention policy before exposing it online.
- Broad site access lets TrueDuck Sentinel inspect visible text on ordinary websites locally. It must be disclosed and justified to Edge users.
- Never promise to detect every scam or call unmatched contacts safe. A match is evidence of a reviewed report, not a criminal finding.
- Do not commit local databases, user data, tokens, backups, `*.db` files or `.env` files to GitHub.
- This is a Beta; the new consumer features have automated tests, but need hands-on Microsoft Edge testing.
