"""Anonymous community reporting and owner-only administration.

This module is a *local development foundation*, not an audited public service.
Passwords are salted PBKDF2 hashes, sessions are random bearer credentials whose
SHA-256 hashes are stored in the database, and all moderation is owner-only.
The public threat feed receives only explicitly published, reviewed domain/URL
pairs. Reporting personal information does not automatically publish it.
"""

# Standard-library building blocks: hashing, randomness, validation and time.
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

# FastAPI handles HTTP, and SQLAlchemy handles parameterized database queries.
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

# Import the EXISTING cloud database and safe public-feed validation helpers.
# The main app imports this router only after these values have been created.
from .app import (community_public_table, engine, metadata, meta_table,
                  now_utc, public_hostname, safe_indicator)

router = APIRouter()
UI_DIR = Path(__file__).resolve().parent / 'dashboard'
PASSWORD_ITERATIONS = 600_000  # Deliberately slow password derivation.
SESSION_LIFETIME = 8 * 3600   # An account session expires after eight hours.
USERNAME_PATTERN = re.compile(r'^[a-z][a-z0-9_.-]{2,31}$')
VALID_KINDS = {'domain', 'url', 'email', 'phone', 'address'}
VALID_DECISIONS = {'pending', 'approved', 'rejected'}
# A non-loginable internal actor preserves old database foreign keys.
ANONYMOUS_ACTOR = '__anonymous__'
_submission_lock = threading.Lock()

# The account table doesn't need emails: a username is sufficient for testing.
accounts = Table(
    'community_accounts', metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String(32), unique=True, nullable=False),
    Column('password_salt', String(64), nullable=False),
    Column('password_hash', String(128), nullable=False),
    Column('role', String(12), nullable=False),
    Column('created_at', String(32), nullable=False),
)

# Store only hashes of high-entropy tokens; not the bearer tokens themselves.
sessions = Table(
    'community_sessions', metadata,
    Column('token_hash', String(64), primary_key=True),
    Column('account_id', Integer, ForeignKey('community_accounts.id'), nullable=False),
    Column('expires_at', Integer, nullable=False),
    Column('created_at', String(32), nullable=False),
)

# Community submissions and their evidence remain OUT of the public feed.
reports = Table(
    'community_reports', metadata,
    Column('id', Integer, primary_key=True),
    Column('reporter_id', Integer, ForeignKey('community_accounts.id'), nullable=False),
    Column('kind', String(10), nullable=False),
    Column('value', String(520), nullable=False),
    Column('details', Text, nullable=False),
    Column('evidence_ref', String(300), nullable=False),
    Column('status', String(12), nullable=False),
    Column('review_note', Text, nullable=False),
    Column('review_reference', String(300), nullable=False),
    Column('created_at', String(32), nullable=False),
    Column('updated_at', String(32), nullable=False),
)

# Review events are append-only in the application. They record every decision.
review_audit = Table(
    'community_review_audit', metadata,
    Column('id', Integer, primary_key=True),
    Column('report_id', Integer, ForeignKey('community_reports.id'), nullable=False),
    Column('moderator_id', Integer, ForeignKey('community_accounts.id'), nullable=False),
    Column('event', String(20), nullable=False),
    Column('note', Text, nullable=False),
    Column('reference', String(300), nullable=False),
    Column('created_at', String(32), nullable=False),
)

# Only the owner can explicitly opt in individual reviewed email/phone entries.
# Keep these IDs separate from the domain/URL public feed so contact values
# never appear in a downloadable list or an unauthenticated browse endpoint.
public_contact_lookup = Table(
    'community_public_contact_lookup', metadata,
    Column('report_id', Integer, ForeignKey('community_reports.id'), primary_key=True),
    Column('created_at', String(32), nullable=False),
)

# Add the v0.9.3 lookup table without rewriting any existing report data.
metadata.create_all(engine)

# An in-process throttle blocks repeated requests during local development.
# IMPORTANT: this is NOT sufficient behind multiple production workers.
# A hosted deployment must use shared rate limits at the reverse proxy/Redis.
_rate_lock = threading.Lock()
_events = defaultdict(deque)


