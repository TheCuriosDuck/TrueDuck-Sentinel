"""Integration tests for v0.8 registration, privacy, moderation and publishing.

Tests run in FastAPI's in-process TestClient; no real browser/network needed.
"""

import os
import secrets
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from cloud_api import app as core
from cloud_api import community as c


class CommunityApiTests(unittest.TestCase):
    def setUp(self):
        # Use the test database selected by test_cloud_api.py during test discovery.
        self.client = TestClient(core.app)
        c._events.clear()
        os.environ['SCAMLENS_ALLOW_SIGNUP'] = '1'
        # Reset community data so an old test cannot leak into the next one.
        with core.engine.begin() as conn:
            conn.execute(delete(core.community_public_table))
            conn.execute(delete(c.public_contact_lookup))
            conn.execute(delete(c.review_audit))
            conn.execute(delete(c.reports))
            conn.execute(delete(c.sessions))
            conn.execute(delete(c.accounts))
        self.owner_name = 'owner' + secrets.token_hex(3)
        self.owner_pass = 'Strong owner password with 2026!'
        c.create_account(self.owner_name, self.owner_pass, 'owner')
        self.reporter_name = 'reporter' + secrets.token_hex(3)
        self.reporter_pass = 'A longer reporter passphrase 2026'
        reg = self.client.post('/v1/auth/register', json={
            'username': self.reporter_name, 'password': self.reporter_pass})
        self.assertEqual(reg.status_code, 200, reg.text)
        self.reporter_headers = self.login(self.reporter_name, self.reporter_pass)
        self.owner_headers = self.login(self.owner_name, self.owner_pass)

    def login(self, username, password):
        r = self.client.post('/v1/auth/login', json={'username': username, 'password': password})
        self.assertEqual(r.status_code, 200, r.text)
        return {'Authorization': 'Bearer ' + r.json()['token']}

    def submit(self, kind='domain', value='community.example.test'):
        return self.client.post('/v1/reports', headers=self.reporter_headers, json={
            'kind': kind, 'value': value,
            'details': 'Suspicious request for gift card payment and urgent contact.',
            'evidence_ref': 'REF-100'})

    def approve(self, report_id):
        return self.client.post(f'/v1/admin/reports/{report_id}/decision',
                                headers=self.owner_headers, json={
            'decision': 'approved', 'note': 'Compared independent evidence in case file.',
            'reference': 'CASE-777'})

    def test_accounts_and_password_storage(self):
        with core.engine.connect() as conn:
            user = conn.execute(c.accounts.select().where(c.accounts.c.username == self.reporter_name)).mappings().first()
            self.assertNotEqual(user['password_hash'], self.reporter_pass)
            self.assertEqual(len(user['password_salt']), 32)
        self.assertEqual(self.client.post('/v1/auth/login', json={
            'username': self.reporter_name, 'password': 'wrong password'}).status_code, 401)
        self.assertEqual(self.client.get('/v1/auth/me', headers=self.reporter_headers).json()['role'], 'reporter')

    def test_signup_disabled_by_default_for_hosted_mode(self):
        os.environ['SCAMLENS_ALLOW_SIGNUP'] = '0'
        response = self.client.post('/v1/auth/register', json={
            'username': 'anotherreporter', 'password': 'Another valid passphrase 2026'})
        self.assertEqual(response.status_code, 403)

    def test_reporter_cannot_moderate_or_read_other_accounts(self):
        new = self.submit().json()['id']
        self.assertEqual(self.client.get('/v1/admin/reports', headers=self.reporter_headers).status_code, 403)
        self.assertEqual(self.client.get('/v1/admin/metrics', headers=self.reporter_headers).status_code, 403)
        self.assertEqual(self.client.post(f'/v1/admin/reports/{new}/publish',
                                          headers=self.reporter_headers).status_code, 403)
        # Another account sees zero records: there is no global reports route.
        c.create_account('anotherreporter', 'Long unique reporter password!', 'reporter')
        other = self.login('anotherreporter', 'Long unique reporter password!')
        self.assertEqual(self.client.get('/v1/reports', headers=other).json()['records'], [])

    def test_approval_does_not_automatically_publish(self):
        record = self.submit().json()['id']
        self.assertEqual(self.approve(record).status_code, 200)
        self.assertFalse(any(x['value'] == 'community.example.test'
                             for x in self.client.get('/v1/feed').json()['indicators']))
        self.assertEqual(self.client.post(f'/v1/admin/reports/{record}/publish',
                                          headers=self.owner_headers).status_code, 200)
        feed = self.client.get('/v1/feed').json()
        self.assertTrue(any(x['value'] == 'community.example.test' for x in feed['indicators']))
        text = str(feed)
        self.assertNotIn('REF-100', text)
        self.assertNotIn(self.reporter_name, text)
        self.assertNotIn('gift card', text)
        self.assertEqual(self.client.post(f'/v1/admin/reports/{record}/retract',
                                          headers=self.owner_headers).status_code, 200)
        self.assertFalse(any(x['value'] == 'community.example.test'
                             for x in self.client.get('/v1/feed').json()['indicators']))

    def test_owner_v07_publish_does_not_erase_community_publications(self):
        # v0.7's owner feed PUT replaces only the owner set, not community work.
        record = self.submit().json()['id']
        self.approve(record)
        self.client.post(f'/v1/admin/reports/{record}/publish', headers=self.owner_headers)
        # The publisher credential is different from the community account token.
        owner_feed_headers = {'Authorization': 'Bearer ' + os.environ['SCAMLENS_PUBLISH_TOKEN']}
        fresh_snapshot = {'schema': 'scamlens.public-feed.v1', 'indicators': []}
        response = self.client.put('/v1/admin/feed', headers=owner_feed_headers, json=fresh_snapshot)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(x['value'] == 'community.example.test'
                            for x in self.client.get('/v1/feed').json()['indicators']))

    def test_re_review_retracts_and_keeps_audit(self):
        record = self.submit().json()['id']
        self.approve(record)
        self.client.post(f'/v1/admin/reports/{record}/publish', headers=self.owner_headers)
        response = self.client.post(f'/v1/admin/reports/{record}/decision',
                                    headers=self.owner_headers, json={
            'decision': 'rejected', 'note': 'Evidence did not confirm this report.', 'reference': ''})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('community.example.test', str(self.client.get('/v1/feed').json()))
        actions = [x['event'] for x in self.client.get('/v1/admin/audit',
                   headers=self.owner_headers).json()['events']]
        self.assertIn('approved', actions)
        self.assertIn('published', actions)
        self.assertIn('rejected', actions)

    def test_email_and_address_never_public(self):
        for kind, value in [('email', 'report@example.test'), ('address', '1234 Sample Street, Example City')]:
            with self.subTest(kind=kind):
                record = self.submit(kind, value).json()['id']
                self.approve(record)
                self.assertEqual(self.client.post(f'/v1/admin/reports/{record}/publish',
                              headers=self.owner_headers).status_code, 422)
                self.assertNotIn(value.lower(), str(self.client.get('/v1/feed').json()).lower())

    def test_anonymous_lookup_requires_explicit_owner_opt_in(self):
        """No account for lookups; reports remain private until owner acts."""
        email = 'reviewed-test@example.test'
        record_id = self.submit('email', email).json()['id']
        lookup = lambda: self.client.post('/v1/lookup', json={'kind': 'email', 'value': email})
        before = lookup()
        self.assertEqual(before.status_code, 200)
        self.assertFalse(before.json()['match'])
        self.assertIn('no-store', before.headers['cache-control'])
        self.assertNotIn(email, before.text)
        self.approve(record_id)
        # Review approval by itself NEVER makes contact data public/searchable.
        self.assertFalse(lookup().json()['match'])
        self.assertEqual(self.client.post(
            f'/v1/admin/reports/{record_id}/lookup-access', json={'enabled': True}
        ).status_code, 401)
        enabled = self.client.post(
            f'/v1/admin/reports/{record_id}/lookup-access', headers=self.owner_headers,
            json={'enabled': True})
        self.assertEqual(enabled.status_code, 200, enabled.text)
        self.assertTrue(lookup().json()['match'])
        self.assertNotIn(email, str(self.client.get('/v1/feed').json()))
        rows = self.client.get('/v1/admin/reports', headers=self.owner_headers).json()['records']
        self.assertTrue(next(x for x in rows if x['id'] == record_id)['lookup_visible'])
        # A new decision automatically revokes any previous lookup consent.
        decision = self.client.post(f'/v1/admin/reports/{record_id}/decision',
            headers=self.owner_headers, json={
                'decision': 'rejected', 'note': 'The report is not corroborated.', 'reference': ''})
        self.assertEqual(decision.status_code, 200)
        self.assertFalse(lookup().json()['match'])

    def test_phone_lookup_is_exact_and_not_enumerable_by_list(self):
        report_id = self.submit('phone', '(202) 555-0177').json()['id']
        self.approve(report_id)
        self.assertEqual(self.client.post(f'/v1/admin/reports/{report_id}/lookup-access',
            headers=self.owner_headers, json={'enabled': True}).status_code, 200)
        yes = self.client.post('/v1/lookup', json={'kind': 'phone', 'value': '+1 202-555-0177'})
        self.assertTrue(yes.json()['match'])
        self.assertNotIn('2025550177', yes.text)
        self.assertFalse(self.client.post('/v1/lookup', json={
            'kind': 'phone', 'value': '202-555-0188'}).json()['match'])
        self.assertEqual(self.client.post('/v1/lookup', json={
            'kind': 'address', 'value': '123 Example Road'}).status_code, 422)
        self.assertEqual(self.client.post('/v1/lookup', json={
            'kind': 'email', 'value': 'not_an_email'}).status_code, 422)

    def test_anonymous_lookup_is_rate_limited(self):
        responses = [self.client.post('/v1/lookup', json={
            'kind': 'email', 'value': 'nobody@example.test'}) for _ in range(13)]
        self.assertTrue(all(x.status_code == 200 for x in responses[:12]))
        self.assertEqual(responses[12].status_code, 429)

    def test_duplicates_and_invalid_query_string(self):
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.submit().status_code, 409)
        bad = self.submit('url', 'https://community.example.test/path?auth=secret')
        self.assertEqual(bad.status_code, 422)

    def test_report_rate_limit_and_metrics(self):
        for number in range(10):
            self.assertEqual(self.submit(value=f'test{number}.example.test').status_code, 201)
        self.assertEqual(self.submit(value='test11.example.test').status_code, 429)
        stats = self.client.get('/v1/admin/metrics', headers=self.owner_headers).json()
        self.assertEqual(stats['total'], 10)
        self.assertEqual(stats['pending'], 10)
        self.assertEqual(stats['by_kind']['domain'], 10)

    def test_logout_revokes_session(self):
        self.assertEqual(self.client.post('/v1/auth/logout', headers=self.reporter_headers).status_code, 200)
        self.assertEqual(self.client.get('/v1/auth/me', headers=self.reporter_headers).status_code, 401)

    def test_dashboard_assets_and_no_api_token_in_html(self):
        page = self.client.get('/dashboard')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Content-Security-Policy', page.headers)
        self.assertNotIn('SCAMLENS_PUBLISH_TOKEN', page.text)
        self.assertEqual(self.client.get('/dashboard/app.js').status_code, 200)
        self.assertEqual(self.client.get('/dashboard/server.py').status_code, 404)


if __name__ == '__main__':
    unittest.main()
