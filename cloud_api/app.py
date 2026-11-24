"""TrueDuck Sentinel cloud API foundation (v0.9).

Endpoints:
  GET  /health                 - Basic server health check.
  GET  /v1/feed                - Public read-only, approved threat indicators.
  PUT  /v1/admin/feed          - Replace published list (owner token required).

This API never reads your private backend/data/scamlens.db file. It has a
separate database and publisher credential. Community report writes are
available only to authenticated accounts and moderated by an owner.
It is NOT a complete production service: you still need HTTPS, hosting, abuse
monitoring, tested backups, and a security review before public release.
"""

# --- Python standard-library modules ---
import hashlib                         # Make an ETag to identify unchanged feeds.
import ipaddress                       # Reject private and loopback network targets.
import json                            # Decode and encode JSON request bodies.
import os                              # Read credentials and the database URL from the environment.
import re                              # Validate domain-label syntax.
import secrets                         # Compare access tokens safely.
from datetime import datetime, timezone  # Timestamp each new publication in UTC.
from pathlib import Path               # Locate our local development database.
from urllib.parse import urlsplit      # Break URLs into safe components.

# --- Third-party packages; install with cloud_api/requirements.txt ---
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

# Fail early rather than starting a public API with local-only credentials or SQLite.
from .production import assert_production_config  # Validate hosted settings before DB setup.
assert_production_config()

# Keep cloud data in a different folder from the owner's private SQLite database.
CLOUD_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE = CLOUD_DIR / 'data' / 'cloud-dev.db'
DEFAULT_SQLITE.parent.mkdir(parents=True, exist_ok=True)

# A hosted instance can instead use: postgresql+psycopg://user:pass@host/db
DATABASE_URL = os.environ.get('SCAMLENS_CLOUD_DATABASE_URL', f'sqlite:///{DEFAULT_SQLITE.as_posix()}')

# SQLite needs this argument when FastAPI calls a database from several threads.
engine_args = {'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite:') else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **engine_args)
metadata = MetaData()

# Only safe-to-share indicators are stored in the separate cloud database.
indicators_table = Table(
    'published_indicators', metadata,
    Column('kind', String(10), primary_key=True),
    Column('value', String(2100), primary_key=True),
    Column('classification', String(40), nullable=False),
)

# Community reports live in a separate table from the owner's uploaded feed.
# Only owner-reviewed, explicitly published community domains and URLs reach readers.
community_public_table = Table(
    'community_published', metadata,
    Column('report_id', Integer, primary_key=True),
    Column('kind', String(10), nullable=False),
    Column('value', String(2100), nullable=False),
    Column('classification', String(40), nullable=False),
)

# One row stores the publication timestamp and revision number.
meta_table = Table(
    'publication_state', metadata,
    Column('id', Integer, primary_key=True),
    Column('generated_at', String(32), nullable=False),
    Column('revision', Integer, nullable=False),
)

# Create tables if missing; production schema upgrades should use migrations.
metadata.create_all(engine)

# The extension can read GET /v1/feed without a secret.
# No CORS middleware is enabled, so ordinary websites do not receive API access.
app = FastAPI(title='TrueDuck Sentinel API', version='0.9.0', docs_url=None, redoc_url=None, openapi_url=None)

# A hosted API should only answer requests for its configured domain.
# In local mode, omit this middleware so the Windows demo remains unchanged.
if os.environ.get('SCAMLENS_ENV') == 'production':
    allowed_hosts = [x.strip() for x in os.environ['SCAMLENS_ALLOWED_HOSTS'].split(',') if x.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


@app.middleware('http')
async def security_response_headers(request: Request, call_next):
    """Send baseline browser security headers with every API response."""
    response = await call_next(request)
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'no-referrer')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    # Mark account and admin responses non-cacheable. The public feed is the
    # exception: its ETag and short caching lifetime are intentional.
    if request.url.path.startswith(('/v1/auth/', '/v1/reports', '/v1/admin/', '/dashboard')):
        response.headers['Cache-Control'] = 'no-store'
    if os.environ.get('SCAMLENS_ENV') == 'production':
        # This is meaningful only when the user connects over HTTPS at the proxy.
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response

