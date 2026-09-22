import pytest
from datetime import date, datetime, timezone
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.project import Site, Project, Pile, PileStatus
from app.models.equipment import Equipment, EquipmentType, EquipmentStatus, ShiftType
from app.models.dpr import StrataType, CasingType, DPRStatus
from app.core.security import create_access_token


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Valid access token headers for the pre-seeded test_user."""
    token = create_access_token(
        data={"sub": str(test_user.id), "phone": test_user.phone, "role": test_user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_pile(db_session: AsyncSession, test_site: Site) -> Pile:
    """Pre-seeded Pile entity with standard diameter >= 400mm."""
    pile = Pile(
        site_id=test_site.id,
        pier_number="P14",
        pile_number="P14-3",
        diameter_mm=1200,
        cutoff_level_m=10.0,
        ground_level_m=14.5,
        planned_depth_m=28.0,
        planned_rock_socket_m=4.0,
        status=PileStatus.PLANNED,
    )
    db_session.add(pile)
    await db_session.commit()
    await db_session.refresh(pile)
    return pile


@pytest.fixture
async def test_pile_small_diameter(db_session: AsyncSession, test_site: Site) -> Pile:
    """Pile entity with anomalous diameter < 400mm to verify Vulnerability 3."""
    pile = Pile(
        site_id=test_site.id,
        pier_number="P99",
        pile_number="P99-1",
        diameter_mm=350,  # Vulnerable: < 400mm
        status=PileStatus.PLANNED,
    )
    db_session.add(pile)
    await db_session.commit()
    await db_session.refresh(pile)
    return pile


@pytest.fixture
async def test_equipment(db_session: AsyncSession, test_site: Site) -> Equipment:
    """Pre-seeded Equipment entity."""
    eq = Equipment(
        name="Bauer BG 28 Hydraulic Rig",
        type=EquipmentType.RIG,
        registration_number="GJ-06-BG-2801",
        site_id=test_site.id,
        fuel_benchmark_liters_per_hour=24.0,
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)
    return eq


# ==============================================================================
# DPR Endpoint Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_create_dpr_valid(
    client: AsyncClient,
    test_site: Site,
    test_pile: Pile,
    test_equipment: Equipment,
    test_user: User,
    auth_headers: Dict[str, str],
):
    """Verify creating a DPR with valid data returns 201 Created with nested records."""
    payload = {
        "site_id": test_site.id,
        "operational_date": "2026-09-21",
        "shift": "DAY",
        "weather_conditions": "Clear and Sunny, 32C",
        "problems_delays": "None reported",
        "tomorrows_plan": "Continue boring pier 14 pile 3",
        "pile_progress": [
            {
                "pile_id": test_pile.id,
                "depth_drilled_today_m": 8.5,
                "cumulative_depth_m": 16.5,
                "empty_bore_depth_m": 2.0,
                "rock_socket_depth_today_m": 1.5,
                "strata_type": "WEATHERED_ROCK",
                "casing_depth_m": 6.0,
                "casing_type": "TEMPORARY",
                "cage_sections_lowered": 2,
                "cage_weight_kg_today": 3200.0,
                "concrete_volume_planned_m3": 10.0,
                "concrete_volume_actual_m3": 10.2,
                "slump_mm": 175.0,
                "bentonite_density_g_cc": 1.08,
            }
        ],
        "equipment_shifts": [
            {
                "equipment_id": test_equipment.id,
                "opening_hours": 1200.0,
                "closing_hours": 1210.0,
                "working_hours": 8.5,
                "breakdown_hours": 0.0,
                "idle_hours": 1.5,
                "fuel_liters": 180.0,
            }
        ],
        "manpower_entries": [
            {
                "category": "Rig Operator",
                "count": 2,
                "shift": "DAY",
                "hours_worked": 10.0,
            }
        ],
    }

    response = await client.post("/api/v1/dpr", json=payload, headers=auth_headers)
    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert data["site_id"] == test_site.id
    assert data["operational_date"] == "2026-09-21"
    assert data["shift"] == "DAY"
    assert data["submitted_by"] == test_user.id
    assert data["status"] in ("DRAFT", "SUBMITTED")
    assert len(data["pile_progress"]) == 1
    assert data["pile_progress"][0]["pile_id"] == test_pile.id
    assert len(data["equipment_logs"]) == 1
    assert len(data["labour_summaries"]) == 1


@pytest.mark.integration
@pytest.mark.anyio
async def test_duplicate_dpr_rejected(
    client: AsyncClient,
    test_site: Site,
    test_user: User,
    auth_headers: Dict[str, str],
):
    """Verify duplicate DPR for same (site_id, operational_date, shift) returns 400/409."""
    payload = {
        "site_id": test_site.id,
        "operational_date": "2026-09-22",
        "shift": "NIGHT",
        "weather_conditions": "Clear night",
    }

    res1 = await client.post("/api/v1/dpr", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201), res1.text

    # Second submission with identical site, date, shift must fail
    res2 = await client.post("/api/v1/dpr", json=payload, headers=auth_headers)
    assert res2.status_code in (400, 409), res2.text
    assert "already exists" in res2.json()["detail"].lower() or "integrity" in res2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_dpr_list_and_details(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """Verify GET /dpr listing with filters and GET /dpr/{id} detailed retrieval."""
    # Seed a DPR
    payload = {
        "site_id": test_site.id,
        "operational_date": "2026-09-23",
        "shift": "DAY",
        "weather_conditions": "Cloudy",
    }
    create_res = await client.post("/api/v1/dpr", json=payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    dpr_id = create_res.json()["id"]

    # Filter list
    list_res = await client.get(f"/api/v1/dpr?site_id={test_site.id}", headers=auth_headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(item["id"] == dpr_id for item in items)

    # Detailed view
    detail_res = await client.get(f"/api/v1/dpr/{dpr_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == dpr_id

    # Nonexistent DPR
    not_found_res = await client.get("/api/v1/dpr/99999", headers=auth_headers)
    assert not_found_res.status_code == 404


@pytest.mark.integration
@pytest.mark.anyio
async def test_verify_dpr(
    client: AsyncClient,
    test_site: Site,
    test_user: User,
    auth_headers: Dict[str, str],
):
    """Verify POST /dpr/{id}/verify sets status to VERIFIED and records verified_by."""
    payload = {
        "site_id": test_site.id,
        "operational_date": "2026-09-24",
        "shift": "DAY",
    }
    create_res = await client.post("/api/v1/dpr", json=payload, headers=auth_headers)
    dpr_id = create_res.json()["id"]

    verify_res = await client.post(f"/api/v1/dpr/{dpr_id}/verify", headers=auth_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "VERIFIED"
    assert verify_res.json()["verified_by"] == test_user.id
    assert verify_res.json()["verified_at"] is not None


@pytest.mark.integration
@pytest.mark.anyio
async def test_pile_progress_diameter_epsilon_under_400_rejected(
    client: AsyncClient,
    test_site: Site,
    test_pile_small_diameter: Pile,
    auth_headers: Dict[str, str],
):
    """
    Verify Vulnerability 3: Pile diameter < 400mm raises validation error
    (prevents mm vs meter confusion, e.g. 1.2m entered as 1.2 instead of 1200mm).
    """
    # Create DPR header first
    dpr_res = await client.post(
        "/api/v1/dpr",
        json={"site_id": test_site.id, "operational_date": "2026-09-25", "shift": "DAY"},
        headers=auth_headers,
    )
    dpr_id = dpr_res.json()["id"]

    # 1. Attempt with small diameter pile from DB (diameter = 350mm)
    payload = {
        "dpr_id": dpr_id,
        "pile_id": test_pile_small_diameter.id,
        "depth_drilled_today_m": 12.0,
        "concrete_volume_actual_m3": 15.0,
    }
    res1 = await client.post("/api/v1/dpr/pile-progress", json=payload, headers=auth_headers)
    assert res1.status_code in (400, 422), res1.text
    assert "Invalid diameter" in res1.text or "400" in res1.text

    # 2. Attempt with explicit float confusion (1.2 entered instead of 1200mm)
    payload_confusion = {
        "dpr_id": dpr_id,
        "pile_id": test_pile_small_diameter.id,
        "diameter_mm": 1.2,  # Confused meter with mm!
        "depth_drilled_today_m": 20.0,
        "concrete_volume_actual_m3": 25.0,
    }
    res2 = await client.post("/api/v1/dpr/pile-progress", json=payload_confusion, headers=auth_headers)
    assert res2.status_code in (400, 422), res2.text
    assert "Invalid diameter" in res2.text or "400" in res2.text


@pytest.mark.integration
@pytest.mark.anyio
async def test_pile_progress_valid_submission(
    client: AsyncClient,
    test_site: Site,
    test_pile: Pile,
    auth_headers: Dict[str, str],
):
    """Verify valid pile progress submission via POST /dpr/pile-progress."""
    dpr_res = await client.post(
        "/api/v1/dpr",
        json={"site_id": test_site.id, "operational_date": "2026-09-26", "shift": "DAY"},
        headers=auth_headers,
    )
    dpr_id = dpr_res.json()["id"]

    payload = {
        "dpr_id": dpr_id,
        "pile_id": test_pile.id,
        "depth_drilled_today_m": 14.0,
        "cumulative_depth_m": 22.0,
        "strata_type": "HARD_ROCK",
        "concrete_volume_planned_m3": 24.0,
        "concrete_volume_actual_m3": 25.5,
    }
    res = await client.post("/api/v1/dpr/pile-progress", json=payload, headers=auth_headers)
    assert res.status_code in (200, 201), res.text
    data = res.json()
    assert data["pile_id"] == test_pile.id
    assert data["depth_drilled_today_m"] == 14.0


# ==============================================================================
# Shift Fuel Register Endpoint Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_create_fuel_register_valid(
    client: AsyncClient,
    test_site: Site,
    test_user: User,
    auth_headers: Dict[str, str],
):
    """Verify creating a fuel register record with valid numbers returns 201."""
    payload = {
        "site_id": test_site.id,
        "date": "2026-09-21",
        "shift": "DAY",
        "opening_stock_liters": 1000.0,
        "received_bowser_liters": 500.0,
        "received_drums_liters": 0.0,
        "total_issued_to_equipment_liters": 300.0,
        "closing_dip_stock_liters": 1200.0,
    }

    response = await client.post("/api/v1/fuel/fuel-register", json=payload, headers=auth_headers)
    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert data["site_id"] == test_site.id
    assert data["opening_stock_liters"] == 1000.0
    assert data["closing_dip_stock_liters"] == 1200.0
    # Expected: (1000 + 500) - 300 = 1200 -> variance = 0.0
    assert data["variance_liters"] == 0.0
    assert data["recorded_by"] == test_user.id


@pytest.mark.integration
@pytest.mark.anyio
async def test_fuel_register_negative_dip_rejected(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify Vulnerability 1: Negative closing dip stock is physically impossible
    and rejected with HTTP 400.
    """
    payload = {
        "site_id": test_site.id,
        "date": "2026-09-22",
        "shift": "DAY",
        "opening_stock_liters": 1000.0,
        "received_bowser_liters": 500.0,
        "received_drums_liters": 0.0,
        "total_issued_to_equipment_liters": 1200.0,
        "closing_dip_stock_liters": -50.0,  # Negative dip!
    }

    response = await client.post("/api/v1/fuel/fuel-register", json=payload, headers=auth_headers)
    assert response.status_code == 400, response.text
    assert "negative fuel dip" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_fuel_register_ghost_issuance_rejected(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify Vulnerability 2: Ghost issuance (total_issued > opening + received)
    is rejected with HTTP 400.
    """
    payload = {
        "site_id": test_site.id,
        "date": "2026-09-23",
        "shift": "DAY",
        "opening_stock_liters": 500.0,
        "received_bowser_liters": 200.0,
        "received_drums_liters": 0.0,
        "total_issued_to_equipment_liters": 701.0,  # Available = 700L, issued = 701L!
        "closing_dip_stock_liters": 0.0,
    }

    response = await client.post("/api/v1/fuel/fuel-register", json=payload, headers=auth_headers)
    assert response.status_code == 400, response.text
    assert "ghost issuance" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_duplicate_fuel_register_rejected(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify duplicate fuel register for same (site_id, date, shift) returns 400/409
    (enforcing uix_site_date_shift_fuel).
    """
    payload = {
        "site_id": test_site.id,
        "date": "2026-09-24",
        "shift": "NIGHT",
        "opening_stock_liters": 800.0,
        "received_bowser_liters": 0.0,
        "received_drums_liters": 0.0,
        "total_issued_to_equipment_liters": 200.0,
        "closing_dip_stock_liters": 600.0,
    }

    res1 = await client.post("/api/v1/fuel/fuel-register", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201), res1.text

    # Second submission with same (site_id, date, shift)
    res2 = await client.post("/api/v1/fuel/fuel-register", json=payload, headers=auth_headers)
    assert res2.status_code in (400, 409), res2.text
    assert "already exists" in res2.json()["detail"].lower() or "integrity" in res2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_fuel_register_list_and_current_stock(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """Verify GET /fuel-register and GET /fuel-register/current-stock/{site_id}."""
    # Seed a register
    payload = {
        "site_id": test_site.id,
        "date": "2026-09-25",
        "shift": "DAY",
        "opening_stock_liters": 1500.0,
        "received_bowser_liters": 0.0,
        "received_drums_liters": 0.0,
        "total_issued_to_equipment_liters": 500.0,
        "closing_dip_stock_liters": 1000.0,
    }
    create_res = await client.post("/api/v1/fuel/fuel-register", json=payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)

    # 1. List fuel registers
    list_res = await client.get(f"/api/v1/fuel/fuel-register?site_id={test_site.id}", headers=auth_headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(item["closing_dip_stock_liters"] == 1000.0 for item in items)

    # 2. Current stock endpoint via prefix /fuel
    stock_res1 = await client.get(f"/api/v1/fuel/current-stock/{test_site.id}", headers=auth_headers)
    assert stock_res1.status_code == 200
    assert stock_res1.json()["closing_dip_stock_liters"] == 1000.0
    assert stock_res1.json()["current_stock_liters"] == 1000.0

    # 3. Current stock endpoint via direct alias /fuel-register/current-stock/{site_id}
    stock_res2 = await client.get(f"/api/v1/fuel-register/current-stock/{test_site.id}", headers=auth_headers)
    assert stock_res2.status_code == 200
    assert stock_res2.json()["closing_dip_stock_liters"] == 1000.0


@pytest.mark.integration
@pytest.mark.anyio
async def test_unauthenticated_access_rejected(
    client: AsyncClient,
    test_site: Site,
):
    """Verify that unauthenticated requests to protected endpoints return 401."""
    res1 = await client.post("/api/v1/dpr", json={"site_id": test_site.id})
    assert res1.status_code == 401

    res2 = await client.post("/api/v1/fuel/fuel-register", json={"site_id": test_site.id})
    assert res2.status_code == 401