def throttle(bucket: str, value: str, limit: int, period_seconds: int) -> None:
    """Sliding-window request limiter for local demos."""
    now = time.monotonic()
    key = (bucket, value)
    with _rate_lock:
        events = _events[key]
        while events and now - events[0] >= period_seconds:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(status_code=429, detail='Too many requests. Try later.')
        events.append(now)
        # Prevent unlimited memory growth from old IP/account keys.
        if len(_events) > 10000:
            for old in list(_events)[:2000]:
                if not _events[old] or now - _events[old][-1] > 3600:
                    _events.pop(old, None)


def client_ip(request: Request) -> str:
    """Use the socket IP; untrusted X-Forwarded-For headers are NOT accepted."""
    return request.client.host if request.client else 'unknown'


async def json_input(request: Request, max_size: int = 5000) -> dict:
    """Read JSON in bounded chunks so huge bodies cannot exhaust memory."""
    chunks, total = [], 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_size:
            raise HTTPException(status_code=413, detail='Request too large')
        chunks.append(chunk)
    try:
        payload = json.loads(b''.join(chunks))
    except (ValueError, UnicodeError):
        raise HTTPException(status_code=400, detail='Expected a JSON object')
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='Expected a JSON object')
    return payload


def field(payload: dict, name: str, max_length: int, required: bool = False) -> str:
    """Validate text lengths and types before writing them to a database."""
    raw = payload.get(name, '')
    if not isinstance(raw, str) or len(raw) > max_length:
        raise HTTPException(status_code=422, detail=f'Invalid {name}')
    value = raw.strip()
    if required and not value:
        raise HTTPException(status_code=422, detail=f'{name} is required')
    return value


def hash_password(password: str, salt_hex: str) -> str:
    """Calculate a password verifier using a unique random salt per account."""
    result = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                 bytes.fromhex(salt_hex), PASSWORD_ITERATIONS)
    return result.hex()


def verify_password(password: str, account: dict | None) -> bool:
    """Do equivalent expensive work for missing accounts to reduce timing leaks."""
    salt = account['password_salt'] if account else '00' * 16
    target = account['password_hash'] if account else '00' * 32
    return hmac.compare_digest(hash_password(password, salt), target) and account is not None


def check_password(password: str) -> None:
    """Accept passphrases of 12-128 characters without forced symbol rules."""
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise HTTPException(status_code=422, detail='Password must be 12-128 characters')
    if password.lower() in {'password1234', 'password123456', 'letmein123456'}:
        raise HTTPException(status_code=422, detail='Choose a less common password')


def normalize_username(username: str) -> str:
    """Usernames must be simple, unique, and safe to display as text."""
    if not isinstance(username, str):
        raise HTTPException(status_code=422, detail='Invalid username')
    name = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(name):
        raise HTTPException(status_code=422, detail='Use 3-32 letters, numbers, dots, dashes or underscores; start with a letter')
    return name


def create_account(username: str, password: str, role: str = 'owner') -> int:
    """Create an administrator through the local CLI only."""
    name = normalize_username(username)
    check_password(password)
    if role != 'owner':
        raise ValueError('Unsupported role')
    salt = secrets.token_bytes(16).hex()
    with engine.begin() as connection:
        result = connection.execute(insert(accounts).values(
            username=name, password_salt=salt,
            password_hash=hash_password(password, salt), role=role,
            created_at=now_utc()))
        return result.inserted_primary_key[0]


def get_user(request: Request, owner_only: bool = False) -> dict:
    """Authenticate a hashed bearer token and optionally require owner role."""
    header = request.headers.get('authorization', '')
    if not header.startswith('Bearer ') or len(header) > 200:
        raise HTTPException(status_code=401, detail='Login required')
    token = header[7:]
    digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
    with engine.connect() as connection:
        row = connection.execute(select(
            accounts.c.id, accounts.c.username, accounts.c.role, sessions.c.expires_at
        ).select_from(sessions.join(accounts, sessions.c.account_id == accounts.c.id))
            .where(sessions.c.token_hash == digest)).mappings().first()
    if not row or row['expires_at'] <= int(time.time()) or row['role'] != 'owner':
        raise HTTPException(status_code=401, detail='Login expired or invalid')
    if owner_only and row['role'] != 'owner':
        raise HTTPException(status_code=403, detail='Owner access required')
    return dict(row)


