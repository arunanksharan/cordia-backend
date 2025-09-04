from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, UniqueConstraint
from app.core.base import Base, TimestampedTenantMixin

class CodeSet(Base, TimestampedTenantMixin):
    name: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (UniqueConstraint("org_id","name",name="uq_codeset_org_name"),)

class CodeValue(Base, TimestampedTenantMixin):
    set_name: Mapped[str] = mapped_column(String(64))  # denormalized for simplicity
    code: Mapped[str] = mapped_column(String(64))
    display: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (UniqueConstraint("org_id","set_name","code",name="uq_codevalue_org_set_code"),)