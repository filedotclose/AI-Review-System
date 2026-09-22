from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Any, Optional
from datetime import date, datetime
from app.models.executive_brief import DeliveryStatus, DeliveryChannel

class MetricCard(BaseModel):
    title: str
    value: Any
    target: Optional[float] = None
    unit: Optional[str] = None
    trend: Optional[str] = None
    status: Optional[str] = "NORMAL"

class OperationalSummary(BaseModel):
    piling_linear_meters: float = 0.0
    wells_sunk_cm: float = 0.0
    total_manpower_headcount: int = 0
    diesel_consumed_liters: float = 0.0
    petty_cash_spent: float = 0.0
    active_delays_count: int = 0
    critical_alerts_count: int = 0

class BriefGenerateRequest(BaseModel):
    operational_date: date
    delivery_channel: DeliveryChannel = DeliveryChannel.BOTH

class ExecutiveBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    operational_date: date
    generated_at: datetime
    delivery_status: DeliveryStatus
    delivery_channel: DeliveryChannel
    brief_data: Dict[str, Any] = {}
    alerts: List[Dict[str, Any]] = []
    summary: Optional[OperationalSummary] = None
    metric_cards: Optional[List[MetricCard]] = None
    ai_review: Optional[Dict[str, Any]] = None
    ai_provider: Optional[str] = None
    created_at: datetime

# Alias
BriefResponse = ExecutiveBriefResponse
