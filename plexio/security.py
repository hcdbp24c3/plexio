"""Security helpers: opaque proxy tokens, SSRF guards and a per-IP limiter.

The addon is stateless by design (the whole configuration travels inside the
install URL), so "hide the Plex origin" has to be done without server-side
state. We mint short-lived AES-256-GCM tokens that carry the upstream Plex
URL; the client only ever sees an opaque blob.
"""

import base64
import hashlib
import ipaddress
import json
import secrets
import time
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from plexio.settings import settings

PROXY_TOKEN_TTL = settings.proxy_token_ttl

# Cloud/link-local metadata endpoints that a public addon must never be
# abused to reach (SSRF). LAN targets stay legitimate for self-hosters.
BLOCKED_TARGET_HOSTS = (
    'localhost',
    'metadata.google.internal',
    '169.254.169.254',
)


def _aes_key() -> bytes:
    return hashlib.sha256(settings.proxy_secret.encode()).digest()


def encrypt_payload(data: bytes) -> str:
    iv = secrets.token_bytes(12)
    ct = AESGCM(_aes_key()).encrypt(iv, data, None)
    return base64.urlsafe_b64encode(iv + ct).rstrip(b'=').decode()


def decrypt_payload(token: str) -> bytes | None:
    try:
        encoded = token.encode()
        encoded += b'=' * (-len(encoded) % 4)
        raw = base64.urlsafe_b64decode(encoded)
        iv, ct = raw[:12], raw[12:]
        return AESGCM(_aes_key()).decrypt(iv, ct, None)
    except Exception:
        return None


def mint_proxy_token(plex_url: str, *, ttl: int | None = None) -> str:
    """Encrypt a full Plex URL into an opaque, expiring proxy token."""
    if ttl is None:
        ttl = PROXY_TOKEN_TTL
    payload = json.dumps({'u': plex_url, 'e': int(time.time()) + ttl}).encode()
    return encrypt_payload(payload)


def unmint_proxy_token(token: str) -> str | None:
    """Return the Plex URL behind a proxy token, or ``None`` if invalid/expired."""
    payload = decrypt_payload(token)
    if payload is None:
        return None
    try:
        data = json.loads(payload)
        if data.get('e', 0) < time.time():
            return None
        url = data.get('u')
        if not isinstance(url, str) or not url.startswith('http'):
            return None
        return url
    except (ValueError, TypeError):
        return None


def blocked_target_url(url: str) -> bool:
    """True when ``url`` points at a host the addon must never fetch."""
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return True
    if not host:
        return True
    host = host.rstrip('.').lower()
    if host in BLOCKED_TARGET_HOSTS or host.endswith('.internal'):
        return True
    if host.startswith('169.254.'):
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    if (
        addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_loopback
        or addr.is_unspecified
    ):
        return True
    return False


class RateLimiter:
    """Minimal per-IP sliding-window limiter (no external dependencies)."""

    def __init__(self, *, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = [t for t in self._hits.get(key, []) if t > window_start]
        if len(hits) >= self.max_requests:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        if len(self._hits) > 10000:
            stale = [
                k for k, v in self._hits.items() if not any(t > window_start for t in v)
            ]
            for k in stale:
                self._hits.pop(k, None)
        return True


def client_ip(request) -> str:
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else 'unknown'