def normalize_indicator(kind: str, value: str) -> str:
    """Normalize indicator values and refuse unbounded or private URL components."""
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=422, detail='Unsupported indicator type')
    if not isinstance(value, str) or len(value) > 500:
        raise HTTPException(status_code=422, detail='Indicator value is too long')
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail='Indicator cannot be blank')
    if kind == 'domain':
        try:
            if '://' in value or '/' in value or '@' in value or ':' in value:
                raise ValueError('Only a hostname belongs in a domain report')
            return public_hostname(value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if kind == 'url':
        # Reuse the strict, public-safe URL validator. Query strings can contain
        # credentials, tracking tokens, and personal data, so we reject them.
        try:
            candidate = value
            url = urlsplit(candidate)
            host = public_hostname(url.hostname or '')
            if url.scheme not in ('http', 'https') or url.query or url.fragment or url.username or url.password:
                raise ValueError('Use an HTTP(S) URL without query, fragment, or credentials')
            if url.port not in (None, 80, 443):
                raise ValueError('Nonstandard ports are unsupported')
            canonical = f'{url.scheme}://{host}{(":" + str(url.port)) if url.port else ""}{url.path or "/"}'
            safe_indicator({'kind': 'url', 'value': canonical, 'classification': 'reviewed_report'})
            return canonical
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f'Invalid URL: {exc}') from exc
    if kind == 'email':
        if not re.fullmatch(r'[^\s@]{1,100}@[^\s@]{1,180}\.[^\s@]{2,30}', value):
            raise HTTPException(status_code=422, detail='Invalid email address')
        return value.lower()
    if kind == 'phone':
        digits = re.sub(r'\D', '', value)
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        if len(digits) != 10:
            raise HTTPException(status_code=422, detail='Enter a 10-digit US/Canada phone number')
        return digits
    # Physical addresses are private report fields and can NEVER be published.
    if len(value) < 8:
        raise HTTPException(status_code=422, detail='Provide a more complete address')
    return ' '.join(value.split())


def report_view(record: dict) -> dict:
    """Select explicit public-to-owner fields; never reveal reporter passwords."""
    return {key: record[key] for key in (
        'id', 'kind', 'value', 'details', 'evidence_ref', 'status',
        'review_note', 'review_reference', 'created_at', 'updated_at',
    ) if key in record}


def advance_revision(connection) -> None:
    """Invalidate the public feed cache after a community publish/retract."""
    state = connection.execute(select(meta_table).where(meta_table.c.id == 1)).mappings().first()
    if state:
        connection.execute(update(meta_table).where(meta_table.c.id == 1).values(
            revision=state['revision'] + 1, generated_at=now_utc()))
    else:
        connection.execute(insert(meta_table).values(
            id=1, revision=1, generated_at=now_utc()))


def audit_event(connection, report_id: int, actor_id: int, event: str,
                note: str, reference: str = '') -> None:
    """Save an immutable history row for every owner moderation action."""
    connection.execute(insert(review_audit).values(
        report_id=report_id, moderator_id=actor_id, event=event,
        note=note, reference=reference, created_at=now_utc()))


@router.get('/report')
@router.get('/dashboard')
def dashboard():
    """Serve our own dashboard UI, without third-party scripts or trackers."""
    return FileResponse(UI_DIR / 'index.html', headers={
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    })


@router.get('/dashboard/{asset}')
def dashboard_asset(asset: str):
    """Allow only our two fixed UI assets; never accept arbitrary disk paths."""
    if asset not in ('app.js', 'styles.css'):
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(UI_DIR / asset, headers={
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store',
    })


@router.post('/v1/auth/register')
def register():
    """Public account registration is permanently disabled; use the local owner CLI."""
    raise HTTPException(status_code=403, detail='Only local administrator setup is supported')


