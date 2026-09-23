import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, PileStatus
from app.models.equipment import Equipment, SiteFuelRegister, SiteInventory
from app.models.attendance import Worker, AttendanceRecord, GangAttendanceRecord
from app.models.dpr import DailyProgressReport, PileDailyProgress, TestReport
from app.models.petty_cash import PettyCashTransaction, PettyCashWallet
from app.models.executive_brief import ExecutiveBrief
from app.db.seed_data import seed_database


@pytest.mark.asyncio
async def test_seed_dataset_integrity(db_session: AsyncSession):
    """Verify that seed_database populates rich, realistic operational records correctly."""
    stats = await seed_database(db_session, force=True)

    assert stats["users"] >= 6
    assert stats["projects"] >= 2
    assert stats["sites"] >= 2
    assert stats["piles"] >= 20
    assert stats["equipments"] >= 10
    assert stats["inventory_items"] >= 8
    assert stats["workers"] >= 12
    assert stats["attendance_records"] >= 50
    assert stats["gang_records"] >= 10
    assert stats["dprs"] >= 5
    assert stats["fuel_registers"] >= 8
    assert stats["petty_cash_transactions"] >= 10
    assert stats["executive_briefs"] >= 2

    # 1. Verify User Roles
    users = (await db_session.execute(select(User))).scalars().all()
    roles = {u.role for u in users}
    assert UserRole.OWNER in roles
    assert UserRole.FINANCE_HEAD in roles
    assert UserRole.PROJECT_MANAGER in roles
    assert UserRole.SITE_ENGINEER in roles
    assert UserRole.SUPERVISOR in roles

    # 2. Verify Pile progression statuses
    piles = (await db_session.execute(select(Pile))).scalars().all()
    pile_statuses = {p.status for p in piles}
    assert PileStatus.COMPLETED in pile_statuses
    assert PileStatus.CAST in pile_statuses
    assert PileStatus.CAGED in pile_statuses
    assert PileStatus.SOCKETING in pile_statuses
    assert PileStatus.BORING in pile_statuses
    assert PileStatus.PLANNED in pile_statuses

    # 3. Verify Anomalies exist for audit detection
    att_anomalies = (await db_session.execute(select(AttendanceRecord).where(AttendanceRecord.anomaly_flag == True))).scalars().all()
    assert len(att_anomalies) >= 1
    assert "geofence" in att_anomalies[0].anomaly_reason.lower()

    fuel_anomalies = (await db_session.execute(select(SiteFuelRegister).where(SiteFuelRegister.variance_liters < -50.0))).scalars().all()
    assert len(fuel_anomalies) >= 1

    tx_anomalies = (await db_session.execute(select(PettyCashTransaction).where(PettyCashTransaction.anomaly_flag == True))).scalars().all()
    assert len(tx_anomalies) >= 1
    assert tx_anomalies[0].duplicate_flag is True

    # 4. Verify Executive Briefs with AI Review
    briefs = (await db_session.execute(select(ExecutiveBrief))).scalars().all()
    assert len(briefs) >= 2
    for b in briefs:
        assert b.brief_data is not None
        assert "piling" in b.brief_data
        assert "fuel" in b.brief_data
        assert b.ai_review is not None
        assert "summary" in b.ai_review
