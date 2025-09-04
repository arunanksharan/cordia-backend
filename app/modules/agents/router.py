from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from pydantic import BaseModel
from app.modules.agents.models import ToolRun
from app.modules.tickets.service import TicketService
from app.modules.appointments.service import AppointmentService

router = APIRouter()
async def get_session(): 
    async with SessionLocal() as s: yield s

TOOLS = [
    {"name":"create_ticket","inputs":{"category":"str","priority":"str","summary_human":"str"},"scopes":["tickets:write"]},
    {"name":"confirm_appointment","inputs":{"appointment_id":"uuid","start":"iso","end":"iso"},"scopes":["appointments:write"]},
]

@router.get("/agent/tools", dependencies=[Depends(require_scopes("agent:read"))])
async def list_tools(): return {"tools": TOOLS}

class RunTool(BaseModel):
    name: str
    args: dict

@router.post("/agent/run", dependencies=[Depends(require_scopes("agent:write"))])
async def run_tool(payload: RunTool, principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session)):
    tr = ToolRun(org_id=principal.org_id, tool=payload.name, inputs=payload.args, success=True)
    s.add(tr)
    try:
        if payload.name == "create_ticket":
            svc = TicketService(s)
            obj = await svc.create_ticket(principal.org_id, type("X",(object,),{"model_dump":lambda s,exclude_unset=True: payload.args})())
            tr.outputs = {"ticket_id": str(obj.id)}
        elif payload.name == "confirm_appointment":
            from datetime import datetime
            svc = AppointmentService(s)
            appt_id = payload.args["appointment_id"]
            start = datetime.fromisoformat(payload.args["start"])
            end = datetime.fromisoformat(payload.args["end"])
            obj = await svc.confirm(principal.org_id, appt_id, type("X",(object,),{"confirmed_start":start,"confirmed_end":end,"model_dump":lambda s,exclude_unset=True: {"confirmed_start":start,"confirmed_end":end}})())
            if not obj: raise HTTPException(400, "cannot_confirm")
            tr.outputs = {"appointment_id": str(obj.id)}
        else:
            raise HTTPException(400, "unknown_tool")
        await s.commit()
        return tr.outputs
    except Exception as e:
        tr.success = False; tr.error = str(e); await s.commit(); raise