import re

from aioresponses import aioresponses
from fastapi.testclient import TestClient

from plexio.main import app
from plexio.security import mint_proxy_token

PMS_RE = re.compile(r'^http://pms\.local/')


class TestProxy:
    def test_invalid_token_returns_404(self):
        with TestClient(app) as client:
            resp = client.get('/proxy/not-a-valid-token')
        assert resp.status_code == 404

    def test_hls_playlist_rewritten_and_token_stripped(self):
        upstream = (
            'http://pms.local/video/:/transcode/universal/start.m3u8'
            '?X-Plex-Token=super-secret&VideoQuality=100'
        )
        token = mint_proxy_token(upstream)
        playlist = (
            '#EXTM3U\n'
            '#EXT-X-VERSION:3\n'
            '#EXT-X-KEY:METHOD=AES-128,URI="key.bin"\n'
            '#EXTINF:4.0,\n'
            'segment0.ts?X-Plex-Token=super-secret\n'
            '#EXTINF:4.0,\n'
            'http://pms.local/other/segment1.ts\n'
            '#EXT-X-ENDLIST\n'
        )
        with aioresponses() as m:
            m.get(
                PMS_RE,
                status=200,
                content_type='application/vnd.apple.mpegurl',
                body=playlist,
            )
            with TestClient(app) as client:
                resp = client.get(f'/proxy/{token}')

        assert resp.status_code == 200
        body = resp.text
        assert 'X-Plex-Token' not in body and 'super-secret' not in body
        assert body.count('/proxy/') == 3  # key + 2 segments
        for line in body.splitlines():
            if line.startswith('#EXT-X-KEY'):
                assert 'URI="' in line and 'X-Plex-Token' not in line
            elif line and not line.startswith('#'):
                assert '/proxy/' in line

    def test_m3u8_segments_resolved_against_upstream(self):
        upstream = 'http://pms.local/video/:/transcode/universal/start.m3u8'
        token = mint_proxy_token(upstream)
        playlist = '#EXTM3U\nsegment0.ts\n'
        with aioresponses() as m:
            m.get(PMS_RE, status=200, body=playlist)
            with TestClient(app) as client:
                resp = client.get(f'/proxy/{token}')
        assert resp.status_code == 200
        line = resp.text.splitlines()[-1]
        assert '/proxy/' in line
        assert 'segment0' not in line

    def test_media_relay_passes_range(self):
        upstream = 'http://pms.local/library/parts/123/file.mp4'
        token = mint_proxy_token(upstream)
        with aioresponses() as m:
            m.get(
                PMS_RE,
                status=206,
                body=b'0123456789',
                headers={
                    'Content-Range': 'bytes 0-9/100',
                    'Content-Type': 'video/mp4',
                },
            )
            with TestClient(app) as client:
                resp = client.get(f'/proxy/{token}', headers={'Range': 'bytes=0-9'})

        assert resp.status_code == 206
        assert resp.content == b'0123456789'
        assert resp.headers.get('content-range') == 'bytes 0-9/100'
        assert resp.headers.get('content-type') == 'video/mp4'

    def test_upstream_error_becomes_502(self):
        upstream = 'http://pms.local/library/parts/123/file.mp4'
        token = mint_proxy_token(upstream)
        with aioresponses() as m:
            m.get(PMS_RE, status=500, body='boom')
            with TestClient(app) as client:
                resp = client.get(f'/proxy/{token}')
        assert resp.status_code == 502
