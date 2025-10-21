import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, delete
from app.modules.intake.models import (
    IntakeSession, IntakeSummary, IntakeChiefComplaint, IntakeSymptom, IntakeAllergy,
    IntakeMedication, IntakeConditionHistory, IntakeFamilyHistory, IntakeSocialHistory, IntakeNote
)

class IntakeRepository:
    def __init__(self, session: AsyncSession): self.session = session

    # --- sessions ---
    async def create_session(self, org: uuid.UUID, patient_id: uuid.UUID | None, conversation_id: uuid.UUID | None, context: dict | None) -> IntakeSession:
        obj = IntakeSession(org_id=org, patient_id=patient_id, conversation_id=conversation_id, context=context or {})
        self.session.add(obj); await self.session.flush(); return obj

    async def get_session(self, org: uuid.UUID, session_id: uuid.UUID) -> IntakeSession | None:
        res = await self.session.execute(select(IntakeSession).where(
            IntakeSession.org_id==org, IntakeSession.id==session_id, IntakeSession.deleted_at.is_(None)
        ))
        return res.scalar_one_or_none()

    async def set_patient(self, org: uuid.UUID, session_id: uuid.UUID, patient_id: uuid.UUID | None) -> IntakeSession | None:
        obj = await self.get_session(org, session_id)
        if not obj: return None
        obj.patient_id = patient_id
        await self.session.flush()
        return obj

    async def list_sessions(self, patient_id: int = None, status: str = None, conversation_id: str = None) -> Sequence[IntakeSession]:
        query = select(IntakeSession)
        if patient_id is not None:
            query = query.where(IntakeSession.patient_id == patient_id)
        if status is not None:
            query = query.where(IntakeSession.status == status)
        if conversation_id is not None:
            query = query.where(IntakeSession.conversation_id == uuid.UUID(conversation_id))
        res = await self.session.execute(query)
        return res.scalars().all()

    async def submit(self, org: uuid.UUID, session_id: uuid.UUID) -> IntakeSession | None:
        obj = await self.get_session(org, session_id)
        if not obj: return None
        obj.status = "submitted"
        await self.session.flush()
        return obj

    # --- records upsert helpers ---
    async def upsert_chief(self, org: uuid.UUID, session_id: uuid.UUID, text: str, codes: dict | None):
        # Only one record; replace if exists
        res = await self.session.execute(select(IntakeChiefComplaint).where(
            IntakeChiefComplaint.org_id==org, IntakeChiefComplaint.session_id==session_id, IntakeChiefComplaint.deleted_at.is_(None)
        ))
        obj = res.scalar_one_or_none()
        if obj:
            obj.text = text; obj.codes = codes
        else:
            obj = IntakeChiefComplaint(org_id=org, session_id=session_id, text=text, codes=codes)
            self.session.add(obj)
        await self.session.flush()

    async def _upsert_list_by_client_id(self, org: uuid.UUID, session_id: uuid.UUID, model, items: list[dict], key_fields: list[str]):
        # For items with client_item_id: upsert. Without: insert new.
        # Also, we DON'T delete unspecified items (allows incremental upsert).
        for item in items:
            cid = item.get("client_item_id")
            if cid:
                res = await self.session.execute(select(model).where(
                    model.org_id==org, model.session_id==session_id, model.client_item_id==cid, model.deleted_at.is_(None)
                ))
                obj = res.scalar_one_or_none()
                if obj:
                    for k,v in item.items():
                        if k in {"client_item_id"}: continue
                        setattr(obj, k, v)
                    continue
            obj = model(org_id=org, session_id=session_id, **{k:v for k,v in item.items() if k!="id"})
            self.session.add(obj)
        await self.session.flush()

    async def set_social_history(self, org: uuid.UUID, session_id: uuid.UUID, data: dict):
        res = await self.session.execute(select(IntakeSocialHistory).where(
            IntakeSocialHistory.org_id==org, IntakeSocialHistory.session_id==session_id, IntakeSocialHistory.deleted_at.is_(None)
        ))
        obj = res.scalar_one_or_none()
        if obj: obj.data = data
        else:
            self.session.add(IntakeSocialHistory(org_id=org, session_id=session_id, data=data))
        await self.session.flush()

    async def add_notes(self, org: uuid.UUID, session_id: uuid.UUID, notes: list[dict]):
        for n in notes:
            self.session.add(IntakeNote(org_id=org, session_id=session_id, text=n["text"], visibility=n.get("visibility","internal")))
        await self.session.flush()

    async def set_summary(self, org: uuid.UUID, session_id: uuid.UUID, text: str) -> IntakeSummary:
        res = await self.session.execute(select(IntakeSummary).where(
            IntakeSummary.org_id==org, IntakeSummary.session_id==session_id, IntakeSummary.deleted_at.is_(None)
        ))
        obj = res.scalar_one_or_none()
        if obj: obj.text = text
        else:
            obj = IntakeSummary(org_id=org, session_id=session_id, text=text)
            self.session.add(obj)
        await self.session.flush()
        return obj