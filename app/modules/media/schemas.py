import uuid
from pydantic import BaseModel

class MediaUploadOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    key: str
    mime_type: str
    size_bytes: int
    download_url: str

    class Config:
        from_attributes = True