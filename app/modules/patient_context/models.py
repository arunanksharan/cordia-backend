import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, ForeignKey, Boolean, Date, UniqueConstraint
from app.core.base import Base, TimestampedTenantMixin
from datetime import date

# 1) Profile (1:1 with Patient) — demographics & preferences
class PatientProfile(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"), unique=True, index=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex_at_birth: Mapped[str | None] = mapped_column(String(32), nullable=True)        # male|female|intersex|unknown
    gender_identity: Mapped[str | None] = mapped_column(String(64), nullable=True)     # free text or code
    pronouns: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)            # BCP-47, e.g. en-IN
    timezone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    interpreter_needed: Mapped[bool] = mapped_column(default=False)
    accessibility: Mapped[dict | None] = mapped_column(JSON, nullable=True)            # {"wheelchair":true,...}
    contact_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)      # {"method":"sms","quiet_hours":[22,7]}

# 2) Identifiers (MRN, payer member id, external ids) — many per patient
class PatientIdentifier(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"), index=True)
    system: Mapped[str] = mapped_column(String(100))    # e.g., "hospital:abc", "payer:xyz", "portal"
    type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # mrn|member|national|other
    value: Mapped[str] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("org_id","patient_id","system","value", name="uq_ident_unique"),)

# 3) Addresses — many per patient
class PatientAddress(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"), index=True)
    use: Mapped[str] = mapped_column(String(16))  # home|work|mailing|temp
    line1: Mapped[str] = mapped_column(String(100))
    line2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    geocode: Mapped[dict | None] = mapped_column(JSON, nullable=True)      # {"lat":..,"lng":..}

# 4) Coverage / Insurance — many per patient
class PatientCoverage(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"), index=True)
    payer: Mapped[str] = mapped_column(String(120))              # e.g., "Aetna"
    plan: Mapped[str | None] = mapped_column(String(120), nullable=True)
    member_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    group_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    period: Mapped[dict | None] = mapped_column(JSON, nullable=True)       # {"start":"YYYY-MM-DD","end":"YYYY-MM-DD"}
    relationship: Mapped[str | None] = mapped_column(String(20), nullable=True)  # self|spouse|child|other
    is_primary: Mapped[bool] = mapped_column(default=True)

# 5) Tags / Segments — many per patient (lightweight CRM flags)
class PatientTag(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"), index=True)
    tag: Mapped[str] = mapped_column(String(64))         # e.g., "vip", "high_risk", "self_pay"
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)  # rule|manual|campaign

# 6) SDOH flags — sparse, consent-sensitive
class PatientSdoh(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"), index=True)
    data: Mapped[dict] = mapped_column(JSON)             # {"transportation":"barrier","caregiver":"limited"}

# 7) External Account links — portal/app identity
class ExternalAccountLink(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64))    # "portal"|"oidc:google"|"mobile"
    subject: Mapped[str] = mapped_column(String(120))    # sub/username/uid
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)         # device tokens (hashed), etc.
    __table_args__ = (UniqueConstraint("org_id","provider","subject", name="uq_external_subject"),)