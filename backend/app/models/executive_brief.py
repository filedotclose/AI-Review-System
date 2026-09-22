from sqlalchemy import Column, Integer, Enum as SQLEnum, DateTime, Date
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
import enum

class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"

class DeliveryChannel(str, enum.Enum):
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    BOTH = "BOTH"

class ExecutiveBrief(Base):
    __tablename__ = "executive_briefs"
    id = Column(Integer, primary_key=True, index=True)
    operational_date = Column(Date)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    delivery_status = Column(SQLEnum(DeliveryStatus), default=DeliveryStatus.PENDING)
    delivery_channel = Column(SQLEnum(DeliveryChannel))
    brief_data = Column(JSONB)
    alerts = Column(JSONB)
    ai_review = Column(JSONB, nullable=True)  # Stores AIReviewResult from AI verification
    created_at = Column(DateTime(timezone=True), server_default=func.now())
