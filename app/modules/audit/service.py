import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.models import AuditEvent

class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self,
                  org_id: uuid.UUID,
                  actor_user_id: uuid.UUID,
                  action: str,
                  resource_type: str,
                  resource_id: str,
                  purpose: str | None,
                  request: Request | None = None,
                  success: bool = True) -> None:
        ev = AuditEvent(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            purpose=purpose,
            success=success,
            client_ip=(request.client.host if request and request.client else None),
            user_agent=(request.headers.get("user-agent") if request else None),
        )
        self.session.add(ev)
        await self.session.commit()