# backend/app/services/cache_service.py
import aioredis
import json
import logging
from typing import Optional, Any, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Cache service initialized successfully")
        except Exception as e:
            logger.warning(f"Cache service initialization failed: {e}")
            self.redis_client = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL"""
        if not self.redis_client:
            return False
        
        try:
            # Convert datetime objects to strings for JSON serialization
            json_value = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, json_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def invalidate_pattern(self, pattern: str):
        """Invalidate keys matching pattern"""
        if not self.redis_client:
            return False
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache pattern invalidation error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self.redis_client:
            return {"status": "unavailable"}
        
        try:
            info = await self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache service"""
        if not self.redis_client:
            return {"status": "unavailable", "message": "Redis client not initialized"}
        
        try:
            # Test basic operations
            await self.redis_client.ping()
            test_key = "health_check_test"
            await self.redis_client.set(test_key, "test_value", ex=60)
            value = await self.redis_client.get(test_key)
            await self.redis_client.delete(test_key)
            
            if value == "test_value":
                return {"status": "healthy", "message": "All operations successful"}
            else:
                return {"status": "degraded", "message": "Get operation failed"}
                
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
