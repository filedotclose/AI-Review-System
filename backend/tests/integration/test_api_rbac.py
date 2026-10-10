import pytest
from datetime import date, datetime, timezone
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.project import Site, Project
from app.models.petty_cash import (
    PettyCashWallet,
    PettyCashTransaction,
    TransactionType,
    ExpenseCategory,
    ApprovalStatus,
    ReimbursementStatus,
)
from app.models.dpr import DailyProgressReport, DPRStatus
from app.models.equipment import ShiftType
from app.models.executive_brief import ExecutiveBrief, DeliveryStatus
from app.core.security import create_access_token


@pytest.fixture
async def rbac_users(db_session: AsyncSession) -> Dict[str, User]:
    """Create a user for each role in the system."""
    roles = {
        "OWNER": UserRole.OWNER,
        "FINANCE_HEAD": UserRole.FINANCE_HEAD,
        "PROJECT_MANAGER": UserRole.PROJECT_MANAGER,
        "SITE_ENGINEER": UserRole.SITE_ENGINEER,
        "SUPERVISOR": UserRole.SUPERVISOR,
    }
    user_map = {}
    for idx, (role_name, role_enum) in enumerate(roles.items(), start=100):
        u = User(
            id=idx,
            name=f"Test {role_name}",
            phone=f"+919800000{idx}",
            email=f"{role_name.lower()}@odipks.test",
            role=role_enum,
            is_active=True,
        )
        db_session.add(u)
        user_map[role_name] = u
    await db_session.commit()
    for u in user_map.values():
        await db_session.refresh(u)
    return user_map


def get_headers_for_user(user: User) -> Dict[str, str]:
    tok = create_access_token(
        data={"sub": str(user.id), "phone": user.phone, "role": user.role.value}
    )
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
async def sample_dpr(db_session: AsyncSession, test_site: Site, rbac_users: Dict[str, User]) -> DailyProgressReport:
    dpr = DailyProgressReport(
        site_id=test_site.id,
        operational_date=date.today(),
        shift=ShiftType.DAY,
        weather_conditions="SUNNY",
        status=DPRStatus.SUBMITTED,
        submitted_by=rbac_users["SITE_ENGINEER"].id,
    )
    db_session.add(dpr)
    await db_session.commit()
    await db_session.refresh(dpr)
    return dpr


@pytest.fixture
async def sample_expense(db_session: AsyncSession, test_site: Site, rbac_users: Dict[str, User]) -> PettyCashTransaction:
    wallet = PettyCashWallet(
        site_id=test_site.id,
        current_balance=10000.0,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)

    tx = PettyCashTransaction(
        wallet_id=wallet.id,
        project_id=test_site.project_id,
        type=TransactionType.EXPENSE,
        amount=1500.0,
        category=ExpenseCategory.FOOD_WATER,
        description="Piling crew tea and refreshments",
        date=date.today(),
        is_out_of_pocket=True,
        has_physical_bill=True,
        recorded_by=rbac_users["SUPERVISOR"].id,
        approval_status=ApprovalStatus.PENDING,
        reimbursement_status=ReimbursementStatus.DUE,
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)
    return tx


# ==============================================================================
# 1. DPR Verification RBAC Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_dpr_verify_rbac_restrictions(
    client: AsyncClient,
    sample_dpr: DailyProgressReport,
    rbac_users: Dict[str, User],
):
    """
    DPRs are uploaded by SITE_ENGINEER and verified/approved by other roles
    (PROJECT_MANAGER, OWNER, SUPERVISOR, FINANCE_HEAD).
    SITE_ENGINEER must receive HTTP 403 Forbidden.
    """
    # 1. Site Engineer attempts to verify DPR -> 403 Forbidden
    se_headers = get_headers_for_user(rbac_users["SITE_ENGINEER"])
    resp = await client.post(f"/api/v1/dpr/{sample_dpr.id}/verify", headers=se_headers)
    assert resp.status_code == 403, f"Expected 403 for Site Engineer, got {resp.status_code}: {resp.text}"

    # 2. Supervisor verifies DPR -> 200 OK
    sup_headers = get_headers_for_user(rbac_users["SUPERVISOR"])
    resp = await client.post(f"/api/v1/dpr/{sample_dpr.id}/verify", headers=sup_headers)
    assert resp.status_code == 200, f"Expected 200 for Supervisor, got {resp.status_code}: {resp.text}"
    assert resp.json()["status"] == "VERIFIED"

    # 3. Finance Head verifies DPR -> 200 OK
    fin_headers = get_headers_for_user(rbac_users["FINANCE_HEAD"])
    resp = await client.post(f"/api/v1/dpr/{sample_dpr.id}/verify", headers=fin_headers)
    assert resp.status_code == 200, f"Expected 200 for Finance Head, got {resp.status_code}: {resp.text}"

    # 4. Project Manager verifies DPR -> 200 OK
    pm_headers = get_headers_for_user(rbac_users["PROJECT_MANAGER"])
    resp = await client.post(f"/api/v1/dpr/{sample_dpr.id}/verify", headers=pm_headers)
    assert resp.status_code == 200, f"Expected 200 for Project Manager, got {resp.status_code}: {resp.text}"

    # 5. Owner verifies DPR -> 200 OK
    owner_headers = get_headers_for_user(rbac_users["OWNER"])
    resp = await client.post(f"/api/v1/dpr/{sample_dpr.id}/verify", headers=owner_headers)
    assert resp.status_code == 200, f"Expected 200 for Owner, got {resp.status_code}: {resp.text}"
    assert resp.json()["status"] == "VERIFIED"


