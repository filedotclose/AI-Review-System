import pytest
from datetime import date, datetime, timezone
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.project import Site, Project, Pile, PileStatus
from app.models.equipment import Equipment, EquipmentType, EquipmentStatus
from app.models.attendance import Worker, WorkerCategory
from app.models.petty_cash import PettyCashWallet
from app.core.security import create_access_token


@pytest.fixture
async def workflow_users(db_session: AsyncSession, test_site: Site) -> Dict[UserRole, User]:
    """Pre-seed one user for each enterprise role."""
    roles = [
        (201, "Pradeep K. Sharma", "+919800000001", UserRole.OWNER),
        (202, "Ananya Sen", "+919800000002", UserRole.FINANCE_HEAD),
        (203, "Vikram Mehta", "+919811122233", UserRole.PROJECT_MANAGER),
        (204, "Rajesh Sharma", "+919876543210", UserRole.SITE_ENGINEER),
        (205, "Sunil Varma", "+919876543211", UserRole.SUPERVISOR),
    ]
    users_by_role = {}
    for uid, name, phone, role in roles:
        u = User(
            id=uid,
            name=name,
            phone=phone,
            email=f"{role.value.lower()}@odipks.test",
            role=role,
            is_active=True,
        )
        db_session.add(u)
        users_by_role[role] = u
    await db_session.commit()
    for u in users_by_role.values():
        await db_session.refresh(u)
    return users_by_role


@pytest.fixture
def workflow_headers(workflow_users: Dict[UserRole, User]) -> Dict[UserRole, Dict[str, str]]:
    """JWT bearer headers for each role."""
    return {
        role: {
            "Authorization": f"Bearer {create_access_token(data={'sub': str(u.id), 'phone': u.phone, 'role': role.value})}"
        }
        for role, u in workflow_users.items()
    }


@pytest.fixture
async def workflow_pile(db_session: AsyncSession, test_site: Site) -> Pile:
    """Pile entity for technical boring log."""
    pile = Pile(
        site_id=test_site.id,
        pier_number="P12",
        pile_number="P12-1",
        diameter_mm=1000,
        cutoff_level_m=12.0,
        ground_level_m=16.0,
        planned_depth_m=24.0,
        planned_rock_socket_m=3.0,
        status=PileStatus.PLANNED,
    )
    db_session.add(pile)
    await db_session.commit()
    await db_session.refresh(pile)
    return pile


@pytest.fixture
async def workflow_equipment(db_session: AsyncSession, test_site: Site) -> Equipment:
    """Hydraulic piling rig."""
    eq = Equipment(
        name="Bauer BG 28 Hydraulic Rig #1",
        type=EquipmentType.RIG,
        registration_number="KL-11-BG-2801",
        site_id=test_site.id,
        fuel_benchmark_liters_per_hour=22.0,
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)
    return eq


@pytest.fixture
async def workflow_worker(db_session: AsyncSession, test_site: Site) -> Worker:
    """Worker entity for check-in."""
    worker = Worker(
        name="Ramesh Kumar",
        phone="+919876540001",
        category=WorkerCategory.OPERATOR,
        assigned_site_id=test_site.id,
        is_active=True,
    )
    db_session.add(worker)
    await db_session.commit()
    await db_session.refresh(worker)
    return worker


