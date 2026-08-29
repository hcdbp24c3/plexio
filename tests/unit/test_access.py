import pytest
from fastapi.testclient import TestClient

import plexio.routers.access as access_module
from plexio.main import app
from plexio.security import RateLimiter
from plexio.settings import settings
from plexio.store import reset_store

TOKEN = 'very-long-config-token'


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    reset_store()
    monkeypatch.setattr(settings, 'manage_key', None)
    monkeypatch.setattr(settings, 'manage_cookie_secure', False)
    monkeypatch.setattr(
        access_module,
        '_login_limiter',
        RateLimiter(max_requests=100),
    )
    yield
    reset_store()


def _status(client: TestClient, token: str = TOKEN):
    return client.post('/api/v1/access/status', json={'token': token}).json()


def _set_lock(password: str = 'config-pass', token: str = TOKEN):
    with TestClient(app) as client:
        client.post(
            '/api/v1/access/password', json={'token': token, 'password': password}
        )


class TestAccessStatus:
    def test_open_config_has_no_password(self):
        with TestClient(app) as client:
            body = _status(client)
        assert body == {'passwordRequired': False, 'unlocked': True}

    def test_locked_config_hides_from_visitors(self):
        _set_lock()
        with TestClient(app) as client:
            body = _status(client)
        assert body == {'passwordRequired': True, 'unlocked': False}

    def test_admin_session_does_not_bypass_lock(self, monkeypatch):
        """Like the fork's edit gate: a locked config needs its own password."""
        monkeypatch.setattr(settings, 'manage_key', 'admin-secret')
        _set_lock()
        with TestClient(app) as client:
            client.post('/api/v1/manage/login', json={'password': 'admin-secret'})
            body = _status(client)
        assert body == {'passwordRequired': True, 'unlocked': False}

    def test_unlock_cookie_opens_config(self):
        _set_lock()
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/login',
                json={'token': TOKEN, 'password': 'config-pass'},
            )
            assert resp.status_code == 204
            body = _status(client)
        assert body == {'passwordRequired': True, 'unlocked': True}


class TestAccessLogin:
    def test_wrong_password_rejected(self):
        _set_lock()
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/login',
                json={'token': TOKEN, 'password': 'nope'},
            )
        assert resp.status_code == 401

    def test_login_conflicts_when_no_password(self):
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/login',
                json={'token': TOKEN, 'password': 'x' * 8},
            )
        assert resp.status_code == 409

    def test_logout_locks_again(self):
        _set_lock()
        with TestClient(app) as client:
            client.post(
                '/api/v1/access/login',
                json={'token': TOKEN, 'password': 'config-pass'},
            )
            assert _status(client)['unlocked'] is True
            client.post('/api/v1/access/logout', json={'token': TOKEN})
            assert _status(client)['unlocked'] is False


class TestAccessPassword:
    def test_first_lock_allowed_for_link_holder(self):
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/password',
                json={'token': TOKEN, 'password': 'new-pass-1'},
            )
            assert resp.status_code == 200
            assert resp.json() == {'ok': True, 'passwordRequired': True}
        assert _status(TestClient(app))['passwordRequired'] is True

    def test_change_requires_current_password(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'admin-secret')
        _set_lock()
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/password',
                json={'token': TOKEN, 'password': 'new-pass-1'},
            )
            assert resp.status_code == 401
            ok = client.post(
                '/api/v1/access/password',
                json={
                    'token': TOKEN,
                    'password': 'new-pass-1',
                    'currentPassword': 'config-pass',
                },
            )
            assert ok.status_code == 200
        with TestClient(app) as client:
            old = client.post(
                '/api/v1/access/login',
                json={'token': TOKEN, 'password': 'config-pass'},
            )
            assert old.status_code == 401
            fresh = client.post(
                '/api/v1/access/login',
                json={'token': TOKEN, 'password': 'new-pass-1'},
            )
            assert fresh.status_code == 204

    def test_change_without_current_password_on_open_instance(self):
        """No MANAGE_KEY → the instance is open and everyone acts as admin."""
        _set_lock()
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/password',
                json={'token': TOKEN, 'password': 'new-pass-1'},
            )
            assert resp.status_code == 200

    def test_admin_changes_without_current_password(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'admin-secret')
        _set_lock()
        with TestClient(app) as client:
            client.post('/api/v1/manage/login', json={'password': 'admin-secret'})
            resp = client.post(
                '/api/v1/access/password',
                json={'token': TOKEN, 'password': 'admin-forced'},
            )
            assert resp.status_code == 200

    def test_empty_password_removes_lock(self):
        _set_lock()
        with TestClient(app) as client:
            client.post(
                '/api/v1/access/login',
                json={'token': TOKEN, 'password': 'config-pass'},
            )
            resp = client.post(
                '/api/v1/access/password',
                json={'token': TOKEN, 'password': ''},
            )
            assert resp.status_code == 200
            assert resp.json() == {'ok': True, 'passwordRequired': False}
        with TestClient(app) as client:
            assert _status(client) == {
                'passwordRequired': False,
                'unlocked': True,
            }

    def test_non_admin_remove_needs_current(self, monkeypatch):
        monkeypatch.setattr(settings, 'manage_key', 'admin-secret')
        _set_lock()
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/password', json={'token': TOKEN, 'password': ''}
            )
            assert resp.status_code == 401
            ok = client.post(
                '/api/v1/access/password',
                json={
                    'token': TOKEN,
                    'password': '',
                    'currentPassword': 'config-pass',
                },
            )
            assert ok.status_code == 200

    def test_password_too_long_rejected(self):
        with TestClient(app) as client:
            resp = client.post(
                '/api/v1/access/password',
                json={'token': TOKEN, 'password': 'x' * 129},
            )
        assert resp.status_code == 422

    def test_locks_are_scoped_per_token(self):
        other = 'different-token'
        _set_lock(password='config-pass')
        with TestClient(app) as client:
            assert _status(client)['passwordRequired'] is True
            assert _status(client, other)['passwordRequired'] is False
