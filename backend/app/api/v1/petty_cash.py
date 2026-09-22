from datetime import datetime, date, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Site
from app.models.petty_cash import (
    PettyCashWallet,
    PettyCashTransaction,
    TransactionType,
    ExpenseCategory,
    ReimbursementStatus,
    ApprovalStatus,
    ReconciliationStatus,
)
from app.schemas.petty_cash import (
    ExpenseCreate,
    ExpenseResponse,
    ReplenishmentCreate,
    WalletBalanceResponse,
    ReimbursementCreate,
    ReimbursementResponse,
    ReimbursementSettleRequest,
    ExpenseApprovalRequest,
    TallyExportResponse,
)
from app.services.anomaly_service import AnomalyDetector

router = APIRouter()


async def _get_or_create_wallet(
    db: AsyncSession,
    wallet_id: Optional[int] = None,
    site_id: Optional[int] = None,
) -> PettyCashWallet:
    """Helper to locate or initialize a PettyCashWallet for site or ID."""
    wallet = None
    if wallet_id is not None:
        wallet = await db.get(PettyCashWallet, wallet_id)
        if wallet is not None:
            return wallet

    if site_id is not None:
        stmt = select(PettyCashWallet).where(PettyCashWallet.site_id == site_id)
        result = await db.execute(stmt)
        wallet = result.scalar_one_or_none()
        if wallet is not None:
            return wallet

        # Verify site exists
        site = await db.get(Site, site_id)
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {site_id} not found.",
            )

        wallet = PettyCashWallet(
            site_id=site_id,
            current_balance=0.0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        return wallet

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either wallet_id or site_id must be provided.",
    )


# ==============================================================================
# 1. Expense Creation (Vulnerability 4 & 5 Enforcement)
# ==============================================================================

