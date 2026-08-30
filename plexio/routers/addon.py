import asyncio
from itertools import chain
from typing import Annotated

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio.client import Redis

from plexio import __version__
from plexio.dependencies import (
    get_addon_configuration,
    get_cache,
    get_http_client,
    set_sentry_user,
)
from plexio.models import PLEX_TO_STREMIO_MEDIA_TYPE, STREMIO_TO_PLEX_MEDIA_TYPE
from plexio.models.addon import AddonConfiguration, ServerConfiguration
from plexio.models.stremio import (
    StremioCatalog,
    StremioCatalogManifest,
    StremioManifest,
    StremioMediaType,
    StremioMetaResponse,
    StremioStreamsResponse,
)
from plexio.models.utils import parse_plexio_id
from plexio.plex.media_server_api import (
    SORT_OPTIONS,
    get_all_episodes,
    get_media,
    get_section_media,
    stremio_to_plex_id,
)
from plexio.settings import settings
from plexio.store import effective_stream_proxy

router = APIRouter()
router.dependencies.append(Depends(set_sentry_user))


def _proxy_base(request: Request) -> str | None:
    if settings.addon_base_url:
        return settings.addon_base_url.rstrip('/')
    return str(request.base_url).rstrip('/')


async def _gather_media(
    client: ClientSession,
    servers: list[ServerConfiguration],
    guid: str,
) -> list[tuple[ServerConfiguration, object]]:
    """Fire get_media on every server concurrently; return (server, meta) pairs."""

    async def _fetch(server: ServerConfiguration):
        return await get_media(
            client=client,
            url=server.discovery_url,
            token=server.access_token,
            guid=guid,
        )

    results = await asyncio.gather(
        *[_fetch(s) for s in servers],
        return_exceptions=True,
    )
    pairs: list[tuple[ServerConfiguration, object]] = []
    for server, result in zip(servers, results, strict=True):
        if isinstance(result, BaseException):
            continue
        for meta in result:
            pairs.append((server, meta))
    return pairs


def _streams_from_pairs(
    pairs: list[tuple[ServerConfiguration, object]],
    configuration: AddonConfiguration,
    *,
    proxy_base: str | None = None,
    installation_id: str | None = None,
) -> list:
    """Build stremio streams from (server, meta) pairs."""
    return [
        s
        for server, meta in pairs
        for s in meta.get_stremio_streams(
            server,
            configuration,
            proxy_base=proxy_base,
            installation_id=installation_id,
        )
    ]


@router.get('/manifest.json', response_model_exclude_none=True)
@router.get(
    '/{installation_id}/{base64_cfg}/manifest.json', response_model_exclude_none=True
)
async def get_manifest(
    configuration: Annotated[
        AddonConfiguration | None,
        Depends(get_addon_configuration),
    ],
    installation_id: str | None = None,
) -> StremioManifest:
    catalogs = []
    description = 'Play movies and series from plex.tv.'
    name = 'Plexio'

    show_catalogs = configuration is not None and configuration.include_catalogs

    if show_catalogs:
        server_names = []
        for idx, server in enumerate(configuration.servers):
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


@router.get(
    '/{installation_id}/{base64_cfg}/catalog/{stremio_type}/{catalog_id}.json',
    response_model_exclude_none=True,
)
@router.get(
    '/{installation_id}/{base64_cfg}/catalog/{stremio_type}/{catalog_id}/{extra}.json',
    response_model_exclude_none=True,
)
async def get_catalog(
    request: Request,
    http: Annotated[ClientSession, Depends(get_http_client)],
    configuration: Annotated[AddonConfiguration, Depends(get_addon_configuration)],
    stremio_type: StremioMediaType,
    catalog_id: str,
    extra: str = '',
    installation_id: str | None = None,
) -> StremioCatalog:
    if not configuration.include_catalogs:
        return StremioCatalog(metas=[])

    parts = catalog_id.split(':', maxsplit=1)
    if len(parts) == 2 and parts[0].isdigit():
        server_index = int(parts[0])
        section_key = parts[1]
    else:
        server_index = 0
        section_key = catalog_id

    if server_index < 0 or server_index >= len(configuration.servers):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    server = configuration.servers[server_index]

    extras = dict(e.split('=') for e in extra.split('&') if e)
    media = await get_section_media(
        client=http,
        url=server.discovery_url,
        token=server.access_token,
        section_id=section_key,
        search=extras.get('search', ''),
        skip=extras.get('skip', 0),
        sort=extras.get('sort', 'Title'),
    )
    proxy_base = _proxy_base(request)
    return StremioCatalog(
        metas=[
            m.to_stremio_meta_review(
                server,
                server_index=server_index,
                stream_proxy=effective_stream_proxy(configuration, installation_id),
                proxy_base=proxy_base,
            )
            for m in media
        ],
    )


