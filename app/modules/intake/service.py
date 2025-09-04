import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.intake.repository import IntakeRepository
from app.modules.intake.schemas import IntakeRecordsUpsert
from app.modules.events.outbox import OutboxService
from app.modules.consent.service import ConsentService

class IntakeService:
    def __init__(self, s: AsyncSession):
        self.s = s
        self.repo = IntakeRepository(s)

    # --- sessions ---
    async def create_session(self, org: uuid.UUID, *, patient_id: uuid.UUID | None, conversation_id: uuid.UUID | None, context: dict | None):
        # If patient_id provided, ensure data_processing consent OR allow anonymous by clearing patient
        if patient_id:
            if not await ConsentService(self.s).is_allowed(org, patient_id, "data_processing"):
                # Keep session anonymous if consent missing
                patient_id = None
        obj = await self.repo.create_session(org, patient_id, conversation_id, context)
        await OutboxService(self.s).enqueue(org, "INTAKE_SESSION_CREATED", "intake_session", obj.id, {"patient_id": str(patient_id) if patient_id else None})
        await self.s.commit()
        return obj

    async def set_session_patient(self, org: uuid.UUID, session_id: uuid.UUID, patient_id: uuid.UUID | None):
        if patient_id and not await ConsentService(self.s).is_allowed(org, patient_id, "data_processing"):
            # reject linking without consent; caller can store PII then create consent
            return None, "consent_required"
        obj = await self.repo.set_patient(org, session_id, patient_id)
        if not obj: return None, "not_found"
        await OutboxService(self.s).enqueue(org, "INTAKE_SESSION_PATIENT_SET", "intake_session", obj.id, {"patient_id": str(patient_id) if patient_id else None})
        await self.s.commit()
        return obj, None

    async def submit(self, org: uuid.UUID, session_id: uuid.UUID):
        obj = await self.repo.submit(org, session_id)
        if not obj: return None
        await OutboxService(self.s).enqueue(org, "INTAKE_SUBMITTED", "intake_session", obj.id, {})
        await self.s.commit()
        return obj

    # --- records ---
    async def upsert_records(self, org: uuid.UUID, session_id: uuid.UUID, payload: IntakeRecordsUpsert):
        sess = await self.repo.get_session(org, session_id)
        if not sess: return None, "not_found"
        data = payload.model_dump(exclude_unset=True)

        if "chief_complaint" in data:
            cc = data["chief_complaint"]; await self.repo.upsert_chief(org, session_id, cc["text"], cc.get("codes"))

        if "symptoms" in data and data["symptoms"]:
            await self.repo._upsert_list_by_client_id(org, session_id, __import__("app.modules.intake.models", fromlist=["IntakeSymptom"]).IntakeSymptom, [s for s in data["symptoms"]], ["client_item_id"])

        if "allergies" in data and data["allergies"]:
            await self.repo._upsert_list_by_client_id(org, session_id, __import__("app.modules.intake.models", fromlist=["IntakeAllergy"]).IntakeAllergy, [a for a in data["allergies"]], ["client_item_id"])

        if "medications" in data and data["medications"]:
            await self.repo._upsert_list_by_client_id(org, session_id, __import__("app.modules.intake.models", fromlist=["IntakeMedication"]).IntakeMedication, [m for m in data["medications"]], ["client_item_id"])

        if "condition_history" in data and data["condition_history"]:
            await self.repo._upsert_list_by_client_id(org, session_id, __import__("app.modules.intake.models", fromlist=["IntakeConditionHistory"]).IntakeConditionHistory, [c for c in data["condition_history"]], ["client_item_id"])

        if "family_history" in data and data["family_history"]:
            await self.repo._upsert_list_by_client_id(org, session_id, __import__("app.modules.intake.models", fromlist=["IntakeFamilyHistory"]).IntakeFamilyHistory, [f for f in data["family_history"]], ["client_item_id"])

        if "social_history" in data and data["social_history"]:
            sh = data["social_history"]
            merged = {k:v for k,v in sh.items() if v is not None}
            await self.repo.set_social_history(org, session_id, merged)

        if "notes" in data and data["notes"]:
            await self.repo.add_notes(org, session_id, data["notes"])

        await OutboxService(self.s).enqueue(org, "INTAKE_RECORD_UPSERTED", "intake_session", session_id, {"sections": list(data.keys())})
        await self.s.commit()
        return {"updated": True, "sections": list(data.keys())}, None

    async def set_summary(self, org: uuid.UUID, session_id: uuid.UUID, text: str):
        sess = await self.repo.get_session(org, session_id)
        if not sess: return None, "not_found"
        obj = await self.repo.set_summary(org, session_id, text)
        await OutboxService(self.s).enqueue(org, "INTAKE_SUMMARY_SET", "intake_session", session_id, {"length": len(text)})
        await self.s.commit()
        return obj, None

    async def get_session(self, org: uuid.UUID, session_id: uuid.UUID):
        return await self.repo.get_session(org, session_id)

    async def list_sessions(self, org: uuid.UUID, **filters):
        return await self.repo.list_sessions(org, **filters)