@router.post('/v1/auth/login')
async def login(request: Request):
    """Return a random, short-lived bearer token after password verification."""
    data = await json_input(request)
    name = normalize_username(data.get('username'))
    password = data.get('password')
    if not isinstance(password, str) or len(password) > 128:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    # Independent limits: IP and username, not just the IP/username pair.
    throttle('login-ip', client_ip(request), 20, 900)
    throttle('login-username', name, 12, 900)
    with engine.connect() as connection:
        account = connection.execute(select(accounts).where(accounts.c.username == name)).mappings().first()
    if not verify_password(password, account) or account['role'] != 'owner':
        raise HTTPException(status_code=401, detail='Invalid credentials')
    token = secrets.token_urlsafe(48)
    expires = int(time.time()) + SESSION_LIFETIME
    with engine.begin() as connection:
        # Remove expired entries during login to avoid growing the sessions table.
        connection.execute(delete(sessions).where(sessions.c.expires_at <= int(time.time())))
        connection.execute(insert(sessions).values(
            token_hash=hashlib.sha256(token.encode('utf-8')).hexdigest(),
            account_id=account['id'], expires_at=expires, created_at=now_utc()))
    return {'token': token, 'expires_at': expires,
            'user': {'id': account['id'], 'username': account['username'], 'role': account['role']}}


@router.get('/v1/auth/me')
def me(request: Request):
    """Read current role without exposing the password hash or login token."""
    user = get_user(request)
    return {'id': user['id'], 'username': user['username'], 'role': user['role']}


@router.post('/v1/auth/logout')
def logout(request: Request):
    """Invalidate a token server-side immediately."""
    get_user(request)
    digest = hashlib.sha256(request.headers['authorization'][7:].encode('utf-8')).hexdigest()
    with engine.begin() as connection:
        connection.execute(delete(sessions).where(sessions.c.token_hash == digest))
    return {'status': 'logged_out'}


def anonymous_actor(connection) -> int:
    """Reuse a disabled internal database actor, not an actual user account.

    This keeps the existing non-null reporter foreign key compatible with v0.9.5.
    No visitor username, password, IP address or session is written to the report.
    """
    row = connection.execute(select(accounts.c.id, accounts.c.role).where(
        accounts.c.username == ANONYMOUS_ACTOR)).first()
    if row:
        if row.role != 'anonymous':
            raise HTTPException(status_code=503, detail='Anonymous intake unavailable')
        return row.id
    result = connection.execute(insert(accounts).values(
        username=ANONYMOUS_ACTOR, password_salt='', password_hash='',
        role='anonymous', created_at=now_utc()))
    return result.inserted_primary_key[0]


@router.post('/v1/reports', status_code=201)
async def submit_report(request: Request):
    """Accept account-free submissions into a private, unverified review queue."""
    # IPs are used only in memory for local throttling; no IP is stored on reports.
    # The global cap also limits simple distributed abuse in a single process.
    throttle('anonymous-ip', client_ip(request), 10, 86400)
    throttle('anonymous-global', 'all', 200, 3600)
    # Require JSON rather than cross-site browser form submissions.
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise HTTPException(status_code=415, detail='Expected application/json')
    data = await json_input(request)
    kind = field(data, 'kind', 10, True)
    value = normalize_indicator(kind, data.get('value'))
    details = field(data, 'details', 600, True)
    evidence_ref = field(data, 'evidence_ref', 300)
    # Serialize duplicate checks locally. Multi-worker hosting needs DB constraints
    # and a shared limiter; the development server is intentionally single-process.
    with _submission_lock, engine.begin() as connection:
        actor = anonymous_actor(connection)
        duplicate = connection.execute(select(reports.c.id).where(and_(
            reports.c.reporter_id == actor, reports.c.kind == kind,
            reports.c.value == value, reports.c.status == 'pending'))).first()
        if not duplicate:
            connection.execute(insert(reports).values(
                reporter_id=actor, kind=kind, value=value, details=details,
                evidence_ref=evidence_ref, status='pending', review_note='',
                review_reference='', created_at=now_utc(), updated_at=now_utc()))
    # Identical responses for duplicates avoid exposing private queue membership.
    return {'status': 'received'}


@router.get('/v1/admin/reports')
def moderation_queue(request: Request):
    """The owner sees the moderation queue, never ordinary reporters."""
    get_user(request, owner_only=True)
    with engine.connect() as connection:
        rows = connection.execute(select(reports).order_by(
            reports.c.id.desc()).limit(200)).mappings().all()
        published_ids = {row[0] for row in connection.execute(select(community_public_table.c.report_id)).all()}
        lookup_ids = {row[0] for row in connection.execute(select(public_contact_lookup.c.report_id)).all()}
    return {'records': [{**report_view(row), 'reporter_id': row['reporter_id'],
                         'published': row['id'] in published_ids,
                         'lookup_visible': row['id'] in lookup_ids} for row in rows]}


