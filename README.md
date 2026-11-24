# TrueDuck Sentinel

**v0.9.8 Beta · Free and open source · No account required**

TrueDuck Sentinel is a browser extension for Microsoft Edge that helps users identify potential scams, check suspicious contact information, and report suspicious activity. It combines local detection rules with administrator-reviewed community intelligence when connected to a compatible service.

## Features

- **Automatic website warnings:** Checks visible webpage content for common scam tactics and matching published website indicators.
- **Email and phone lookup:** Checks email addresses and US/Canada phone numbers for reviewed reports.
- **Quick Check:** Paste a suspicious message, link, email address, or phone number for analysis.
- **Anonymous reporting:** Submit suspicious indicators without creating an account.
- **Reviewed intelligence:** Public matches can include a review summary explaining why the indicator was flagged.
- **Privacy controls:** Customize scanning sensitivity, pause scanning on selected websites, and optionally keep a local alert history.

## Installation

TrueDuck Sentinel is currently a Beta developer preview. To install it manually in Microsoft Edge:

1. Download the project from the repository's **Releases** page or select **Code → Download ZIP**.
2. Extract the downloaded ZIP.
3. Open Microsoft Edge and enter `edge://extensions` in the address bar.
4. Enable **Developer mode** and select **Load unpacked**.
5. Select the `extension` folder containing `manifest.json`.
6. Open TrueDuck Sentinel from the Extensions menu. Pin it to your toolbar if desired.

No account or Python installation is required for local detection.

## How to use

### Browse normally

When automatic scanning is enabled, TrueDuck Sentinel checks supported webpages as you browse and displays a dismissible warning when suspicious patterns or published indicators match.

### Look up an email or phone number

Open the extension, select **Email address** or **Phone number (US / Canada)**, enter the contact information, and click **Look up indicator**. If a reviewed, searchable record matches, its public review summary is displayed when available.

### Check a suspicious message

Paste a message or link into **Quick Check** and click **Check text**. The extension will identify matching indicators and common suspicious-language patterns.

### Report a scam

Select **Report a scam anonymously**, enter the suspicious information and a description, and submit the report. Reports remain private until an administrator reviews them and explicitly enables public access. Submitting a report does not automatically trigger a public warning.

## Beta availability

Local suspicious-language detection works without a server. Shared website intelligence, live contact lookups, and anonymous reporting require a trusted, compatible intelligence service configured in **Settings → Public intelligence feed (optional)**. No central hosted service is configured by default in this release.

A missing report, unavailable service, or absence of a warning does not mean a website or contact is safe.

## Privacy and security

Automatic webpage analysis runs locally. Manual contact lookups send the entered value to the configured service when requested. Reports send the information you choose to submit; server access logs may record IP addresses. No user account is required. Optional alert history is stored locally and is disabled by default.

The extension requires webpage access to provide automatic scanning. You can disable scanning or pause it on selected sites in Settings. Only connect to intelligence services you trust.

This is experimental software and has not undergone an independent security audit. It is not a replacement for established security software or independent verification.

## Open source

TrueDuck Sentinel is released under [The Unlicense](LICENSE) for original code that contributors have the rights to release. You are free to use, copy, modify, and redistribute that code, including commercially, without attribution. Third-party software and data remain subject to their own terms. No exclusive project trademark rights are asserted; this does not prevent third-party trademark claims.

Contributions, bug reports, and improvements are welcome. For security vulnerability reporting, see [SECURITY.md](SECURITY.md).

## Project resources

- [Development and administration guide](DEVELOPMENT.md) — server setup, report moderation, and testing.
- [Sources and acknowledgments](SOURCES.md) — research references, technologies, and AI usage disclosure.
- [License](LICENSE) — open-source licensing terms.

OpenAI's ChatGPT was used substantially to assist with architecture, code generation, debugging, security guidance, documentation, and automated testing. The maintainer directed the requirements, tested builds, and guided revisions. Independent review is encouraged.

---

**Disclaimer:** TrueDuck Sentinel provides educational scam awareness and advisory warnings. A report or match is not proof of fraud, and the absence of a warning does not establish safety. The software is provided as-is, without warranty.
