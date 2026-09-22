from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AnalysisDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"

class AIReviewResult(BaseModel):
    executive_summary: str = Field(description="2-3 sentence natural language summary of the day's operations")
    risk_assessment: RiskLevel = Field(description="Overall risk level for the day")
    key_insights: List[str] = Field(default_factory=list, description="Bullet-point observations about operations")
    recommendations: List[str] = Field(default_factory=list, description="Actionable next steps for management")
    anomaly_analysis: str = Field(default="", description="AI interpretation of detected anomalies")
    safety_concerns: List[str] = Field(default_factory=list, description="Safety-specific flags")
    productivity_score: int = Field(default=50, ge=0, le=100, description="AI-assessed productivity rating")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model confidence in assessment")

class AIReviewRequest(BaseModel):
    brief_data: Dict[str, Any]
    include_recommendations: bool = True
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD

class AIReviewResponse(BaseModel):
    review: AIReviewResult
    provider_used: str
    model_name: str
    tokens_used: Optional[int] = None
    latency_ms: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
