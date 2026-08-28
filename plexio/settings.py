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


settings = Settings()
