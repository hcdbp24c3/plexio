import re

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from yarl import URL

import plexio.plex.media_server_api as api_module
from plexio.models.plex import PlexMediaType
from plexio.plex.media_server_api import stremio_to_plex_id
from plexio.plex.utils import PlexUnauthorizedError


class FakeCache:
    """Dict-backed cache mirroring the duck-typed cache interface."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self.calls = 0

    async def get(self, key: str) -> str | None:
        self.calls += 1
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.calls += 1
        self._store[key] = value


MATCHES_RE = re.compile(
    r'^https://metadata\.provider\.plex\.tv/library/metadata/matches\?'
)
PMS_ALL_RE = re.compile(r'^http://pms\.local/library/all\?')
PMS_META_RE = re.compile(r'^http://pms\.local/library/metadata/12345\?')
PMS_LEAVES_RE = re.compile(r'^http://pms\.local/library/metadata/12345/allLeaves')

SHOW_GUID = 'plex://show/5d9c086ce2b877001eb405d5'
MOVIE_GUID = 'plex://movie/5d7768461972a8001ec8544f'


async def test_movie_happy_path():
    with aioresponses() as m:
        m.add(
            MATCHES_RE,
            payload={
                'MediaContainer': {
                    'totalSize': 1,
                    'Metadata': [{'guid': MOVIE_GUID}],
                }
            },
        )
        async with ClientSession() as client:
            fake = FakeCache()
            result = await stremio_to_plex_id(
                client=client,
                url=URL('http://pms.local'),
                token='tok',
                cache=fake,
                stremio_id='tt0111161',
                media_type=PlexMediaType.movie,
            )
    assert result == MOVIE_GUID
    assert fake._store.get('tt0111161') == MOVIE_GUID


async def test_cache_hit():
    fake = FakeCache()
    fake._store['tt0111161'] = MOVIE_GUID
    # No aioresponses registered -- any unexpected HTTP would raise
    async with ClientSession() as client:
        result = await stremio_to_plex_id(
            client=client,
            url=URL('http://pms.local'),
            token='tok',
            cache=fake,
            stremio_id='tt0111161',
            media_type=PlexMediaType.movie,
        )
    assert result == MOVIE_GUID
    assert fake.calls == 1  # only the get() call


async def test_no_match():
    with aioresponses() as m:
        m.add(
            MATCHES_RE,
            payload={'MediaContainer': {'totalSize': 0, 'Metadata': []}},
        )
        async with ClientSession() as client:
            fake = FakeCache()
            result = await stremio_to_plex_id(
                client=client,
                url=URL('http://pms.local'),
                token='tok',
                cache=fake,
                stremio_id='tt0111161',
                media_type=PlexMediaType.movie,
            )
    assert result is None
    assert fake._store == {}


async def test_show_happy_path():
    with aioresponses() as m:
        # 1. matches endpoint -> show GUID
        m.add(
            MATCHES_RE,
            payload={
                'MediaContainer': {
                    'totalSize': 1,
                    'Metadata': [{'guid': SHOW_GUID}],
                }
            },
        )
        # 2. get_media: library/all query
        m.add(
            PMS_ALL_RE,
            payload={
                'MediaContainer': {
                    'Metadata': [
                        {
                            'ratingKey': '12345',
                            'type': 'show',
                            'guid': SHOW_GUID,
                            'title': 'Test Show',
                            'key': '/library/metadata/12345/children',
                        }
                    ]
                }
            },
        )
        # 3. get_media: library/metadata/12345 detail
        m.add(
            PMS_META_RE,
            payload={
                'MediaContainer': {
                    'Metadata': [
                        {
                            'guid': SHOW_GUID,
                            'type': 'show',
                            'title': 'Test Show',
                            'ratingKey': '12345',
                            'key': '/library/metadata/12345/children',
                        }
                    ]
                }
            },
        )
        # 4. get_all_episodes: allLeaves
        m.add(
            PMS_LEAVES_RE,
            payload={
                'MediaContainer': {
                    'Metadata': [
                        {
                            'guid': 'plex://episode/abc',
                            'title': 'Pilot',
                            'parentIndex': 1,
                            'index': 1,
                            'addedAt': 0,
                        }
                    ]
                }
            },
        )
        async with ClientSession() as client:
            fake = FakeCache()
            result = await stremio_to_plex_id(
                client=client,
                url=URL('http://pms.local'),
                token='tok',
                cache=fake,
                stremio_id='tt0944947:1:1',
                media_type=PlexMediaType.show,
            )
    assert result == 'plex://episode/abc'
    assert fake._store.get('tt0944947:1:1') == 'plex://episode/abc'


async def test_invalid_show_id_format():
    # Only 2 parts instead of required 3
    async with ClientSession() as client:
        fake = FakeCache()
        result = await stremio_to_plex_id(
            client=client,
            url=URL('http://pms.local'),
            token='tok',
            cache=fake,
            stremio_id='tt0944947:1',
            media_type=PlexMediaType.show,
        )
    assert result is None
    assert fake._store == {}


async def test_token_precedence(monkeypatch):
    monkeypatch.setattr(api_module.settings, 'plex_matching_token', 'matching-tok')
    captured_params: dict = {}

    async def fake_get_json(client, url, params=None):
        if 'matches' in str(url):
            captured_params.update(params or {})
        return {
            'MediaContainer': {
                'totalSize': 1,
                'Metadata': [{'guid': MOVIE_GUID}],
            }
        }

    monkeypatch.setattr(api_module, 'get_json', fake_get_json)

    async with ClientSession() as client:
        fake = FakeCache()
        await stremio_to_plex_id(
            client=client,
            url=URL('http://pms.local'),
            token='tok',
            cache=fake,
            stremio_id='tt0111161',
            media_type=PlexMediaType.movie,
        )
    assert captured_params.get('X-Plex-Token') == 'matching-tok'


async def test_default_token_uses_passed_token(monkeypatch):
    monkeypatch.setattr(api_module.settings, 'plex_matching_token', None)
    captured_params: dict = {}

    async def fake_get_json(client, url, params=None):
        if 'matches' in str(url):
            captured_params.update(params or {})
        return {
            'MediaContainer': {
                'totalSize': 1,
                'Metadata': [{'guid': MOVIE_GUID}],
            }
        }

    monkeypatch.setattr(api_module, 'get_json', fake_get_json)

    async with ClientSession() as client:
        fake = FakeCache()
        await stremio_to_plex_id(
            client=client,
            url=URL('http://pms.local'),
            token='tok',
            cache=fake,
            stremio_id='tt0111161',
            media_type=PlexMediaType.movie,
        )
    assert captured_params.get('X-Plex-Token') == 'tok'


async def test_unauthorized():
    with aioresponses() as m:
        m.add(MATCHES_RE, status=401)
        async with ClientSession() as client:
            fake = FakeCache()
            with pytest.raises(PlexUnauthorizedError):
                await stremio_to_plex_id(
                    client=client,
                    url=URL('http://pms.local'),
                    token='tok',
                    cache=fake,
                    stremio_id='tt0111161',
                    media_type=PlexMediaType.movie,
                )
