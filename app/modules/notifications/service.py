import uuid
from string import Template
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.notifications.models import MessageTemplate, OutboundMessage

class NotificationsService:
    def __init__(self, s: AsyncSession): self.s = s

    async def create_template(self, org: uuid.UUID, *, channel: str, name: str, subject: str | None, body: str) -> MessageTemplate:
        t = MessageTemplate(org_id=org, channel=channel, name=name, subject=subject, body=body)
        self.s.add(t); await self.s.flush(); await self.s.commit(); return t

    async def send(self, org: uuid.UUID, *, channel: str, to: str, subject: str | None, body: str, variables: dict | None) -> OutboundMessage:
        rendered_subject = Template(subject or "").safe_substitute(variables or {})
        rendered_body = Template(body or "").safe_substitute(variables or {})
        m = OutboundMessage(org_id=org, channel=channel, to=to, subject=rendered_subject or None, body=rendered_body, meta=variables or {}, status="sent")
        self.s.add(m); await self.s.flush(); await self.s.commit()
        # NOOP delivery: message persisted as 'sent'; swap with real adapter later
        return m

    async def send_with_template(self, org: uuid.UUID, *, channel: str, to: str, template_name: str, variables: dict | None) -> OutboundMessage:
        res = await self.s.execute(select(MessageTemplate).where(MessageTemplate.org_id==org, MessageTemplate.channel==channel, MessageTemplate.name==template_name, MessageTemplate.deleted_at.is_(None)))
        t = res.scalar_one_or_none()
        if not t: raise ValueError("template_not_found")
        return await self.send(org, channel=channel, to=to, subject=t.subject, body=t.body, variables=variables)