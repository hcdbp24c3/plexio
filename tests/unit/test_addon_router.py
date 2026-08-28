import base64
import json
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from plexio.dependencies import get_addon_configuration, get_cache, get_http_client
from plexio.models.addon import AddonConfiguration
from plexio.models.stremio import StremioStream
from plexio.routers.addon import router

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

LEGACY_SERVER = {
    'accessToken': 'tok-old',
    'discoveryUrl': 'https://old.example.com',
    'streamingUrl': 'https://old-stream.example.com',
    'serverName': 'Old Server',
    'sections': [{'key': '10', 'title': 'Movies', 'type': 'movie'}],
}


def _b64(cfg):
    return base64.b64encode(json.dumps(cfg).encode()).decode()


class _FakeCache:
    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value):
        self._store[key] = value


class _FakeSession:
    pass


def _set_deps(*, configuration: Any = None, http_client: Any = None, cache: Any = None):
    """Set dependency overrides and return a TestClient.

    Override functions must match original dependency signatures so FastAPI
    doesn't try to resolve extra params from the request.
    """

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

    if configuration is not None:
        APP.dependency_overrides[get_addon_configuration] = _override_cfg
    else:
        APP.dependency_overrides[get_addon_configuration] = _override_cfg
    if http_client is not None:
        APP.dependency_overrides[get_http_client] = _override_http
    if cache is not None:
        APP.dependency_overrides[get_cache] = _override_cache
    return TestClient(APP)


def _clear_deps():
    APP.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
