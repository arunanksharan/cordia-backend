from typing import Protocol, runtime_checkable

@runtime_checkable
class EventBusPort(Protocol):
    async def publish(self, topic: str, key: str, value: dict, headers: dict | None = None) -> None: ...