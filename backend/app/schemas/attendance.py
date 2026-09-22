from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.models.attendance import WorkerCategory, AttendanceStatus, GangTrade
from app.models.equipment import ShiftType

class WorkerCreate(BaseModel):
    name: str = Field(min_length=2)
    phone: Optional[str] = None
    category: WorkerCategory
    assigned_site_id: int

class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: Optional[str] = None
    category: WorkerCategory
    assigned_site_id: int
    is_active: bool
    created_at: datetime

class CheckInRequest(BaseModel):
    site_id: int
    worker_id: int
    date: date
    shift: ShiftType
    check_in_lat: Optional[float] = None
    check_in_lng: Optional[float] = None

class CheckOutRequest(BaseModel):
    record_id: Optional[int] = None
    worker_id: Optional[int] = None
    site_id: Optional[int] = None
    check_out_lat: Optional[float] = None
    check_out_lng: Optional[float] = None

class GangMusterCreate(BaseModel):
    site_id: int
    date: date
    shift: ShiftType
    subcontractor_name: str = Field(min_length=2)
    trade: GangTrade
    headcount_present: int = Field(gt=0)
    total_ot_hours: float = Field(default=0.0, ge=0.0)
    muster_roll_photo_url: Optional[str] = None

GangAttendanceCreate = GangMusterCreate

class GangMusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    date: date
    shift: ShiftType
    subcontractor_name: str
    trade: GangTrade
    headcount_present: int
    total_ot_hours: float
    muster_roll_photo_url: Optional[str] = None
    verified_by: int
    created_at: datetime

GangAttendanceResponse = GangMusterResponse

class WorkerAttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    worker_id: int
    date: date
    shift: ShiftType
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    check_in_lat: Optional[float] = None
    check_in_lng: Optional[float] = None
    check_out_lat: Optional[float] = None
    check_out_lng: Optional[float] = None
    within_geofence: bool
    hours_worked: Optional[float] = None
    overtime_hours: float
    verified_by_supervisor: Optional[int] = None
    verified_at: Optional[datetime] = None
    status: AttendanceStatus
    anomaly_flag: bool
    anomaly_reason: Optional[str] = None

AttendanceRecordResponse = WorkerAttendanceResponse

class AttendanceVerifyRequest(BaseModel):
    status: AttendanceStatus = AttendanceStatus.PRESENT
    remarks: Optional[str] = None

class AnomalyAlertResponse(BaseModel):
    id: Optional[int] = None
    anomaly_type: str
    site_id: int
    date: date
    shift: Optional[ShiftType] = None
    worker_id: Optional[int] = None
    subcontractor_name: Optional[str] = None
    description: str
    severity: str = "WARNING"
    detected_at: datetime
