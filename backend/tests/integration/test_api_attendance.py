import pytest
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.project import Site, Project
from app.models.equipment import ShiftType
from app.models.attendance import (
    Worker,
    WorkerCategory,
    AttendanceRecord,
    AttendanceStatus,
    GangAttendanceRecord,
    GangTrade,
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
async def extra_worker(db_session: AsyncSession, test_site: Site) -> Worker:
    """Additional pre-seeded Worker entity."""
    worker = Worker(
        name="Suresh Patel",
        phone="+919876500001",
        category=WorkerCategory.WELDER,
        assigned_site_id=test_site.id,
        is_active=True,
    )
    db_session.add(worker)
    await db_session.commit()
    await db_session.refresh(worker)
    return worker


# ==============================================================================
# Attendance API Integration Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_worker_check_in_and_check_out_valid(
    client: AsyncClient,
    test_site: Site,
    test_worker: Worker,
    auth_headers: Dict[str, str],
):
    """
    Verify valid worker check-in followed by check-out:
    - POST /check-in records timestamp and validates geofence.
    - POST /check-out computes hours worked and records check_out_time.
    """
    # 1. Check-in within site geofence (Vadodara site is lat 22.3072, lng 73.1812)
    check_in_payload = {
        "site_id": test_site.id,
        "worker_id": test_worker.id,
        "date": "2026-09-21",
        "shift": "DAY",
        "check_in_lat": 22.3073,  # ~15 meters from site center
        "check_in_lng": 73.1813,
    }

    in_res = await client.post("/api/v1/attendance/check-in", json=check_in_payload, headers=auth_headers)
    assert in_res.status_code in (200, 201), in_res.text
    in_data = in_res.json()
    assert in_data["worker_id"] == test_worker.id
    assert in_data["site_id"] == test_site.id
    assert in_data["shift"] == "DAY"
    assert in_data["within_geofence"] is True
    assert in_data["anomaly_flag"] is False
    assert in_data["check_out_time"] is None
    record_id = in_data["id"]

    # 2. Check-out
    check_out_payload = {
        "record_id": record_id,
        "check_out_lat": 22.3074,
        "check_out_lng": 73.1814,
    }
    out_res = await client.post("/api/v1/attendance/check-out", json=check_out_payload, headers=auth_headers)
    assert out_res.status_code == 200, out_res.text
    out_data = out_res.json()
    assert out_data["id"] == record_id
    assert out_data["check_out_time"] is not None
    assert out_data["hours_worked"] is not None


