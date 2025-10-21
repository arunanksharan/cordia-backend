from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class TwilioTextMessage(BaseModel):
    """
    Structure for a text message received from Twilio
    """
    message_id: str = Field(..., alias='MessageSid')
    from_number: str = Field(..., alias='From')
    to_number: str = Field(..., alias='To')
    body: str = Field(..., alias='Body')
    message_type: str = "text"
    
    class Config:
        populate_by_name = True
        extra = 'ignore'


class TwilioMediaMessage(BaseModel):
    """
    Structure for media messages (audio, image, etc.)
    """
    message_id: str = Field(..., alias='MessageSid')
    from_number: str = Field(..., alias='From')
    to_number: str = Field(..., alias='To')
    body: Optional[str] = Field(None, alias='Body')
    num_media: int = Field(0, alias='NumMedia')
    
    media_urls: Optional[List[HttpUrl]] = None
    media_types: Optional[List[str]] = None
    message_type: str = "media"

    class Config:
        populate_by_name = True
        extra = 'ignore'