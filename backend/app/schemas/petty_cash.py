from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.models.petty_cash import (
    TransactionType,
    ExpenseCategory,
    ReimbursementStatus,
    ApprovalStatus,
    ReconciliationStatus,
)

class ExpenseCreate(BaseModel):
    wallet_id: Optional[int] = None
    site_id: Optional[int] = None
    project_id: Optional[int] = None
    amount: float = Field(gt=0.0, description="Expense amount must be strictly positive")
    category: ExpenseCategory
    quantity: Optional[float] = None
    unit: Optional[str] = None
    description: str = Field(min_length=3)
    receipt_photo_url: Optional[str] = None
    has_physical_bill: bool = False
    date: date

class ReplenishmentCreate(BaseModel):
    wallet_id: int
    amount: float = Field(gt=0.0)
    description: str = Field(min_length=3)

class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    wallet_id: int
    project_id: int
    type: TransactionType
    amount: float
    category: ExpenseCategory
    quantity: Optional[float] = None
    unit: Optional[str] = None
    description: str
    receipt_photo_url: Optional[str] = None
    has_physical_bill: bool
    is_out_of_pocket: bool
    reimbursement_status: ReimbursementStatus
    reimbursed_at: Optional[datetime] = None
    reimbursed_by: Optional[int] = None
    reimbursement_ref: Optional[str] = None
    recorded_by: int
    approved_by: Optional[int] = None
    approval_status: ApprovalStatus
    duplicate_flag: bool
    anomaly_flag: bool
    anomaly_reason: Optional[str] = None
    date: date
    created_at: datetime

class WalletBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    current_balance: float
    supervisor_deficit: float = 0.0
    last_replenishment_date: Optional[datetime] = None
    last_reconciliation_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

# Alias
WalletResponse = WalletBalanceResponse

class ReimbursementCreate(BaseModel):
    wallet_id: int
    transaction_ids: Optional[List[int]] = None
    amount: float = Field(gt=0.0)
    reimbursement_ref: Optional[str] = None
    remarks: Optional[str] = None

class ReimbursementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    wallet_id: int
    amount: float
    reimbursement_status: ReimbursementStatus
    reimbursement_ref: Optional[str] = None
    reimbursed_at: Optional[datetime] = None
    reimbursed_by: Optional[int] = None

class ReimbursementSettleRequest(BaseModel):
    reimbursement_ref: str = Field(min_length=1)

class ExpenseApprovalRequest(BaseModel):
    approval_status: ApprovalStatus = ApprovalStatus.APPROVED
    remarks: Optional[str] = None

class ReconciliationCreate(BaseModel):
    wallet_id: int
    period_start: datetime
    period_end: datetime
    opening_balance: float
    total_replenishments: float
    total_expenses: float
    total_out_of_pocket_claimed: float = 0.0
    expected_closing: float
    actual_closing: float
    discrepancy: float = 0.0
    remarks: Optional[str] = None

class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    wallet_id: int
    period_start: datetime
    period_end: datetime
    opening_balance: float
    total_replenishments: float
    total_expenses: float
    total_out_of_pocket_claimed: float
    expected_closing: float
    actual_closing: float
    discrepancy: float
    reconciled_by: int
    reconciled_at: datetime
    status: ReconciliationStatus
    remarks: Optional[str] = None

class TallyExportResponse(BaseModel):
    format: str = "tally-xml"
    exported_at: datetime
    transaction_count: int
    total_amount: float
    xml_payload: Optional[str] = None
    download_url: Optional[str] = None