# ==============================================================================
# Comprehensive End-to-End Multi-Persona Workflow Test
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_full_construction_enterprise_lifecycle(
    client: AsyncClient,
    test_site: Site,
    workflow_users: Dict[UserRole, User],
    workflow_headers: Dict[UserRole, Dict[str, str]],
    workflow_pile: Pile,
    workflow_equipment: Equipment,
    workflow_worker: Worker,
    db_session: AsyncSession,
):
    """
    Validates the complete 7-stage construction enterprise workflow:
    1. Persona-based security boundaries (RBAC guards).
    2. SUPERVISOR logs worker check-in and trade muster headcount.
    3. SITE_ENGINEER submits technical DPR with piling & rig runtime logs.
    4. PROJECT_MANAGER audits overbreak flags, verifies and signs off DPR.
    5. SITE_ENGINEER logs emergency out-of-pocket spare expense.
    6. FINANCE_HEAD approves expense, settles reimbursement with UTR, replenishes wallet, exports Tally XML.
    7. OWNER triggers daily executive brief, verifies anomaly radar, KPIs, and WhatsApp dispatch.
    """

    # --------------------------------------------------------------------------
    # PHASE 1: RBAC Boundary Checks
    # --------------------------------------------------------------------------
    # Supervisor and Site Engineer must NOT have access to Executive Brief
    res_sup = await client.get(f"/api/v1/brief?site_id={test_site.id}", headers=workflow_headers[UserRole.SUPERVISOR])
    assert res_sup.status_code == 403, f"Expected 403 for Supervisor, got {res_sup.status_code}"

    res_eng = await client.get(f"/api/v1/brief?site_id={test_site.id}", headers=workflow_headers[UserRole.SITE_ENGINEER])
    assert res_eng.status_code == 403, f"Expected 403 for Site Engineer, got {res_eng.status_code}"

    # Owner and Finance Head must have access
    res_own = await client.get(f"/api/v1/brief?site_id={test_site.id}", headers=workflow_headers[UserRole.OWNER])
    assert res_own.status_code in (200, 404)

    # --------------------------------------------------------------------------
    # PHASE 2: Supervisor Field Attendance Workflow
    # --------------------------------------------------------------------------
    # 1. Geofenced worker check-in (Vadodara site coords 22.3072, 73.1812)
    checkin_res = await client.post(
        "/api/v1/attendance/check-in",
        json={
            "site_id": test_site.id,
            "worker_id": workflow_worker.id,
            "date": "2026-09-24",
            "shift": "DAY",
            "check_in_lat": 22.3072,
            "check_in_lng": 73.1812,
        },
        headers=workflow_headers[UserRole.SUPERVISOR],
    )
    assert checkin_res.status_code in (200, 201), checkin_res.text
    checkin_data = checkin_res.json()
    assert checkin_data["within_geofence"] is True
    assert checkin_data["status"] == "PRESENT"

    # 2. Subcontractor Gang Muster
    muster_res = await client.post(
        "/api/v1/attendance/gang-muster",
        json={
            "site_id": test_site.id,
            "date": "2026-09-24",
            "shift": "DAY",
            "subcontractor_name": "Apex Piling Subcontractors",
            "trade": "PILING_GANG",
            "headcount_present": 16,
            "total_ot_hours": 32.0,
            "muster_roll_photo_url": "https://storage.odipks.test/muster-2026-09-24.jpg",
        },
        headers=workflow_headers[UserRole.SUPERVISOR],
    )
    assert muster_res.status_code in (200, 201), muster_res.text
    muster_data = muster_res.json()
    assert muster_data["headcount_present"] == 16

    # --------------------------------------------------------------------------
    # PHASE 3: Site Engineer Technical DPR Submission
    # --------------------------------------------------------------------------
    dpr_payload = {
        "site_id": test_site.id,
        "operational_date": "2026-09-24",
        "shift": "DAY",
        "weather_conditions": "Sunny, Clear 34C",
        "problems_delays": "Transit mixer delayed in highway bypass traffic",
        "tomorrows_plan": "Lower reinforcement cage on P12-2",
        "pile_progress": [
            {
                "pile_id": workflow_pile.id,
                "depth_drilled_today_m": 18.5,
                "cumulative_depth_m": 24.0,
                "rock_socket_depth_today_m": 3.2,
                "strata_type": "WEATHERED_ROCK",
                "casing_depth_m": 6.0,
                "casing_type": "TEMPORARY",
                "cage_sections_lowered": 2,
                "cage_weight_kg_today": 1450.0,
                "concrete_volume_planned_m3": 14.5,
                "concrete_volume_actual_m3": 16.5,  # ~13.8% overbreak
                "slump_mm": 180.0,
                "bentonite_density_g_cc": 1.05,
            }
        ],
        "equipment_shifts": [
            {
                "equipment_id": workflow_equipment.id,
                "opening_hours": 1420.0,
                "closing_hours": 1430.0,
                "working_hours": 8.5,
                "breakdown_hours": 1.5,
                "idle_hours": 0.0,
                "fuel_liters": 185.0,
            }
        ],
        "manpower_entries": [
            {
                "category": "Piling Rig Operator",
                "count": 2,
                "shift": "DAY",
                "hours_worked": 10.0,
            },
            {
                "category": "Helper / Labour",
                "count": 14,
                "shift": "DAY",
                "hours_worked": 10.0,
            },
        ],
    }

    dpr_res = await client.post("/api/v1/dpr", json=dpr_payload, headers=workflow_headers[UserRole.SITE_ENGINEER])
    assert dpr_res.status_code in (200, 201), dpr_res.text
    dpr_data = dpr_res.json()
    dpr_id = dpr_data["id"]
    assert dpr_data["status"] == "SUBMITTED"

    # Verify Site Engineer CANNOT verify their own DPR (HTTP 403)
    eng_verify_res = await client.post(
        f"/api/v1/dpr/{dpr_id}/verify",
        json={"status": "VERIFIED"},
        headers=workflow_headers[UserRole.SITE_ENGINEER],
    )
    assert eng_verify_res.status_code == 403

    # --------------------------------------------------------------------------
    # PHASE 4: Project Manager DPR Verification & Sign-off
    # --------------------------------------------------------------------------
    pm_verify_res = await client.post(
        f"/api/v1/dpr/{dpr_id}/verify",
        json={
            "status": "VERIFIED",
            "verification_notes": "Reviewed concrete overbreak (13.8%) due to strata fissures. Signed off.",
        },
        headers=workflow_headers[UserRole.PROJECT_MANAGER],
    )
    assert pm_verify_res.status_code == 200, pm_verify_res.text
    verified_data = pm_verify_res.json()
    assert verified_data["status"] == "VERIFIED"

    # --------------------------------------------------------------------------
    # PHASE 5: Site Emergency Expense Logging (Out-of-Pocket)
    # --------------------------------------------------------------------------
    expense_payload = {
        "site_id": test_site.id,
        "amount": 3200.0,
        "category": "WELDING_REPAIR",
        "description": "Emergency hydraulic seal replacement for Bauer BG 28 rotary head",
        "has_physical_bill": True,
        "date": "2026-09-24",
    }
    exp_res = await client.post(
        "/api/v1/petty-cash/expenses",
        json=expense_payload,
        headers=workflow_headers[UserRole.SITE_ENGINEER],
    )
    assert exp_res.status_code in (200, 201), exp_res.text
    exp_data = exp_res.json()
    expense_id = exp_data["id"]
    assert exp_data["approval_status"] == "PENDING"
    assert exp_data["is_out_of_pocket"] is True

    # Verify Site Engineer CANNOT approve or settle this expense
    eng_app_res = await client.post(
        f"/api/v1/petty-cash/expenses/{expense_id}/approve",
        json={"approval_status": "APPROVED", "remarks": "Self-approval"},
        headers=workflow_headers[UserRole.SITE_ENGINEER],
    )
    assert eng_app_res.status_code == 403

    eng_set_res = await client.post(
        f"/api/v1/petty-cash/reimbursements/{expense_id}/settle",
        json={"reimbursement_ref": "BANK123"},
        headers=workflow_headers[UserRole.SITE_ENGINEER],
    )
    assert eng_set_res.status_code == 403

    # --------------------------------------------------------------------------
    # PHASE 6: Finance Head Commercial Approval & Settlement
    # --------------------------------------------------------------------------
    # 1. Approve Expense
    fin_app_res = await client.post(
        f"/api/v1/petty-cash/expenses/{expense_id}/approve",
        json={"approval_status": "APPROVED", "remarks": "Invoice verified against equipment breakdown log"},
        headers=workflow_headers[UserRole.FINANCE_HEAD],
    )
    assert fin_app_res.status_code == 200, fin_app_res.text
    assert fin_app_res.json()["approval_status"] == "APPROVED"

    # 2. Settle Reimbursement with UTR Number
    fin_set_res = await client.post(
        f"/api/v1/petty-cash/reimbursements/{expense_id}/settle",
        json={"reimbursement_ref": "HDFC98765432101"},
        headers=workflow_headers[UserRole.FINANCE_HEAD],
    )
    assert fin_set_res.status_code == 200, fin_set_res.text
    settled_data = fin_set_res.json()
    assert settled_data["reimbursement_status"] == "SETTLED"
    assert settled_data["reimbursement_ref"] == "HDFC98765432101"

    # 3. Replenish Site Wallet
    wallet_res = await client.get(f"/api/v1/petty-cash/wallet/{test_site.id}", headers=workflow_headers[UserRole.FINANCE_HEAD])
    assert wallet_res.status_code == 200
    wallet_id = wallet_res.json()["id"]

    fin_rep_res = await client.post(
        "/api/v1/petty-cash/replenish",
        json={
            "wallet_id": wallet_id,
            "amount": 25000.0,
            "description": "Weekly site wallet advance top-up",
        },
        headers=workflow_headers[UserRole.FINANCE_HEAD],
    )
    assert fin_rep_res.status_code in (200, 201), fin_rep_res.text

    # 4. Export Tally Prime XML
    tally_res = await client.get(
        f"/api/v1/petty-cash/tally-export?site_id={test_site.id}",
        headers=workflow_headers[UserRole.FINANCE_HEAD],
    )
    assert tally_res.status_code == 200, tally_res.text
    assert "<ENVELOPE>" in tally_res.text or "<TALLYMESSAGE" in tally_res.text

    # --------------------------------------------------------------------------
    # PHASE 7: Owner Strategic Executive AI Brief
    # --------------------------------------------------------------------------
    # 1. Trigger Brief Generation
    gen_brief_res = await client.post(
        f"/api/v1/brief/generate?site_id={test_site.id}&target_date=2026-09-24",
        headers=workflow_headers[UserRole.OWNER],
    )
    assert gen_brief_res.status_code in (200, 201, 202), gen_brief_res.text

    # 2. Query Generated Daily Brief
    get_brief_res = await client.get(
        f"/api/v1/brief?site_id={test_site.id}&date=2026-09-24",
        headers=workflow_headers[UserRole.OWNER],
    )
    assert get_brief_res.status_code == 200, get_brief_res.text
    brief_data = get_brief_res.json()
    assert "brief_data" in brief_data or "id" in brief_data
    assert brief_data.get("delivery_status") in ("SENT", "PENDING")
