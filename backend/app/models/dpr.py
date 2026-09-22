from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum, DateTime, ForeignKey, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
import enum
from .equipment import ShiftType

class DPRStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"

class StrataType(str, enum.Enum):
    SOIL = "SOIL"
    CLAY = "CLAY"
    SAND = "SAND"
    WEATHERED_ROCK = "WEATHERED_ROCK"
    HARD_ROCK = "HARD_ROCK"
    MIXED = "MIXED"

class CasingType(str, enum.Enum):
    TEMPORARY = "TEMPORARY"
    PERMANENT = "PERMANENT"

class TestType(str, enum.Enum):
    SLUMP_TEST = "SLUMP_TEST"
    CUBE_CASTING = "CUBE_CASTING"
    BENTONITE_TEST = "BENTONITE_TEST"
    INTEGRITY_TEST = "INTEGRITY_TEST"

class PassFail(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class DailyProgressReport(Base):
    __tablename__ = "dprs"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    operational_date = Column(Date)
    shift = Column(SQLEnum(ShiftType))
    submitted_by = Column(Integer, ForeignKey("users.id"))
    submitted_at = Column(DateTime(timezone=True))
    status = Column(SQLEnum(DPRStatus), default=DPRStatus.DRAFT)
    weather_conditions = Column(String)
    problems_delays = Column(String)
    tomorrows_plan = Column(String)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('site_id', 'operational_date', 'shift', name='uix_site_date_shift_dpr'),)

class PileDailyProgress(Base):
    __tablename__ = "pile_daily_progresses"
    id = Column(Integer, primary_key=True, index=True)
    dpr_id = Column(Integer, ForeignKey("dprs.id"))
    pile_id = Column(Integer, ForeignKey("piles.id"))
    depth_drilled_today_m = Column(Float)
    cumulative_depth_m = Column(Float)
    empty_bore_depth_m = Column(Float)
    rock_socket_depth_today_m = Column(Float)
    strata_type = Column(SQLEnum(StrataType))
    casing_depth_m = Column(Float)
    casing_type = Column(SQLEnum(CasingType))
    cage_sections_lowered = Column(Integer)
    cage_weight_kg_today = Column(Float)
    concrete_volume_planned_m3 = Column(Float)
    concrete_volume_actual_m3 = Column(Float)
    slump_mm = Column(Float, nullable=True)
    bentonite_density_g_cc = Column(Float, nullable=True)
    boring_start_time = Column(DateTime(timezone=True), nullable=True)
    boring_end_time = Column(DateTime(timezone=True), nullable=True)
    delay_reason = Column(String, nullable=True)
    remarks = Column(String, nullable=True)
    photos = Column(JSONB, nullable=True)
    __table_args__ = (UniqueConstraint('dpr_id', 'pile_id', name='uix_dpr_pile'),)

class WellLog(Base):
    __tablename__ = "well_logs"
    id = Column(Integer, primary_key=True, index=True)
    dpr_id = Column(Integer, ForeignKey("dprs.id"))
    well_number = Column(String)
    steining_lift_number = Column(Integer)
    sinking_depth_today_cm = Column(Float)
    cumulative_sinking_depth_m = Column(Float)
    tilt_longitudinal_mm = Column(Float)
    tilt_transverse_mm = Column(Float)
    shift_mm = Column(Float)
    soil_type_at_cutting_edge = Column(String)
    water_level_m = Column(Float)
    remarks = Column(String)
    photos = Column(JSONB, nullable=True)
    __table_args__ = (UniqueConstraint('dpr_id', 'well_number', name='uix_dpr_well'),)

class EquipmentLog(Base):
    __tablename__ = "equipment_logs"
    id = Column(Integer, primary_key=True, index=True)
    dpr_id = Column(Integer, ForeignKey("dprs.id"))
    equipment_id = Column(Integer, ForeignKey("equipments.id"))
    opening_hours = Column(Float)
    closing_hours = Column(Float)
    working_hours = Column(Float)
    breakdown_hours = Column(Float)
    idle_hours = Column(Float)
    fuel_liters = Column(Float)
    breakdown_reason = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint('dpr_id', 'equipment_id', name='uix_dpr_equipment'),)

class LabourSummary(Base):
    __tablename__ = "labour_summaries"
    id = Column(Integer, primary_key=True, index=True)
    dpr_id = Column(Integer, ForeignKey("dprs.id"))
    category = Column(String)
    count = Column(Integer)
    shift = Column(SQLEnum(ShiftType))
    hours_worked = Column(Float)

class MaterialConsumption(Base):
    __tablename__ = "material_consumptions"
    id = Column(Integer, primary_key=True, index=True)
    dpr_id = Column(Integer, ForeignKey("dprs.id"))
    material_name = Column(String)
    unit = Column(String)
    quantity_used = Column(Float)
    remarks = Column(String, nullable=True)

class TestReport(Base):
    __tablename__ = "test_reports"
    id = Column(Integer, primary_key=True, index=True)
    dpr_id = Column(Integer, ForeignKey("dprs.id"))
    pile_progress_id = Column(Integer, ForeignKey("pile_daily_progresses.id"), nullable=True)
    test_type = Column(SQLEnum(TestType))
    result_value = Column(String)
    result_unit = Column(String)
    pass_fail = Column(SQLEnum(PassFail))
    photo_url = Column(String, nullable=True)
    remarks = Column(String)
