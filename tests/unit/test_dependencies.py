import base64
import json

from plexio.dependencies import decode_base64_cfg, get_addon_configuration
from plexio.models.addon import AddonConfiguration

CONFIG = {
    'servers': [
        {
            'accessToken': 'tok+1/2',
            'discoveryUrl': 'https://disco.example.com',
            'streamingUrl': 'https://stream.example.com',
            'serverName': 'My Server',
            'sections': [{'key': '1', 'title': 'Movies', 'type': 'movie'}],
        }
    ],
    'includeCatalogs': True,
}


class TestDecodeBase64Cfg:
    def test_url_safe_token_without_padding(self):
        token = base64.urlsafe_b64encode(json.dumps(CONFIG).encode()).rstrip(b'=')
        assert decode_base64_cfg(token.decode()) == json.dumps(CONFIG)

    def test_legacy_standard_token_with_padding(self):
        # Old installs used standard base64, which can contain + and /.
        token = base64.b64encode(json.dumps(CONFIG).encode())
        assert decode_base64_cfg(token.decode()) == json.dumps(CONFIG)

    def test_legacy_url_safe_with_padding(self):
        token = base64.urlsafe_b64encode(json.dumps(CONFIG).encode())
        assert decode_base64_cfg(token.decode()) == json.dumps(CONFIG)

    def test_token_with_plus_and_slash_decodes(self):
        # U+083E U+083F → UTF-8 bytes E0 A0 BE E0 A0 BF → base64 '4KC+4KC/',
        # which exercises the '+' and '/' characters of the standard alphabet.
        payload = '\u083e\u083f'
        token = base64.b64encode(payload.encode()).decode()
        assert '+' in token and '/' in token
        assert decode_base64_cfg(token) == payload

    def test_short_token_gets_padding_restored(self):
        # 10 bytes → base64 of length 14, which is not a multiple of 4.
        payload = '{"a":"bc"}'
        token = base64.urlsafe_b64encode(payload.encode()).rstrip(b'=').decode()
        assert len(token) % 4 == 2
        assert decode_base64_cfg(token) == payload


class TestGetAddonConfiguration:
    def test_none_returns_none(self):
        assert get_addon_configuration(None) is None

    def test_roundtrip_url_safe(self):
        token = (
            base64.urlsafe_b64encode(json.dumps(CONFIG).encode()).rstrip(b'=').decode()
        )
        cfg = get_addon_configuration(token)
        assert isinstance(cfg, AddonConfiguration)
        assert cfg.servers[0].access_token == 'tok+1/2'

    def test_roundtrip_legacy_standard(self):
        token = base64.b64encode(json.dumps(CONFIG).encode()).decode()
        cfg = get_addon_configuration(token)
        assert cfg.include_catalogs is True
