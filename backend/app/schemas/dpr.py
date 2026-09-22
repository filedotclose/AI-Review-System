from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import date, datetime
from app.models.dpr import DPRStatus, StrataType, CasingType, TestType, PassFail
from app.models.equipment import ShiftType

class PilingProgressCreate(BaseModel):
    pile_id: int
    depth_drilled_today_m: float = Field(ge=0.0)
    cumulative_depth_m: float = Field(ge=0.0)
    empty_bore_depth_m: float = Field(default=0.0, ge=0.0)
    rock_socket_depth_today_m: float = Field(default=0.0, ge=0.0)
    strata_type: StrataType
    casing_depth_m: float = Field(default=0.0, ge=0.0)
    casing_type: CasingType = CasingType.TEMPORARY
    cage_sections_lowered: int = Field(default=0, ge=0)
    cage_weight_kg_today: float = Field(default=0.0, ge=0.0)
    concrete_volume_planned_m3: float = Field(default=0.0, ge=0.0)
    concrete_volume_actual_m3: float = Field(default=0.0, ge=0.0)
    slump_mm: Optional[float] = None
    bentonite_density_g_cc: Optional[float] = None
    boring_start_time: Optional[datetime] = None
    boring_end_time: Optional[datetime] = None
    delay_reason: Optional[str] = None
    remarks: Optional[str] = None
    photos: Optional[List[str]] = None

class PilingProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dpr_id: int
    pile_id: int
    depth_drilled_today_m: float
    cumulative_depth_m: float
    empty_bore_depth_m: float
    rock_socket_depth_today_m: float
    strata_type: StrataType
    casing_depth_m: float
    casing_type: CasingType
    cage_sections_lowered: int
    cage_weight_kg_today: float
    concrete_volume_planned_m3: float
    concrete_volume_actual_m3: float
    slump_mm: Optional[float] = None
    bentonite_density_g_cc: Optional[float] = None
    boring_start_time: Optional[datetime] = None
    boring_end_time: Optional[datetime] = None
    delay_reason: Optional[str] = None
    remarks: Optional[str] = None
    photos: Optional[Any] = None

# Aliases for compatibility
PileDailyProgressCreate = PilingProgressCreate
PileDailyProgressResponse = PilingProgressResponse

class WellLogCreate(BaseModel):
    well_number: str
    steining_lift_number: int = Field(ge=1)
    sinking_depth_today_cm: float = Field(ge=0.0)
    cumulative_sinking_depth_m: float = Field(ge=0.0)
    tilt_longitudinal_mm: float = Field(default=0.0)
    tilt_transverse_mm: float = Field(default=0.0)
    shift_mm: float = Field(default=0.0)
    soil_type_at_cutting_edge: str
    water_level_m: float = Field(default=0.0)
    remarks: Optional[str] = ""
    photos: Optional[List[str]] = None

class WellLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dpr_id: int
    well_number: str
    steining_lift_number: int
    sinking_depth_today_cm: float
    cumulative_sinking_depth_m: float
    tilt_longitudinal_mm: float
    tilt_transverse_mm: float
    shift_mm: float
    soil_type_at_cutting_edge: str
    water_level_m: float
    remarks: Optional[str] = None
    photos: Optional[Any] = None

class EquipmentShiftCreate(BaseModel):
    equipment_id: int
    opening_hours: float = Field(ge=0.0)
    closing_hours: float = Field(ge=0.0)
    working_hours: float = Field(ge=0.0)
    breakdown_hours: float = Field(default=0.0, ge=0.0)
    idle_hours: float = Field(default=0.0, ge=0.0)
    fuel_liters: float = Field(default=0.0, ge=0.0)
    breakdown_reason: Optional[str] = None

class EquipmentShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dpr_id: int
    equipment_id: int
    opening_hours: float
    closing_hours: float
    working_hours: float
    breakdown_hours: float
    idle_hours: float
    fuel_liters: float
    breakdown_reason: Optional[str] = None

EquipmentLogCreate = EquipmentShiftCreate
EquipmentLogResponse = EquipmentShiftResponse

class DelayLogCreate(BaseModel):
    pile_id: Optional[int] = None
    delay_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: float = Field(default=0.0, ge=0.0)
    reason: str
    action_taken: Optional[str] = None

class DelayLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    dpr_id: Optional[int] = None
    pile_id: Optional[int] = None
    delay_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: float = 0.0
    reason: str
    action_taken: Optional[str] = None

class ManpowerEntryCreate(BaseModel):
    category: str
    count: int = Field(ge=0)
    shift: ShiftType
    hours_worked: float = Field(ge=0.0)

class ManpowerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dpr_id: int
    category: str
    count: int
    shift: ShiftType
    hours_worked: float

LabourSummaryCreate = ManpowerEntryCreate
LabourSummaryResponse = ManpowerEntryResponse

class MaterialConsumptionCreate(BaseModel):
    material_name: str
    unit: str
    quantity_used: float = Field(ge=0.0)
    remarks: Optional[str] = None

class MaterialConsumptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dpr_id: int
    material_name: str
    unit: str
    quantity_used: float
    remarks: Optional[str] = None

class TestReportCreate(BaseModel):
    pile_progress_id: Optional[int] = None
    test_type: TestType
    result_value: str
    result_unit: str
    pass_fail: PassFail
    photo_url: Optional[str] = None
    remarks: Optional[str] = ""

class TestReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dpr_id: int
    pile_progress_id: Optional[int] = None
    test_type: TestType
    result_value: str
    result_unit: str
    pass_fail: PassFail
    photo_url: Optional[str] = None
    remarks: Optional[str] = None

class DPRCreate(BaseModel):
    site_id: int
    operational_date: date
    shift: ShiftType
    weather_conditions: Optional[str] = ""
    problems_delays: Optional[str] = ""
    tomorrows_plan: Optional[str] = ""
    pile_progress: Optional[List[PilingProgressCreate]] = []
    well_logs: Optional[List[WellLogCreate]] = []
    equipment_logs: Optional[List[EquipmentShiftCreate]] = []
    equipment_shifts: Optional[List[EquipmentShiftCreate]] = []
    delays: Optional[List[DelayLogCreate]] = []
    labour_summaries: Optional[List[ManpowerEntryCreate]] = []
    manpower_entries: Optional[List[ManpowerEntryCreate]] = []
    material_consumptions: Optional[List[MaterialConsumptionCreate]] = []
    test_reports: Optional[List[TestReportCreate]] = []

class DPRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    operational_date: date
    shift: ShiftType
    submitted_by: int
    submitted_at: Optional[datetime] = None
    status: DPRStatus
    weather_conditions: Optional[str] = None
    problems_delays: Optional[str] = None
    tomorrows_plan: Optional[str] = None
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    pile_progress: Optional[List[PilingProgressResponse]] = None
    well_logs: Optional[List[WellLogResponse]] = None
    equipment_logs: Optional[List[EquipmentShiftResponse]] = None
    labour_summaries: Optional[List[ManpowerEntryResponse]] = None
    material_consumptions: Optional[List[MaterialConsumptionResponse]] = None
    test_reports: Optional[List[TestReportResponse]] = None

class DPRVerifyRequest(BaseModel):
    status: DPRStatus = DPRStatus.VERIFIED
    remarks: Optional[str] = None
