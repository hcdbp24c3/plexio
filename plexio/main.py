from contextlib import asynccontextmanager

import aiohttp
import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from plexio.cache import init_cache
from plexio.routers.access import router as access_router
from plexio.routers.addon import router as addon_router
from plexio.routers.configuration import router as configuration_router
from plexio.routers.manage import router as manage_router
from plexio.routers.proxy import router as proxy_router
from plexio.security import RateLimiter, client_ip
from plexio.settings import settings

_public_limiter = RateLimiter(max_requests=60)


def before_send(event, hint):
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, HTTPException) and exc_value.status_code in (502, 504):
            return None
    return event


sentry_sdk.init(before_send=before_send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    plex_client = aiohttp.ClientSession(
        headers={'accept': 'application/json'},
    )
    cache = init_cache(settings)

    yield {
        'plex_client': plex_client,
        'cache': cache,
    }

    await plex_client.close()
    await cache.close()


app = FastAPI(
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.middleware('http')
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        if not _public_limiter.allow(client_ip(request)):
            return Response(status_code=429, content='Too many requests; slow down')
    return await call_next(request)


app.include_router(access_router)
app.include_router(addon_router)
app.include_router(configuration_router)
app.include_router(manage_router)
app.include_router(proxy_router)


@app.get('/health')
async def health():
    return {'status': 'ok'}
