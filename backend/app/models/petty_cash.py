from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum, DateTime, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class TransactionType(str, enum.Enum):
    REPLENISHMENT = "REPLENISHMENT"
    EXPENSE = "EXPENSE"

class ExpenseCategory(str, enum.Enum):
    TRANSPORT = "TRANSPORT"
    FUEL = "FUEL"
    TOOLS = "TOOLS"
    WELDING_REPAIR = "WELDING_REPAIR"
    FOOD_WATER = "FOOD_WATER"
    LABOUR = "LABOUR"
    MATERIAL = "MATERIAL"
    VEHICLE = "VEHICLE"
    ACCOMMODATION = "ACCOMMODATION"
    OTHER = "OTHER"

class ReimbursementStatus(str, enum.Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    DUE = "DUE"
    SETTLED = "SETTLED"

class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ReconciliationStatus(str, enum.Enum):
    BALANCED = "BALANCED"
    DISCREPANCY = "DISCREPANCY"
    SETTLED = "SETTLED"

class PettyCashWallet(Base):
    __tablename__ = "petty_cash_wallets"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    current_balance = Column(Float, default=0.0)
    last_replenishment_date = Column(DateTime(timezone=True), nullable=True)
    last_reconciliation_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PettyCashTransaction(Base):
    __tablename__ = "petty_cash_transactions"
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("petty_cash_wallets.id"))
    type = Column(SQLEnum(TransactionType))
    amount = Column(Float)
    category = Column(SQLEnum(ExpenseCategory))
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    description = Column(String)
    receipt_photo_url = Column(String, nullable=True)
    has_physical_bill = Column(Boolean)
    is_out_of_pocket = Column(Boolean, default=False)
    reimbursement_status = Column(SQLEnum(ReimbursementStatus), default=ReimbursementStatus.NOT_APPLICABLE)
    reimbursed_at = Column(DateTime(timezone=True), nullable=True)
    reimbursed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reimbursement_ref = Column(String, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    duplicate_flag = Column(Boolean, default=False)
    anomaly_flag = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PettyCashReconciliation(Base):
    __tablename__ = "petty_cash_reconciliations"
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("petty_cash_wallets.id"))
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    opening_balance = Column(Float)
    total_replenishments = Column(Float)
    total_expenses = Column(Float)
    total_out_of_pocket_claimed = Column(Float)
    expected_closing = Column(Float)
    actual_closing = Column(Float)
    discrepancy = Column(Float)
    reconciled_by = Column(Integer, ForeignKey("users.id"))
    reconciled_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(SQLEnum(ReconciliationStatus))
    remarks = Column(String, nullable=True)
