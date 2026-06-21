"""GDPR/PIPEDA/PDPA consent record model."""
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.sql import func
from app.db.base import Base


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True)  # UUID
    tenant_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    consent_type = Column(String, nullable=False)
    # data_processing / analytics / benchmarking_contribution / regulatory_evidence / marketing
    jurisdiction = Column(String, nullable=False, default="us")
    # us / eu / uk / ca / au / sg / jp / kr
    granted = Column(Boolean, nullable=False, default=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    withdrawal_reason = Column(Text, nullable=True)
    legal_basis = Column(String, nullable=True)
    # gdpr_legitimate_interest / gdpr_consent / gdpr_contract / pipeda_consent / hipaa_authorization
    ip_address_hash = Column(String, nullable=True)  # SHA-256 of IP — never raw IP
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
