"""Admin session for the Configure page.

A server operator can protect the Configure page with a password
(``MANAGE_KEY`` env var, or a hash stored in the database). Every /api/v1/manage
endpoint below is open on purpose; the gate it provides is enforced by the
frontend plus the admin-only checks in the addon/proxy routers. Login is
rate-limited per IP.
"""

import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from plexio.security import RateLimiter, client_ip
from plexio.settings import settings
from plexio.store import get_proxy_admin_only, get_proxy_enabled, get_store

router = APIRouter(prefix='/api/v1/manage')

SESSION_TTL = 30 * 24 * 60 * 60

_login_limiter = RateLimiter(max_requests=5)


def manage_key_hash() -> str | None:
    """Hash of the effective manage password, if one is configured."""
    if settings.manage_key:
        return hashlib.sha256(settings.manage_key.encode()).hexdigest()
    return get_store().get_setting('manage_key_hash')


def is_admin(request: Request) -> bool:
    """True when no password is configured or the session cookie is valid."""
    key_hash = manage_key_hash()
    if key_hash is None:
        return True
    cookie = request.cookies.get(settings.manage_cookie_name)
    return bool(cookie) and secrets.compare_digest(cookie, key_hash)


def _clear_session(response: Response) -> None:
    response.delete_cookie(
        settings.manage_cookie_name,
        path='/',
        samesite='lax',
    )


def _set_session(response: Response, key_hash: str) -> None:
    response.set_cookie(
        settings.manage_cookie_name,
        key_hash,
        httponly=True,
        samesite='lax',
        secure=settings.manage_cookie_secure,
        path='/',
        max_age=SESSION_TTL,
    )


@router.get('/status')
async def status(request: Request):
    key_hash = manage_key_hash()
    return {
        'passwordRequired': key_hash is not None,
        'admin': is_admin(request),
        'proxyEnabled': get_proxy_enabled(),
        'proxyAdminOnly': get_proxy_admin_only(),
    }


class LoginBody(BaseModel):
    password: str


@router.post('/login')
async def login(request: Request, body: LoginBody):
    if not _login_limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail='Too many attempts; slow down')
    key_hash = manage_key_hash()
    if key_hash is None:
        raise HTTPException(status_code=409, detail='No password is configured')
    candidate = hashlib.sha256(body.password.encode()).hexdigest()
    if not secrets.compare_digest(candidate, key_hash):
        raise HTTPException(status_code=401, detail='Wrong password')
    response = Response(status_code=204)
    _set_session(response, key_hash)
    return response


@router.post('/logout')
async def logout():
    response = Response(status_code=204)
    _clear_session(response)
    return response


class SetPasswordBody(BaseModel):
    password: str


@router.post('/password')
async def set_password(body: SetPasswordBody):
    """Store the manage password hash (only while none is configured)."""
    if manage_key_hash() is not None:
        raise HTTPException(status_code=409, detail='A password is already configured')
    if len(body.password) < 8:
        raise HTTPException(
            status_code=422, detail='Password must be at least 8 characters'
        )
    get_store().set_setting(
        'manage_key_hash',
        hashlib.sha256(body.password.encode()).hexdigest(),
    )
    return {'ok': True}
