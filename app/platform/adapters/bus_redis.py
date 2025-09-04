import asyncio
import json
import logging
from redis.asyncio import from_url as redis_from_url
from app.platform.ports.event_bus import EventBusPort
from app.core.config import settings

log = logging.getLogger("bus.redis")

class RedisEventBus(EventBusPort):
    def __init__(self):
        if not settings.REDIS_URL:
            raise RuntimeError("REDIS_URL not configured")
        self.redis = redis_from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        self.stream = settings.REDIS_STREAM or "prm.events"

    async def publish(self, topic: str, key: str, value: dict, headers: dict | None = None) -> None:
        payload = {
            "topic": topic,
            "key": key,
            "value": json.dumps(value),
            "headers": json.dumps(headers or {}),
        }
        await self.redis.xadd(self.stream, payload, maxlen=settings.REDIS_STREAM_MAXLEN, approximate=True)
        log.debug(f"[REDIS BUS] XADD stream={self.stream} topic={topic} key={key}")