MAX_INDICATORS = 5000                # Bound the amount of content an admin can publish.
MAX_BODY_BYTES = 700_000            # Reject an oversized upload before JSON decoding.
MAX_URL_LENGTH = 2100               # Limit URL lengths stored in the database.
DOMAIN_LABEL = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')


def now_utc() -> str:
    """Return a portable UTC timestamp for the public feed."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def public_hostname(value: str) -> str:
    """Return a validated public DNS hostname, or raise ValueError.

    Checking a hostname does not establish that it is fraudulent or reachable.
    """
    if not isinstance(value, str) or len(value) > 253 or not value:
        raise ValueError('Invalid hostname length')
    try:
        host = value.lower().rstrip('.').encode('idna').decode('ascii')
    except UnicodeError as exc:
        raise ValueError('Invalid hostname encoding') from exc
    if (host in ('localhost',) or host.endswith(('.localhost', '.local', '.internal'))
            or not host or '.' not in host):
        raise ValueError('Local or single-label hostname is not publishable')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # A DNS name must contain valid labels, including a nonnumeric TLD.
        labels = host.split('.')
        if not all(DOMAIN_LABEL.fullmatch(label) for label in labels):
            raise ValueError('Invalid domain label')
        if labels[-1].isdigit():
            raise ValueError('Invalid top-level domain')
        return host
    if not address.is_global:
        raise ValueError('Private, reserved, or local IP addresses cannot be published')
    return host


def safe_indicator(raw: dict) -> dict:
    """Validate an opted-in indicator again at the cloud trust boundary.

    We trust neither a browser request nor a malformed export. The cloud API
    only understands exact domains and URLs marked as reviewed reports.
    """
    if not isinstance(raw, dict) or raw.get('classification') != 'reviewed_report':
        raise ValueError('Only owner-reviewed report indicators are accepted')
    kind, value = raw.get('kind'), raw.get('value')
    if kind not in ('domain', 'url') or not isinstance(value, str):
        raise ValueError('Only domain and URL indicators may be published')
    if kind == 'domain':
        if value != value.lower().rstrip('.'):
            raise ValueError('Domain must be canonical lowercase without a trailing dot')
        if public_hostname(value) != value:
            raise ValueError('Domain must be canonical')
        return {'kind': 'domain', 'value': value, 'classification': 'reviewed_report'}

    # URL entries may not carry passwords, personal session IDs, or query data.
    if len(value) > MAX_URL_LENGTH or value.strip() != value:
        raise ValueError('Invalid URL length')
    try:
        url = urlsplit(value)
        hostname = url.hostname or ''
        if (url.scheme not in ('http', 'https') or url.username or url.password
                or url.query or url.fragment or not hostname):
            raise ValueError('URLs with credentials, queries, or fragments are not publishable')
        public_hostname(hostname)
        # Normalized URLs from the local exporter do not contain unusual ports.
        if url.port not in (None, 80, 443):
            raise ValueError('Nonstandard ports cannot be published')
        if value != f'{url.scheme}://{url.netloc}{url.path or "/"}':
            raise ValueError('URL must be canonical')
    except ValueError as exc:
        raise ValueError(f'Invalid publishable URL: {exc}') from exc
    return {'kind': 'url', 'value': value, 'classification': 'reviewed_report'}


def check_owner_token(request: Request) -> None:
    """Protect the publish endpoint using a separate owner-only secret.

    Never put this secret in Edge's source code, public JSON, or a Git repo.
    A strong token is only a starting protection; production needs auditing.
    """
    expected = os.environ.get('SCAMLENS_PUBLISH_TOKEN', '')
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail='Publishing is not configured')
    supplied = request.headers.get('authorization', '')
    if not supplied.startswith('Bearer ') or not secrets.compare_digest(supplied[7:], expected):
        raise HTTPException(status_code=401, detail='Invalid publisher credential')


def current_feed() -> dict:
    """Build a public snapshot only from the cloud database's safe columns."""
    with engine.connect() as connection:
        items = connection.execute(select(indicators_table).order_by(
            indicators_table.c.kind, indicators_table.c.value)).mappings().all()
        meta = connection.execute(select(meta_table).where(meta_table.c.id == 1)).mappings().first()
        community = connection.execute(select(
            community_public_table.c.kind, community_public_table.c.value,
            community_public_table.c.classification
        )).mappings().all()
    # Merge the two approved feeds. A matching entry appears only once.
    # Owner-uploaded entries have precedence if both sets contain the same value.
    merged = {(item['kind'], item['value']): dict(item) for item in items}
    for item in community:
        merged.setdefault((item['kind'], item['value']), dict(item))
    published = sorted(merged.values(), key=lambda item: (item['kind'], item['value']))
    # Public results contain no private evidence, reporter information, or token.
    return {
        'schema': 'scamlens.public-feed.v1',
        'generated_at': meta['generated_at'] if meta else None,
        'revision': meta['revision'] if meta else 0,
        'description': 'Owner-approved, opt-in indicators. A match is not proof of fraud.',
        'count': len(published),
        'indicators': published,
    }


