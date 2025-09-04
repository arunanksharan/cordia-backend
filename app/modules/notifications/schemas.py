from pydantic import BaseModel, Field

class TemplateCreate(BaseModel):
    channel: str = Field(..., pattern="^(sms|email|whatsapp)$")
    name: str
    subject: str | None = None
    body: str

class TemplateOut(TemplateCreate):
    id: str
    org_id: str
    class Config: from_attributes = True

class SendMessage(BaseModel):
    channel: str = Field(..., pattern="^(sms|email|whatsapp)$")
    to: str
    template_name: str | None = None
    subject: str | None = None
    body: str | None = None
    variables: dict | None = None

class OutboundOut(BaseModel):
    id: str
    org_id: str
    channel: str
    to: str
    subject: str | None
    body: str
    status: str
    class Config: from_attributes = True