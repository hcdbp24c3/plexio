"""Per-configuration access passwords.

Each addon configuration (identified by the token in its install URL) may
carry its own optional password, mirroring the reference stremio-jellyfin
setup: the server admin may add/change/remove any lock outright (password
recovery), everyone else must present the current password. A configuration
without a password stays open. ``MANAGE_KEY`` / the admin hash only ever gate
the /admin page — never the Configure page.
"""

import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from plexio.routers.manage import is_admin
from plexio.security import RateLimiter, client_ip
from plexio.settings import settings
from plexio.store import get_store

router = APIRouter(prefix='/api/v1/access')

SESSION_TTL = 30 * 24 * 60 * 60
MAX_PASSWORD_LEN = 128

_login_limiter = RateLimiter(max_requests=5)


def _kv_key(token: str) -> str:
    """Store key for a token's access hash (short, no credentials in it)."""
    return f'acc:{hashlib.sha256(token.encode()).hexdigest()}'


def access_hash_for(token: str) -> str | None:
    return get_store().get_setting(_kv_key(token))


def _access_hash(token: str, password: str) -> str:
    """Hash salted with the token, like the reference fork's acc:<id>."""
    return hashlib.sha256(f'{token}:{password}'.encode()).hexdigest()


def access_cookie_name(token: str) -> str:
    digest = hashlib.sha256(token.encode()).hexdigest()[:16]
    return f'plexio_access_{digest}'


def is_unlocked(request: Request, token: str) -> bool:
    """True for an open config or a valid unlock cookie.

    Like the reference fork's edit gate, a locked configuration requires its
    own password from everyone — the admin session included. Password
    recovery (changing a lock without the current password) happens through
    POST /password instead.
    """
    expected = access_hash_for(token)
    if expected is None:
        return True
    cookie = request.cookies.get(access_cookie_name(token))
    return bool(cookie) and secrets.compare_digest(cookie, expected)


def _set_access_cookie(response: Response, token: str, value: str) -> None:
    response.set_cookie(
        access_cookie_name(token),
        value,
        max_age=SESSION_TTL,
        httponly=True,
        samesite='lax',
        secure=settings.manage_cookie_secure,
        path='/',
    )


class TokenBody(BaseModel):
    token: str


class LoginBody(TokenBody):
    password: str


class AccessPasswordBody(TokenBody):
    password: str
    currentPassword: str | None = None


@router.post('/status')
async def access_status(body: TokenBody, request: Request):
    expected = access_hash_for(body.token)
    return {
        'passwordRequired': expected is not None,
        'unlocked': is_unlocked(request, body.token),
    }


@router.post('/login')
async def access_login(request: Request, response: Response, body: LoginBody):
    expected = access_hash_for(body.token)
    if expected is None:
        raise HTTPException(
            status_code=409, detail='This configuration has no password'
        )
    if not _login_limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail='Too many attempts')
    candidate = _access_hash(body.token, body.password)
    if not secrets.compare_digest(candidate, expected):
        raise HTTPException(status_code=401, detail='Wrong password')
    response.status_code = 204
    _set_access_cookie(response, body.token, expected)
    return response


@router.post('/logout')
async def access_logout(body: TokenBody, response: Response):
    response.status_code = 204
    response.delete_cookie(access_cookie_name(body.token), path='/')
    return response


@router.post('/password')
async def set_access_password(body: AccessPasswordBody, request: Request):
    """Add, change or remove a configuration's password.

    Rules mirror the reference fork: the server admin may change or remove
    any lock outright; anyone else must present the current password. An
    empty password removes the lock; adding the first lock is allowed to
    whoever holds the (secret) install link.
    """
    if len(body.password) > MAX_PASSWORD_LEN:
        raise HTTPException(status_code=422, detail='Password too long')
    current = access_hash_for(body.token)
    if current is not None and not is_admin(request):
        supplied = _access_hash(body.token, body.currentPassword or '')
        if not secrets.compare_digest(supplied, current):
            raise HTTPException(status_code=401, detail='Current password required')
    store = get_store()
    if body.password:
        store.set_setting(_kv_key(body.token), _access_hash(body.token, body.password))
    else:
        store.delete_setting(_kv_key(body.token))
    return {'ok': True, 'passwordRequired': bool(body.password)}
