import pytest
from pydantic import ValidationError

from plexio.models.addon import AddonConfiguration


def _legacy_dict(**overrides):
    base = {
        'accessToken': 'tok-abc',
        'discoveryUrl': 'https://disco.example.com',
        'streamingUrl': 'https://stream.example.com',
        'serverName': 'My Server',
        'sections': [{'key': '1', 'title': 'Movies', 'type': 'movie'}],
    }
    base.update(overrides)
    return base


def _new_dict(*, servers=None, **overrides):
    if servers is None:
        servers = [
            {
                'accessToken': 'tok-1',
                'discoveryUrl': 'https://s1.example.com',
                'streamingUrl': 'https://s1-stream.example.com',
                'serverName': 'Server A',
                'sections': [{'key': '1', 'title': 'Movies', 'type': 'movie'}],
            }
        ]
    base = {'servers': servers}
    base.update(overrides)
    return base


class TestLegacyFlatConfig:
    def test_wraps_into_servers(self):
        cfg = AddonConfiguration(**_legacy_dict())
        assert len(cfg.servers) == 1
        assert cfg.servers[0].access_token == 'tok-abc'

    def test_all_fields_mapped(self):
        cfg = AddonConfiguration(**_legacy_dict())
        s = cfg.servers[0]
        assert str(s.discovery_url) == 'https://disco.example.com'
        assert str(s.streaming_url) == 'https://stream.example.com'
        assert s.server_name == 'My Server'
        assert len(s.sections) == 1
        assert s.sections[0].key == '1'

    def test_url_coercion_from_string(self):
        cfg = AddonConfiguration(**_legacy_dict())
        assert cfg.servers[0].discovery_url.__class__.__name__ == 'URL'

    def test_transcode_flags_at_top_level(self):
        cfg = AddonConfiguration(
            **_legacy_dict(
                includeTranscodeOriginal=True,
                includeTranscodeDown=True,
                transcodeDownQualities=['720p'],
            )
        )
        assert cfg.include_transcode_original is True
        assert cfg.include_transcode_down is True
        assert len(cfg.transcode_down_qualities) == 1

    def test_version_preserved(self):
        cfg = AddonConfiguration(**_legacy_dict(version='1.2.3'))
        assert cfg.version == '1.2.3'

    def test_default_values(self):
        cfg = AddonConfiguration(**_legacy_dict())
        assert cfg.include_transcode_original is False
        assert cfg.include_transcode_down is False
        assert cfg.transcode_down_qualities == []
        assert cfg.include_plex_tv is False
        assert cfg.version == '0.0.1'


class TestNewMultiServerConfig:
    def test_single_server(self):
        cfg = AddonConfiguration(**_new_dict())
        assert len(cfg.servers) == 1
        assert cfg.servers[0].access_token == 'tok-1'

    def test_two_servers(self):
        servers = [
            {
                'accessToken': 'tok-a',
                'discoveryUrl': 'https://a.example.com',
                'streamingUrl': 'https://a-stream.example.com',
                'serverName': 'Server A',
                'sections': [
                    {'key': '1', 'title': 'Movies', 'type': 'movie'},
                    {'key': '2', 'title': 'TV', 'type': 'show'},
                ],
            },
            {
                'accessToken': 'tok-b',
                'discoveryUrl': 'https://b.example.com',
                'streamingUrl': 'https://b-stream.example.com',
                'serverName': 'Server B',
                'sections': [{'key': '3', 'title': 'Music', 'type': 'movie'}],
            },
        ]
        cfg = AddonConfiguration(**_new_dict(servers=servers))
        assert len(cfg.servers) == 2
        assert cfg.servers[0].server_name == 'Server A'
        assert cfg.servers[1].server_name == 'Server B'
        assert len(cfg.servers[0].sections) == 2
        assert len(cfg.servers[1].sections) == 1

    def test_servers_min_length_enforced(self):
        with pytest.raises(ValidationError):
            AddonConfiguration(**_new_dict(servers=[]))


class TestMissingConfig:
    def test_neither_servers_nor_legacy_fields(self):
        with pytest.raises(ValidationError):
            AddonConfiguration(**{'foo': 'bar'})