# ==============================================================================
# 2. Petty Cash Approval & Settlement RBAC Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_petty_cash_approval_rbac_restrictions(
    client: AsyncClient,
    sample_expense: PettyCashTransaction,
    rbac_users: Dict[str, User],
):
    """
    Only FINANCE_HEAD, PROJECT_MANAGER, and OWNER can approve expenses.
    SUPERVISOR and SITE_ENGINEER must receive HTTP 403 Forbidden.
    """
    sup_headers = get_headers_for_user(rbac_users["SUPERVISOR"])
    resp = await client.post(
        f"/api/v1/petty-cash/expenses/{sample_expense.id}/approve",
        json={"approval_status": "APPROVED", "remarks": "Looks good"},
        headers=sup_headers,
    )
    assert resp.status_code == 403, f"Expected 403 for Supervisor, got {resp.status_code}: {resp.text}"

    fin_headers = get_headers_for_user(rbac_users["FINANCE_HEAD"])
    resp = await client.post(
        f"/api/v1/petty-cash/expenses/{sample_expense.id}/approve",
        json={"approval_status": "APPROVED", "remarks": "Approved by Finance"},
        headers=fin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["approval_status"] == "APPROVED"


@pytest.mark.integration
@pytest.mark.anyio
async def test_reimbursement_settle_rbac_restrictions(
    client: AsyncClient,
    sample_expense: PettyCashTransaction,
    rbac_users: Dict[str, User],
):
    """
    Only FINANCE_HEAD and OWNER can settle reimbursements.
    SITE_ENGINEER and SUPERVISOR must receive HTTP 403 Forbidden.
    """
    se_headers = get_headers_for_user(rbac_users["SITE_ENGINEER"])
    resp = await client.post(
        f"/api/v1/petty-cash/reimbursements/{sample_expense.id}/settle",
        json={"reimbursement_ref": "NEFT12345678"},
        headers=se_headers,
    )
    assert resp.status_code == 403

    fin_headers = get_headers_for_user(rbac_users["FINANCE_HEAD"])
    resp = await client.post(
        f"/api/v1/petty-cash/reimbursements/{sample_expense.id}/settle",
        json={"reimbursement_ref": "NEFT12345678"},
        headers=fin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["reimbursement_status"] == "SETTLED"


@pytest.mark.integration
@pytest.mark.anyio
async def test_tally_export_rbac_restrictions(
    client: AsyncClient,
    test_site: Site,
    rbac_users: Dict[str, User],
):
    """
    Only FINANCE_HEAD and OWNER can export Tally Prime XML.
    SUPERVISOR and SITE_ENGINEER must receive HTTP 403 Forbidden.
    """
    sup_headers = get_headers_for_user(rbac_users["SUPERVISOR"])
    resp = await client.get(f"/api/v1/petty-cash/tally-export?site_id={test_site.id}", headers=sup_headers)
    assert resp.status_code == 403

    fin_headers = get_headers_for_user(rbac_users["FINANCE_HEAD"])
    resp = await client.get(f"/api/v1/petty-cash/tally-export?site_id={test_site.id}", headers=fin_headers)
    assert resp.status_code == 200
    assert "xml" in resp.headers.get("content-type", "").lower()


# ==============================================================================
# 3. Executive Brief RBAC Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_executive_brief_rbac_restrictions(
    client: AsyncClient,
    db_session: AsyncSession,
    rbac_users: Dict[str, User],
):
    """
    Only OWNER, PROJECT_MANAGER, and FINANCE_HEAD can access Executive Briefs.
    SUPERVISOR and SITE_ENGINEER must receive HTTP 403 Forbidden.
    """
    # Seed a dummy brief
    brief = ExecutiveBrief(
        operational_date=date.today(),
        delivery_status=DeliveryStatus.SENT,
        brief_data={"summary": "ODIPKS Pilot operations running smoothly across packages.", "metrics": {}},
        alerts=[],
    )
    db_session.add(brief)
    await db_session.commit()

    # 1. Site Engineer blocked with 403
    se_headers = get_headers_for_user(rbac_users["SITE_ENGINEER"])
    resp = await client.get("/api/v1/brief/today", headers=se_headers)
    assert resp.status_code == 403

    # 2. Supervisor blocked with 403
    sup_headers = get_headers_for_user(rbac_users["SUPERVISOR"])
    resp = await client.get("/api/v1/brief/today", headers=sup_headers)
    assert resp.status_code == 403

    # 3. Owner permitted with 200
    owner_headers = get_headers_for_user(rbac_users["OWNER"])
    resp = await client.get("/api/v1/brief/today", headers=owner_headers)
    assert resp.status_code == 200
