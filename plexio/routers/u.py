"""Per-user setup URLs, mirroring the reference stremio-jellyfin fork.

``/u/<id>`` is a stable, bookmarkable link to one saved configuration — the
install id never changes, so it survives config edits (the base64 token in the
URL changes on every save). The routes redirect to the real install URL, which
still carries the configuration itself; nothing about other setups is exposed.
"""

import base64
import json

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from plexio.store import get_store

router = APIRouter()


def _encode_config(config: dict) -> str:
    raw = json.dumps(config, separators=(',', ':')).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def _install_url(request: Request, config_id: str) -> str | None:
    config = get_store().get_config(config_id)
    if config is None:
        return None
    return f'{str(request.base_url).rstrip("/")}/{config_id}/{_encode_config(config)}'


@router.get('/u/{config_id}')
@router.get('/u/{config_id}/configure')
async def u_configure(request: Request, config_id: str):
    install = _install_url(request, config_id)
    if install is None:
        return RedirectResponse('/', status_code=302)
    return RedirectResponse(f'{install}/configure', status_code=302)


@router.get('/u/{config_id}/manifest.json')
async def u_manifest(request: Request, config_id: str):
    install = _install_url(request, config_id)
    if install is None:
        return RedirectResponse('/', status_code=302)
    return RedirectResponse(f'{install}/manifest.json', status_code=302)
