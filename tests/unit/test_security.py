import time

from plexio.security import (
    blocked_target_url,
    mint_proxy_token,
    unmint_proxy_token,
)


class TestProxyToken:
    def test_roundtrip(self):
        token = mint_proxy_token('http://pms.local/video.mkv')
        assert unmint_proxy_token(token) == 'http://pms.local/video.mkv'

    def test_opaque_and_url_safe(self):
        token = mint_proxy_token('http://pms.local/a?X-Plex-Token=secret')
        assert 'pms.local' not in token
        assert 'secret' not in token
        assert token.replace('-', '').replace('_', '').isalnum()
        assert '=' not in token

    def test_expired(self, monkeypatch):
        monkeypatch.setattr('plexio.security.PROXY_TOKEN_TTL', -1)
        token = mint_proxy_token('http://pms.local/video.mkv')
        assert unmint_proxy_token(token) is None

    def test_tampered(self):
        token = mint_proxy_token('http://pms.local/video.mkv')
        tampered = ('A' if token[0] != 'A' else 'B') + token[1:]
        assert unmint_proxy_token(tampered) is None

    def test_garbage(self):
        assert unmint_proxy_token('not-a-token') is None

    def test_expiry_window_respected(self):
        token = mint_proxy_token('http://pms.local/video.mkv', ttl=2)
        assert unmint_proxy_token(token) == 'http://pms.local/video.mkv'
        time.sleep(2.1)
        assert unmint_proxy_token(token) is None


class TestBlockedTarget:
    def test_localhost_blocked(self):
        assert blocked_target_url('http://localhost:32400/identity')

    def test_cloud_metadata_blocked(self):
        assert blocked_target_url('http://169.254.169.254/latest/meta-data/')
        assert blocked_target_url('http://metadata.google.internal/')

    def test_link_local_blocked(self):
        assert blocked_target_url('http://169.254.1.1/')

    def test_multicast_and_reserved_blocked(self):
        assert blocked_target_url('http://224.0.0.1/')
        assert blocked_target_url('http://127.0.0.1/')

    def test_private_lan_allowed(self):
        assert not blocked_target_url('http://192.168.1.5:32400/identity')
        assert not blocked_target_url('http://10.0.0.5/')
        assert not blocked_target_url('http://172.16.5.5/')

    def test_public_host_allowed(self):
        assert not blocked_target_url('http://pms.example.com/')

    def test_no_host_rejected(self):
        assert blocked_target_url('not a url')
