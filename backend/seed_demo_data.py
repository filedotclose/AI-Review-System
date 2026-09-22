import asyncio
import os
import sys
from datetime import date, datetime

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import sqlalchemy.types
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON

# Patch JSONB to JSON for SQLite compatibility
sqlalchemy.types.JSONB = JSON

from app.db.base import Base, engine, async_session
import app.models  # Load all models
from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, ProjectStatus, SiteStatus, PileStatus
from app.models.equipment import Equipment, EquipmentType, SiteFuelRegister, ShiftType
from app.models.petty_cash import PettyCashWallet, PettyCashTransaction, ExpenseCategory, ApprovalStatus, ReimbursementStatus, TransactionType
from app.models.attendance import Worker, AttendanceRecord, WorkerCategory, AttendanceStatus, GangAttendanceRecord
from app.models.dpr import DailyProgressReport, DPRStatus, PileDailyProgress, EquipmentLog, StrataType, CasingType
from app.core.security import get_password_hash, get_pin_hash

# Rewrite any already instantiated table columns
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()


async def init_and_seed():
    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

    async with async_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(User).filter_by(phone="9876543210"))
        if res.scalars().first():
            print("Database already seeded with demo data.")
            return

        print("Seeding demo records...")

        # 1. Users
        user_field = User(
            name="Rajesh Sharma",
            email="rajesh@odipks.com",
            phone="9876543210",
            role=UserRole.SITE_ENGINEER,
            password_hash=get_password_hash("password123"),
            pin_hash=get_pin_hash("1234"),
            is_active=True,
        )
        user_admin = User(
            name="Vikram Mehta",
            email="engineer@odipks.com",
            phone="9811122233",
            role=UserRole.PROJECT_MANAGER,
            password_hash=get_password_hash("password123"),
            pin_hash=get_pin_hash("9999"),
            is_active=True,
        )
        session.add_all([user_field, user_admin])
        await session.flush()

        # 2. Project & Site
        proj = Project(
            name="ADANI-ODIPKS AVRP Flyover Package",
            code="AVRP-FLYOVER-01",
            status=ProjectStatus.ACTIVE,
            location="Vadakara, Kerala",
        )
        session.add(proj)
        await session.flush()

        site = Site(
            project_id=proj.id,
            name="Vadakara AVRP Flyover Site Office",
            status=SiteStatus.ACTIVE,
            location_lat=11.6086,
            location_lng=75.5912,
            geofence_radius_m=500,
        )
        session.add(site)
        await session.flush()

        # 3. Piles
        piles = [
            Pile(site_id=site.id, pier_number="P12", pile_number="P-101", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.COMPLETED),
            Pile(site_id=site.id, pier_number="P12", pile_number="P-102", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.COMPLETED),
            Pile(site_id=site.id, pier_number="P12", pile_number="P-103", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.BORING),
            Pile(site_id=site.id, pier_number="P12", pile_number="P-104", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.PLANNED),
            Pile(site_id=site.id, pier_number="P12", pile_number="P-105", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.PLANNED),
        ]
        session.add_all(piles)

        # 4. Equipment
        eq1 = Equipment(name="Bauer BG-28 Rotary Rig #1", registration_number="EQ-RIG-01", type=EquipmentType.RIG, site_id=site.id)
        eq2 = Equipment(name="Sany SCC-500 Crawler Crane", registration_number="EQ-CRANE-01", type=EquipmentType.CRANE, site_id=site.id)
        eq3 = Equipment(name="DG Set 125 kVA Standby", registration_number="EQ-DG-01", type=EquipmentType.GENERATOR, site_id=site.id)
        session.add_all([eq1, eq2, eq3])

        # 5. Site Wallet
        wallet = PettyCashWallet(site_id=site.id, current_balance=14500.0)
        session.add(wallet)
        await session.flush()

        # 6. Workers
        workers = [
            Worker(name="Ramesh Kumar", category=WorkerCategory.OPERATOR, phone="9876500001", assigned_site_id=site.id),
            Worker(name="Suresh Yadav", category=WorkerCategory.WELDER, phone="9876500002", assigned_site_id=site.id),
            Worker(name="Manoj Singh", category=WorkerCategory.RIG_HELPER, phone="9876500003", assigned_site_id=site.id),
            Worker(name="Anil Pillai", category=WorkerCategory.FITTER, phone="9876500004", assigned_site_id=site.id),
            Worker(name="Vikram Das", category=WorkerCategory.LABOURER, phone="9876500005", assigned_site_id=site.id),
        ]
        session.add_all(workers)

        # 7. Sample Initial Expenses
        today = date.today()
        exp1 = PettyCashTransaction(
            wallet_id=wallet.id,
            project_id=proj.id,
            type=TransactionType.EXPENSE,
            amount=3200.0,
            category=ExpenseCategory.FUEL,
            description="Emergency diesel for standby DG set (35L)",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_field.id,
        )
        exp2 = PettyCashTransaction(
            wallet_id=wallet.id,
            project_id=proj.id,
            type=TransactionType.EXPENSE,
            amount=1450.0,
            category=ExpenseCategory.TOOLS,
            description="Bauer rig hydraulic seals & replacement O-rings",
            has_physical_bill=True,
            is_out_of_pocket=True,
            approval_status=ApprovalStatus.PENDING,
            reimbursement_status=ReimbursementStatus.DUE,
            recorded_by=user_field.id,
        )
        session.add_all([exp1, exp2])

        await session.commit()
        print("Demo data seeded successfully into SQLite!")


if __name__ == "__main__":
    asyncio.run(init_and_seed())
