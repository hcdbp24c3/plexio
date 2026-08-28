from typing import Annotated

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException
from yarl import URL

from plexio.dependencies import get_http_client
from plexio.plex.media_server_api import check_server_connection, get_library_sections
from plexio.security import blocked_target_url

router = APIRouter(prefix='/api/v1')


def _assert_safe_target(url: str) -> None:
    if blocked_target_url(url):
        raise HTTPException(
            status_code=400,
            detail='This target host is not allowed',
        )


@router.get('/test-connection')
async def test_connection(
    http: Annotated[ClientSession, Depends(get_http_client)],
    url: str,
    token: str,
):
    _assert_safe_target(url)
    success = await check_server_connection(
        client=http,
        url=URL(url),
        token=token,
    )
    return {'success': success}


@router.get('/sections')
async def sections(
    http: Annotated[ClientSession, Depends(get_http_client)],
    url: str,
    token: str,
):
    _assert_safe_target(url)
    try:
        library_sections = await get_library_sections(
            client=http,
            url=URL(url),
            token=token,
        )
    except Exception:
        return {'sections': []}
    return {
        'sections': [
            {
                'key': s.key,
                'title': s.title,
                'type': s.type,
            }
            for s in library_sections
        ],
    }
