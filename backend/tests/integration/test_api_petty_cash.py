import pytest
from datetime import date, datetime, timezone
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.project import Site, Project
from app.models.petty_cash import (
    PettyCashWallet,
    PettyCashTransaction,
    TransactionType,
    ExpenseCategory,
    ReimbursementStatus,
    ApprovalStatus,
)
from app.core.security import create_access_token


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Valid access token headers for pre-seeded test_user."""
    token = create_access_token(
        data={"sub": str(test_user.id), "phone": test_user.phone, "role": test_user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def funded_wallet(db_session: AsyncSession, test_site: Site) -> PettyCashWallet:
    """Petty cash wallet pre-funded with ₹20,000."""
    wallet = PettyCashWallet(
        site_id=test_site.id,
        current_balance=20000.0,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)
    return wallet


# ==============================================================================
# Petty Cash API Integration Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_create_expense_normal_and_wallet_deduction(
    client: AsyncClient,
    test_site: Site,
    funded_wallet: PettyCashWallet,
    auth_headers: Dict[str, str],
):
    """
    Verify normal expense creation within wallet balance:
    - Returns HTTP 201 Created.
    - Wallet balance is deducted by expense amount.
    - Out-of-pocket is False and reimbursement status is NOT_APPLICABLE.
    """
    payload = {
        "site_id": test_site.id,
        "wallet_id": funded_wallet.id,
        "amount": 2500.0,
        "category": "FUEL",
        "description": "Diesel for Generator",
        "has_physical_bill": True,
        "date": "2026-09-21",
    }

    res = await client.post("/api/v1/petty-cash/expenses", json=payload, headers=auth_headers)
    assert res.status_code in (200, 201), res.text
    data = res.json()
    assert data["amount"] == 2500.0
    assert data["category"] == "FUEL"
    assert data["is_out_of_pocket"] is False
    assert data["reimbursement_status"] == "NOT_APPLICABLE"
    assert data["approval_status"] == "PENDING"

    # Verify wallet balance was deducted
    wallet_res = await client.get(f"/api/v1/petty-cash/wallet/{test_site.id}", headers=auth_headers)
    assert wallet_res.status_code == 200
    wallet_data = wallet_res.json()
    # 20,000 - 2,500 = 17,500
    assert wallet_data["current_balance"] == 17500.0
    assert wallet_data["supervisor_deficit"] == 0.0


@pytest.mark.integration
@pytest.mark.anyio
async def test_permissive_deficit_allows_out_of_pocket_up_to_50k(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify Vulnerability 5: Permissive deficit spending allows out-of-pocket expenses
    up to ₹50,000 deficit when wallet has zero or insufficient balance.
    """
    payload = {
        "site_id": test_site.id,
        "amount": 35000.0,
        "category": "TOOLS",
        "description": "Emergency hydraulic jack and spares",
        "has_physical_bill": True,
        "date": "2026-09-21",
    }

    res = await client.post("/api/v1/petty-cash/expenses", json=payload, headers=auth_headers)
    assert res.status_code in (200, 201), res.text
    data = res.json()
    assert data["amount"] == 35000.0
    assert data["is_out_of_pocket"] is True
    assert data["reimbursement_status"] == "DUE"

    # Verify wallet current balance is negative (-35,000) and supervisor deficit is 35,000
    wallet_res = await client.get(f"/api/v1/petty-cash/wallet/{test_site.id}", headers=auth_headers)
    assert wallet_res.status_code == 200
    wallet_data = wallet_res.json()
    assert wallet_data["current_balance"] == -35000.0
    assert wallet_data["supervisor_deficit"] == 35000.0


