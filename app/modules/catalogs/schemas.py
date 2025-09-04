from pydantic import BaseModel

class CodeValueCreate(BaseModel):
    set_name: str
    code: str
    display: str
    active: bool = True

class CodeValueOut(CodeValueCreate):
    id: str
    org_id: str
    class Config: from_attributes = True