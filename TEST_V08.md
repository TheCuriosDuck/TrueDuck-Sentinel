# v0.8 acceptance checks

Work only with fictional `example.test` records. Don't test against real scam links.

1. Open `http://127.0.0.1:8877/health`. Expected: `status: ok`.
2. Run `CREATE_OWNER.cmd`. Sign in at `/dashboard`. Expected: owner-only Moderation, Audit history and Overview.
3. Open a separate Edge InPrivate window and register a reporter. Expected: no owner access.
4. Reporter submits `community-test.example.test`. Expected: pending report and **no public feed match**.
5. Owner approves with a review reason and evidence reference. Expected: approved, still **not** in public feed.
6. Owner clicks Publish. Expected: now visible in `/v1/feed` and, after sync, detectable in Edge Quick Check.
7. Owner retracts or changes review state. Expected: disappears from `/v1/feed`; sync Edge again to clear old results.
8. Try reporting the same indicator twice from the same reporter. Expected: duplicate rejected.
9. Try to publish an email or physical address, even after approval. Expected: server refuses.
10. Run `BACKUP_NOW.cmd`. Expected: valid SQLite backup files under `%LOCALAPPDATA%\TrueDuck Sentinel\Backups`.
11. Run `py -3.12 -m unittest discover -s tests -v` in the main folder. Expected: all tests pass.
12. Run `node tests/detector.test.js` if Node.js is installed. Expected: detector tests pass.

**Common pitfalls**

- `ModuleNotFoundError: cloud_api`: use the new `START_CLOUD_API.cmd` from the project root.
- Missing `cloud_api\requirements.txt`: Command Prompt is in the wrong directory.
- Error 403 on signup outside the demo: expected. Signup defaults to disabled unless `SCAMLENS_ALLOW_SIGNUP=1`.
- Published report still appears after retracting: sync the Edge published feed again. The extension uses a cache.
- Forgot the owner password: this demo has no online account-recovery flow. You can create a new test DB, but real deployments need a controlled recovery process.
