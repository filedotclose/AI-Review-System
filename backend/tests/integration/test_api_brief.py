import pytest
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User
from app.models.project import Project, Site, Pile, PileStatus
from app.models.equipment import SiteFuelRegister, ShiftType, Equipment, EquipmentType, EquipmentStatus
from app.models.dpr import DailyProgressReport, PileDailyProgress, DPRStatus
from app.models.petty_cash import (
    PettyCashWallet,
    PettyCashTransaction,
    TransactionType,
    ExpenseCategory,
    ReimbursementStatus,
)
from app.models.attendance import (
    Worker,
    WorkerCategory,
    AttendanceRecord,
    AttendanceStatus,
    GangAttendanceRecord,
    GangTrade,
)
from app.models.executive_brief import ExecutiveBrief, DeliveryStatus, DeliveryChannel
from app.tasks.celery_app import celery_app
from app.tasks.notification_tasks import (
    simulate_whatsapp_delivery,
    simulate_email_delivery,
    format_whatsapp_brief_message,
    format_email_brief_html,
)
from app.tasks.brief_tasks import generate_morning_brief, generate_morning_brief_task


# ==============================================================================
# 1. Celery Configuration Tests
# ==============================================================================

def test_celery_app_configuration():
    """Verify Celery app broker, backend, timezone (Asia/Kolkata), and beat schedule."""
    assert celery_app.conf.timezone == "Asia/Kolkata"
    assert celery_app.conf.enable_utc is False
    assert celery_app.conf.beat_schedule is not None
    assert "daily-morning-brief-8am" in celery_app.conf.beat_schedule

    schedule_cfg = celery_app.conf.beat_schedule["daily-morning-brief-8am"]
    assert schedule_cfg["task"] == "app.tasks.brief_tasks.generate_morning_brief_task"
    # Schedule is crontab hour=8, minute=0
    crontab_sched = schedule_cfg["schedule"]
    assert 8 in crontab_sched.hour
    assert 0 in crontab_sched.minute


# ==============================================================================
# 2. Notification Delivery Simulation Tests
# ==============================================================================

def test_whatsapp_delivery_simulation_payload():
    """Verify WhatsApp markdown payload formatting with civil KPIs and alerts."""
    sample_brief_data = {
        "operational_date": "2026-09-21",
        "piling": {
            "completed_piles": 3,
            "drilled_meters": 42.5,
            "concrete_poured_m3": 28.0,
            "active_rigs": 2,
            "delays": ["Rig 2 hydraulic hose maintenance (1.5h)"],
        },
        "fuel": {
            "total_opening_stock": 5000.0,
            "total_received": 2000.0,
            "total_issued": 1200.0,
            "total_closing_dip": 5740.0,
            "total_variance": -60.0,
        },
        "petty_cash": {
            "total_spent": 8500.0,
            "out_of_pocket_spent": 3000.0,
            "deficit_amount": 15000.0,
        },
        "attendance": {
            "direct_workers_present": 8,
            "direct_hours": 64.0,
            "gang_headcount": 22,
            "total_headcount": 30,
        },
        "alerts": [
            {
                "type": "FUEL_VARIANCE",
                "severity": "WARNING",
                "message": "Site #1 fuel dip variance of -60.0L exceeds threshold",
            },
            {
                "type": "WALLET_DEFICIT",
                "severity": "WARNING",
                "message": "Site #1 wallet in deficit: ₹15,000.00",
            },
        ],
    }

    result = simulate_whatsapp_delivery(
        brief_id=1,
        phone_numbers=["+919876543210"],
        brief_data=sample_brief_data,
    )

    assert result["status"] == "DELIVERED"
    assert result["channel"] == "WHATSAPP"
    assert result["brief_id"] == 1
    assert "+919876543210" in result["recipients"]

    msg = result["formatted_text"]
    assert "ODIPKS EXECUTIVE DAILY BRIEF" in msg
    assert "2026-09-21" in msg
    assert "42.5 m" in msg
    assert "Completed Piles: *3*" in msg
    assert "1200.0 L" in msg
    assert "₹8,500.00" in msg
    assert "₹15,000.00" in msg
    assert "Total Headcount: *30*" in msg
    assert "ALERTS & ANOMALIES" in msg