@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/expense",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/petty-cash/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/petty-cash/expense",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_expense(
    expense_in: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log a petty cash expense.
    Enforces:
    - Vulnerability 4: Duplicate expense check with float epsilon (<0.01) and
      actual expense date comparison within 7 days via AnomalyDetector.check_duplicate_expense.
    - Vulnerability 5: Permissive deficit cap strictly limited to ₹50,000
      via AnomalyDetector.process_petty_cash. Deficit exceeding ₹50,000 is rejected with HTTP 400.
    """
    # 1. Resolve target wallet
    wallet = await _get_or_create_wallet(db, wallet_id=expense_in.wallet_id, site_id=expense_in.site_id)

    # 2. Resolve project_id
    project_id = expense_in.project_id
    if project_id is None:
        site = await db.get(Site, wallet.site_id)
        project_id = site.project_id if site else 1

    # 3. Duplicate check within 7 days of actual expense date (Vulnerability 4)
    check_date = datetime.combine(expense_in.date, datetime.min.time())
    start_date = expense_in.date - timedelta(days=7)
    end_date = expense_in.date + timedelta(days=7)

    stmt = select(PettyCashTransaction).where(
        PettyCashTransaction.wallet_id == wallet.id,
        PettyCashTransaction.type == TransactionType.EXPENSE,
        PettyCashTransaction.date >= start_date,
        PettyCashTransaction.date <= end_date,
    )
    res = await db.execute(stmt)
    existing_txs = res.scalars().all()

    existing_expenses_data = [
        {
            "amount": tx.amount,
            "description": tx.description or "",
            "date": datetime.combine(tx.date, datetime.min.time()),
        }
        for tx in existing_txs
    ]

    is_duplicate, dup_reason = AnomalyDetector.check_duplicate_expense(
        new_amount=expense_in.amount,
        new_desc=expense_in.description,
        new_date=check_date,
        existing_expenses=existing_expenses_data,
    )
    if is_duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate expense detected: {dup_reason}",
        )

    # 4. Permissive deficit processing and ₹50,000 cap (Vulnerability 5)
    try:
        new_balance, is_out_of_pocket = AnomalyDetector.process_petty_cash(
            wallet_balance=wallet.current_balance,
            expense_amount=expense_in.amount,
            max_deficit=50000.0,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # 5. Missing physical receipt check
    anomaly_flag = False
    anomaly_reason = None
    if expense_in.amount > 500.0 and not expense_in.receipt_photo_url and not expense_in.has_physical_bill:
        anomaly_flag = True
        anomaly_reason = "Missing receipt or physical bill for expense > 500"

    # 6. Apply wallet balance deduction
    wallet.current_balance = new_balance

    # 7. Create PettyCashTransaction entity
    tx = PettyCashTransaction(
        wallet_id=wallet.id,
        type=TransactionType.EXPENSE,
        amount=expense_in.amount,
        category=expense_in.category,
        quantity=expense_in.quantity,
        unit=expense_in.unit,
        description=expense_in.description,
        receipt_photo_url=expense_in.receipt_photo_url,
        has_physical_bill=expense_in.has_physical_bill,
        is_out_of_pocket=is_out_of_pocket,
        reimbursement_status=(
            ReimbursementStatus.DUE if is_out_of_pocket else ReimbursementStatus.NOT_APPLICABLE
        ),
        recorded_by=current_user.id,
        approval_status=ApprovalStatus.PENDING,
        duplicate_flag=False,
        anomaly_flag=anomaly_flag,
        anomaly_reason=anomaly_reason,
        project_id=project_id,
        date=expense_in.date,
        created_at=datetime.now(timezone.utc),
    )
    db.add(tx)

    try:
        await db.commit()
        await db.refresh(tx)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
        )

    return ExpenseResponse.model_validate(tx)


# ==============================================================================
# 2. Expense Listing and Details
# ==============================================================================

@router.get(
    "/expenses",
    response_model=List[ExpenseResponse],
)
@router.get(
    "/petty-cash/expenses",
    response_model=List[ExpenseResponse],
    include_in_schema=False,
)
async def list_expenses(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    wallet_id: Optional[int] = Query(None, description="Filter by wallet ID"),
    category: Optional[ExpenseCategory] = Query(None, description="Filter by category"),
    status_filter: Optional[ApprovalStatus] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List expenses filtered by site, wallet, category, or approval status."""
    stmt = (
        select(PettyCashTransaction)
        .where(PettyCashTransaction.type == TransactionType.EXPENSE)
        .order_by(PettyCashTransaction.date.desc(), PettyCashTransaction.id.desc())
    )

    conditions = []
    if wallet_id is not None:
        conditions.append(PettyCashTransaction.wallet_id == wallet_id)
    elif site_id is not None:
        wallet_subq = select(PettyCashWallet.id).where(PettyCashWallet.site_id == site_id)
        conditions.append(PettyCashTransaction.wallet_id.in_(wallet_subq))

    if category is not None:
        conditions.append(PettyCashTransaction.category == category)
    if status_filter is not None:
        conditions.append(PettyCashTransaction.approval_status == status_filter)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    txs = result.scalars().all()

    return [ExpenseResponse.model_validate(tx) for tx in txs]


@router.get(
    "/expenses/{id}",
    response_model=ExpenseResponse,
)
@router.get(
    "/petty-cash/expenses/{id}",
    response_model=ExpenseResponse,
    include_in_schema=False,
)
async def get_expense(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a single petty cash expense by transaction ID."""
    tx = await db.get(PettyCashTransaction, id)
    if not tx or tx.type != TransactionType.EXPENSE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with id {id} not found.",
        )
    return ExpenseResponse.model_validate(tx)


# ==============================================================================
# 3. Wallet Balance & Deficit Status
# ==============================================================================

@router.get(
    "/wallet/{site_id}",
    response_model=WalletBalanceResponse,
)
@router.get(
    "/petty-cash/wallet/{site_id}",
    response_model=WalletBalanceResponse,
    include_in_schema=False,
)
async def get_wallet(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve current wallet balance, supervisor out-of-pocket deficit totals,
    and replenishment history for a site.
    """
    wallet = await _get_or_create_wallet(db, site_id=site_id)

    supervisor_deficit = round(abs(wallet.current_balance), 2) if wallet.current_balance < 0 else 0.0

    return WalletBalanceResponse(
        id=wallet.id,
        site_id=wallet.site_id,
        current_balance=round(wallet.current_balance, 2),
        supervisor_deficit=supervisor_deficit,
        last_replenishment_date=wallet.last_replenishment_date,
        last_reconciliation_date=wallet.last_reconciliation_date,
        created_at=wallet.created_at,
    )


# ==============================================================================
# 4. Replenishment & Reimbursements
# ==============================================================================

@router.post(
    "/replenish",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/petty-cash/replenish",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def replenish_wallet(
    replenish_in: ReplenishmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replenish a site petty cash wallet balance."""
    wallet = await db.get(PettyCashWallet, replenish_in.wallet_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with id {replenish_in.wallet_id} not found.",
        )

    site = await db.get(Site, wallet.site_id)
    project_id = site.project_id if site else 1

    wallet.current_balance += replenish_in.amount
    wallet.last_replenishment_date = datetime.now(timezone.utc)

    tx = PettyCashTransaction(
        wallet_id=wallet.id,
        type=TransactionType.REPLENISHMENT,
        amount=replenish_in.amount,
        category=ExpenseCategory.OTHER,
        description=replenish_in.description,
        has_physical_bill=False,
        is_out_of_pocket=False,
        reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
        recorded_by=current_user.id,
        approval_status=ApprovalStatus.APPROVED,
        duplicate_flag=False,
        anomaly_flag=False,
        project_id=project_id,
        date=datetime.now(timezone.utc).date(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    return ExpenseResponse.model_validate(tx)


@router.post(
    "/reimbursements",
    response_model=ReimbursementResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/petty-cash/reimbursements",
    response_model=ReimbursementResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_reimbursement(
    reimb_in: ReimbursementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a reimbursement request for out-of-pocket transactions."""
    wallet = await db.get(PettyCashWallet, reimb_in.wallet_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with id {reimb_in.wallet_id} not found.",
        )

    # If transaction IDs specified, verify and update them
    if reimb_in.transaction_ids:
        stmt = select(PettyCashTransaction).where(
            PettyCashTransaction.id.in_(reimb_in.transaction_ids),
            PettyCashTransaction.wallet_id == wallet.id,
        )
        res = await db.execute(stmt)
        txs = res.scalars().all()
        for tx in txs:
            if tx.is_out_of_pocket:
                tx.reimbursement_status = ReimbursementStatus.DUE
                if reimb_in.reimbursement_ref:
                    tx.reimbursement_ref = reimb_in.reimbursement_ref
        await db.commit()

    return ReimbursementResponse(
        id=reimb_in.wallet_id,
        wallet_id=reimb_in.wallet_id,
        amount=reimb_in.amount,
        reimbursement_status=ReimbursementStatus.DUE,
        reimbursement_ref=reimb_in.reimbursement_ref,
        reimbursed_at=None,
        reimbursed_by=None,
    )


@router.post(
    "/reimbursements/{id}/settle",
    response_model=ReimbursementResponse,
)
@router.patch(
    "/reimbursements/{id}/settle",
    response_model=ReimbursementResponse,
)
@router.post(
    "/petty-cash/reimbursements/{id}/settle",
    response_model=ReimbursementResponse,
    include_in_schema=False,
)
@router.patch(
    "/petty-cash/reimbursements/{id}/settle",
    response_model=ReimbursementResponse,
    include_in_schema=False,
)
async def settle_reimbursement(
    id: int,
    settle_req: ReimbursementSettleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Settle an out-of-pocket transaction reimbursement."""
    tx = await db.get(PettyCashTransaction, id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {id} not found.",
        )

    now_ts = datetime.now(timezone.utc)
    tx.reimbursement_status = ReimbursementStatus.SETTLED
    tx.reimbursed_at = now_ts
    tx.reimbursed_by = current_user.id
    tx.reimbursement_ref = settle_req.reimbursement_ref

    await db.commit()
    await db.refresh(tx)

    return ReimbursementResponse(
        id=tx.id,
        wallet_id=tx.wallet_id,
        amount=tx.amount,
        reimbursement_status=tx.reimbursement_status,
        reimbursement_ref=tx.reimbursement_ref,
        reimbursed_at=tx.reimbursed_at,
        reimbursed_by=tx.reimbursed_by,
    )


@router.patch(
    "/expenses/{id}/approve",
    response_model=ExpenseResponse,
)
@router.post(
    "/expenses/{id}/approve",
    response_model=ExpenseResponse,
    include_in_schema=False,
)
@router.patch(
    "/petty-cash/expenses/{id}/approve",
    response_model=ExpenseResponse,
    include_in_schema=False,
)
async def approve_expense(
    id: int,
    approval_req: ExpenseApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve or reject a petty cash expense."""
    tx = await db.get(PettyCashTransaction, id)
    if not tx or tx.type != TransactionType.EXPENSE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with id {id} not found.",
        )

    tx.approval_status = approval_req.approval_status
    tx.approved_by = current_user.id

    await db.commit()
    await db.refresh(tx)
    return ExpenseResponse.model_validate(tx)


# ==============================================================================
# 5. Tally Prime XML Export
# ==============================================================================

@router.get(
    "/tally-export",
)
@router.get(
    "/petty-cash/tally-export",
    include_in_schema=False,
)
@router.get(
    "/petty-cash/export",
    include_in_schema=False,
)
async def export_tally_xml(
    site_id: int = Query(..., description="Target site ID"),
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    export_format: str = Query("xml", alias="format", description="Export format (xml or json)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export petty cash expenses in Tally Prime XML format:
    `<ENVELOPE><HEADER>...<BODY><VOUCHER>...`
    """
    wallet = await _get_or_create_wallet(db, site_id=site_id)

    stmt = select(PettyCashTransaction).where(
        PettyCashTransaction.wallet_id == wallet.id,
        PettyCashTransaction.type == TransactionType.EXPENSE,
    )
    if from_date is not None:
        stmt = stmt.where(PettyCashTransaction.date >= from_date)
    if to_date is not None:
        stmt = stmt.where(PettyCashTransaction.date <= to_date)

    stmt = stmt.order_by(PettyCashTransaction.date.asc(), PettyCashTransaction.id.asc())
    result = await db.execute(stmt)
    txs = result.scalars().all()

    total_amount = sum(t.amount for t in txs)

    # Build Tally Prime XML vouchers
    vouchers_xml_parts = []
    for tx in txs:
        tx_date = tx.date or (tx.created_at.date() if getattr(tx, "created_at", None) else date.today())
        date_str = tx_date.strftime("%Y%m%d")
        category_name = tx.category.value if hasattr(tx.category, "value") else str(tx.category)
        desc_escaped = (tx.description or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        voucher_block = f"""      <VOUCHER VCHTYPE="Payment" ACTION="Create">
        <DATE>{date_str}</DATE>
        <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
        <NARRATION>{desc_escaped}</NARRATION>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>{category_name}</LEDGERNAME>
          <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
          <AMOUNT>-{tx.amount:.2f}</AMOUNT>
        </ALLLEDGERENTRIES.LIST>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>Petty Cash</LEDGERNAME>
          <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
          <AMOUNT>{tx.amount:.2f}</AMOUNT>
        </ALLLEDGERENTRIES.LIST>
      </VOUCHER>"""
        vouchers_xml_parts.append(voucher_block)

    vouchers_xml = "\n".join(vouchers_xml_parts)

    full_xml = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>All Masters</REPORTNAME>
      </REQUESTDESC>
      <REQUESTDATA>
{vouchers_xml}
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""

    if export_format.lower() == "json":
        return TallyExportResponse(
            format="tally-xml",
            exported_at=datetime.now(timezone.utc),
            transaction_count=len(txs),
            total_amount=round(total_amount, 2),
            xml_payload=full_xml,
            download_url=None,
        )

    return Response(content=full_xml, media_type="application/xml")
