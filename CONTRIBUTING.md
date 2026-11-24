# Contributing to TrueDuck Sentinel

Thanks for considering improvements to TrueDuck Sentinel by TrueDuck Security.

1. Open an issue or describe the behavior you want to change before a large patch.
2. Keep changes focused, with comments explaining non-obvious Python behavior.
3. Run `py -3.12 -m unittest discover -s tests` and `node tests/detector.test.js` before proposing code changes (if Node.js is installed).
4. Do not submit real victims' messages, email addresses, phone numbers, credentials, tokens, or reports. Use `.example` / `.test` domains and fabricated test values.
5. Avoid introducing broad permissions or new external data transfers without a clear justification and privacy review.
6. Disclose the third-party licensing of any dependency, image, data feed, or other code you add.
7. Treat reports as allegations unless evidence has been reviewed. Never label an individual a scammer just because a user submitted a report.

Unless explicitly stated otherwise, contributions submitted for inclusion are
subject to the Apache License 2.0 as described by Section 5. Contributors
should contribute only material they have the right to license. Maintainers
can decline contributions that affect privacy, security, or scope.

See `SECURITY.md` for responsible reporting of vulnerabilities rather than
posting exploitation details in public issues.
