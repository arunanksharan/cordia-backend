from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class PatientData(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None

class ChiefComplaintData(BaseModel):
    text: Optional[str] = None

class AppointmentRequestData(BaseModel):
    preferred_time: Optional[str] = None
    preferred_location: Optional[str] = None

class IntakeData(BaseModel):
    chief_complaint: Optional[ChiefComplaintData] = None
    symptoms: Optional[List[Dict[str, Any]]] = None
    condition_history: Optional[List[Dict[str, Any]]] = None
    allergies: Optional[List[Dict[str, Any]]] = None
    medications: Optional[List[Dict[str, Any]]] = None
    family_history: Optional[List[Dict[str, Any]]] = None

class ConversationData(BaseModel):
    patient: PatientData
    intake: IntakeData
    appointment_request: Optional[AppointmentRequestData] = None

class IntakeResponsePayload(BaseModel):
    conversation_id: str
    intent: str
    is_complete: bool
    missing_fields: List[str]
    next_question: Optional[str] = None
    data: ConversationData

class GptResponsePayload(BaseModel):
    conversation_id: str
    extracted_fields: Dict[str, Any]
    next_question: str
    next_field: Optional[str] = None