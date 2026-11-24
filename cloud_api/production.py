"""Security configuration checks for a possible future hosted TrueDuck Sentinel instance.

This module does not deploy anything. Its job is to fail closed when someone
tries to launch the cloud API in production with a development-only setup.
"""

import os  # Read runtime configuration without storing passwords in source code.
from urllib.parse import urlsplit  # Parse the public HTTPS hostname safely.


def validate_production_config(settings: dict | None = None) -> list[str]:
    """Return configuration errors; an empty list means only these checks passed.

    These checks do not replace a security review, penetration test, or abuse
    controls. They only catch several dangerous deployment mistakes early.
    """
    config = settings if settings is not None else os.environ
    if config.get('SCAMLENS_ENV', 'development').lower() != 'production':
        return []  # Do not break the working local Windows demonstration.

    problems = []
    db_url = config.get('SCAMLENS_CLOUD_DATABASE_URL', '')
    if not db_url.startswith(('postgresql+psycopg://', 'postgresql://')):
        problems.append('Production needs a PostgreSQL SCAMLENS_CLOUD_DATABASE_URL')

    origin = config.get('SCAMLENS_PUBLIC_ORIGIN', '')
    try:
        url = urlsplit(origin)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.port not in (None, 443) or url.path not in ('', '/')
                or url.query or url.fragment or url.hostname in ('localhost', '127.0.0.1')):
            problems.append('SCAMLENS_PUBLIC_ORIGIN must be a public HTTPS origin without a path')
    except ValueError:
        problems.append('SCAMLENS_PUBLIC_ORIGIN is not a valid HTTPS origin')

    hosts = [host.strip().lower() for host in config.get('SCAMLENS_ALLOWED_HOSTS', '').split(',') if host.strip()]
    if not hosts or '*' in hosts or any('*' in host for host in hosts):
        problems.append('Set explicit SCAMLENS_ALLOWED_HOSTS, without wildcards')
    elif origin:
        try:
            if urlsplit(origin).hostname not in hosts:
                problems.append('Public origin hostname must be in SCAMLENS_ALLOWED_HOSTS')
        except ValueError:
            pass

    # Registration is disabled until stronger, shared abuse protection and
    # email/account recovery are implemented and reviewed.
    if config.get('SCAMLENS_ALLOW_SIGNUP') == '1':
        problems.append('Disable public signup in production until abuse controls are reviewed')
    return problems


def assert_production_config() -> None:
    """Stop deployment instead of accepting an unsafe production configuration."""
    issues = validate_production_config()
    if issues:
        raise RuntimeError('TrueDuck Sentinel production configuration blocked:\n- ' + '\n- '.join(issues))
