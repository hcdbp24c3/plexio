"""Settings parsing — pydantic-settings 2.0 JSON-decodes env values."""

from plexio.settings import Settings


def test_numeric_manage_key_coerced_to_string():
    """MANAGE_KEY=11042006 arrives as an int; it must become the string."""
    assert Settings(manage_key=11042006).manage_key == '11042006'


def test_none_manage_key_stays_none():
    assert Settings(manage_key=None).manage_key is None


def test_plain_string_manage_key_unchanged():
    assert Settings(manage_key='admin-secret').manage_key == 'admin-secret'
