import redis.asyncio as redis
from typing import Optional
import json
from app.platform.core.config import settings
from app.platform.observability.logging import logger

class RedisCache:
    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        try:
            self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    async def disconnect(self):
        if self.client:
            await self.client.aclose()
            logger.info("Disconnected from Redis.")

    async def get(self, key: str) -> Optional[dict]:
        if not self.client:
            return None
        try:
            val = await self.client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis GET failed for {key}: {e}")
        return None

    async def set(self, key: str, value: dict, expire: int = 10):
        if not self.client:
            return
        try:
            await self.client.set(key, json.dumps(value), ex=expire)
        except Exception as e:
            logger.warning(f"Redis SET failed for {key}: {e}")

redis_cache = RedisCache()