def test_email_delivery_simulation_payload():
    """Verify Email HTML payload formatting with complete executive scorecard."""
    sample_brief_data = {
        "operational_date": "2026-09-21",
        "piling": {
            "completed_piles": 2,
            "drilled_meters": 35.0,
            "concrete_poured_m3": 24.0,
            "active_rigs": 1,
        },
        "fuel": {
            "total_issued": 650.0,
            "total_closing_dip": 4500.0,
            "total_variance": 0.0,
        },
        "petty_cash": {
            "total_spent": 4200.0,
            "out_of_pocket_spent": 0.0,
            "deficit_amount": 0.0,
        },
        "attendance": {
            "direct_workers_present": 6,
            "gang_headcount": 14,
            "total_headcount": 20,
        },
        "alerts": [],
    }

    result = simulate_email_delivery(
        brief_id=2,
        emails=["executive@odipks.test"],
        brief_data=sample_brief_data,
    )

    assert result["status"] == "DELIVERED"
    assert result["channel"] == "EMAIL"
    assert result["brief_id"] == 2
    assert "executive@odipks.test" in result["recipients"]
    assert "ODIPKS Construction OS — Executive Daily Brief" in result["subject"]
    assert "<!DOCTYPE html>" in result["html_body"]
    assert "35.0 m" in result["html_body"]
    assert "650.0 L" in result["html_body"]
    assert "₹4,200.00" in result["html_body"]


# ==============================================================================
# 3. Aggregation Engine & DB Persistence Tests
# ==============================================================================