@app.get('/health')
def health():
    """Return a minimal status without leaking database or environment secrets."""
    return {'status': 'ok', 'service': 'scamlens-public-feed'}


@app.get('/v1/feed')
def feed(request: Request):
    """Serve read-only indicators with an ETag and short cache lifetime."""
    doc = current_feed()
    body = json.dumps(doc, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    etag = '"' + hashlib.sha256(body).hexdigest() + '"'
    headers = {'ETag': etag, 'Cache-Control': 'public, max-age=300', 'X-Content-Type-Options': 'nosniff'}
    if request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type='application/json', headers=headers)


@app.put('/v1/admin/feed')
async def replace_feed(request: Request):
    """Replace the *entire* published set after checking owner authentication.

    Replacing rather than merging means an owner's retractions disappear from
    the next public feed, instead of remaining on users' blocklists forever.
    """
    check_owner_token(request)
    # Read the incoming body incrementally to enforce an actual byte limit.
    chunks, seen = [], 0
    async for chunk in request.stream():
        seen += len(chunk)
        if seen > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail='Publication exceeds the size limit')
        chunks.append(chunk)
    try:
        payload = json.loads(b''.join(chunks))
        if not isinstance(payload, dict) or payload.get('schema') != 'scamlens.public-feed.v1':
            raise ValueError('Unexpected feed format')
        submitted = payload.get('indicators')
        if not isinstance(submitted, list) or len(submitted) > MAX_INDICATORS:
            raise ValueError('Indicators must be a list within the item limit')
        # Reject duplicated records rather than silently skewing the count.
        normalized = [safe_indicator(record) for record in submitted]
        keys = {(record['kind'], record['value']) for record in normalized}
        if len(keys) != len(normalized):
            raise ValueError('Duplicate indicator')
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f'Invalid feed: {exc}') from exc
    # Replacing all rows in a transaction prevents users from seeing half an update.
    timestamp = now_utc()
    try:
        with engine.begin() as connection:
            state = connection.execute(select(meta_table).where(meta_table.c.id == 1)).mappings().first()
            connection.execute(delete(indicators_table))
            if normalized:
                connection.execute(insert(indicators_table), normalized)
            if state:
                connection.execute(update(meta_table).where(meta_table.c.id == 1).values(
                    generated_at=timestamp, revision=state['revision'] + 1))
                revision = state['revision'] + 1
            else:
                connection.execute(insert(meta_table).values(id=1, generated_at=timestamp, revision=1))
                revision = 1
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail='Database temporarily unavailable') from exc
    # Explicitly avoid returning a token or the submitted data in the response.
    return JSONResponse({'published': len(normalized), 'revision': revision, 'generated_at': timestamp},
                        headers={'Cache-Control': 'no-store'})


# The community router adds account, report, moderation, and dashboard endpoints.
# Import after the base tables/routes are defined to avoid circular imports.
from .community import router as community_router  # noqa: E402
app.include_router(community_router)