class TestManifest:
    def test_two_server_catalog_count(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
        )
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        assert r.status_code == 200
        assert len(r.json()['catalogs']) == 3

    def test_catalog_ids_prefixed(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
        )
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        ids = [c['id'] for c in r.json()['catalogs']]
        assert ids == ['0:1', '0:2', '1:3']

    def test_catalog_names_include_server(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
        )
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        names = {c['name'] for c in r.json()['catalogs']}
        assert 'Movies | Server A' in names
        assert 'TV Shows | Server A' in names
        assert 'Anime | Server B' in names

    def test_manifest_name_joins_servers(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
        )
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        assert r.json()['name'] == 'Plexio (Server A, Server B)'

    def test_no_config_returns_empty_catalogs(self):
        client = _set_deps(configuration=None)
        r = client.get('/manifest.json')
        _clear_deps()
        assert r.status_code == 200
        body = r.json()
        assert body['catalogs'] == []
        assert body['behaviorHints']['configurationRequired'] is True

    def test_legacy_flat_config_wraps(self):
        client = _set_deps(
            configuration={
                'servers': [
                    {
                        'sections': [{'key': '10', 'title': 'M', 'type': 'movie'}],
                        'accessToken': 'x',
                        'discoveryUrl': 'http://x',
                        'streamingUrl': 'http://x',
                        'serverName': 'S',
                    }
                ],
                'version': '0.0.1',
            },
        )
        r = client.get('/inst/abc/manifest.json')
        _clear_deps()
        assert r.status_code == 200
        assert len(r.json()['catalogs']) == 1
        assert r.json()['catalogs'][0]['id'] == '0:10'


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
class TestCatalog:
    def test_server_index_parsing(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with patch(
            'plexio.routers.addon.get_section_media',
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_gsm:
            client.get('/inst/abc/catalog/movie/1:2.json')
            _clear_deps()
            args, kwargs = mock_gsm.call_args
            assert str(kwargs['url']) == 'https://b.example.com'
            assert kwargs['token'] == 'tok-b'

    def test_bare_key_uses_server_zero(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with patch(
            'plexio.routers.addon.get_section_media',
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_gsm:
            client.get('/inst/abc/catalog/movie/1.json')
            _clear_deps()
            args, kwargs = mock_gsm.call_args
            assert str(kwargs['url']) == 'https://a.example.com'
            assert kwargs['section_id'] == '1'

    def test_out_of_range_server_returns_404(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        r = client.get('/inst/abc/catalog/movie/99:1.json')
        _clear_deps()
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------
class _MockMedia:
    def __init__(self, guid, title='Title', stremio_type='movie', key='/meta'):
        self.guid = guid
        self.title = title
        self.type = stremio_type
        self.key = key
        self.thumb = None
        self.art = None
        self.year = 2020
        self.genre = []
        self.audience_rating = None
        self.summary = 'Summary'
        self.guids = []

    def to_stremio_meta(
        self, server, server_index=None, *, stream_proxy=False, proxy_base=None
    ):
        from plexio.models.stremio import StremioMeta
        from plexio.models.utils import guid_to_plexio_id

        return StremioMeta(
            id=guid_to_plexio_id(self.guid, server_index=server_index),
            type='movie',
            name=self.title,
        )


class TestMeta:
    def test_marked_id_queries_only_that_server(self):
        mock_media = _MockMedia('plex://movie/aaa')
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with patch(
            'plexio.routers.addon.get_media',
            new_callable=AsyncMock,
            return_value=[mock_media],
        ) as mock_get:
            pid = 'plexio:1:cGxleDovL21vdmllL2FhYQ'
            r = client.get(f'/inst/abc/meta/movie/{pid}.json')
            _clear_deps()
            assert r.status_code == 200
            args, kwargs = mock_get.call_args
            assert str(kwargs['url']) == 'https://b.example.com'
            assert kwargs['guid'] == 'plex://movie/aaa'

    def test_legacy_id_probes_in_order(self):
        mock_media = _MockMedia('plex://movie/aaa')
        call_count = 0

        async def fake_get_media(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return [mock_media]
            return []

        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with patch(
            'plexio.routers.addon.get_media',
            side_effect=fake_get_media,
        ):
            from plexio.models.utils import guid_to_plexio_id

            pid = guid_to_plexio_id('plex://movie/aaa')
            r = client.get(f'/inst/abc/meta/movie/{pid}.json')
            _clear_deps()
            assert r.status_code == 200
            assert call_count == 2

    def test_not_found(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with patch(
            'plexio.routers.addon.get_media',
            new_callable=AsyncMock,
            return_value=[],
        ):
            from plexio.models.utils import guid_to_plexio_id

            pid = guid_to_plexio_id('plex://movie/missing')
            r = client.get(f'/inst/abc/meta/movie/{pid}.json')
            _clear_deps()
            assert r.status_code == 404


# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------
class _MockMediaForStream:
    def __init__(self, guid):
        self.guid = guid

    def get_stremio_streams(self, server, configuration, *, proxy_base=None):
        return [
            StremioStream(
                name=server.server_name,
                description=f'stream-{server.server_name}',
                url=f'https://{server.server_name}/stream',
            ),
        ]


class TestStream:
    def test_tt_id_queries_all_servers(self):
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
                side_effect=lambda **kw: [_MockMediaForStream(kw['guid'])],
            ),
        ):
            r = client.get('/inst/abc/stream/movie/tt0111161.json')
            _clear_deps()
            assert r.status_code == 200
            body = r.json()
            assert len(body['streams']) == 2

    def test_marked_plexio_id_routes_to_server(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with patch(
            'plexio.routers.addon.get_media',
            new_callable=AsyncMock,
            side_effect=lambda **kw: [_MockMediaForStream(kw['guid'])],
        ):
            from plexio.models.utils import guid_to_plexio_id

            pid = guid_to_plexio_id('plex://movie/abc', server_index=1)
            r = client.get(f'/inst/abc/stream/movie/{pid}.json')
            _clear_deps()
            assert r.status_code == 200
            body = r.json()
            assert len(body['streams']) == 1
            assert body['streams'][0]['name'] == 'Server B'

    def test_tt_no_resolution_returns_empty(self):
        client = _set_deps(
            configuration={'servers': SERVERS, 'version': '0.0.1'},
            http_client=_FakeSession(),
            cache=_FakeCache(),
        )
        with (
            patch(
                'plexio.routers.addon.stremio_to_plex_id',
                new_callable=AsyncMock,
                return_value=None,
            ) as _mock_resolve,
            patch(
                'plexio.routers.addon.get_media',
                new_callable=AsyncMock,
            ) as mock_get,
        ):
            r = client.get('/inst/abc/stream/movie/tt0000000.json')
            _clear_deps()
            assert r.status_code == 200
            assert r.json()['streams'] == []
            mock_get.assert_not_called()
