from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List
from datetime import date, datetime
from app.models.equipment import ShiftType

class FuelIssuanceEntry(BaseModel):
    equipment_id: int
    liters_issued: float = Field(ge=0.0)
    meter_reading: Optional[float] = None
    remarks: Optional[str] = None

class FuelRegisterCreate(BaseModel):
    site_id: int
    date: date
    shift: ShiftType
    opening_stock_liters: float = Field(default=0.0, ge=0.0)
    received_bowser_liters: float = Field(default=0.0, ge=0.0)
    received_drums_liters: float = Field(default=0.0, ge=0.0)
    total_issued_to_equipment_liters: float = Field(default=0.0, ge=0.0)
    closing_dip_stock_liters: float = Field(ge=0.0)
    dpr_id: Optional[int] = None
    issuances: Optional[List[FuelIssuanceEntry]] = None

    @model_validator(mode='after')
    def validate_fuel_rules(self) -> 'FuelRegisterCreate':
        if self.closing_dip_stock_liters < 0:
            raise ValueError("Negative fuel dip is physically impossible.")
        total_input = self.opening_stock_liters + self.received_bowser_liters + self.received_drums_liters
        if self.total_issued_to_equipment_liters > total_input:
            raise ValueError("Ghost issuance: Cannot issue more fuel than is physically in the tank.")
        return self

class FuelRegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    dpr_id: Optional[int] = None
    date: date
    shift: ShiftType
    opening_stock_liters: float
    received_bowser_liters: float
    received_drums_liters: float
    total_issued_to_equipment_liters: float
    closing_dip_stock_liters: float
    variance_liters: float
    recorded_by: int
    created_at: datetime
