import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.tickets.repository import (
    TicketRepository, TicketNoteRepository, TaskRepository,
    AssignmentRepository, SlaPolicyRepository, SlaApplicationRepository
)
from app.modules.tickets.models import Ticket
from app.modules.tickets.schemas import (
    TicketCreate, TicketUpdate,
    TicketNoteCreate, TaskCreate, TaskUpdate,
    AssignmentCreate, SlaPolicyCreate, SlaRecalcResult
)
from app.modules.events.outbox import OutboxService

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _compute_due(base: datetime, minutes: int) -> datetime:
    return base + timedelta(minutes=minutes)

def _breach_state(now: datetime, start: datetime, due: datetime) -> str:
    if now >= due:
        return "breached"
    total = (due - start).total_seconds()
    left = (due - now).total_seconds()
    # "At risk" if <10% time remains
    return "at_risk" if total > 0 and (left / total) <= 0.10 else "ontrack"

class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tickets = TicketRepository(session)
        self.notes = TicketNoteRepository(session)
        self.tasks = TaskRepository(session)
        self.assignments = AssignmentRepository(session)
        self.sla_policies = SlaPolicyRepository(session)
        self.sla_apps = SlaApplicationRepository(session)

    # ---- Tickets ----
    async def create_ticket(self, org_id: uuid.UUID, payload: TicketCreate) -> Ticket:
        obj = await self.tickets.create(org_id, **payload.model_dump(exclude_unset=True))
        # SLA application
        policy = await self.sla_policies.match_for_ticket(org_id, obj.category, obj.priority)
        base = _now()
        if policy:
            due_resp = _compute_due(base, policy.respond_within_minutes)
            due_reso = _compute_due(base, policy.resolve_within_minutes)
            await self.sla_apps.create(
                org_id,
                subject_type="ticket",
                subject_id=obj.id,
                policy_id=policy.id,
                started_at=base,
                paused_total_seconds=0,
                pause_started_at=None,
                due_response_at=due_resp,
                due_resolution_at=due_reso,
                breach_state=_breach_state(base, base, due_reso),  # initial
                last_recalc_at=base,
            )
        await OutboxService(self.session).enqueue(
            org_id, "TICKET_CREATED", "ticket", obj.id,
            {"category": obj.category, "priority": obj.priority, "severity": obj.severity}
        )
        await self.session.commit()
        return obj

    async def get_ticket(self, org_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        return await self.tickets.get(org_id, ticket_id)

    async def list_tickets(self, org_id: uuid.UUID, **filters):
        return await self.tickets.list(org_id, **filters)

    async def update_ticket(self, org_id: uuid.UUID, ticket_id: uuid.UUID, payload: TicketUpdate) -> Ticket | None:
        # adjust SLA pause when status switches in/out of pause set
        obj = await self.tickets.get(org_id, ticket_id)
        if not obj:
            return None

        before_status = obj.status
        obj = await self.tickets.update_fields(org_id, ticket_id, **payload.model_dump(exclude_unset=True))
        # recompute pause bookkeeping if status changed
        if payload.status and payload.status != before_status:
            sla = await self.sla_apps.get_for_ticket(org_id, ticket_id)
            pol = await self.sla_policies.match_for_ticket(org_id, obj.category, obj.priority) if obj else None
            pause_list = set(pol.pause_statuses.get("list", [])) if pol and pol.pause_statuses else set(["waiting_on_patient", "waiting_on_payer"])
            now = _now()
            if sla:
                # entering paused
                if payload.status in pause_list and sla.pause_started_at is None:
                    sla.pause_started_at = now
                # leaving paused
                if before_status in pause_list and payload.status not in pause_list and sla.pause_started_at is not None:
                    delta = int((now - sla.pause_started_at).total_seconds())
                    sla.paused_total_seconds += max(delta, 0)
                    sla.pause_started_at = None
                sla.last_recalc_at = now
            # enqueue status-changed event
            await OutboxService(self.session).enqueue(
                org_id, "TICKET_STATUS_CHANGED", "ticket", obj.id,
                {"from": before_status, "to": payload.status}
            )
        await self.session.commit()
        return obj

    # ---- Notes ----
    async def add_note(self, org_id: uuid.UUID, ticket_id: uuid.UUID, payload: TicketNoteCreate):
        # ensure ticket exists
        t = await self.tickets.get(org_id, ticket_id)
        if not t:
            return None
        obj = await self.notes.create(org_id, ticket_id, payload.author_id, payload.body, payload.visibility)
        await self.session.commit()
        return obj

    async def list_notes(self, org_id: uuid.UUID, ticket_id: uuid.UUID):
        return await self.notes.list_for_ticket(org_id, ticket_id)

    # ---- Tasks ----
    async def create_task(self, org_id: uuid.UUID, ticket_id: uuid.UUID, payload: TaskCreate):
        # ensure ticket exists
        t = await self.tickets.get(org_id, ticket_id)
        if not t:
            return None
        obj = await self.tasks.create(org_id, subject_type="ticket", subject_id=ticket_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def list_tasks(self, org_id: uuid.UUID, ticket_id: uuid.UUID):
        return await self.tasks.list_for_ticket(org_id, ticket_id)

    async def update_task(self, org_id: uuid.UUID, task_id: uuid.UUID, payload: TaskUpdate):
        obj = await self.tasks.get(org_id, task_id)
        if not obj:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        await self.session.commit()
        return obj

    # ---- Assignment ----
    async def assign(self, org_id: uuid.UUID, ticket_id: uuid.UUID, payload: AssignmentCreate):
        t = await self.tickets.get(org_id, ticket_id)
        if not t:
            return None
        obj = await self.assignments.create(org_id, ticket_id, payload.assignee_id, payload.reason)
        await self.session.commit()
        return obj

    # ---- SLA ----
    async def create_sla_policy(self, org_id: uuid.UUID, payload: SlaPolicyCreate):
        obj = await self.sla_policies.create(org_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def list_sla_policies(self, org_id: uuid.UUID):
        return await self.sla_policies.list(org_id)

    async def recalc_sla(self, org_id: uuid.UUID, ticket_id: uuid.UUID) -> SlaRecalcResult | None:
        t = await self.tickets.get(org_id, ticket_id)
        if not t:
            return None
        sla = await self.sla_apps.get_for_ticket(org_id, ticket_id)
        if not sla:
            return None
        pol = await self.sla_policies.match_for_ticket(org_id, t.category, t.priority)
        now = _now()

        # account for paused time (if currently paused)
        paused_seconds = sla.paused_total_seconds
        if sla.pause_started_at:
            paused_seconds += int((now - sla.pause_started_at).total_seconds())

        # recompute breach against resolution due; keep response due as created earlier
        start = sla.started_at + timedelta(seconds=paused_seconds)
        breach = _breach_state(now, start, sla.due_resolution_at)
        sla.breach_state = breach
        sla.last_recalc_at = now
        await self.session.commit()
        return SlaRecalcResult(
            ticket_id=ticket_id,
            breach_state=breach,
            due_response_at=sla.due_response_at,
            due_resolution_at=sla.due_resolution_at,
            last_recalc_at=now,
        )