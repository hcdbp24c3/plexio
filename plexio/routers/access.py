"""Per-configuration access passwords.

Each addon setup (identified by its installation id, the first segment of the
install URL) may carry its own optional password, mirroring the reference
stremio-jellyfin setup: the server admin may add/change/remove any lock
outright (password recovery), everyone else must present the current
password. A setup without a password stays open. ``MANAGE_KEY`` / the admin
hash only ever gate the /admin page — never the Configure page.

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


def _kv_key(config_id: str) -> str:
    """Store key for a setup's access hash, keyed by its install id."""
    return f'acc:{config_id}'


def access_hash_for(config_id: str) -> str | None:
    return get_store().get_setting(_kv_key(config_id))


def _access_hash(config_id: str, password: str) -> str:
    """Hash salted with the id, like the reference fork's acc:<id>."""
    return hashlib.sha256(f'{config_id}:{password}'.encode()).hexdigest()


class IdBody(BaseModel):
    id: str


class LoginBody(IdBody):
    password: str


class AccessPasswordBody(IdBody):
    password: str
    currentPassword: str | None = None


@router.post('/status')
async def access_status(body: IdBody):
    return {'passwordRequired': access_hash_for(body.id) is not None}


@router.post('/login')
async def access_login(request: Request, body: LoginBody):
    """Validate the setup password for this page load. No session is kept."""
    expected = access_hash_for(body.id)
    if expected is None:
        raise HTTPException(
            status_code=409, detail='This configuration has no password'
        )
    if not _login_limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail='Too many attempts')
    candidate = _access_hash(body.id, body.password)
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
    current = access_hash_for(body.id)
    if current is not None and not is_admin(request):
        supplied = _access_hash(body.id, body.currentPassword or '')
        if not secrets.compare_digest(supplied, current):
            raise HTTPException(status_code=401, detail='Current password required')
    store = get_store()
    if body.password:
        store.set_setting(_kv_key(body.id), _access_hash(body.id, body.password))
    else:
        store.delete_setting(_kv_key(body.id))
    return {'ok': True, 'passwordRequired': bool(body.password)}
