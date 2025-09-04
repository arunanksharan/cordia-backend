import uuid
from typing import Sequence
from datetime import datetime, timezone
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.tickets.models import (
    Ticket, TicketNote, Task, WorkQueue, Assignment, SlaPolicy, SlaApplication
)

class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Ticket:
        obj = Ticket(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        q = select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
            Ticket.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list(self, org_id: uuid.UUID, *, status: str | None = None, category: str | None = None, priority: str | None = None, limit: int = 50, offset: int = 0) -> Sequence[Ticket]:
        conditions = [Ticket.org_id == org_id, Ticket.deleted_at.is_(None)]
        if status:   conditions.append(Ticket.status == status)
        if category: conditions.append(Ticket.category == category)
        if priority: conditions.append(Ticket.priority == priority)
        q = select(Ticket).where(and_(*conditions)).order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(q)
        return res.scalars().all()

    async def update_fields(self, org_id: uuid.UUID, ticket_id: uuid.UUID, **data) -> Ticket | None:
        obj = await self.get(org_id, ticket_id)
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.flush()
        return obj

class TicketNoteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, ticket_id: uuid.UUID, author_id: uuid.UUID, body: str, visibility: str) -> TicketNote:
        obj = TicketNote(org_id=org_id, ticket_id=ticket_id, author_id=author_id, body=body, visibility=visibility)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def list_for_ticket(self, org_id: uuid.UUID, ticket_id: uuid.UUID) -> Sequence[TicketNote]:
        q = select(TicketNote).where(
            TicketNote.org_id == org_id,
            TicketNote.ticket_id == ticket_id,
            TicketNote.deleted_at.is_(None),
        ).order_by(TicketNote.created_at.asc())
        res = await self.session.execute(q)
        return res.scalars().all()

class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Task:
        obj = Task(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, task_id: uuid.UUID) -> Task | None:
        q = select(Task).where(
            Task.id == task_id,
            Task.org_id == org_id,
            Task.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list_for_ticket(self, org_id: uuid.UUID, ticket_id: uuid.UUID) -> Sequence[Task]:
        q = select(Task).where(
            Task.org_id == org_id,
            Task.subject_type == "ticket",
            Task.subject_id == ticket_id,
            Task.deleted_at.is_(None),
        ).order_by(Task.created_at.asc())
        res = await self.session.execute(q)
        return res.scalars().all()

class AssignmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, ticket_id: uuid.UUID, assignee_id: uuid.UUID, reason: str | None) -> Assignment:
        obj = Assignment(org_id=org_id, ticket_id=ticket_id, assignee_id=assignee_id, reason=reason)
        self.session.add(obj)
        await self.session.flush()
        return obj

class SlaPolicyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> SlaPolicy:
        obj = SlaPolicy(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def list(self, org_id: uuid.UUID) -> Sequence[SlaPolicy]:
        q = select(SlaPolicy).where(SlaPolicy.org_id == org_id, SlaPolicy.deleted_at.is_(None))
        res = await self.session.execute(q)
        return res.scalars().all()

    async def match_for_ticket(self, org_id: uuid.UUID, category: str, priority: str) -> SlaPolicy | None:
        # Simple matcher: first policy with category_filter (or None) and priority_filter (or None)
        q = select(SlaPolicy).where(
            SlaPolicy.org_id == org_id,
            SlaPolicy.deleted_at.is_(None)
        )
        res = await self.session.execute(q)
        policies = res.scalars().all()
        # Prefer exact matches first
        for p in policies:
            if (p.category_filter == category or p.category_filter is None) and (p.priority_filter == priority or p.priority_filter is None):
                return p
        return None

class SlaApplicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_for_ticket(self, org_id: uuid.UUID, ticket_id: uuid.UUID) -> SlaApplication | None:
        q = select(SlaApplication).where(
            SlaApplication.org_id == org_id,
            SlaApplication.subject_type == "ticket",
            SlaApplication.subject_id == ticket_id,
            SlaApplication.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def create(self, org_id: uuid.UUID, **data) -> SlaApplication:
        obj = SlaApplication(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj