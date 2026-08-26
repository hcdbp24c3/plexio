import logging
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from plexio.cache import MemoryCache, RedisCache

# ---------------------------------------------------------------------------
# MemoryCache tests
# ---------------------------------------------------------------------------


async def test_memory_cache_set_get_roundtrip():
    cache = MemoryCache()
    await cache.set('key1', 'value1')
    result = await cache.get('key1')
    assert result == 'value1'


async def test_memory_cache_evicts_oldest_when_full():
    cache = MemoryCache(maxsize=2)
    await cache.set('k1', 'v1')
    await cache.set('k2', 'v2')
    await cache.set('k3', 'v3')

    assert await cache.get('k1') is None
    assert await cache.get('k2') == 'v2'
    assert await cache.get('k3') == 'v3'


async def test_memory_cache_lru_get_refreshes_order():
    cache = MemoryCache(maxsize=2)
    await cache.set('a', 1)
    await cache.set('b', 2)
    # Access 'a' to refresh its LRU position
    await cache.get('a')
    # Insert 'c' — should evict 'b' (oldest untouched), not 'a'
    await cache.set('c', 3)

    assert await cache.get('a') == 1
    assert await cache.get('b') is None
    assert await cache.get('c') == 3


def test_memory_cache_rejects_invalid_maxsize():
    with pytest.raises(ValueError, match='maxsize must be >= 1'):
        MemoryCache(maxsize=0)


# ---------------------------------------------------------------------------
# RedisCache tests — all patch Redis.from_url so no real connection needed
# ---------------------------------------------------------------------------

REDIS_PATCH_TARGET = 'plexio.cache.Redis'


async def test_redis_cache_set_logs_after_exhausted_retries(caplog):
    with patch(REDIS_PATCH_TARGET) as MockRedis:
        mock_instance = AsyncMock()
        MockRedis.from_url.return_value = mock_instance
        mock_instance.set.side_effect = RedisConnectionError('connection refused')

        cache = RedisCache('redis://localhost:6379')
        with caplog.at_level(logging.ERROR, logger='plexio.cache'):
            result = await cache.set('mykey', 'myvalue')

        assert result is None
        assert mock_instance.set.call_count == RedisCache.RETRY_TIMES
        assert any('mykey' in record.message for record in caplog.records)
        assert any(record.levelno == logging.ERROR for record in caplog.records)


async def test_redis_cache_get_returns_none_and_logs_after_exhausted_retries(
    caplog,
):
    with patch(REDIS_PATCH_TARGET) as MockRedis:
        mock_instance = AsyncMock()
        MockRedis.from_url.return_value = mock_instance
        mock_instance.get.side_effect = RedisConnectionError('connection refused')

        cache = RedisCache('redis://localhost:6379')
        with caplog.at_level(logging.ERROR, logger='plexio.cache'):
            result = await cache.get('mykey')

        assert result is None
        assert mock_instance.get.call_count == RedisCache.RETRY_TIMES
        assert any('mykey' in record.message for record in caplog.records)
        assert any(record.levelno == logging.ERROR for record in caplog.records)


async def test_redis_cache_set_succeeds_first_try_no_log(caplog):
    with patch(REDIS_PATCH_TARGET) as MockRedis:
        mock_instance = AsyncMock()
        MockRedis.from_url.return_value = mock_instance
        # .set succeeds silently (returns None)
        mock_instance.set.return_value = None

        cache = RedisCache('redis://localhost:6379')
        with caplog.at_level(logging.ERROR, logger='plexio.cache'):
            result = await cache.set('mykey', 'myvalue')

        assert result is None
        assert mock_instance.set.call_count == 1
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_records == []