@pytest.mark.anyio
async def test_brief_aggregation_engine_with_real_records(
    db_session: AsyncSession,
    test_user: User,
    test_project: Project,
    test_site: Site,
    test_worker: Worker,
):
    """
    Verify genuine multi-table data aggregation across:
    DPR + Piling progress, Fuel register, Petty cash wallet & expenses, Direct + Gang attendance.
    """
    test_date = date(2026, 9, 21)

    # 1. Create DPR and Pile progress
    dpr = DailyProgressReport(
        site_id=test_site.id,
        operational_date=test_date,
        shift=ShiftType.DAY,
        submitted_by=test_user.id,
        submitted_at=datetime.now(timezone.utc),
        status=DPRStatus.SUBMITTED,
        problems_delays="Bentonite pump tripped for 45 mins",
        tomorrows_plan="Complete socketing Pier 4",
    )
    db_session.add(dpr)
    await db_session.commit()
    await db_session.refresh(dpr)

    pile = Pile(
        site_id=test_site.id,
        pier_number="P4",
        pile_number="P4-1",
        diameter_mm=1200,
        status=PileStatus.COMPLETED,
    )
    db_session.add(pile)
    await db_session.commit()
    await db_session.refresh(pile)

    pile_prog = PileDailyProgress(
        dpr_id=dpr.id,
        pile_id=pile.id,
        depth_drilled_today_m=18.5,
        concrete_volume_actual_m3=21.0,
        delay_reason="Power cable inspection",
    )
    db_session.add(pile_prog)

    # 2. Create Fuel Register with variance
    fuel_reg = SiteFuelRegister(
        site_id=test_site.id,
        dpr_id=dpr.id,
        date=test_date,
        shift=ShiftType.DAY,
        opening_stock_liters=4000.0,
        received_bowser_liters=1000.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=900.0,
        closing_dip_stock_liters=4020.0,
        variance_liters=-80.0,
        recorded_by=test_user.id,
    )
    db_session.add(fuel_reg)

    # 3. Create Petty Cash Wallet with deficit & expense transaction
    wallet = PettyCashWallet(
        site_id=test_site.id,
        current_balance=-15000.0,  # ₹15k deficit
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)

    tx = PettyCashTransaction(
        wallet_id=wallet.id,
        project_id=test_project.id,
        date=test_date,
        type=TransactionType.EXPENSE,
        amount=6500.0,
        category=ExpenseCategory.TOOLS,
        description="Emergency rig drill teeth replacement",
        has_physical_bill=True,
        is_out_of_pocket=True,
        reimbursement_status=ReimbursementStatus.DUE,
        recorded_by=test_user.id,
    )
    db_session.add(tx)

    # 4. Create Attendance: 1 Direct worker + 1 Gang muster (12 workers)
    att_rec = AttendanceRecord(
        site_id=test_site.id,
        worker_id=test_worker.id,
        date=test_date,
        shift=ShiftType.DAY,
        check_in_time=datetime.now(timezone.utc),
        hours_worked=9.0,
        status=AttendanceStatus.PRESENT,
    )
    db_session.add(att_rec)

    gang_rec = GangAttendanceRecord(
        site_id=test_site.id,
        date=test_date,
        shift=ShiftType.DAY,
        subcontractor_name="Shree Ram Construction",
        trade=GangTrade.PILING_GANG,
        headcount_present=12,
        total_ot_hours=6.0,
        verified_by=test_user.id,
    )
    db_session.add(gang_rec)
    await db_session.commit()

    # Execute Aggregation Engine
    result = await generate_morning_brief(operational_date=test_date, session=db_session)

    # Validate output dictionary
    assert result["operational_date"] == test_date
    assert result["delivery_status"] == DeliveryStatus.SENT
    assert result["delivery_channel"] == DeliveryChannel.BOTH

    bd = result["brief_data"]
    assert bd["piling"]["drilled_meters"] == 18.5
    assert bd["piling"]["concrete_poured_m3"] == 21.0
    assert bd["piling"]["completed_piles"] == 1

    assert bd["fuel"]["total_issued"] == 900.0
    assert bd["fuel"]["total_closing_dip"] == 4020.0
    assert bd["fuel"]["total_variance"] == -80.0

    assert bd["petty_cash"]["total_spent"] == 6500.0
    assert bd["petty_cash"]["out_of_pocket_spent"] == 6500.0
    assert bd["petty_cash"]["deficit_amount"] == 15000.0

    assert bd["attendance"]["direct_workers_present"] == 1
    assert bd["attendance"]["gang_headcount"] == 12
    assert bd["attendance"]["total_headcount"] == 13

    # Summary checks
    assert result["summary"]["piling_linear_meters"] == 18.5
    assert result["summary"]["total_manpower_headcount"] == 13
    assert result["summary"]["diesel_consumed_liters"] == 900.0
    assert result["summary"]["petty_cash_spent"] == 6500.0

    # Verify persisted in database
    db_brief_stmt = select(ExecutiveBrief).where(ExecutiveBrief.operational_date == test_date)
    persisted = (await db_session.execute(db_brief_stmt)).scalars().first()
    assert persisted is not None
    assert persisted.delivery_status == DeliveryStatus.SENT
    assert persisted.brief_data["piling"]["drilled_meters"] == 18.5


# ==============================================================================
# 4. API Endpoints Integration Tests
# ==============================================================================

