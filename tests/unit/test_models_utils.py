import pytest

from plexio.models.utils import guid_to_plexio_id, plexio_id_to_guid


@pytest.mark.parametrize(
    'guid',
    [
        'com.plexapp.agents.imdb://tt0111161?lang=en',
        'com.plexapp.agents.imdb://tt0111161?lang=\U0001f30d',
        'path/with:colons and spaces',
        'a',
        '',
        'plex://movie/5d7768461972a8001ec8544f',
        'com.plexapp.agents.themoviedb://550?lang=en',
    ],
)
def test_roundtrip(guid):
    plexio_id = guid_to_plexio_id(guid)
    assert plexio_id.startswith('plexio:')
    assert plexio_id_to_guid(plexio_id) == guid


def test_determinism():
    guid = 'com.plexapp.agents.imdb://tt0111161?lang=en'
    first_id = guid_to_plexio_id(guid)
    second_id = guid_to_plexio_id(guid)
    assert first_id == second_id
    assert plexio_id_to_guid(first_id) == plexio_id_to_guid(second_id)


def test_padding_various_lengths():
    """Roundtrip handles all valid base64 padding cases (len % 4 in {0, 2, 3})."""
    inputs = [
        'abc',  # 3 bytes -> no base64 padding stripped -> len%4 = 0
        'abcd',  # 4 bytes -> 2 padding stripped -> len%4 = 2
        'abcde',  # 5 bytes -> 1 padding stripped -> len%4 = 3
        'abcdef',  # 6 bytes -> no padding stripped -> len%4 = 0
        'abcdefgh',  # 8 bytes -> 2 padding stripped -> len%4 = 2
    ]
    for guid in inputs:
        encoded = guid_to_plexio_id(guid)
        assert encoded.startswith('plexio:')
        assert plexio_id_to_guid(encoded) == guid
