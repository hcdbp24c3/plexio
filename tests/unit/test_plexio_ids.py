import pytest

from plexio.models.utils import (
    guid_to_plexio_id,
    parse_plexio_id,
    plexio_id_to_guid,
)


class TestGuidToPlexioId:
    def test_legacy_no_server_index(self):
        pid = guid_to_plexio_id('plex://movie/abc')
        assert pid == 'plexio:elerikbGVtbw' or pid.startswith('plexio:')
        assert ':' not in pid[len('plexio:') :]

    def test_with_server_index(self):
        pid = guid_to_plexio_id('plex://movie/abc', server_index=2)
        assert pid.startswith('plexio:2:')

    def test_server_index_zero(self):
        pid = guid_to_plexio_id('plex://movie/abc', server_index=0)
        assert pid.startswith('plexio:0:')

    @pytest.mark.parametrize(
        'guid',
        [
            'com.plexapp.agents.imdb://tt0111161?lang=en',
            'plex://movie/5d7768461972a8001ec8544f',
            'a',
            '',
        ],
    )
    def test_roundtrip_legacy(self, guid):
        pid = guid_to_plexio_id(guid)
        assert plexio_id_to_guid(pid) == guid

    @pytest.mark.parametrize(
        'guid',
        [
            'com.plexapp.agents.imdb://tt0111161?lang=en',
            'plex://movie/5d7768461972a8001ec8544f',
            'a',
            '',
        ],
    )
    def test_roundtrip_marked(self, guid):
        pid = guid_to_plexio_id(guid, server_index=3)
        si, g = parse_plexio_id(pid)
        assert si == 3
        assert g == guid

    def test_parse_legacy_returns_none_index(self):
        pid = guid_to_plexio_id('some-guid')
        si, guid = parse_plexio_id(pid)
        assert si is None
        assert guid == 'some-guid'

    def test_parse_marked_returns_index(self):
        pid = guid_to_plexio_id('some-guid', server_index=5)
        si, guid = parse_plexio_id(pid)
        assert si == 5
        assert guid == 'some-guid'


class TestDeterminism:
    def test_same_input_same_output(self):
        guid = 'com.plexapp.agents.imdb://tt0111161?lang=en'
        assert guid_to_plexio_id(guid) == guid_to_plexio_id(guid)

    def test_marked_deterministic(self):
        guid = 'plex://movie/abc'
        pid1 = guid_to_plexio_id(guid, server_index=1)
        pid2 = guid_to_plexio_id(guid, server_index=1)
        assert pid1 == pid2

    def test_different_servers_different_ids(self):
        guid = 'plex://movie/abc'
        assert guid_to_plexio_id(guid, server_index=0) != guid_to_plexio_id(
            guid, server_index=1
        )
