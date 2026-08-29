import secrets

from pydantic_settings import BaseSettings

from plexio.cache import CacheType


class Settings(BaseSettings):
    cors_origin_regex: str = (
        r'https?:\/\/localhost:\d+|.*plexio.stream|.*strem.io|.*stremio.com'
    )
    plex_requests_timeout: int = 20
    cache_type: CacheType = CacheType.memory
    redis_url: str = 'redis://redis:6399/0'
    plex_matching_token: str | None = None
    # Opaque stream-proxy tokens are encrypted with this secret. Set it to a
    # stable value (e.g. `openssl rand -hex 32`) so proxy URLs survive
    # restarts; otherwise one is generated per process.
    proxy_secret: str = secrets.token_hex(32)
    # How long a minted proxy token stays valid, in seconds.
    proxy_token_ttl: int = 48 * 60 * 60
    # Force the base URL used for stream/poster proxy links (useful behind
    # reverse proxies that rewrite the Host header). Falls back to the
    # request's own origin.
    addon_base_url: str | None = None
    # SQLite file for server-owned settings (manage password hash, proxy-token
    # secret, admin toggles). ':memory:' keeps everything in-process, which is
    # fine for tests but drops persisted state on restart.
    db_path: str = ':memory:'
    # Password protecting the Configure page. When set, an admin session
    # (HttpOnly cookie) is required to view the form; leave empty to keep the
    # page open. Takes precedence over a hash stored in the database.
    manage_key: str | None = None
    # Server-wide master switch for the media relay. When off, the proxy
    # refuses every request regardless of what a config asks for.
    proxy_enabled: bool = True
    # When true, the stream-proxy toggle only appears for admin sessions.
    proxy_admin_only: bool = True
    # Admin session cookie name.
    manage_cookie_name: str = 'plexio_manage'
    # Mark the admin cookie Secure (send over HTTPS only).
    manage_cookie_secure: bool = True


settings = Settings()
