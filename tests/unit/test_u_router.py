"""Tests for the per-user /u/<id> setup links."""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from plexio.main import app
from plexio.store import get_store, reset_store


@pytest.fixture(autouse=True)
def clean_state():
    reset_store()
    yield
    reset_store()


def _encoded(config: dict) -> str:
    raw = json.dumps(config, separators=(',', ':')).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


class TestUserSetupRoutes:
    def test_u_id_redirects_to_configure(self):
        get_store().save_config({'streamProxy': False}, 'Alpha', 'setup-1')
        with TestClient(app) as client:
            resp = client.get('/u/setup-1', follow_redirects=False)
            assert resp.status_code == 302
            assert (
                resp.headers['location']
                == f'http://testserver/setup-1/{_encoded({"streamProxy": False})}/configure'
            )

    def test_u_id_manifest_redirect(self):
        get_store().save_config({'streamProxy': True}, 'Beta', 'setup-1')
        with TestClient(app) as client:
            resp = client.get('/u/setup-1/manifest.json', follow_redirects=False)
            assert resp.status_code == 302
            assert (
                resp.headers['location']
                == f'http://testserver/setup-1/{_encoded({"streamProxy": True})}/manifest.json'
            )

    def test_unknown_id_redirects_home(self):
        with TestClient(app) as client:
            assert client.get('/u/ghost', follow_redirects=False).status_code == 302
            assert client.get('/u/ghost/configure', follow_redirects=False).status_code == 302
            assert client.get('/u/ghost/manifest.json', follow_redirects=False).status_code == 302
            assert client.get('/u/ghost', follow_redirects=False).headers['location'] == '/'

    def test_u_link_preserves_id_after_edit(self):
        """Re-saving with the same id keeps /u/<id> working with the new token."""
        get_store().save_config({'streamProxy': False}, 'Alpha', 'setup-1')
        get_store().save_config(
            {'streamProxy': False, 'includeCatalogs': True}, 'Alpha', 'setup-1'
        )
        with TestClient(app) as client:
            resp = client.get('/u/setup-1', follow_redirects=False)
            assert resp.status_code == 302
            assert '/setup-1/' in resp.headers['location']
            assert resp.headers['location'].endswith('/configure')
