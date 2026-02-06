# -*- coding: utf-8 -*-
"""
缓存服务 - 使用 Redis 实现分布式缓存
"""
import json
import time
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from pydantic import BaseModel
from app.config import fund_config
from app.logger import get_logger

logger = get_logger("cache_service")


class PydanticEncoder(json.JSONEncoder):
    """支持 Pydantic 模型的 JSON 编码器"""
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode='json')
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class CacheService:
    """缓存服务类"""
    
    def __init__(self):
        """初始化缓存服务"""
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = False
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=fund_config.REDIS_URL.split(':')[1].split('//')[1] if '//' in fund_config.REDIS_URL else 'localhost',
                    port=int(fund_config.REDIS_URL.split(':')[2].split('/')[0]) if ':' in fund_config.REDIS_URL else 6379,
                    db=int(fund_config.REDIS_URL.split('/')[-1]) if '/' in fund_config.REDIS_URL else 0,
                    decode_responses=True
                )
                self.enabled = True
                logger.info("Redis 缓存服务已启用")
            except Exception as e:
                logger.warning(f"Redis 连接失败，禁用缓存: {e}")
                self.enabled = False
        else:
            logger.warning("Redis 未安装，禁用缓存")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.enabled:
            return None
        
        try:
            data = self.redis_client.get(key)
            if data:
                self.stats['hits'] += 1
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int) -> bool:
        """设置缓存"""
        if not self.enabled:
            return False
        
        try:
            data = json.dumps(value, ensure_ascii=False, cls=PydanticEncoder)
            self.redis_client.setex(key, ttl, data)
            self.stats['sets'] += 1
            return True
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled:
            return False
        
        try:
            self.redis_client.delete(key)
            self.stats['deletes'] += 1
            return True
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """清空匹配模式的缓存"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"清空缓存失败 {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'total': total,
            'hit_rate': f"{hit_rate:.2f}%",
            'enabled': self.enabled
        }
    
    def warmup(self, data: Dict[str, Any]) -> int:
        """缓存预热"""
        if not self.enabled:
            return 0
        
        warmed = 0
        for key, value in data.items():
            if self.set(key, value, 3600):  # 1小时
                warmed += 1
        
        logger.info(f"缓存预热完成: {warmed}/{len(data)}")
        return warmed


# 单例模式
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取缓存服务实例（单例）"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def get_cache(key: str) -> Optional[Any]:
    """便捷方法：获取缓存"""
    return get_cache_service().get(key)


def set_cache(key: str, value: Any, ttl: int) -> bool:
    """便捷方法：设置缓存"""
    return get_cache_service().set(key, value, ttl)


def delete_cache(key: str) -> bool:
    """便捷方法：删除缓存"""
    return get_cache_service().delete(key)


def get_cache_stats() -> Dict[str, Any]:
    """便捷方法：获取缓存统计"""
    return get_cache_service().get_stats()