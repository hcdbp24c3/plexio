"""Per-configuration access passwords.

Each addon configuration (identified by the token in its install URL) may
carry its own optional password, mirroring the reference stremio-jellyfin
setup: the server admin may add/change/remove any lock outright (password
recovery), everyone else must present the current password. A configuration
without a password stays open. ``MANAGE_KEY`` / the admin hash only ever gate
the /admin page — never the Configure page.

Unlocking is stateless on purpose: POST /login only validates the password
for this render. No cookie is stored, so reloading the Configure page asks
for the password again.
"""

import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from plexio.routers.manage import is_admin
from plexio.security import RateLimiter, client_ip
from plexio.store import get_store

router = APIRouter(prefix='/api/v1/access')

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


class TokenBody(BaseModel):
    token: str


class LoginBody(TokenBody):
    password: str


class AccessPasswordBody(TokenBody):
    password: str
    currentPassword: str | None = None


@router.post('/status')
async def access_status(body: TokenBody):
    return {'passwordRequired': access_hash_for(body.token) is not None}


@router.post('/login')
async def access_login(request: Request, body: LoginBody):
    """Validate the config password for this page load. No session is kept."""
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
    return Response(status_code=204)


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
