import uuid
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import TIMESTAMP, text, String, Integer, Text, JSON, select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import Base, TimestampedTenantMixin
from app.core.db import SessionLocal
from app.platform.provider_registry import registry

log = logging.getLogger("event.outbox")

class EventOutbox(Base, TimestampedTenantMixin):
    event_type: Mapped[str] = mapped_column(String(64))
    subject_type: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)

    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | processing | sent | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def enqueue(self, org_id: uuid.UUID, *, event_type: str, subject_type: str, subject_id: str, payload: dict, occurred_at: datetime | None = None) -> EventOutbox:
        obj = EventOutbox(
            org_id=org_id,
            event_type=event_type,
            subject_type=subject_type,
            subject_id=str(subject_id),
            payload=payload,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            status="pending",
            attempts=0,
            next_attempt_at=datetime.now(timezone.utc),
        )
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def claim_batch(self, limit: int = 50) -> list[EventOutbox]:
        # SELECT ... FOR UPDATE SKIP LOCKED
        q = (
            select(EventOutbox)
            .where(
                and_(
                    EventOutbox.deleted_at.is_(None),
                    EventOutbox.status == "pending",
                    EventOutbox.next_attempt_at <= datetime.now(timezone.utc),
                )
            )
            .order_by(EventOutbox.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        res = await self.session.execute(q)
        rows = list(res.scalars().all())
        # mark as processing
        for r in rows:
            r.status = "processing"
        await self.session.flush()
        return rows

    async def mark_sent(self, obj: EventOutbox):
        obj.status = "sent"
        obj.last_error = None
        await self.session.flush()

    async def mark_failed(self, obj: EventOutbox, error: str):
        obj.status = "pending"  # retry
        obj.attempts = (obj.attempts or 0) + 1
        backoff = min(60, 2 ** min(obj.attempts, 6))  # 1,2,4,8,16,32,60s
        obj.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
        obj.last_error = error[:2000]  # truncate
        await self.session.flush()

class OutboxService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OutboxRepository(session)

    async def enqueue(self, org_id: uuid.UUID, event_type: str, subject_type: str, subject_id: str | uuid.UUID, payload: dict, occurred_at: datetime | None = None) -> EventOutbox:
        return await self.repo.enqueue(org_id, event_type=event_type, subject_type=subject_type, subject_id=str(subject_id), payload=payload, occurred_at=occurred_at)

# ---- Background relay ----

async def run_outbox_relay(poll_interval_seconds: float = 1.0):
    bus = registry.event_bus()
    log.info("Outbox relay started with bus=%s", bus.__class__.__name__)
    try:
        while True:
            # claim and publish in small batches
            async with SessionLocal() as session:
                repo = OutboxRepository(session)
                try:
                    batch = await repo.claim_batch(limit=50)
                    if not batch:
                        await session.commit()
                        await asyncio.sleep(poll_interval_seconds)
                        continue
                    for ev in batch:
                        try:
                            topic = "prm.events"
                            key = ev.subject_id or "-"
                            # publish
                            await bus.publish(topic=topic, key=key, value={
                                "org_id": str(ev.org_id),
                                "event_type": ev.event_type,
                                "subject": {"type": ev.subject_type, "id": ev.subject_id},
                                "payload": ev.payload,
                                "occurred_at": ev.occurred_at.isoformat(),
                                "outbox_id": str(ev.id),
                            })
                            await repo.mark_sent(ev)
                        except Exception as ex:  # noqa
                            log.exception("Publish failed")
                            await repo.mark_failed(ev, error=str(ex))
                    await session.commit()
                except Exception as e:
                    log.exception("Outbox relay iteration failed")
                    await session.rollback()
                    await asyncio.sleep(poll_interval_seconds)
            await asyncio.sleep(0)  # yield
    except asyncio.CancelledError:
        log.info("Outbox relay cancelled; shutting down")
        raise