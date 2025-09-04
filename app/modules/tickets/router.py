import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.tickets.schemas import (
    TicketCreate, TicketUpdate, TicketOut,
    TicketNoteCreate, TicketNoteOut,
    TaskCreate, TaskUpdate, TaskOut,
    AssignmentCreate, AssignmentOut,
    SlaPolicyCreate, SlaPolicyOut, SlaRecalcResult
)
from app.modules.tickets.service import TicketService

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> TicketService:
    return TicketService(session)

# ---- Tickets ----

@router.post("/tickets", response_model=TicketOut, dependencies=[Depends(require_scopes("tickets:write"))])
async def create_ticket(
    payload: TicketCreate,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    obj = await service.create_ticket(principal.org_id, payload)
    return obj

@router.get("/tickets/{ticket_id}", response_model=TicketOut, dependencies=[Depends(require_scopes("tickets:read"))])
async def get_ticket(
    ticket_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    obj = await service.get_ticket(principal.org_id, ticket_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return obj

@router.get("/tickets", response_model=list[TicketOut], dependencies=[Depends(require_scopes("tickets:read"))])
async def list_tickets(
    status: str | None = Query(default=None, pattern="^(new|triaged|in_progress|waiting_on_patient|waiting_on_payer|resolved|closed)$"),
    category: str | None = Query(default=None, pattern="^(appointment|billing|insurance|facilities|information|complaint|feedback|other)$"),
    priority: str | None = Query(default=None, pattern="^p[0-3]$"),
    limit: int = 50, offset: int = 0,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    return await service.list_tickets(principal.org_id, status=status, category=category, priority=priority, limit=limit, offset=offset)

@router.patch("/tickets/{ticket_id}", response_model=TicketOut, dependencies=[Depends(require_scopes("tickets:write"))])
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    obj = await service.update_ticket(principal.org_id, ticket_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return obj

# ---- Notes ----

@router.post("/tickets/{ticket_id}/notes", response_model=TicketNoteOut, dependencies=[Depends(require_scopes("tickets:write"))])
async def add_note(
    ticket_id: uuid.UUID,
    payload: TicketNoteCreate,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    obj = await service.add_note(principal.org_id, ticket_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return obj

@router.get("/tickets/{ticket_id}/notes", response_model=list[TicketNoteOut], dependencies=[Depends(require_scopes("tickets:read"))])
async def list_notes(
    ticket_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    return await service.list_notes(principal.org_id, ticket_id)

# ---- Tasks ----

@router.post("/tickets/{ticket_id}/tasks", response_model=TaskOut, dependencies=[Depends(require_scopes("tasks:write"))])
async def create_task(
    ticket_id: uuid.UUID,
    payload: TaskCreate,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    obj = await service.create_task(principal.org_id, ticket_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return obj

@router.get("/tickets/{ticket_id}/tasks", response_model=list[TaskOut], dependencies=[Depends(require_scopes("tasks:read"))])
async def list_tasks(
    ticket_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    return await service.list_tasks(principal.org_id, ticket_id)

@router.patch("/tasks/{task_id}", response_model=TaskOut, dependencies=[Depends(require_scopes("tasks:write"))])
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    obj = await service.update_task(principal.org_id, task_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Task not found")
    return obj

# ---- Assignment ----

@router.post("/tickets/{ticket_id}/assign", response_model=AssignmentOut, dependencies=[Depends(require_scopes("tickets:write"))])
async def assign_ticket(
    ticket_id: uuid.UUID,
    payload: AssignmentCreate,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    obj = await service.assign(principal.org_id, ticket_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return obj

# ---- SLA ----

@router.post("/sla/policies", response_model=SlaPolicyOut, dependencies=[Depends(require_scopes("sla:write"))])
async def create_sla_policy(
    payload: SlaPolicyCreate,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    return await service.create_sla_policy(principal.org_id, payload)

@router.get("/sla/policies", response_model=list[SlaPolicyOut], dependencies=[Depends(require_scopes("sla:read"))])
async def list_sla_policies(
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    return await service.list_sla_policies(principal.org_id)

@router.post("/tickets/{ticket_id}/sla/recalc", response_model=SlaRecalcResult, dependencies=[Depends(require_scopes("sla:write"))])
async def recalc_ticket_sla(
    ticket_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: TicketService = Depends(svc),
):
    res = await service.recalc_sla(principal.org_id, ticket_id)
    if not res:
        raise HTTPException(status_code=404, detail="SLA not found for ticket")
    return res