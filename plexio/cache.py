import asyncio
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict
from enum import Enum

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)

PLEX_CACHE_TTL = 24 * 60 * 60


def init_cache(settings):
    if settings.cache_type is CacheType.memory:
        return MemoryCache()
    if settings.cache_type is CacheType.redis:
        return RedisCache(settings.redis_url)
    raise NotImplementedError(f'Cache type {settings.cache_type} not implemented')


class CacheType(Enum):
    memory = 'memory'
    redis = 'redis'


class AbstractCache(ABC):
    @abstractmethod
    async def set(self, key, value):
        pass

    @abstractmethod
    async def get(self, key):
        pass

    @abstractmethod
    async def close(self):
        pass


class MemoryCache(AbstractCache):
    def __init__(self, maxsize: int = 1024):
        if maxsize < 1:
            raise ValueError('maxsize must be >= 1')
        self._maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()

    async def set(self, key, value):
        if key in self._cache:
            del self._cache[key]
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    async def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    async def close(self):
        pass


class RedisCache(AbstractCache):
    RETRY_TIMES = 3
    RETRY_BACKOFF_SEC = 1

    def __init__(self, redis_url):
        self._redis = Redis.from_url(url=redis_url)

    async def set(self, key, value):
        for _ in range(RedisCache.RETRY_TIMES):
            try:
                await self._redis.set(key, value, ex=PLEX_CACHE_TTL)
                return
            except RedisConnectionError:
                await asyncio.sleep(RedisCache.RETRY_BACKOFF_SEC)
        logger.exception(
            'Failed to set key %r after %d attempts',
            key,
            RedisCache.RETRY_TIMES,
        )

    async def get(self, key):
        for _ in range(RedisCache.RETRY_TIMES):
            try:
                if value := await self._redis.get(key):
                    return value.decode()
                return None
            except RedisConnectionError:
                await asyncio.sleep(RedisCache.RETRY_BACKOFF_SEC)
        logger.error(
            'Failed to get key %r after %d attempts',
            key,
            RedisCache.RETRY_TIMES,
        )
        return None

    async def close(self):
        await self._redis.close()
