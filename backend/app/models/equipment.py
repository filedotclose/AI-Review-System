from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum, DateTime, ForeignKey, Date, Boolean, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class EquipmentType(str, enum.Enum):
    RIG = "RIG"
    CRANE = "CRANE"
    EXCAVATOR = "EXCAVATOR"
    PUMP = "PUMP"
    GENERATOR = "GENERATOR"
    BARGE = "BARGE"
    OTHER = "OTHER"

class EquipmentStatus(str, enum.Enum):
    OPERATIONAL = "OPERATIONAL"
    BREAKDOWN = "BREAKDOWN"
    IDLE = "IDLE"

class ShiftType(str, enum.Enum):
    DAY = "DAY"
    NIGHT = "NIGHT"

class Equipment(Base):
    __tablename__ = "equipments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(SQLEnum(EquipmentType))
    registration_number = Column(String)
    site_id = Column(Integer, ForeignKey("sites.id"))
    fuel_benchmark_liters_per_hour = Column(Float)
    status = Column(SQLEnum(EquipmentStatus), default=EquipmentStatus.OPERATIONAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SiteFuelRegister(Base):
    __tablename__ = "site_fuel_registers"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    dpr_id = Column(Integer, nullable=True) # Will link to DailyProgressReport
    date = Column(Date)
    shift = Column(SQLEnum(ShiftType))
    opening_stock_liters = Column(Float)
    received_bowser_liters = Column(Float)
    received_drums_liters = Column(Float)
    total_issued_to_equipment_liters = Column(Float)
    closing_dip_stock_liters = Column(Float)
    variance_liters = Column(Float)
    recorded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint('site_id', 'date', 'shift', name='uix_site_date_shift_fuel'),
        CheckConstraint('closing_dip_stock_liters >= 0', name='check_positive_dip'),
        CheckConstraint('total_issued_to_equipment_liters <= (opening_stock_liters + received_bowser_liters + received_drums_liters)', name='check_valid_issuance'),
    )

class SiteInventory(Base):
    __tablename__ = "site_inventories"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    material_name = Column(String)
    unit = Column(String)
    current_stock = Column(Float)
    reorder_threshold = Column(Float)
    last_updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    __table_args__ = (UniqueConstraint('site_id', 'material_name', name='uix_site_material'),)
