import logging
from sqlalchemy import select
from app.db.base import async_session
from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, ProjectStatus, SiteStatus, PileStatus
from app.models.equipment import Equipment, EquipmentType
from app.models.petty_cash import PettyCashWallet
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
        "email": "engineer@odipks.com",
        "phone": "9811122233",
        "role": UserRole.PROJECT_MANAGER,
        "pin": "9999",
        "password": "password123",
    },
    {
        "name": "Rajesh Sharma",
        "email": "rajesh@odipks.com",
        "phone": "9876543210",
        "role": UserRole.SITE_ENGINEER,
        "pin": "1234",
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
]

async def ensure_initial_data():
    """
    Self-healing database initialization:
    Ensures that default users for all 5 system roles and initial site data always exist.
    """
    try:
        async with async_session() as session:
            # 1. Ensure all 5 roles exist in the users table
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
                    logger.info(f"Seeded user for role {u['role'].value}: {u['name']}")

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

                # Wallet
                wallet = PettyCashWallet(site_id=site.id, current_balance=14500.0)
                session.add(wallet)

            await session.commit()
            logger.info("Database users and operational data verified for all 5 roles.")

    except Exception as e:
        logger.error(f"Error checking/seeding initial database data: {e}", exc_info=True)
