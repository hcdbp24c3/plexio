import re
from typing import Annotated
from urllib.parse import urljoin

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from plexio.dependencies import get_http_client
from plexio.security import mint_proxy_token, unmint_proxy_token
from plexio.settings import settings

router = APIRouter()

# Forward these hop-by-hop-ish headers from the upstream response so range
# requests (seeking) keep working through the relay.
_PROXIED_HEADERS = ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges')
_CHUNK_SIZE = 256 * 1024

_URI_TAG_RE = re.compile(r'(URI=")([^"]+)(")')
_TOKEN_RE = re.compile(r'[?&]X-Plex-Token=[^&\s"\']*')


def _proxy_base(request: Request) -> str:
    if settings.addon_base_url:
        return settings.addon_base_url.rstrip('/')
    return str(request.base_url).rstrip('/')


async def _fetch_upstream(
    client: ClientSession,
    url: str,
    range_header: str | None = None,
):
    headers = {
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (compatible; Plexio/1.0)',
    }
    if range_header:
        headers['Range'] = range_header
    return await client.get(url, headers=headers)


def _rewrite_playlist(text: str, plex_url: str, proxy_base: str) -> str:
    """Rewrite an HLS playlist so every URI goes back through the relay.

    Relative URIs are resolved against the current Plex URL, absolute ones are
    kept as-is; each becomes a fresh, expiring proxy token. Any leaked
    ``X-Plex-Token`` is stripped — it is re-injected upstream at mint time.
    """

    def _proxy_uri(uri: str) -> str:
        resolved = urljoin(plex_url, uri)
        if _TOKEN_RE.search(resolved):
            resolved = _TOKEN_RE.sub('', resolved)
        return f'{proxy_base}/proxy/{mint_proxy_token(resolved)}'

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            if 'URI="' in line:
                line = _URI_TAG_RE.sub(
                    lambda m: f'{m.group(1)}{_proxy_uri(m.group(2))}{m.group(3)}',
                    line,
                )
            lines.append(line)
            continue
        if not stripped or stripped.startswith('//'):
            continue
        lines.append(_proxy_uri(stripped))
    return '\n'.join(lines) + '\n'


async def _relay(
    request: Request,
    http: ClientSession,
    token: str,
) -> Response:
    plex_url = unmint_proxy_token(token)
    if plex_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    upstream = await _fetch_upstream(http, plex_url, request.headers.get('Range'))
    if upstream.status >= 400:
        await upstream.release()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY)

    headers = {
        h: upstream.headers.get(h)
        for h in _PROXIED_HEADERS
        if upstream.headers.get(h) is not None
    }

    if plex_url.split('?')[0].endswith('.m3u8'):
        body = await upstream.read()
        rewritten = _rewrite_playlist(
            body.decode('utf-8', errors='replace'),
            plex_url,
            _proxy_base(request),
        )
        headers['Content-Length'] = str(len(rewritten.encode()))
        await upstream.release()
        return Response(content=rewritten, status_code=upstream.status, headers=headers)

    async def _stream():
        try:
            async for chunk in upstream.content.iter_chunked(_CHUNK_SIZE):
                yield chunk
        finally:
            await upstream.release()

    return StreamingResponse(_stream(), status_code=upstream.status, headers=headers)


@router.get('/proxy/{token}')
async def proxy(
    request: Request,
    http: Annotated[ClientSession, Depends(get_http_client)],
    token: str,
) -> Response:
    return await _relay(request, http, token)
