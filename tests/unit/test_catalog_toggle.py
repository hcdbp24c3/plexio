from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from plexio.dependencies import get_addon_configuration, get_cache, get_http_client
from plexio.models.addon import AddonConfiguration, ServerConfiguration
from plexio.models.stremio import StremioStream
from plexio.routers.addon import _gather_media, router

APP = FastAPI()
APP.include_router(router)

SERVERS = [
    {
        'accessToken': 'tok-a',
        'discoveryUrl': 'https://a.example.com',
        'streamingUrl': 'https://a-stream.example.com',
        'serverName': 'Server A',
        'sections': [
            {'key': '1', 'title': 'Movies', 'type': 'movie'},
            {'key': '2', 'title': 'TV Shows', 'type': 'show'},
        ],
    },
    {
        'accessToken': 'tok-b',
        'discoveryUrl': 'https://b.example.com',
        'streamingUrl': 'https://b-stream.example.com',
        'serverName': 'Server B',
        'sections': [{'key': '3', 'title': 'Anime', 'type': 'show'}],
    },
]


class _FakeCache:
    def __init__(self):
        self._store: dict = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value):
        self._store[key] = value


class _FakeSession:
    pass


def _set_deps(*, configuration=None, http_client=None, cache=None):
    def _override_cfg(base64_cfg: str | None = None):
        if configuration is None:
            return None
        if isinstance(configuration, dict):
            return AddonConfiguration(**configuration)
        return configuration

    def _override_http(request: Request):
        return http_client

    def _override_cache(request: Request):
        return cache

    APP.dependency_overrides[get_addon_configuration] = _override_cfg
    if http_client is not None:
        APP.dependency_overrides[get_http_client] = _override_http
    if cache is not None:
        APP.dependency_overrides[get_cache] = _override_cache
    return TestClient(APP)


def _clear_deps():
    APP.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Model: include_catalogs defaults
# ---------------------------------------------------------------------------
class TestIncludeCatalogsModel:
    def test_legacy_config_defaults_to_true(self):
        cfg = AddonConfiguration(
            servers=[
                {
                    'accessToken': 'tok',
                    'discoveryUrl': 'https://d.example.com',
                    'streamingUrl': 'https://s.example.com',
                    'serverName': 'S',
                    'sections': [{'key': '1', 'title': 'M', 'type': 'movie'}],
                }
            ],
        )
        assert cfg.include_catalogs is True

    def test_camelcase_false_parses(self):
        cfg = AddonConfiguration(
            servers=[
                {
                    'accessToken': 'tok',
                    'discoveryUrl': 'https://d.example.com',
                    'streamingUrl': 'https://s.example.com',
                    'serverName': 'S',
                    'sections': [],
                }
            ],
            includeCatalogs=False,
        )
        assert cfg.include_catalogs is False

    def test_camelcase_true_parses(self):
        cfg = AddonConfiguration(
            servers=[
                {
                    'accessToken': 'tok',
                    'discoveryUrl': 'https://d.example.com',
                    'streamingUrl': 'https://s.example.com',
                    'serverName': 'S',
                    'sections': [],
                }
            ],
            includeCatalogs=True,
        )
        assert cfg.include_catalogs is True


# ---------------------------------------------------------------------------
# Manifest: catalog toggle
# ---------------------------------------------------------------------------
class TestCatalogToggleManifest:
    def test_disabled_catalogs_not_in_resources(self):
        cfg = {'servers': SERVERS, 'version': '0.0.1', 'includeCatalogs': False}
        client = _set_deps(configuration=cfg)
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        assert r.status_code == 200
        body = r.json()
        assert 'catalog' not in body['resources']
        assert body['catalogs'] == []

    def test_disabled_catalogs_stream_and_meta_still_present(self):
        cfg = {'servers': SERVERS, 'version': '0.0.1', 'includeCatalogs': False}
        client = _set_deps(configuration=cfg)
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        body = r.json()
        assert 'stream' in body['resources']
        meta_res = [
            r
            for r in body['resources']
            if isinstance(r, dict) and r.get('name') == 'meta'
        ]
        assert len(meta_res) == 1

    def test_legacy_config_no_key_has_catalogs(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
        )
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        assert r.status_code == 200
        body = r.json()
        assert len(body['catalogs']) == 3
        assert 'catalog' in body['resources']

    def test_disabled_name_still_joins_servers(self):
        cfg = {'servers': SERVERS, 'version': '0.0.1', 'includeCatalogs': False}
        client = _set_deps(configuration=cfg)
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        assert r.json()['name'] == 'Plexio (Server A, Server B)'


