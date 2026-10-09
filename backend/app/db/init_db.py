import logging
from datetime import datetime, timezone
from sqlalchemy import select, delete, update
from app.db.base import async_session
from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, ProjectStatus, SiteStatus, PileStatus
from app.models.equipment import Equipment, EquipmentType, SiteFuelRegister
from app.models.petty_cash import (
    PettyCashWallet,
    PettyCashTransaction,
    TransactionType,
    ExpenseCategory,
    ApprovalStatus,
    ReimbursementStatus,
)
from app.models.attendance import Worker, WorkerCategory
from app.models.dpr import (
    DailyProgressReport,
    PileDailyProgress,
    WellLog,
    EquipmentLog,
    LabourSummary,
    MaterialConsumption,
    TestReport,
)
from app.core.security import get_password_hash, get_pin_hash

logger = logging.getLogger(__name__)

STANDARD_USERS = [
    {
        "name": "Pradeep K. Sharma",
        "email": "owner@odipks.com",
        "phone": "9800000001",
        "role": UserRole.OWNER,
        "pin": "1234",
        "password": "password123",
    },
    {
        "name": "Ananya Sen",
        "email": "finance@odipks.com",
        "phone": "9800000002",
        "role": UserRole.FINANCE_HEAD,
        "pin": "1234",
        "password": "password123",
    },
    {
        "name": "Vikram Mehta",
        "email": "pm@odipks.com",
        "phone": "9811122233",
        "role": UserRole.PROJECT_MANAGER,
        "pin": "1234",
        "password": "password123",
    },
    {
        "name": "Vikram Mehta (Alias)",
        "email": "engineer@odipks.com",
        "phone": "9811122234",
        "role": UserRole.PROJECT_MANAGER,
        "pin": "9999",
        "password": "password123",
    },
    {
        "name": "Sunil Varma",
        "email": "supervisor@odipks.com",
        "phone": "9876543211",
        "role": UserRole.SUPERVISOR,
        "pin": "1234",
        "password": "password123",
    },
    # 3 Standard Site Engineers (enggA, enggB, enggC)
    {
        "name": "Site Engineer A",
        "email": "engga@odipks.com",
        "phone": "9876543201",
        "role": UserRole.SITE_ENGINEER,
        "pin": "1234",
        "password": "password123",
    },
    {
        "name": "Site Engineer B",
        "email": "enggb@odipks.com",
        "phone": "9876543202",
        "role": UserRole.SITE_ENGINEER,
        "pin": "1234",
        "password": "password123",
    },
    {
        "name": "Site Engineer C",
        "email": "enggc@odipks.com",
        "phone": "9876543203",
        "role": UserRole.SITE_ENGINEER,
        "pin": "1234",
        "password": "password123",
    },
    # Legacy default Site Engineer
    {
        "name": "Rajesh Sharma",
        "email": "rajesh@odipks.com",
        "phone": "9876543210",
        "role": UserRole.SITE_ENGINEER,
        "pin": "1234",
        "password": "password123",
    },
]