@router.post('/v1/admin/reports/{report_id}/decision')
async def review_report(report_id: int, request: Request):
    """Owner decision is audited; every re-review automatically retracts publishing."""
    user = get_user(request, owner_only=True)
    data = await json_input(request)
    decision = field(data, 'decision', 12, True)
    reason = field(data, 'note', 600, True)
    reference = field(data, 'reference', 300)
    if decision not in VALID_DECISIONS:
        raise HTTPException(status_code=422, detail='Choose pending, approved, or rejected')
    if decision == 'approved' and len(reference) < 4:
        raise HTTPException(status_code=422, detail='Approval requires an evidence reference')
    with engine.begin() as connection:
        row = connection.execute(select(reports).where(reports.c.id == report_id)).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail='Report not found')
        removed = connection.execute(delete(community_public_table).where(
            community_public_table.c.report_id == report_id)).rowcount
        # Re-review also revokes searchable email/phone contact records.
        removed_contact = connection.execute(delete(public_contact_lookup).where(
            public_contact_lookup.c.report_id == report_id)).rowcount
        if removed or removed_contact:
            advance_revision(connection)
        connection.execute(update(reports).where(reports.c.id == report_id).values(
            status=decision, review_note=reason, review_reference=reference,
            updated_at=now_utc()))
        audit_event(connection, report_id, user['id'], decision, reason, reference)
    return {'id': report_id, 'status': decision, 'published': False}


@router.post('/v1/admin/reports/{report_id}/publish')
def publish_community(report_id: int, request: Request):
    """Owner deliberately publishes only a previously approved safe domain/URL."""
    user = get_user(request, owner_only=True)
    with engine.begin() as connection:
        row = connection.execute(select(reports).where(reports.c.id == report_id)).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail='Report not found')
        if row['status'] != 'approved' or not row['review_reference']:
            raise HTTPException(status_code=409, detail='Approve with evidence before publishing')
        try:
            record = safe_indicator({'kind': row['kind'], 'value': row['value'],
                                     'classification': 'reviewed_report'})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f'Cannot publish: {exc}') from exc
        other = connection.execute(select(community_public_table.c.report_id).where(and_(
            community_public_table.c.kind == record['kind'],
            community_public_table.c.value == record['value'],
            community_public_table.c.report_id != report_id))).first()
        if other:
            raise HTTPException(status_code=409, detail='Another community report already publishes this indicator')
        exists = connection.execute(select(community_public_table.c.report_id).where(
            community_public_table.c.report_id == report_id)).first()
        if not exists:
            connection.execute(insert(community_public_table).values(report_id=report_id, **record))
            advance_revision(connection)
            audit_event(connection, report_id, user['id'], 'published', 'Explicit owner publication')
    return {'id': report_id, 'published': True}


@router.post('/v1/admin/reports/{report_id}/retract')
def retract_community(report_id: int, request: Request):
    """Remove an existing public entry and increment the feed revision."""
    user = get_user(request, owner_only=True)
    with engine.begin() as connection:
        if not connection.execute(select(reports.c.id).where(reports.c.id == report_id)).first():
            raise HTTPException(status_code=404, detail='Report not found')
        removed = connection.execute(delete(community_public_table).where(
            community_public_table.c.report_id == report_id)).rowcount
        # Re-review also revokes searchable email/phone contact records.
        removed_contact = connection.execute(delete(public_contact_lookup).where(
            public_contact_lookup.c.report_id == report_id)).rowcount
        if removed or removed_contact:
            advance_revision(connection)
            audit_event(connection, report_id, user['id'], 'retracted', 'Owner retracted public entry')
    return {'id': report_id, 'published': False}


