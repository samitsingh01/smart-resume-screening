import logging
from typing import Optional, Any, Dict
import time

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}

    async def initialize(self):
        """Initialize cache service"""
        logger.info("Simple in-memory cache service initialized")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if key in self.cache:
                # Check if expired (default 1 hour TTL)
                if time.time() - self.timestamps.get(key, 0) < 3600:
                    return self.cache[key]
                else:
                    # Remove expired entry
                    self.cache.pop(key, None)
                    self.timestamps.pop(key, None)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL"""
        try:
            self.cache[key] = value
            self.timestamps[key] = time.time()
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache service"""
        return {
            "status": "healthy", 
            "message": "In-memory cache working",
            "keys": len(self.cache)
        }