@pytest.mark.integration
@pytest.mark.anyio
async def test_deficit_exceeding_50k_rejected_infinite_deficit_blocked(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify Vulnerability 5: Deficit exceeding ₹50,000 is blocked with HTTP 400
    ('Infinite Deficit Blocked: Max allowed deficit is 50000.0').
    """
    payload = {
        "site_id": test_site.id,
        "amount": 50001.0,  # Exceeds ₹50,000 deficit cap!
        "category": "MATERIAL",
        "description": "Rogue unauthorized bulk purchase",
        "has_physical_bill": True,
        "date": "2026-09-21",
    }

    res = await client.post("/api/v1/petty-cash/expenses", json=payload, headers=auth_headers)
    assert res.status_code == 400, res.text
    assert "infinite deficit blocked" in res.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_duplicate_expense_floating_point_epsilon_rejected(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify Vulnerability 4: Duplicate expense with floating-point epsilon difference
    (< 0.01) within 7 days is rejected with HTTP 400.
    """
    # 1. First expense: 500.0000000000001
    payload1 = {
        "site_id": test_site.id,
        "amount": 500.0000000000001,
        "category": "FUEL",
        "description": "Diesel for Piling Rig",
        "has_physical_bill": True,
        "date": "2026-09-21",
    }
    res1 = await client.post("/api/v1/petty-cash/expenses", json=payload1, headers=auth_headers)
    assert res1.status_code in (200, 201), res1.text

    # 2. Second expense: exactly 500.0 on next day (within 7 days)
    payload2 = {
        "site_id": test_site.id,
        "amount": 500.0,
        "category": "FUEL",
        "description": "Diesel for Piling Rig Day 2",
        "has_physical_bill": True,
        "date": "2026-09-22",
    }
    res2 = await client.post("/api/v1/petty-cash/expenses", json=payload2, headers=auth_headers)
    assert res2.status_code == 400, res2.text
    assert "duplicate expense detected" in res2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_duplicate_expense_timezone_shift_rejected(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify Vulnerability 4: Duplicate expense comparison compares against actual
    expense date, catching duplicates within 7 days regardless of synchronization timestamp.
    """
    payload1 = {
        "site_id": test_site.id,
        "amount": 1200.0,
        "category": "VEHICLE",
        "description": "Tractor Rent",
        "has_physical_bill": True,
        "date": "2026-09-10",
    }
    res1 = await client.post("/api/v1/petty-cash/expenses", json=payload1, headers=auth_headers)
    assert res1.status_code in (200, 201), res1.text

    # Second expense with same amount on 15th (within 7 days of 10th)
    payload2 = {
        "site_id": test_site.id,
        "amount": 1200.0,
        "category": "VEHICLE",
        "description": "Tractor Rent Extension",
        "has_physical_bill": True,
        "date": "2026-09-15",
    }
    res2 = await client.post("/api/v1/petty-cash/expenses", json=payload2, headers=auth_headers)
    assert res2.status_code == 400, res2.text
    assert "duplicate expense detected" in res2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_tally_xml_export_valid_envelope(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify Tally XML export produces valid XML envelope:
    `<ENVELOPE><HEADER>...<BODY><VOUCHER>...`
    """
    # Create an expense
    payload = {
        "site_id": test_site.id,
        "amount": 1800.0,
        "category": "WELDING_REPAIR",
        "description": "Casing shoe welding repair",
        "has_physical_bill": True,
        "date": "2026-09-21",
    }
    res_exp = await client.post("/api/v1/petty-cash/expenses", json=payload, headers=auth_headers)
    assert res_exp.status_code in (200, 201)

    # Export Tally XML
    res_export = await client.get(
        f"/api/v1/petty-cash/tally-export?site_id={test_site.id}",
        headers=auth_headers,
    )
    assert res_export.status_code == 200
    assert "application/xml" in res_export.headers.get("content-type", "")
    xml_text = res_export.text
    assert "<ENVELOPE>" in xml_text
    assert "<HEADER>" in xml_text
    assert "<TALLYREQUEST>Import Data</TALLYREQUEST>" in xml_text
    assert "<BODY>" in xml_text
    assert "<VOUCHER" in xml_text
    assert "<LEDGERNAME>Petty Cash</LEDGERNAME>" in xml_text
    assert "1800.00" in xml_text


@pytest.mark.integration
@pytest.mark.anyio
async def test_reimbursement_settle(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify settling an out-of-pocket expense reimbursement.
    """
    # Create an out-of-pocket expense
    payload = {
        "site_id": test_site.id,
        "amount": 4200.0,
        "category": "TOOLS",
        "description": "Torque wrench and cutting discs",
        "has_physical_bill": True,
        "date": "2026-09-21",
    }
    res = await client.post("/api/v1/petty-cash/expenses", json=payload, headers=auth_headers)
    assert res.status_code in (200, 201)
    tx_id = res.json()["id"]

    # Settle reimbursement
    settle_payload = {"reimbursement_ref": "BANK-NEFT-994411"}
    settle_res = await client.post(
        f"/api/v1/petty-cash/reimbursements/{tx_id}/settle",
        json=settle_payload,
        headers=auth_headers,
    )
    assert settle_res.status_code == 200, settle_res.text
    settle_data = settle_res.json()
    assert settle_data["reimbursement_status"] == "SETTLED"
    assert settle_data["reimbursement_ref"] == "BANK-NEFT-994411"
    assert settle_data["reimbursed_at"] is not None


@pytest.mark.integration
@pytest.mark.anyio
async def test_direct_root_alias_routes(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify that direct alias routes like /api/v1/expenses and /api/v1/wallet/{site_id} work.
    """
    # 1. GET /expenses
    res = await client.get(f"/api/v1/expenses?site_id={test_site.id}", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 2. GET /wallet/{site_id}
    w_res = await client.get(f"/api/v1/wallet/{test_site.id}", headers=auth_headers)
    assert w_res.status_code == 200
    assert "current_balance" in w_res.json()


@pytest.mark.integration
@pytest.mark.anyio
async def test_unauthenticated_petty_cash_access_rejected(
    client: AsyncClient,
    test_site: Site,
):
    """Verify that unauthenticated requests to petty cash endpoints return 401."""
    res1 = await client.post("/api/v1/petty-cash/expenses", json={"site_id": test_site.id})
    assert res1.status_code == 401

    res2 = await client.get(f"/api/v1/petty-cash/wallet/{test_site.id}")
    assert res2.status_code == 401
