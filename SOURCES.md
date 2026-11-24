# TrueDuck Sentinel — Sources and Acknowledgments

This document records identifiable development resources, software dependencies, and AI assistance for TrueDuck Sentinel (v0.9.8 Beta and earlier development versions). It is not an exhaustive browsing history. Listing a resource does not imply affiliation, endorsement, or that its source code was copied.

## Security and browser-extension references

The following references were identified during development or supplied as part of the project's security checklist:

- [Chrome Developers — Stay secure](https://developer.chrome.com/docs/extensions/develop/security-privacy/stay-secure): extension security, safe code execution, and network permissions.
- [Chrome Developers — Protect user privacy](https://developer.chrome.com/docs/extensions/develop/security-privacy/user-privacy): minimal permissions and data collection.
- [Chrome Developers — Extension documentation](https://developer.chrome.com/docs/extensions/): Manifest V3, content scripts, storage, and extension APIs.
- [Microsoft Edge extension documentation](https://learn.microsoft.com/en-us/microsoft-edge/extensions/): extension development, testing, and publishing guidance.
- [OWASP Cheat Sheet Series — Browser Extension Vulnerabilities](https://cheatsheetseries.owasp.org/cheatsheets/Browser_Extension_Vulnerabilities_Cheat_Sheet.html): extension security practices.
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) and [OWASP API Security Project](https://owasp.org/www-project-api-security/): authentication, access control, and API security guidance.
- [AppSecBrief — Browser Extension Security Developer Guide](https://appsecbrief.com/articles/browser-extension-security-developer-guide-2026/): supplementary security reference supplied during development.
- [Safeguard — Browser Extension Security Risks for Developers](https://safeguard.sh/resources/blog/browser-extension-security-risks-for-developers): supplementary dependency and update-security reference supplied during development.

## Languages, libraries, and technologies

| Resource | Role in the project |
| --- | --- |
| [Python](https://docs.python.org/3/) | Backend programming, validation, authentication, database operations, and automated testing |
| [JavaScript, HTML, and CSS (MDN)](https://developer.mozilla.org/) | Browser extension, detection logic, user interface, and administrator dashboard |
| [SQLite](https://www.sqlite.org/) | Local development database |
| [FastAPI](https://fastapi.tiangolo.com/) | HTTP API and request handling |
| [Starlette](https://www.starlette.io/) | Web middleware and API testing support through FastAPI |
| [Uvicorn](https://www.uvicorn.org/) | Local API server |
| [SQLAlchemy](https://www.sqlalchemy.org/) | Database access and queries |
| [PostgreSQL](https://www.postgresql.org/) and [Psycopg](https://www.psycopg.org/) | Optional production database support |
| [Node.js](https://nodejs.org/) | Running JavaScript tests |
| [Docker](https://docs.docker.com/) and [Caddy](https://caddyserver.com/docs/) | Optional deployment configuration examples; not evidence of a deployed service |

The current declared Python dependencies are in `cloud_api/requirements.txt`. Other libraries may be installed transitively or needed for testing.

## Threat intelligence

- [URLhaus (abuse.ch)](https://urlhaus.abuse.ch/) — Optional malware-URL intelligence integration developed in earlier versions. Legacy importer code remains in the source archive, but the retired private database is not part of the current normal public-warning workflow. URLhaus is not a comprehensive scam-contact database. Its data and API have separate terms of use.
- Community reports and administrator-reviewed indicators are the intended source of published project intelligence. Fictional examples in the test suite are not real fraud reports.

## Development tools

- [Git](https://git-scm.com/) — Version control.
- [GitHub](https://docs.github.com/) and [GitHub Desktop](https://desktop.github.com/) — Repository management and release preparation.
- [Microsoft Edge](https://www.microsoft.com/edge) — Browser extension installation and manual testing.
- [OpenAI ChatGPT](https://chatgpt.com/) — AI-assisted development, as described below.

## AI-assisted development disclosure

This project was developed with assistance from OpenAI's ChatGPT. AI was used to generate and revise source code, help design the architecture, troubleshoot errors, suggest security controls, write documentation, and develop automated tests.

The maintainer directed the project's requirements and design decisions, installed and tested builds, reported errors, and guided revisions. AI assistance contributed substantially to the implementation; the project is not represented as entirely handwritten by its maintainer.

AI-generated code can contain errors, vulnerabilities, or licensing issues. Automated tests and static security checks do not constitute an independent security audit. The project remains experimental, and community contributions, code reviews, and security improvements are encouraged.

## Licensing and project status

- [The Unlicense](https://unlicense.org/) — Current license for original project contributions to the extent their contributors have the rights to release them. Earlier project versions used the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). Third-party software, data, and assets retain their applicable licenses and terms; this document is not a substitute for required third-party notices.
- TrueDuck Sentinel is an independent open-source developer Beta. It is not affiliated with or endorsed by the organizations listed here.
- The software is provided as-is. Warnings are not proof of fraud, and absence of a warning does not establish safety. Independent security review and production deployment safeguards remain necessary.
