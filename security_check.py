"""Static security preflight for the TrueDuck Sentinel Microsoft Edge extension.

Run from the project root:
    py -3.12 security_check.py

This is a quick lint-style gate, NOT a substitute for a browser security audit,
penetration test, privacy review, or automated dependency vulnerability scan.
"""

import json  # Read the same manifest file Microsoft Edge reads.
import re  # Find common unsafe JavaScript patterns.
from html.parser import HTMLParser  # Inspect script tags without executing JavaScript.
from pathlib import Path  # Keep checks independent of the current working directory.

PROJECT = Path(__file__).resolve().parent


class ScriptParser(HTMLParser):
    """Identify inline scripts and scripts loaded from another origin."""

    def __init__(self):
        super().__init__()
        self.issues = []

    def handle_starttag(self, tag, attributes):
        if tag.lower() != 'script':
            return
        attrs = dict(attributes)
        src = attrs.get('src', '')
        # In Manifest V3, executable JavaScript must ship inside the package.
        if not src or '://' in src or src.startswith('//') or src.startswith('data:'):
            self.issues.append(f'Inline or remote script: {src or "<inline>"}')


def inspect(root: Path = PROJECT):
    """Return (blocking_errors, review_warnings), with no files modified."""
    errors, warnings = [], []
    manifest = json.loads((root / 'extension' / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('manifest_version') != 3:
        errors.append('Use Manifest V3, not an older extension manifest.')

    # Compare permission names with the small set needed for the local design.
    required = set(manifest.get('permissions', []))
    if not required <= {'storage', 'activeTab', 'alarms'}:
        errors.append(f'Unexpected required browser API permission(s): {sorted(required - {"storage", "activeTab", "alarms"})}')

    # No feed server is permitted automatically on installation.
    hosts = manifest.get('host_permissions', [])
    if hosts != []:
        errors.append(f'Required host permission changed: {hosts!r}')

    # An explicitly selected hosted feed may use HTTPS, never arbitrary HTTP.
    for host in manifest.get('optional_host_permissions', []):
        if not (host.startswith('https://') or host in ('http://127.0.0.1:8877/*',)):
            errors.append(f'Unsafe optional host permission: {host}')
    if 'https://*/*' in manifest.get('optional_host_permissions', []):
        warnings.append('Optional HTTPS access is broad but requires explicit user consent. A store release should ideally use an audited fixed endpoint.')

    # The only predeclared optional hosts are HTTPS (with permission) and local test services.
    expected = {'http://127.0.0.1:8877/*'}
    if set(manifest.get('optional_host_permissions', [])) != expected | {'https://*/*'}:
        errors.append('Unexpected optional feed host: Only explicitly requested HTTPS or local development hosts are permitted.')

    auto_matches = [value for spec in manifest.get('content_scripts', []) for value in spec.get('matches', [])]
    if 'http://*/*' in auto_matches or 'https://*/*' in auto_matches:
        warnings.append('Auto-scanning is broad by design: it can read normal webpages. Disclose and justify this, or offer a lower-permission on-demand edition.')

    # A strict extension policy blocks inline/remote JavaScript execution.
    csp = manifest.get('content_security_policy', {}).get('extension_pages', '')
    if "script-src 'self'" not in csp or "object-src 'none'" not in csp or "base-uri 'none'" not in csp:
        errors.append('Missing restrictive extension Content Security Policy.')
    if "unsafe-inline" in csp or "unsafe-eval" in csp:
        errors.append('Unsafe CSP script execution is not allowed.')

    # Content scripts should be isolated from website scripts by default.
    for spec in manifest.get('content_scripts', []):
        if spec.get('world', 'ISOLATED') != 'ISOLATED':
            errors.append('Content scripts must not run in the webpage MAIN world.')

    js_sources = list((root / 'extension').rglob('*.js')) + list((root / 'cloud_api' / 'dashboard').glob('*.js'))
    unsafe_patterns = {
        r'\binnerHTML\s*=': 'Assigning untrusted HTML via innerHTML',
        r'\bdocument\.write\s*\(': 'document.write',
        r'(?<![\w.])eval\s*\(': 'eval() execution',
        r'\bnew\s+Function\s*\(': 'new Function() execution',
    }
    for file in js_sources:
        source = file.read_text(encoding='utf-8')
        for pattern, description in unsafe_patterns.items():
            if re.search(pattern, source):
                errors.append(f'{file.relative_to(root)}: {description}')

    for html in (root / 'extension').glob('*.html'):
        parser = ScriptParser()
        parser.feed(html.read_text(encoding='utf-8'))
        errors.extend(f'{html.relative_to(root)}: {finding}' for finding in parser.issues)

    bg = (root / 'extension' / 'background.js').read_text(encoding='utf-8')
    if 'TRUSTED_CONTEXTS' not in bg or 'recordsForPage(' not in bg:
        errors.append('Expected restricted storage and minimized content-script records.')

    # Missing cloud production safety checks must prevent building a release image.
    docker = (root / 'cloud_api' / 'Dockerfile').read_text(encoding='utf-8')
    if 'cloud_api/production.py' not in docker:
        errors.append('Docker image must include the production configuration guard.')
    dockerignore = (root / '.dockerignore').read_text(encoding='utf-8')
    for item in ('cloud_api/data/', 'backend/data/', '.env'):
        if item not in dockerignore:
            errors.append(f'Missing {item} from .dockerignore')

    # The public author field is optional. This source release omits it.

    return errors, warnings


def main():
    """Return a nonzero exit code if the preflight finds a blocking error."""
    errors, warnings = inspect()
    print('TrueDuck Sentinel v0.9.8 — static security preflight')
    for warning in warnings:
        print('REVIEW:', warning)
    for error in errors:
        print('FAIL:', error)
    if errors:
        print(f'FAILED: {len(errors)} blocking finding(s).')
        raise SystemExit(1)
    print('PASS: no blocking findings in these LIMITED static checks.')
    print('NOT CERTIFIED: hands-on Edge testing, dependency audit and external review still required.')


if __name__ == '__main__':
    main()
