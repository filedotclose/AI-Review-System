from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.models.project import ProjectStatus, SiteStatus, PileStatus

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2)
    code: str = Field(min_length=2)
    client_name: Optional[str] = None
    location: Optional[str] = None
    contract_value: Optional[float] = None
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    status: ProjectStatus = ProjectStatus.ACTIVE

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    client_name: Optional[str] = None
    location: Optional[str] = None
    contract_value: Optional[float] = None
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    status: ProjectStatus
    created_at: datetime

class SiteCreate(BaseModel):
    project_id: int
    name: str = Field(min_length=2)
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    geofence_radius_m: int = Field(default=500, ge=10)
    status: SiteStatus = SiteStatus.ACTIVE

class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    geofence_radius_m: int
    status: SiteStatus
    created_at: datetime

class PileCreate(BaseModel):
    site_id: int
    pier_number: str
    pile_number: str
    diameter_mm: int = Field(ge=400, description="Minimum pile diameter is 400mm")
    cutoff_level_m: Optional[float] = None
    ground_level_m: Optional[float] = None
    planned_depth_m: Optional[float] = None
    planned_rock_socket_m: Optional[float] = None
    status: PileStatus = PileStatus.PLANNED

class PileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    pier_number: str
    pile_number: str
    diameter_mm: int
    cutoff_level_m: Optional[float] = None
    ground_level_m: Optional[float] = None
    planned_depth_m: Optional[float] = None
    planned_rock_socket_m: Optional[float] = None
    status: PileStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
