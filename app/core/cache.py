"""
Caching utilities for PC Recommendation System
"""
import json
import asyncio
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import hashlib

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class Cache:
    """Simple in-memory cache with optional Redis support"""

    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.memory_cache: Dict[str, Dict[str, Any]] = {}

        if REDIS_AVAILABLE and redis_url:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        else:
            self.redis_client = None

    async def _get_cache_key(self, key: str) -> str:
        """Generate a consistent cache key"""
        return f"pc_rec:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        cache_key = await self._get_cache_key(key)

        # Try Redis first if available
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception:
                pass  # Fall back to memory cache

        # Fall back to memory cache
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if entry['expires_at'] > datetime.utcnow():
                return entry['value']
            else:
                # Remove expired entry
                del self.memory_cache[cache_key]

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        cache_key = await self._get_cache_key(key)
        expires_at = datetime.utcnow() + timedelta(seconds=ttl or self.default_ttl)

        cache_entry = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.utcnow()
        }

        # Try Redis first if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    ttl or self.default_ttl,
                    json.dumps(value, default=str)
                )
                return
            except Exception:
                pass  # Fall back to memory cache

        # Fall back to memory cache
        self.memory_cache[cache_key] = cache_entry

    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        cache_key = await self._get_cache_key(key)

        # Try Redis first if available
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                return
            except Exception:
                pass  # Fall back to memory cache

        # Remove from memory cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]

    async def clear_pattern(self, pattern: str) -> None:
        """Clear cache entries matching a pattern"""
        pattern_key = await self._get_cache_key(pattern)

        # Try Redis first if available
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(f"{pattern_key}*")
                if keys:
                    await self.redis_client.delete(*keys)
                return
            except Exception:
                pass  # Fall back to memory cache

        # Clear matching memory cache entries
        keys_to_delete = [
            key for key in self.memory_cache.keys()
            if key.startswith(pattern_key)
        ]
        for key in keys_to_delete:
            del self.memory_cache[key]

    async def get_or_set(self, key: str, getter_func, ttl: Optional[int] = None):
        """Get from cache or set if not found"""
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        # Call getter function
        value = await getter_func()

        # Cache the result
        await self.set(key, value, ttl)

        return value

    async def health_check(self) -> Dict[str, Any]:
        """Check cache health"""
        health = {
            'memory_cache': {
                'entries': len(self.memory_cache),
                'healthy': True
            },
            'redis_cache': {
                'available': REDIS_AVAILABLE and self.redis_client is not None,
                'healthy': False
            }
        }

        # Check Redis health
        if health['redis_cache']['available']:
            try:
                await self.redis_client.ping()
                health['redis_cache']['healthy'] = True
            except Exception as e:
                health['redis_cache']['error'] = str(e)

        return health


# Global cache instance
cache = Cache()


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a deterministic cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])

    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


async def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{generate_cache_key(func.__name__, *args, **kwargs)}"

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator
