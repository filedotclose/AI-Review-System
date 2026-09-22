from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum, DateTime, ForeignKey, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum
from .equipment import ShiftType

class WorkerCategory(str, enum.Enum):
    OPERATOR = "OPERATOR"
    RIG_HELPER = "RIG_HELPER"
    WELDER = "WELDER"
    FITTER = "FITTER"
    LABOURER = "LABOURER"
    DRIVER = "DRIVER"
    OTHER = "OTHER"

class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"
    ON_LEAVE = "ON_LEAVE"

class GangTrade(str, enum.Enum):
    PILING_GANG = "PILING_GANG"
    STEEL_BENDING = "STEEL_BENDING"
    CONCRETING = "CONCRETING"
    CARPENTRY = "CARPENTRY"
    EARTHWORK = "EARTHWORK"
    OTHER = "OTHER"

class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    category = Column(SQLEnum(WorkerCategory))
    assigned_site_id = Column(Integer, ForeignKey("sites.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    worker_id = Column(Integer, ForeignKey("workers.id"))
    date = Column(Date)
    shift = Column(SQLEnum(ShiftType))
    check_in_time = Column(DateTime(timezone=True))
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    check_in_lat = Column(Float, nullable=True)
    check_in_lng = Column(Float, nullable=True)
    check_out_lat = Column(Float, nullable=True)
    check_out_lng = Column(Float, nullable=True)
    within_geofence = Column(Boolean, default=True)
    hours_worked = Column(Float, nullable=True)
    overtime_hours = Column(Float, default=0)
    verified_by_supervisor = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    anomaly_flag = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint('worker_id', 'date', 'shift', name='uix_worker_date_shift_att'),)

class GangAttendanceRecord(Base):
    __tablename__ = "gang_attendance_records"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    date = Column(Date)
    shift = Column(SQLEnum(ShiftType))
    subcontractor_name = Column(String)
    trade = Column(SQLEnum(GangTrade))
    headcount_present = Column(Integer)
    total_ot_hours = Column(Float)
    muster_roll_photo_url = Column(String, nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('site_id', 'date', 'shift', 'subcontractor_name', 'trade', name='uix_site_date_shift_gang'),)
