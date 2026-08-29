import pytest
from fastapi.testclient import TestClient

import plexio.routers.manage as manage_module
from plexio.main import app
from plexio.security import RateLimiter
from plexio.settings import settings
from plexio.store import reset_store


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    reset_store()
    monkeypatch.setattr(settings, 'manage_key', None)
    monkeypatch.setattr(settings, 'manage_cookie_secure', False)
    monkeypatch.setattr(
        manage_module,
        '_login_limiter',
        RateLimiter(max_requests=100),
    )
    yield
    reset_store()


def _status(client: TestClient):
    return client.get('/api/v1/manage/status').json()


class TestStatus:
    def test_no_password_configured_is_open(self):
        with TestClient(app) as client:
            body = _status(client)
        assert body['passwordRequired'] is False
        assert body['admin'] is True

    def test_env_manage_key_requires_password(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'hunter2-secret')
        with TestClient(app) as client:
            body = _status(client)
        assert body['passwordRequired'] is True
        assert body['admin'] is False

    def test_status_reports_proxy_toggles(self):
        from plexio.store import get_store

        get_store().set_setting('proxy_enabled', False)
        with TestClient(app) as client:
            body = _status(client)
        assert body['proxyEnabled'] is False
        assert body['proxyAdminOnly'] is True


class TestLogin:
    def test_login_rejects_wrong_password(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'hunter2-secret')
        with TestClient(app) as client:
            resp = client.post('/api/v1/manage/login', json={'password': 'nope'})
        assert resp.status_code == 401

    def test_login_sets_admin_cookie(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'hunter2-secret')
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/manage/login', json={'password': 'hunter2-secret'}
            )
            assert resp.status_code == 204
            assert settings.manage_cookie_name in resp.headers['set-cookie']
            body = _status(client)
        assert body['admin'] is True

    def test_login_when_no_password(self):
        with TestClient(app) as client:
            resp = client.post('/api/v1/manage/login', json={'password': 'x'})
        assert resp.status_code == 409

    def test_login_rate_limited(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'hunter2-secret')
        monkeypatch.setattr(
            manage_module,
            '_login_limiter',
            RateLimiter(max_requests=1),
        )
        with TestClient(app) as client:
            first = client.post('/api/v1/manage/login', json={'password': 'wrong'})
            second = client.post('/api/v1/manage/login', json={'password': 'wrong'})
        assert first.status_code == 401
        assert second.status_code == 429


class TestLogout:
    def test_logout_clears_admin(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'hunter2-secret')
        with TestClient(app) as client:
            client.post('/api/v1/manage/login', json={'password': 'hunter2-secret'})
            assert _status(client)['admin'] is True
            client.post('/api/v1/manage/logout')
            assert _status(client)['admin'] is False


class TestSetPassword:
    def test_set_password_then_login(self):
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/manage/password', json={'password': 'long-enough'}
            )
            assert resp.status_code == 200
            body = _status(client)
            assert body['passwordRequired'] is True
            assert body['admin'] is False
            login = client.post(
                '/api/v1/manage/login', json={'password': 'long-enough'}
            )
            assert login.status_code == 204
            assert _status(client)['admin'] is True

    def test_set_password_rejects_short(self):
        with TestClient(app) as client:
            resp = client.post('/api/v1/manage/password', json={'password': 'short'})
        assert resp.status_code == 422

    def test_set_password_rejected_when_already_configured(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'env-key-secret')
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/manage/password', json={'password': 'another-key'}
            )
        assert resp.status_code == 409


class TestProxyEnforcement:
    def test_proxy_returns_403_when_disabled(self):
        from plexio.store import get_store

        get_store().set_setting('proxy_enabled', False)
        with TestClient(app) as client:
            resp = client.get('/proxy/any-token')
        assert resp.status_code == 403

    def test_proxy_still_resolves_when_enabled(self):
        with TestClient(app) as client:
            resp = client.get('/proxy/not-a-valid-token')
        assert resp.status_code == 404

    def test_stream_proxy_guard_honors_server_switch(self):
        from types import SimpleNamespace

        from plexio.routers.addon import _stream_proxy
        from plexio.store import get_store

        cfg = SimpleNamespace(stream_proxy=True)
        assert _stream_proxy(cfg) is True
        get_store().set_setting('proxy_enabled', False)
        assert _stream_proxy(cfg) is False
        cfg.stream_proxy = False
        assert _stream_proxy(cfg) is False