@pytest.mark.anyio
async def test_get_daily_brief_success(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    owner_headers: Dict[str, str],
):
    """Verify GET /api/v1/brief/daily returns existing executive brief."""
    op_date = date(2026, 9, 20)
    sample_brief = ExecutiveBrief(
        operational_date=op_date,
        delivery_status=DeliveryStatus.SENT,
        delivery_channel=DeliveryChannel.BOTH,
        brief_data={
            "operational_date": op_date.isoformat(),
            "summary": {
                "piling_linear_meters": 28.0,
                "wells_sunk_cm": 0.0,
                "total_manpower_headcount": 18,
                "diesel_consumed_liters": 450.0,
                "petty_cash_spent": 1200.0,
                "active_delays_count": 0,
                "critical_alerts_count": 0,
            },
            "metric_cards": [
                {"title": "Piling Depth", "value": 28.0, "unit": "m", "status": "NORMAL"}
            ],
            "alerts": [],
        },
        alerts=[],
    )
    db_session.add(sample_brief)
    await db_session.commit()

    # Query with specific date
    res = await client.get(f"/api/v1/brief/daily?date={op_date.isoformat()}", headers=owner_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["operational_date"] == op_date.isoformat()
    assert data["delivery_status"] == "SENT"
    assert data["delivery_channel"] == "BOTH"
    assert data["summary"]["piling_linear_meters"] == 28.0
    assert len(data["metric_cards"]) == 1

    # Query without date (returns latest)
    res_latest = await client.get("/api/v1/brief/daily", headers=owner_headers)
    assert res_latest.status_code == 200
    assert res_latest.json()["operational_date"] == op_date.isoformat()


@pytest.mark.anyio
async def test_get_daily_brief_not_found(
    client: AsyncClient,
    test_user: User,
    owner_headers: Dict[str, str],
):
    """Verify GET /api/v1/brief/daily returns 404 when date does not exist."""
    res = await client.get("/api/v1/brief/daily?date=2099-12-31", headers=owner_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.anyio
async def test_post_brief_generate_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    owner_headers: Dict[str, str],
    test_site: Site,
    test_user: User,
):
    """Verify POST /api/v1/brief/generate creates and returns fresh executive brief."""
    gen_date = date(2026, 9, 22)

    # Pre-seed a fuel record to ensure dynamic aggregation produces non-zero metrics
    fuel_reg = SiteFuelRegister(
        site_id=test_site.id,
        date=gen_date,
        shift=ShiftType.DAY,
        opening_stock_liters=3000.0,
        received_bowser_liters=1500.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=750.0,
        closing_dip_stock_liters=3750.0,
        variance_liters=0.0,
        recorded_by=test_user.id,
    )
    db_session.add(fuel_reg)
    await db_session.commit()

    # Trigger generation
    payload = {
        "operational_date": gen_date.isoformat(),
        "delivery_channel": "BOTH",
    }
    res = await client.post("/api/v1/brief/generate", json=payload, headers=owner_headers)
    assert res.status_code in (200, 201), res.text
    data = res.json()

    assert data["operational_date"] == gen_date.isoformat()
    assert data["delivery_status"] == "SENT"
    assert data["brief_data"]["fuel"]["total_issued"] == 750.0
    assert data["summary"]["diesel_consumed_liters"] == 750.0


@pytest.mark.anyio
async def test_brief_endpoints_unauthenticated_rejected(client: AsyncClient):
    """Verify unauthenticated requests to /brief/daily and /brief/generate are rejected with 401."""
    res1 = await client.get("/api/v1/brief/daily")
    assert res1.status_code == 401

    res2 = await client.post("/api/v1/brief/generate", json={"operational_date": "2026-09-21"})
    assert res2.status_code == 401


@pytest.mark.anyio
async def test_brief_history_and_redelivery(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    owner_headers: Dict[str, str],
):
    """Verify GET /api/v1/brief/history and POST /api/v1/brief/{id}/deliver."""
    d1 = date(2026, 9, 18)
    d2 = date(2026, 9, 19)

    b1 = ExecutiveBrief(operational_date=d1, delivery_status=DeliveryStatus.SENT, delivery_channel=DeliveryChannel.BOTH, brief_data={})
    b2 = ExecutiveBrief(operational_date=d2, delivery_status=DeliveryStatus.SENT, delivery_channel=DeliveryChannel.BOTH, brief_data={})
    db_session.add_all([b1, b2])
    await db_session.commit()
    await db_session.refresh(b1)

    # Test history
    res_hist = await client.get("/api/v1/brief/history", headers=owner_headers)
    assert res_hist.status_code == 200
    items = res_hist.json()
    assert len(items) >= 2

    # Test redelivery simulation
    res_deliv = await client.post(f"/api/v1/brief/{b1.id}/deliver?channel=WHATSAPP", headers=owner_headers)
    assert res_deliv.status_code == 200
    deliv_data = res_deliv.json()
    assert deliv_data["brief_id"] == b1.id
    assert "whatsapp" in deliv_data["deliveries"]


@pytest.mark.anyio
async def test_brief_task_direct_execution(
    db_session: AsyncSession,
    test_user: User,
    test_site: Site,
):
    """Verify generate_morning_brief executes directly with an AsyncSession and persists record."""
    direct_date = date(2026, 9, 24)
    result = await generate_morning_brief(operational_date=direct_date, session=db_session)
    assert result["operational_date"] == direct_date
    assert result["delivery_status"] == DeliveryStatus.SENT
    assert "brief_data" in result
    assert "summary" in result