@router.get(
    '/{installation_id}/{base64_cfg}/meta/{stremio_type}/{plex_id:path}.json',
    response_model_exclude_none=True,
)
async def get_meta(
    request: Request,
    http: Annotated[ClientSession, Depends(get_http_client)],
    configuration: Annotated[AddonConfiguration, Depends(get_addon_configuration)],
    stremio_type: StremioMediaType,
    plex_id: str,
    installation_id: str | None = None,
) -> StremioMetaResponse:
    if not plex_id.startswith('plexio:'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    server_index, guid = parse_plexio_id(plex_id)
    proxy_base = _proxy_base(request)
    stream_proxy = effective_stream_proxy(configuration, installation_id)

    # Determined server: query only that server
    if server_index is not None and 0 <= server_index < len(configuration.servers):
        server = configuration.servers[server_index]
        media = await get_media(
            client=http,
            url=server.discovery_url,
            token=server.access_token,
            guid=guid,
            get_only_first=True,
        )
        if media:
            meta = media[0].to_stremio_meta(
                server,
                server_index=server_index,
                stream_proxy=stream_proxy,
                proxy_base=proxy_base,
            )
            if stremio_type == StremioMediaType.series:
                episodes = await get_all_episodes(
                    client=http,
                    url=server.discovery_url,
                    token=server.access_token,
                    key=media[0].key,
                )
                meta.videos = [
                    e.to_stremio_video_meta(
                        server,
                        server_index=server_index,
                        stream_proxy=stream_proxy,
                        proxy_base=proxy_base,
                    )
                    for e in episodes
                ]
            return StremioMetaResponse(meta=meta)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Legacy / unresolvable marker: probe all servers in parallel
    async def _fetch(server: ServerConfiguration, idx: int):
        return idx, await get_media(
            client=http,
            url=server.discovery_url,
            token=server.access_token,
            guid=guid,
            get_only_first=True,
        )

    results = await asyncio.gather(
        *[_fetch(s, i) for i, s in enumerate(configuration.servers)],
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, BaseException):
            continue
        idx, media = result
        if media:
            server = configuration.servers[idx]
            meta = media[0].to_stremio_meta(
                server,
                server_index=idx,
                stream_proxy=stream_proxy,
                proxy_base=proxy_base,
            )
            if stremio_type == StremioMediaType.series:
                episodes = await get_all_episodes(
                    client=http,
                    url=server.discovery_url,
                    token=server.access_token,
                    key=media[0].key,
                )
                meta.videos = [
                    e.to_stremio_video_meta(
                        server,
                        server_index=idx,
                        stream_proxy=stream_proxy,
                        proxy_base=proxy_base,
                    )
                    for e in episodes
                ]
            return StremioMetaResponse(meta=meta)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def _resolve_tt_to_plex_id(
    *,
    client: ClientSession,
    cache: Redis,
    stremio_id: str,
    stremio_type: StremioMediaType,
    servers: list[ServerConfiguration],
) -> str | None:
    """Resolve a stremio tt-ID to a plex GUID by probing all servers in parallel."""

    async def _fetch(server: ServerConfiguration):
        return await stremio_to_plex_id(
            client=client,
            url=server.discovery_url,
            token=server.access_token,
            cache=cache,
            stremio_id=stremio_id,
            media_type=STREMIO_TO_PLEX_MEDIA_TYPE[stremio_type],
        )

    results = await asyncio.gather(
        *[_fetch(s) for s in servers],
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, BaseException):
            continue
        if result:
            return result
    return None


@router.get(
    '/{installation_id}/{base64_cfg}/stream/{stremio_type}/{media_id:path}.json',
    response_model_exclude_none=True,
)
async def get_stream(
    request: Request,
    http: Annotated[ClientSession, Depends(get_http_client)],
    cache: Annotated[Redis, Depends(get_cache)],
    configuration: Annotated[AddonConfiguration, Depends(get_addon_configuration)],
    stremio_type: StremioMediaType,
    media_id: str,
    installation_id: str | None = None,
) -> StremioStreamsResponse:
    servers = configuration.servers
    proxy_base = _proxy_base(request)

    if media_id.startswith('tt'):
        plex_id = await _resolve_tt_to_plex_id(
            client=http,
            cache=cache,
            stremio_id=media_id,
            stremio_type=stremio_type,
            servers=servers,
        )
        if not plex_id:
            return StremioStreamsResponse()

        pairs = await _gather_media(http, servers, plex_id)
        streams = _streams_from_pairs(
            pairs, configuration, proxy_base=proxy_base, installation_id=installation_id
        )
        return StremioStreamsResponse(streams=streams)

    if media_id.startswith('plexio:'):
        server_index, guid = parse_plexio_id(media_id)

        if server_index is not None and 0 <= server_index < len(servers):
            server = servers[server_index]
            media = await get_media(
                client=http,
                url=server.discovery_url,
                token=server.access_token,
                guid=guid,
            )
            return StremioStreamsResponse(
                streams=chain.from_iterable(
                    meta.get_stremio_streams(
                        server,
                        configuration,
                        proxy_base=proxy_base,
                        installation_id=installation_id,
                    )
                    for meta in media
                ),
            )

        # Fallback: probe all servers in parallel
        pairs = await _gather_media(http, servers, guid)
        streams = _streams_from_pairs(
            pairs, configuration, proxy_base=proxy_base, installation_id=installation_id
        )
        return StremioStreamsResponse(streams=streams)

    # Raw ID: get_media on every server, merged in parallel
    pairs = await _gather_media(http, servers, media_id)
    streams = _streams_from_pairs(
        pairs, configuration, proxy_base=proxy_base, installation_id=installation_id
    )
    return StremioStreamsResponse(streams=streams)