async def ensure_initial_data():
    """
    Self-healing database initialization:
    - Ensures standard users for all roles and 3 site engineers (enggA, enggB, enggC)
    - Ensures project, site, and petty cash wallet exist
    - Ensures standard workers exist for site attendance
    - Cleans out seeded demo DPRs so newly uploaded company DPRs take precedence
    """
    try:
        async with async_session() as session:
            # 1. Ensure all standard roles and site engineers exist in users table
            for u in STANDARD_USERS:
                stmt = select(User).where((User.phone == u["phone"]) | (User.email == u["email"])).limit(1)
                res = await session.execute(stmt)
                user = res.scalar_one_or_none()

                if not user:
                    new_user = User(
                        name=u["name"],
                        email=u["email"],
                        phone=u["phone"],
                        role=u["role"],
                        password_hash=get_password_hash(u["password"]),
                        pin_hash=get_pin_hash(u["pin"]),
                        is_active=True,
                    )
                    session.add(new_user)
                    logger.info(f"Seeded user for role {u['role'].value}: {u['name']} ({u['email']})")
                else:
                    user.email = u["email"]
                    user.role = u["role"]
                    user.password_hash = get_password_hash(u["password"])
                    user.pin_hash = get_pin_hash(u["pin"])
                    user.is_active = True

            await session.flush()

            # 2. Ensure default project & site exist
            proj_stmt = select(Project).limit(1)
            proj_res = await session.execute(proj_stmt)
            proj = proj_res.scalar_one_or_none()

            if not proj:
                proj = Project(
                    name="ADANI-ODIPKS AVRP Flyover Package",
                    code="AVRP-FLYOVER-01",
                    status=ProjectStatus.ACTIVE,
                    location="Vadakara, Kerala",
                )
                session.add(proj)
                await session.flush()

            site_stmt = select(Site).limit(1)
            site_res = await session.execute(site_stmt)
            site = site_res.scalar_one_or_none()

            if not site:
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

                # Piles
                piles = [
                    Pile(site_id=site.id, pier_number="P12", pile_number="P-101", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.COMPLETED),
                    Pile(site_id=site.id, pier_number="P12", pile_number="P-102", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.COMPLETED),
                    Pile(site_id=site.id, pier_number="P12", pile_number="P-103", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.BORING),
                ]
                session.add_all(piles)

                # Equipment
                eq1 = Equipment(name="Bauer BG-28 Rotary Rig #1", registration_number="EQ-RIG-01", type=EquipmentType.RIG, site_id=site.id)
                eq2 = Equipment(name="Sany SCC-500 Crawler Crane", registration_number="EQ-CRANE-01", type=EquipmentType.CRANE, site_id=site.id)
                session.add_all([eq1, eq2])

            # 3. Ensure Petty Cash Wallet exists with clean starting balance (no fake transactions)
            wallet_stmt = select(PettyCashWallet).where(PettyCashWallet.site_id == site.id).limit(1)
            wallet = (await session.execute(wallet_stmt)).scalar_one_or_none()
            if not wallet:
                wallet = PettyCashWallet(site_id=site.id, current_balance=25000.0)
                session.add(wallet)
                await session.flush()

            # 4. Ensure standard Workers exist for Attendance check-in
            worker_count_stmt = select(Worker).where(Worker.assigned_site_id == site.id).limit(1)
            existing_worker = (await session.execute(worker_count_stmt)).scalar_one_or_none()
            if not existing_worker:
                standard_workers = [
                    Worker(name="Ramesh Kumar", category=WorkerCategory.OPERATOR, phone="9876500001", assigned_site_id=site.id, is_active=True),
                    Worker(name="Suresh Yadav", category=WorkerCategory.WELDER, phone="9876500002", assigned_site_id=site.id, is_active=True),
                    Worker(name="Manoj Singh", category=WorkerCategory.RIG_HELPER, phone="9876500003", assigned_site_id=site.id, is_active=True),
                    Worker(name="Anil Pillai", category=WorkerCategory.FITTER, phone="9876500004", assigned_site_id=site.id, is_active=True),
                    Worker(name="Vikram Das", category=WorkerCategory.LABOURER, phone="9876500005", assigned_site_id=site.id, is_active=True),
                ]
                session.add_all(standard_workers)

            # 5. Purge seeded demo DPRs so new company DPRs will be uploaded fresh
            demo_weather_markers = [
                "Clear sunny skies, 32°C, humidity 74%. Normal sea breeze.",
                "Partly cloudy, 30°C. Piling conditions favorable.",
                "Overcast, 29°C. Light intermittent drizzle.",
                "Heavy coastal monsoon squall in late afternoon, 27°C.",
                "Clear skies, 31°C, calm wind.",
            ]
            demo_dprs_stmt = select(DailyProgressReport.id).where(
                (DailyProgressReport.weather_conditions.in_(demo_weather_markers))
                | (DailyProgressReport.problems_delays.like("%Monsoon%"))
                | (DailyProgressReport.problems_delays.like("%Bauer BG-28 hydraulic seal weeping%"))
                | (DailyProgressReport.problems_delays.like("%transit mixer stuck%"))
                | (DailyProgressReport.problems_delays.like("%Minor 20-minute wait%"))
                | (DailyProgressReport.problems_delays.like("%Hard rock core extraction%"))
                | (DailyProgressReport.problems_delays.like("%Dual rigs operating concurrently%"))
            )
            demo_dpr_ids = (await session.execute(demo_dprs_stmt)).scalars().all()
            if demo_dpr_ids:
                await session.execute(
                    update(SiteFuelRegister)
                    .where(SiteFuelRegister.dpr_id.in_(demo_dpr_ids))
                    .values(dpr_id=None)
                )
                await session.execute(delete(PileDailyProgress).where(PileDailyProgress.dpr_id.in_(demo_dpr_ids)))
                await session.execute(delete(WellLog).where(WellLog.dpr_id.in_(demo_dpr_ids)))
                await session.execute(delete(EquipmentLog).where(EquipmentLog.dpr_id.in_(demo_dpr_ids)))
                await session.execute(delete(LabourSummary).where(LabourSummary.dpr_id.in_(demo_dpr_ids)))
                await session.execute(delete(MaterialConsumption).where(MaterialConsumption.dpr_id.in_(demo_dpr_ids)))
                await session.execute(delete(TestReport).where(TestReport.dpr_id.in_(demo_dpr_ids)))
                await session.execute(delete(DailyProgressReport).where(DailyProgressReport.id.in_(demo_dpr_ids)))
                logger.info(f"Purged {len(demo_dpr_ids)} seeded demo DPR records.")

            await session.commit()
            logger.info("Database users, operational data, and workers verified.")

    except Exception as e:
        logger.error(f"Error checking/seeding initial database data: {e}", exc_info=True)