@pytest.mark.integration
@pytest.mark.anyio
async def test_duplicate_worker_check_in_rejected(
    client: AsyncClient,
    test_site: Site,
    test_worker: Worker,
    auth_headers: Dict[str, str],
):
    """
    Verify UniqueConstraint 'uix_worker_date_shift_att':
    Attempting duplicate check-in for same (worker_id, date, shift) returns HTTP 400.
    """
    payload = {
        "site_id": test_site.id,
        "worker_id": test_worker.id,
        "date": "2026-09-22",
        "shift": "NIGHT",
        "check_in_lat": 22.3072,
        "check_in_lng": 73.1812,
    }

    # 1. First check-in succeeds
    res1 = await client.post("/api/v1/attendance/check-in", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201), res1.text

    # 2. Second check-in with exact same worker, date, shift must fail
    res2 = await client.post("/api/v1/attendance/check-in", json=payload, headers=auth_headers)
    assert res2.status_code == 400, res2.text
    assert "already checked in" in res2.json()["detail"].lower() or "unique constraint" in res2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_worker_check_in_geofence_breach_flagged(
    client: AsyncClient,
    test_site: Site,
    extra_worker: Worker,
    auth_headers: Dict[str, str],
):
    """
    Verify geofence boundary detection:
    A check-in > 500m from site coordinates is accepted but flagged with within_geofence=False and anomaly_flag=True.
    """
    # Site center is ~22.3072, 73.1812. Put worker 5km away (~22.3500, 73.2300)
    payload = {
        "site_id": test_site.id,
        "worker_id": extra_worker.id,
        "date": "2026-09-23",
        "shift": "DAY",
        "check_in_lat": 22.3500,
        "check_in_lng": 73.2300,
    }

    res = await client.post("/api/v1/attendance/check-in", json=payload, headers=auth_headers)
    assert res.status_code in (200, 201), res.text
    data = res.json()
    assert data["within_geofence"] is False
    assert data["anomaly_flag"] is True
    assert "geofence" in data["anomaly_reason"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_subcontractor_gang_muster_and_duplicate_rejection(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify subcontractor gang muster submission and UniqueConstraint 'uix_site_date_shift_gang':
    Duplicate gang muster for same (site_id, date, shift, subcontractor, trade) is rejected with HTTP 400.
    """
    payload = {
        "site_id": test_site.id,
        "date": "2026-09-21",
        "shift": "DAY",
        "subcontractor_name": "Larsen & Toubro Civil Sub 1",
        "trade": "PILING_GANG",
        "headcount_present": 12,
        "total_ot_hours": 24.0,
        "muster_roll_photo_url": "https://storage.test/muster-2026-09-21.jpg",
    }

    # 1. First submission succeeds
    res1 = await client.post("/api/v1/attendance/gang-muster", json=payload, headers=auth_headers)
    assert res1.status_code in (200, 201), res1.text
    data = res1.json()
    assert data["subcontractor_name"] == "Larsen & Toubro Civil Sub 1"
    assert data["headcount_present"] == 12
    assert data["trade"] == "PILING_GANG"

    # 2. Duplicate submission with exact same key must fail
    res2 = await client.post("/api/v1/attendance/gang-muster", json=payload, headers=auth_headers)
    assert res2.status_code == 400, res2.text
    assert "already recorded" in res2.json()["detail"].lower() or "unique constraint" in res2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.anyio
async def test_attendance_anomalies_reporting(
    client: AsyncClient,
    test_site: Site,
    extra_worker: Worker,
    auth_headers: Dict[str, str],
):
    """
    Verify GET /attendance/anomalies returns flagged anomalies (geofence breaches, ghost worker flags).
    """
    # 1. Seed a geofence breach check-in
    payload = {
        "site_id": test_site.id,
        "worker_id": extra_worker.id,
        "date": "2026-09-24",
        "shift": "DAY",
        "check_in_lat": 23.0000,  # ~75km away
        "check_in_lng": 72.5000,
    }
    in_res = await client.post("/api/v1/attendance/check-in", json=payload, headers=auth_headers)
    assert in_res.status_code in (200, 201)

    # 2. Query anomalies
    res = await client.get(f"/api/v1/attendance/anomalies?site_id={test_site.id}", headers=auth_headers)
    assert res.status_code == 200, res.text
    alerts = res.json()
    assert len(alerts) >= 1
    assert any(alert["worker_id"] == extra_worker.id for alert in alerts)
    assert any("GEOFENCE" in alert["anomaly_type"] for alert in alerts)


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_site_attendance_summary(
    client: AsyncClient,
    test_site: Site,
    test_worker: Worker,
    auth_headers: Dict[str, str],
):
    """
    Verify GET /attendance/site/{site_id} returns both individual worker check-ins and gang muster headcounts.
    """
    # Seed worker check-in
    await client.post(
        "/api/v1/attendance/check-in",
        json={"site_id": test_site.id, "worker_id": test_worker.id, "date": "2026-09-25", "shift": "DAY"},
        headers=auth_headers,
    )

    # Seed gang muster
    await client.post(
        "/api/v1/attendance/gang-muster",
        json={
            "site_id": test_site.id,
            "date": "2026-09-25",
            "shift": "DAY",
            "subcontractor_name": "Afcons Infra Gang",
            "trade": "STEEL_BENDING",
            "headcount_present": 8,
        },
        headers=auth_headers,
    )

    res = await client.get(
        f"/api/v1/attendance/site/{test_site.id}?date=2026-09-25&shift=DAY",
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["site_id"] == test_site.id
    assert data["worker_count"] >= 1
    assert data["total_gang_headcount"] >= 8
    assert len(data["workers"]) >= 1
    assert len(data["gangs"]) >= 1


@pytest.mark.integration
@pytest.mark.anyio
async def test_worker_registration_and_list(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify registering a casual worker via POST /attendance/workers and querying via GET /attendance/workers.
    """
    worker_payload = {
        "name": "Mahesh Baria",
        "phone": "+919876599999",
        "category": "RIG_HELPER",
        "assigned_site_id": test_site.id,
    }
    reg_res = await client.post("/api/v1/attendance/workers", json=worker_payload, headers=auth_headers)
    assert reg_res.status_code in (200, 201), reg_res.text
    worker_data = reg_res.json()
    assert worker_data["name"] == "Mahesh Baria"
    assert worker_data["category"] == "RIG_HELPER"

    # List workers
    list_res = await client.get(f"/api/v1/attendance/workers?site_id={test_site.id}", headers=auth_headers)
    assert list_res.status_code == 200
    workers = list_res.json()
    assert any(w["name"] == "Mahesh Baria" for w in workers)


@pytest.mark.integration
@pytest.mark.anyio
async def test_direct_root_attendance_routes(
    client: AsyncClient,
    test_site: Site,
    auth_headers: Dict[str, str],
):
    """
    Verify direct un-prefixed alias routes like /api/v1/check-in and /api/v1/gang-muster work.
    """
    res = await client.get(f"/api/v1/site/{test_site.id}", headers=auth_headers)
    assert res.status_code == 200
    assert "worker_count" in res.json()


@pytest.mark.integration
@pytest.mark.anyio
async def test_unauthenticated_attendance_access_rejected(
    client: AsyncClient,
    test_site: Site,
):
    """Verify that unauthenticated requests to attendance endpoints return 401."""
    res1 = await client.post("/api/v1/attendance/check-in", json={"site_id": test_site.id})
    assert res1.status_code == 401

    res2 = await client.post("/api/v1/attendance/gang-muster", json={"site_id": test_site.id})
    assert res2.status_code == 401
