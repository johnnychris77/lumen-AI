from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    file_name = Column(String, nullable=False)
    stain_detected = Column(Boolean, default=False, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    material_type = Column(String, default="unknown", nullable=False)
    status = Column(String, default="queued", nullable=False)