# ---------------------------------------------------------------------------
# Catalog endpoint: disabled returns empty
# ---------------------------------------------------------------------------
class TestCatalogToggleEndpoint:
    def test_disabled_returns_empty_metas(self):
        cfg = {'servers': SERVERS, 'version': '0.0.1', 'includeCatalogs': False}
        client = _set_deps(
            configuration=cfg,
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        r = client.get('/inst/abc/catalog/movie/1:1.json')
        _clear_deps()
        assert r.status_code == 200
        assert r.json()['metas'] == []


# ---------------------------------------------------------------------------
# Stream: parallel proof — both servers fetched concurrently
# ---------------------------------------------------------------------------
class _FakeStreamMedia:
    def __init__(self, guid):
        self.guid = guid

    def get_stremio_streams(self, server, configuration):
        return [
            StremioStream(
                name=server.server_name,
                description=f'stream-{server.server_name}',
                url=f'https://{server.server_name}/stream',
            ),
        ]


class TestParallelStream:
    def test_tt_path_both_servers_awaited(self):
        """Both servers should be called (no short-circuit after first success)."""
        mock_meta = _FakeStreamMedia('plex://movie/resolved')
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with (
            patch(
                'plexio.routers.addon.stremio_to_plex_id',
                new_callable=AsyncMock,
                return_value='plex://movie/resolved',
            ),
            patch(
                'plexio.routers.addon.get_media',
                new_callable=AsyncMock,
                return_value=[mock_meta],
            ) as mock_get_media,
        ):
            r = client.get('/inst/abc/stream/movie/tt0111161.json')
            _clear_deps()
            assert r.status_code == 200
            # Both servers called — no short-circuit
            assert mock_get_media.await_count == len(SERVERS)
            # Each server produces 1 stream → 2 total
            assert len(r.json()['streams']) == 2

    def test_raw_id_both_servers_awaited(self):
        mock_meta = _FakeStreamMedia('plex://movie/raw')
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with patch(
            'plexio.routers.addon.get_media',
            new_callable=AsyncMock,
            return_value=[mock_meta],
        ) as mock_get_media:
            r = client.get('/inst/abc/stream/movie/plex://movie/raw.json')
            _clear_deps()
            assert r.status_code == 200
            assert mock_get_media.await_count == len(SERVERS)
            assert len(r.json()['streams']) == 2


# ---------------------------------------------------------------------------
# _gather_media helper: one server fails, other still returned
# ---------------------------------------------------------------------------
class TestGatherMediaHelper:
    async def test_one_server_raises_other_returns(self):
        s1 = ServerConfiguration(
            accessToken='tok-a',
            discoveryUrl='https://a.example.com',
            streamingUrl='https://a-stream.example.com',
            serverName='Server A',
            sections=[],
        )
        s2 = ServerConfiguration(
            accessToken='tok-b',
            discoveryUrl='https://b.example.com',
            streamingUrl='https://b-stream.example.com',
            serverName='Server B',
            sections=[],
        )

        call_count = 0

        async def fake_get_media(**kwargs):
            nonlocal call_count
            call_count += 1
            if 'a.example.com' in str(kwargs['url']):
                raise HTTPException(status_code=500)
            return [_FakeStreamMedia(kwargs['guid'])]

        client = _FakeSession()
        with patch(
            'plexio.routers.addon.get_media',
            side_effect=fake_get_media,
        ):
            pairs = await _gather_media(client, [s1, s2], 'plex://movie/test')
            assert len(pairs) == 1
            assert pairs[0][0].server_name == 'Server B'
