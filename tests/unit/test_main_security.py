from fastapi.testclient import TestClient

import plexio.main as main_module
from plexio.main import app
from plexio.security import RateLimiter


class TestSecurityHeaders:
    def test_headers_present(self):
        with TestClient(app) as client:
            resp = client.get('/health')
        assert resp.headers['x-content-type-options'] == 'nosniff'
        assert resp.headers['x-frame-options'] == 'SAMEORIGIN'
        assert resp.headers['referrer-policy'] == 'no-referrer'


class TestRateLimit:
    def test_api_requests_throttled(self, monkeypatch):
        monkeypatch.setattr(
            main_module,
            '_public_limiter',
            RateLimiter(max_requests=1, window_seconds=60),
        )
        with TestClient(app) as client:
            first = client.get(
                '/api/v1/test-connection',
                params={'url': 'http://localhost:32400', 'token': 't'},
            )
            second = client.get(
                '/api/v1/test-connection',
                params={'url': 'http://localhost:32400', 'token': 't'},
            )
        assert first.status_code == 400  # SSRF block, reached the handler
        assert second.status_code == 429

    def test_addon_paths_not_throttled(self, monkeypatch):
        monkeypatch.setattr(
            main_module,
            '_public_limiter',
            RateLimiter(max_requests=1, window_seconds=60),
        )
        with TestClient(app) as client:
            # /proxy is auth-token protected; should not hit the API limiter.
            resp = client.get('/proxy/garbage')
        assert resp.status_code == 404
