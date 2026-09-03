"""Per-user setup URLs, mirroring the reference stremio-jellyfin fork.

``/u/<id>`` is a stable, bookmarkable link to one saved configuration — the
install id never changes, so it survives config edits (the base64 token in the
URL changes on every save). The routes redirect to the real install URL, which
still carries the configuration itself; nothing about other setups is exposed.

``/u/<uid>/manifest.json`` can also serve the stored manifest directly from
the DB without a redirect, mirroring the ``/s/<id>`` pattern of the jellyfin
fork.  When the stored config is a valid :class:`AddonConfiguration`, the
manifest is built server-side (200 JSON).  When the config is minimal/legacy
or missing, the handler falls back to the old redirect behaviour so that
existing installs and the ``/u/<id>/configure`` helpers keep working.
"""

import base64
import json

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from plexio import __version__
from plexio.models import PLEX_TO_STREMIO_MEDIA_TYPE
from plexio.models.addon import AddonConfiguration
from plexio.models.stremio import (
    StremioCatalogManifest,
    StremioManifest,
    StremioMediaType,
)
from plexio.plex.media_server_api import SORT_OPTIONS
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


def _build_manifest_from_config(
    configuration: AddonConfiguration | None,
    installation_id: str | None,
) -> StremioManifest:
    catalogs: list[StremioCatalogManifest] = []
    description = 'Play movies and series from plex.tv.'
    name = 'Plexio'

    show_catalogs = configuration is not None and configuration.include_catalogs

    if show_catalogs:
        server_names: list[str] = []
        for idx, server in enumerate(configuration.servers):  # type: ignore[union-attr]
            server_names.append(server.server_name)
            for section in server.sections:
                catalogs.append(
                    StremioCatalogManifest(
                        id=f'{idx}:{section.key}',
                        type=PLEX_TO_STREMIO_MEDIA_TYPE[section.type],
                        name=f'{section.title} | {server.server_name}',
                        extra=[
                            {'name': 'skip', 'isRequired': False},
                            {'name': 'search', 'isRequired': False},
                            {'name': 'sort', 'options': list(SORT_OPTIONS.keys())},
                        ],
                    ),
                )

        joined = ', '.join(server_names)
        if len(joined) + len('Plexio ()') > 60:
            joined = joined[: 60 - len('Plexio (...)') - 1].rstrip(', ') + '...'
        name += f' ({joined})'
        description += f' Your installation ID: {installation_id}'
    elif configuration is not None:
        server_names = [s.server_name for s in configuration.servers]
        joined = ', '.join(server_names)
        if len(joined) + len('Plexio ()') > 60:
            joined = joined[: 60 - len('Plexio (...)') - 1].rstrip(', ') + '...'
        name += f' ({joined})'
        description += f' Your installation ID: {installation_id}'

    resources: list[str | dict] = [
        'stream',
        {
            'name': 'meta',
            'types': ['movie', 'series'],
            'idPrefixes': ['plexio'],
        },
    ]
    if show_catalogs:
        resources.insert(1, 'catalog')

    return StremioManifest(
        id='com.stremio.plexio',
        version=__version__,
        description=description,
        name=name,
        resources=resources,
        types=[StremioMediaType.movie, StremioMediaType.series],
        catalogs=catalogs,
        idPrefixes=['tt', 'plexio'],
        behaviorHints={
            'configurable': True,
            'configurationRequired': configuration is None,
        },
        contactEmail='support@plexio.stream',
    )


@router.get('/u/{config_id}')
@router.get('/u/{config_id}/configure')
async def u_configure(request: Request, config_id: str):
    install = _install_url(request, config_id)
    if install is None:
        return RedirectResponse('/', status_code=302)
    return RedirectResponse(f'{install}/configure', status_code=302)


@router.get('/u/{config_id}/manifest.json', response_model_exclude_none=True)
async def u_manifest(request: Request, config_id: str):
    raw_config = get_store().get_config(config_id)
    if raw_config is None:
        return RedirectResponse('/', status_code=302)

    try:
        configuration = AddonConfiguration(**raw_config)
    except Exception:
        install = _install_url(request, config_id)
        if install is None:
            return RedirectResponse('/', status_code=302)
        return RedirectResponse(f'{install}/manifest.json', status_code=302)

    manifest = _build_manifest_from_config(configuration, config_id)
    return manifest
