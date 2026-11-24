# Security policy (development release)

**TrueDuck Sentinel v0.9.2 has not undergone an independent security audit and is not ready for public production hosting.** No promise of vulnerability response time or patch SLA is made.

## Reporting vulnerabilities

Please do **not** post secrets, working exploits, or private reports in public GitHub issues. Until a dedicated security inbox is established, contact the project operator privately through the verified contact channel published on https://trueducksecurity.com/. Do not assume an address or account is secure without verifying it. Once a GitHub repository is created, maintainers should enable private vulnerability reporting and update this policy with the exact procedure.

Include affected version, steps to reproduce using invented data, expected/actual results, and potential impact. Never test against another person's accounts or data without authorization.

## Protect secrets and private data

- Do not commit `.env`, `backend/data/`, `cloud_api/data/`, `*.db`, backups, tokens, passwords, or genuine reports.
- `CHECK_SECURITY.cmd` is a lightweight static preflight, **not** a security audit.
- Keep development servers bound to localhost; do not open ports 8765 or 8877 to the public internet.
- Before hosting: use HTTPS, managed PostgreSQL, independent backups, access controls, secrets management, distributed rate limits, logging, and external security review.
- Validate third-party feeds for permitted reuse; external indicators do not automatically imply criminal conduct.

Refer to `PUBLIC_RELEASE_CHECKLIST.md` and `SECURITY_REVIEW_V09.md`.
