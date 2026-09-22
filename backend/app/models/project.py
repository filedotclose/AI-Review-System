from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"

class SiteStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class PileStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    BORING = "BORING"
    SOCKETING = "SOCKETING"
    CAGED = "CAGED"
    CAST = "CAST"
    COMPLETED = "COMPLETED"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True)
    client_name = Column(String)
    location = Column(String)
    contract_value = Column(Float)
    start_date = Column(Date)
    expected_end_date = Column(Date)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    sites = relationship("Site", back_populates="project")

class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String, nullable=False)
    location_lat = Column(Float)
    location_lng = Column(Float)
    geofence_radius_m = Column(Integer, default=500)
    status = Column(SQLEnum(SiteStatus), default=SiteStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    project = relationship("Project", back_populates="sites")
    piles = relationship("Pile", back_populates="site")

class Pile(Base):
    __tablename__ = "piles"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    pier_number = Column(String, nullable=False)
    pile_number = Column(String, nullable=False)
    diameter_mm = Column(Integer)
    cutoff_level_m = Column(Float)
    ground_level_m = Column(Float)
    planned_depth_m = Column(Float)
    planned_rock_socket_m = Column(Float)
    status = Column(SQLEnum(PileStatus), default=PileStatus.PLANNED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    site = relationship("Site", back_populates="piles")

    __table_args__ = (
        UniqueConstraint('site_id', 'pier_number', 'pile_number', name='uix_site_pier_pile'),
    )
