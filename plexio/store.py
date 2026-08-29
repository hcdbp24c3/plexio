"""Server-side persistence: settings, secrets and (future) config records.

Plexio keeps the addon configuration in the install URL, but a handful of
server-owned values (the manage password hash, the proxy-token encryption
secret, admin toggles) must survive restarts. This mirrors the SQLite store
used by the reference stremio-jellyfin setup: a ``kv`` table holding
JSON-encoded settings, backed by sqlite3 when a DB path is configured and by
an in-memory dict otherwise.
"""

import json
import logging
import secrets
import sqlite3
import threading
import time

from plexio.settings import settings

logger = logging.getLogger(__name__)

_ID_ALPHABET = 'abcdefghijkmnopqrstuvwxyz023456789'


def random_id(length: int = 12) -> str:
    """Short, URL-safe id (ambiguous chars omitted), like the reference store."""
    return ''.join(secrets.choice(_ID_ALPHABET) for _ in range(length))


class Store:
    def get_setting(self, key: str):
        raise NotImplementedError

    def set_setting(self, key: str, value) -> None:
        raise NotImplementedError

    def delete_setting(self, key: str) -> None:
        raise NotImplementedError

    def get_secret(self) -> str | None:
        raise NotImplementedError

    def set_secret(self, value: str) -> None:
        raise NotImplementedError

    def save_config(self, config: dict, name: str) -> str:
        raise NotImplementedError

    def list_configs(self) -> list[dict]:
        raise NotImplementedError

    def delete_config(self, config_id: str) -> bool:
        raise NotImplementedError


class MemoryStore(Store):
    def __init__(self):
        self._kv: dict[str, str] = {}
        self._configs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def get_setting(self, key: str):
        with self._lock:
            raw = self._kv.get(f'setting:{key}')
        return json.loads(raw) if raw is not None else None

    def set_setting(self, key: str, value) -> None:
        with self._lock:
            self._kv[f'setting:{key}'] = json.dumps(value)

    def delete_setting(self, key: str) -> None:
        with self._lock:
            self._kv.pop(f'setting:{key}', None)

    def get_secret(self) -> str | None:
        with self._lock:
            return self._kv.get('server_secret')

    def set_secret(self, value: str) -> None:
        with self._lock:
            self._kv['server_secret'] = value

    def save_config(self, config: dict, name: str) -> str:
        config_id = random_id()
        with self._lock:
            self._configs[config_id] = {
                'id': config_id,
                'name': name,
                'config': config,
                'created_at': int(time.time()),
            }
        return config_id

    def list_configs(self) -> list[dict]:
        with self._lock:
            return list(self._configs.values())

    def delete_config(self, config_id: str) -> bool:
        with self._lock:
            return self._configs.pop(config_id, None) is not None


class SqliteStore(Store):
    def __init__(self, db_path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA busy_timeout = 5000;
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )

    def _get(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                'SELECT value FROM kv WHERE key = ?', (key,)
            ).fetchone()
        return row['value'] if row else None

    def _set(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                'INSERT INTO kv (key, value) VALUES (?, ?) '
                'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                (key, value),
            )
            self._conn.commit()

    def get_setting(self, key: str):
        raw = self._get(f'setting:{key}')
        return json.loads(raw) if raw is not None else None

    def set_setting(self, key: str, value) -> None:
        self._set(f'setting:{key}', json.dumps(value))

    def delete_setting(self, key: str) -> None:
        with self._lock:
            self._conn.execute('DELETE FROM kv WHERE key = ?', (f'setting:{key}',))
            self._conn.commit()

    def get_secret(self) -> str | None:
        return self._get('server_secret')

    def set_secret(self, value: str) -> None:
        self._set('server_secret', value)

    def save_config(self, config: dict, name: str) -> str:
        config_id = random_id()
        with self._lock:
            self._conn.execute(
                'INSERT INTO configs (id, name, config_json, created_at) '
                'VALUES (?, ?, ?, ?)',
                (config_id, name, json.dumps(config), int(time.time())),
            )
            self._conn.commit()
        return config_id

    def list_configs(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                'SELECT id, name, config_json, created_at FROM configs '
                'ORDER BY created_at'
            ).fetchall()
        return [
            {
                'id': row['id'],
                'name': row['name'],
                'config': json.loads(row['config_json']),
                'created_at': row['created_at'],
            }
            for row in rows
        ]

    def delete_config(self, config_id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                'DELETE FROM configs WHERE id = ?', (config_id,)
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()


_store: Store | None = None


def init_store(db_path: str | None = None) -> Store:
    """Build (or rebuild) the process-wide store. Returns the active store."""
    global _store
    path = db_path if db_path is not None else settings.db_path
    if path and path != ':memory:':
        try:
            _store = SqliteStore(path)
            logger.info('store: sqlite at %s', path)
            return _store
        except Exception:
            logger.exception('store: sqlite unavailable, using memory store')
    _store = MemoryStore()
    return _store


def get_store() -> Store:
    global _store
    if _store is None:
        _store = init_store()
    return _store


def reset_store() -> None:
    """Drop the current store (used by tests)."""
    global _store
    if isinstance(_store, SqliteStore):
        _store.close()
    _store = None


def get_or_create_server_secret() -> str:
    """The AES key material for proxy tokens, persisted across restarts."""
    store = get_store()
    secret = store.get_secret()
    if not secret:
        secret = settings.proxy_secret or secrets.token_hex(32)
        store.set_secret(secret)
    return secret


def get_proxy_enabled() -> bool:
    """Server-wide master switch for the media relay (DB overrides env)."""
    value = get_store().get_setting('proxy_enabled')
    return settings.proxy_enabled if value is None else bool(value)


def get_proxy_admin_only() -> bool:
    """Whether the stream-proxy toggle requires an admin session."""
    value = get_store().get_setting('proxy_admin_only')
    return settings.proxy_admin_only if value is None else bool(value)
