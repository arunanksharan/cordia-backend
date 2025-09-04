import json
import logging
from app.platform.ports.event_bus import EventBusPort

log = logging.getLogger("bus.noop")

class NoopEventBus(EventBusPort):
    async def publish(self, topic: str, key: str, value: dict, headers: dict | None = None) -> None:
        log.info(f"[NOOP BUS] topic={topic} key={key} value={json.dumps(value)} headers={headers or {}}")