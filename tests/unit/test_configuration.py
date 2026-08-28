import re

from aioresponses import aioresponses
from fastapi.testclient import TestClient

from plexio.main import app

PMS_RE = re.compile(r'^http://pms\.local/')
IDENTITY_RE = re.compile(r'^http://pms\.local/?\?')


class TestTestConnection:
    def test_ok(self):
        with aioresponses() as m:
            m.get(
                IDENTITY_RE,
                status=200,
                payload={'MediaContainer': {'machineIdentifier': 'abc'}},
            )
            with TestClient(app) as client:
                resp = client.get(
                    '/api/v1/test-connection',
                    params={'url': 'http://pms.local', 'token': 'tok'},
                )
        assert resp.status_code == 200
        assert resp.json() == {'success': True}

    def test_ssrf_metadata_blocked(self):
        with TestClient(app) as client:
            resp = client.get(
                '/api/v1/test-connection',
                params={
                    'url': 'http://169.254.169.254/latest/meta-data/',
                    'token': 'tok',
                },
            )
        assert resp.status_code == 400

    def test_ssrf_localhost_blocked(self):
        with TestClient(app) as client:
            resp = client.get(
                '/api/v1/test-connection',
                params={'url': 'http://localhost:32400', 'token': 'tok'},
            )
        assert resp.status_code == 400


class TestSections:
    def test_returns_movie_and_show_sections(self):
        payload = {
            'MediaContainer': {
                'Directory': [
                    {'key': '1', 'title': 'Movies', 'type': 'movie'},
                    {'key': '2', 'title': 'TV', 'type': 'show'},
                    {'key': '3', 'title': 'Music', 'type': 'artist'},
                ]
            }
        }
        with aioresponses() as m:
            m.get(PMS_RE, status=200, payload=payload)
            with TestClient(app) as client:
                resp = client.get(
                    '/api/v1/sections',
                    params={'url': 'http://pms.local', 'token': 'tok'},
                )
        assert resp.status_code == 200
        sections = resp.json()['sections']
        assert [s['key'] for s in sections] == ['1', '2']

    def test_returns_empty_on_upstream_error(self):
        with aioresponses() as m:
            m.get(PMS_RE, status=500, body='err')
            with TestClient(app) as client:
                resp = client.get(
                    '/api/v1/sections',
                    params={'url': 'http://pms.local', 'token': 'tok'},
                )
        assert resp.status_code == 200
        assert resp.json() == {'sections': []}

    def test_ssrf_blocked(self):
        with TestClient(app) as client:
            resp = client.get(
                '/api/v1/sections',
                params={'url': 'http://localhost:32400', 'token': 'tok'},
            )
        assert resp.status_code == 400