@router.post('/v1/admin/reports/{report_id}/lookup-access')
async def owner_contact_lookup_access(report_id: int, request: Request):
    """Owner opts a reviewed email/phone into or out of contact lookups.

    This separate action is NEVER implicit when a reporter submits or when an
    administrator approves a report. The ordinary feed still excludes contact
    indicators. Public lookup responses disclose only a yes/no match.
    """
    owner = get_user(request, owner_only=True)
    payload = await json_input(request, max_size=200)
    enabled = payload.get('enabled')
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=422, detail='enabled must be true or false')
    with engine.begin() as connection:
        record = connection.execute(select(reports).where(reports.c.id == report_id)).mappings().first()
        if record is None:
            raise HTTPException(status_code=404, detail='Report not found')
        if enabled and (record['kind'] not in ('email', 'phone') or
                        record['status'] != 'approved' or not record['review_reference']):
            raise HTTPException(status_code=409, detail='Only reviewed emails/phones with evidence can be made searchable')
        connection.execute(delete(public_contact_lookup).where(
            public_contact_lookup.c.report_id == report_id))
        if enabled:
            connection.execute(insert(public_contact_lookup).values(
                report_id=report_id, created_at=now_utc()))
        audit_event(connection, report_id, owner['id'],
                    'lookup_on' if enabled else 'lookup_off',
                    'Explicit owner contact-lookup choice; not included in the public feed')
    return {'id': report_id, 'lookup_visible': enabled}


@router.post('/v1/lookup')
async def public_contact_lookup_endpoint(request: Request):
    """No-account, exact-match contact lookup; no public directory or search.

    The person chooses to submit a single email/phone. This is never used for
    background webpage scanning. Reject invalid and oversized requests before
    querying. Rate limiting protects the local demo from casual enumeration;
    production needs a shared limiter plus anti-enumeration review.
    """
    throttle('contact-lookup-minute', client_ip(request), 12, 60)
    throttle('contact-lookup-hour', client_ip(request), 75, 3600)
    data = await json_input(request, max_size=550)
    kind = field(data, 'kind', 8, True)
    if kind not in ('email','phone'):
        raise HTTPException(status_code=422, detail='Only email and phone lookups are supported')
    value = normalize_indicator(kind, data.get('value'))
    # Parameterized exact-match query; only explicitly opted-in APPROVED rows.
    with engine.connect() as connection:
        found = connection.execute(select(reports.c.id).join(
            public_contact_lookup, public_contact_lookup.c.report_id == reports.c.id
        ).where(and_(reports.c.kind == kind, reports.c.value == value,
                     reports.c.status == 'approved')).limit(1)).first() is not None
    # Do not echo email, phone, evidence, reporter, or database IDs.
    return Response(
        content=json.dumps({'match': found, 'classification': 'reviewed_report' if found else 'none',
                            'scope': 'owner_opt_in_only',
                            'note': 'A match is a reviewed report, not proof of fraud. No match does not mean safe.'}),
        media_type='application/json',
        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                 'Referrer-Policy': 'no-referrer'})


@router.get('/v1/admin/audit')
def audit_log(request: Request):
    """Read the latest owner decisions without editing historical records."""
    get_user(request, owner_only=True)
    with engine.connect() as connection:
        rows = connection.execute(select(review_audit).order_by(
            review_audit.c.id.desc()).limit(100)).mappings().all()
    return {'events': [dict(row) for row in rows]}


@router.get('/v1/admin/metrics')
def owner_metrics(request: Request):
    """Return counts and per-day trends for a real threat-management dashboard."""
    get_user(request, owner_only=True)
    with engine.connect() as connection:
        totals = {row[0]: row[1] for row in connection.execute(
            select(reports.c.status, func.count()).group_by(reports.c.status)).all()}
        by_kind = {row[0]: row[1] for row in connection.execute(
            select(reports.c.kind, func.count()).group_by(reports.c.kind)).all()}
        activity = connection.execute(select(func.substr(reports.c.created_at, 1, 10),
            func.count()).group_by(func.substr(reports.c.created_at, 1, 10)).order_by(
            func.substr(reports.c.created_at, 1, 10).desc()).limit(14)).all()
        reporter_count = connection.execute(select(func.count()).select_from(accounts).where(
            accounts.c.role == 'reporter')).scalar_one()
        published_count = connection.execute(select(func.count()).select_from(community_public_table)).scalar_one()
    return {'total': sum(totals.values()), 'pending': totals.get('pending', 0),
            'approved': totals.get('approved', 0), 'rejected': totals.get('rejected', 0),
            'published': published_count, 'reporters': reporter_count, 'by_kind': by_kind,
            'daily': [{'date': date, 'count': count} for date, count in reversed(activity)]}
