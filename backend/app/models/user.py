from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, DateTime
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    FINANCE_HEAD = "FINANCE_HEAD"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    SITE_ENGINEER = "SITE_ENGINEER"
    SUPERVISOR = "SUPERVISOR"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    pin_hash = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
