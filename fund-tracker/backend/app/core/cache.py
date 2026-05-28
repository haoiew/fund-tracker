# -*- coding: utf-8 -*-
"""
L1内存缓存 - 线程安全，O(1) LRU淘汰，TTL过期
替代原Redis CacheService，无需外部依赖
"""
import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass

from app.logger import get_logger

logger = get_logger("cache")


@dataclass
class CacheEntry:
    value: Any
    expire_at: float
    access_count: int = 0


class MemoryCache:
    """线程安全的L1内存缓存，OrderedDict实现O(1) LRU"""

    def __init__(self, max_size: int = 2000, default_ttl: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._stats = {'hits': 0, 'misses': 0, 'sets': 0, 'evictions': 0}

        self._cleanup_interval = 60
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                self._stats['misses'] += 1
                return None
            if time.time() > entry.expire_at:
                del self._cache[key]
                self._stats['misses'] += 1
                return None
            entry.access_count += 1
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        ttl = ttl or self._default_ttl
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            while len(self._cache) >= self._max_size:
                self._evict_lru()
            self._cache[key] = CacheEntry(
                value=value,
                expire_at=time.time() + ttl,
                access_count=1
            )
            self._stats['sets'] += 1
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_multi(self, keys: List[str]) -> int:
        count = 0
        with self._lock:
            for key in keys:
                if key in self._cache:
                    del self._cache[key]
                    count += 1
        return count

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def _evict_lru(self):
        if not self._cache:
            return
        lru_key = next(iter(self._cache))
        del self._cache[lru_key]
        self._stats['evictions'] += 1

    def _cleanup_loop(self):
        while True:
            time.sleep(self._cleanup_interval)
            try:
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"缓存清理失败: {e}")

    def _cleanup_expired(self) -> int:
        now = time.time()
        expired_keys = []
        with self._lock:
            for key, entry in self._cache.items():
                if now > entry.expire_at:
                    expired_keys.append(key)
            for key in expired_keys:
                del self._cache[key]
        if expired_keys:
            logger.debug(f"清理过期缓存: {len(expired_keys)} 条")
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0
            return {
                **self._stats,
                'size': len(self._cache),
                'max_size': self._max_size,
                'hit_rate': f"{hit_rate:.2f}%",
            }

    def get_or_set(self, key: str, getter: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        try:
            value = getter()
            if value is not None:
                self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"获取数据失败 {key}: {e}")
            raise

    def invalidate_pattern(self, prefix: str) -> int:
        """删除匹配前缀的缓存条目"""
        keys_to_delete = []
        with self._lock:
            for key in self._cache:
                if key.startswith(prefix):
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del self._cache[key]
        return len(keys_to_delete)


_cache: Optional[MemoryCache] = None


def get_cache() -> MemoryCache:
    global _cache
    if _cache is None:
        _cache = MemoryCache()
    return _cache
