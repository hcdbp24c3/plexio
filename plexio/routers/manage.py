"""Server admin session, protecting only the /admin page.

``MANAGE_KEY`` (env) or a hash stored in the database is the *server* admin
password. It gates the /admin page and the admin-only endpoints in this
router. It never gates the Configure page — each addon configuration has its
own optional password via the /api/v1/access router (see routers/access.py).
Login is rate-limited per IP; mutating admin endpoints require a valid
session.
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


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail='Admin session required')


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


class ChangePasswordBody(BaseModel):
    currentPassword: str
    newPassword: str


@router.post('/password/change')
async def change_password(request: Request, body: ChangePasswordBody):
    """Replace the DB-stored manage password (env MANAGE_KEY wins)."""
    require_admin(request)
    if settings.manage_key:
        raise HTTPException(
            status_code=409,
            detail='The password is managed by the MANAGE_KEY environment variable',
        )
    current = manage_key_hash()
    if current is None:
        raise HTTPException(status_code=409, detail='No password is configured')
    candidate = hashlib.sha256(body.currentPassword.encode()).hexdigest()
    if not secrets.compare_digest(candidate, current):
        raise HTTPException(status_code=401, detail='Current password is wrong')
    if len(body.newPassword) < 8:
        raise HTTPException(
            status_code=422, detail='Password must be at least 8 characters'
        )
    get_store().set_setting(
        'manage_key_hash',
        hashlib.sha256(body.newPassword.encode()).hexdigest(),
    )
    response = Response(status_code=204)
    _set_session(response, manage_key_hash() or '')
    return response


class SettingsBody(BaseModel):
    proxyEnabled: bool | None = None
    proxyAdminOnly: bool | None = None


@router.post('/settings')
async def update_settings(request: Request, body: SettingsBody):
    """Persist server-wide admin toggles."""
    require_admin(request)
    store = get_store()
    if body.proxyEnabled is not None:
        store.set_setting('proxy_enabled', bool(body.proxyEnabled))
    if body.proxyAdminOnly is not None:
        store.set_setting('proxy_admin_only', bool(body.proxyAdminOnly))
    return {
        'proxyEnabled': get_proxy_enabled(),
        'proxyAdminOnly': get_proxy_admin_only(),
    }


def _config_name(config: dict) -> str:
    servers = config.get('servers') or []
    names = [s.get('serverName') for s in servers if s.get('serverName')]
    if not names:
        return 'Unnamed addon'
    head = ', '.join(names[:2])
    return f'{head} +{len(names) - 2}' if len(names) > 2 else head


class SaveConfigBody(BaseModel):
    config: dict
    # The install id from the URL the visitor just saved; preserved across
    # edits so /u/<id> and per-config settings stay stable.
    id: str | None = None


class ProxyBody(BaseModel):
    enabled: bool


@router.post('/configs')
async def save_config(request: Request, body: SaveConfigBody):
    """Record a saved addon configuration (any visitor, their own setup).

    The list endpoint stays admin-only; posting here just lets /u/<id> and
    /admin features know the setup exists.
    """
    config_id = get_store().save_config(body.config, _config_name(body.config), body.id)
    return {'id': config_id}


@router.get('/configs')
async def list_configs(request: Request):
    """Privacy-minimized list of recorded installations."""
    require_admin(request)
    store = get_store()
    return [
        {
            'id': c['id'],
            'name': c['name'],
            'serverCount': len(c['config'].get('servers') or []),
            'createdAt': c['created_at'],
            'proxyOverride': store.get_proxy_override(c['id']),
            'configProxy': bool(c['config'].get('streamProxy')),
        }
        for c in store.list_configs()
    ]


@router.put('/configs/{config_id}/proxy')
async def set_config_proxy(request: Request, config_id: str, body: ProxyBody):
    """Force the media relay on/off for one configuration (admin only)."""
    require_admin(request)
    if get_store().get_config(config_id) is None:
        raise HTTPException(status_code=404, detail='Config not found')
    get_store().set_proxy_override(config_id, body.enabled)
    return {'ok': True, 'proxyOverride': body.enabled}


@router.delete('/configs/{config_id}')
async def delete_config(request: Request, config_id: str):
    require_admin(request)
    if not get_store().delete_config(config_id):
        raise HTTPException(status_code=404, detail='Config not found')
    return Response(status_code=204)
