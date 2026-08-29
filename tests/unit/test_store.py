import pytest

from plexio import store as store_module
from plexio.settings import settings
from plexio.store import (
    SqliteStore,
    get_or_create_server_secret,
    get_proxy_admin_only,
    get_proxy_enabled,
    reset_store,
)


@pytest.fixture(autouse=True)
def fresh_store():
    reset_store()
    yield
    reset_store()


class TestMemoryStore:
    def test_settings_roundtrip(self):
        st = store_module.init_store(':memory:')
        assert st.get_setting('foo') is None
        st.set_setting('foo', {'a': 1})
        assert st.get_setting('foo') == {'a': 1}
        st.delete_setting('foo')
        assert st.get_setting('foo') is None

    def test_server_secret_roundtrip(self):
        st = store_module.init_store(':memory:')
        st.set_secret('s3cr3t')
        assert st.get_secret() == 's3cr3t'


class TestSqliteStore:
    def test_settings_survive_reopen(self, tmp_path):
        db = tmp_path / 'plexio.db'
        st = SqliteStore(str(db))
        st.set_setting('proxy_enabled', False)
        st.set_secret('persisted-secret')

        reopened = SqliteStore(str(db))
        assert reopened.get_setting('proxy_enabled') is False
        assert reopened.get_secret() == 'persisted-secret'

    def test_delete_setting(self, tmp_path):
        db = tmp_path / 'plexio.db'
        st = SqliteStore(str(db))
        st.set_setting('k', 1)
        st.delete_setting('k')
        assert st.get_setting('k') is None

    def test_configs_survive_reopen(self, tmp_path):
        db = tmp_path / 'plexio.db'
        st = SqliteStore(str(db))
        config_id = st.save_config({'servers': [{'serverName': 'A'}]}, 'A')
        assert st.delete_config('missing-id') is False

        reopened = SqliteStore(str(db))
        items = reopened.list_configs()
        assert len(items) == 1
        assert items[0]['id'] == config_id
        assert items[0]['name'] == 'A'
        assert items[0]['config']['servers'][0]['serverName'] == 'A'
        assert reopened.delete_config(config_id) is True
        assert reopened.list_configs() == []


class TestMemoryStoreConfigs:
    def test_save_list_delete(self):
        st = store_module.init_store(':memory:')
        first = st.save_config({'servers': []}, 'One')
        second = st.save_config({'servers': []}, 'Two')
        assert first != second
        names = {c['name'] for c in st.list_configs()}
        assert names == {'One', 'Two'}
        assert st.delete_config(first) is True
        assert st.delete_config(first) is False


class TestStoreHelpers:
    def test_get_or_create_server_secret_persists(self):
        first = get_or_create_server_secret()
        second = get_or_create_server_secret()
        assert first == second
        assert len(first) == 64

    def test_get_or_create_uses_settings_secret(self, monkeypatch):
        monkeypatch.setattr(settings, 'proxy_secret', 'configured-secret')
        assert get_or_create_server_secret() == 'configured-secret'

    def test_proxy_enabled_defaults_to_settings(self, monkeypatch):
        monkeypatch.setattr(settings, 'proxy_enabled', True)
        assert get_proxy_enabled() is True

    def test_proxy_enabled_db_override(self):
        store_module.get_store().set_setting('proxy_enabled', False)
        assert get_proxy_enabled() is False

    def test_proxy_admin_only_defaults_to_settings(self, monkeypatch):
        monkeypatch.setattr(settings, 'proxy_admin_only', True)
        assert get_proxy_admin_only() is True
