import logging
from sqlalchemy import select
from app.db.base import async_session
from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, ProjectStatus, SiteStatus, PileStatus
from app.models.equipment import Equipment, EquipmentType
from app.models.petty_cash import PettyCashWallet
from app.core.security import get_password_hash, get_pin_hash

logger = logging.getLogger(__name__)

async def ensure_initial_data():
    """
    Self-healing database initialization:
    Ensures that default users and initial site data always exist in the database.
    """
    try:
        async with async_session() as session:
            # Check if users already exist
            stmt = select(User).limit(1)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.info("Database users table already verified.")
                return

            logger.info("Users table is empty. Seeding initial users and site records...")

            # 1. Default Field Worker / Site Engineer
            user_field = User(
                name="Rajesh Sharma",
                email="rajesh@odipks.com",
                phone="9876543210",
                role=UserRole.SITE_ENGINEER,
                password_hash=get_password_hash("password123"),
                pin_hash=get_pin_hash("1234"),
                is_active=True,
            )

            # 2. Default Project Manager
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

            # 3. Default Project & Site
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

            # 4. Initial Piles
            piles = [
                Pile(site_id=site.id, pier_number="P12", pile_number="P-101", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.COMPLETED),
                Pile(site_id=site.id, pier_number="P12", pile_number="P-102", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.COMPLETED),
                Pile(site_id=site.id, pier_number="P12", pile_number="P-103", diameter_mm=1000, planned_depth_m=24.0, status=PileStatus.BORING),
            ]
            session.add_all(piles)

            # 5. Site Equipment
            eq1 = Equipment(name="Bauer BG-28 Rotary Rig #1", registration_number="EQ-RIG-01", type=EquipmentType.RIG, site_id=site.id)
            eq2 = Equipment(name="Sany SCC-500 Crawler Crane", registration_number="EQ-CRANE-01", type=EquipmentType.CRANE, site_id=site.id)
            session.add_all([eq1, eq2])

            # 6. Site Wallet
            wallet = PettyCashWallet(site_id=site.id, current_balance=14500.0)
            session.add(wallet)

            await session.commit()
            logger.info("Successfully seeded default users and initial site data!")

    except Exception as e:
        logger.error(f"Error checking/seeding initial database data: {e}", exc_info=True)
