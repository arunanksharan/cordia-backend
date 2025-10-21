import json
from redis import asyncio as aioredis
from datetime import timedelta

REDIS_URL = "redis://localhost:6379"
SESSION_EXPIRY = timedelta(minutes=15)  # expire after 15 minutes


class RedisManager:
    def __init__(self):
        self.redis = None

    async def connect(self):
        """Connect to Redis (called on FastAPI startup)."""
        self.redis = await aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def set_session(self, user_id: str, data: dict):
        """Store or update user session."""
        json_data = json.dumps(data)
        await self.redis.setex(user_id, int(SESSION_EXPIRY.total_seconds()), json_data)

    async def get_session(self, user_id: str) -> dict | None:
        """Retrieve user session if active."""
        data = await self.redis.get(user_id)
        if data:
            return json.loads(data)
        return None

    async def delete_session(self, user_id: str):
        """Manually clear session (if chat completed)."""
        await self.redis.delete(user_id)

redis_manager = RedisManager()
