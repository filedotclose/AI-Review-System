import os
import sys
from pathlib import Path
from datetime import datetime, date, timezone, timedelta
from typing import AsyncGenerator, Optional, Dict, Any

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Set test environment variables BEFORE importing app or settings
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_TIMEZONE", "Asia/Kolkata")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("MINIO_BUCKET", "test-bucket")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-12345678901234567890123456789012")
os.environ.setdefault("WHATSAPP_API_URL", "https://api.whatsapp.test")
os.environ.setdefault("WHATSAPP_API_TOKEN", "test-token")
os.environ.setdefault("WHATSAPP_OWNER_PHONE", "+919876543210")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")
os.environ.setdefault("TWILIO_WHATSAPP_NUMBER", "+14155238886")
os.environ.setdefault("SMTP_HOST", "smtp.test")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "user@test.com")
os.environ.setdefault("SMTP_PASSWORD", "secret")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.com")

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.compiler import compiles
import sqlalchemy.types
from httpx import AsyncClient, ASGITransport

from app.db.base import Base
import app.models  # Import all SQLAlchemy models to register them on Base.metadata
from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, ProjectStatus, SiteStatus, PileStatus
from app.models.equipment import SiteFuelRegister, ShiftType
from app.models.attendance import Worker, AttendanceRecord, WorkerCategory, AttendanceStatus

# Model aliases for flexible testing nomenclature
ShiftFuelRegister = SiteFuelRegister
WorkerAttendance = AttendanceRecord

# Patch JSONB for SQLite testing & compile hook
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

sqlalchemy.types.JSONB = JSON

# Rewrite any already instantiated JSONB column types to SQLite JSON
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configures AnyIO to use standard asyncio event loop for all async fixtures & tests."""
    return "asyncio"


@pytest.fixture
async def test_engine():
    """In-memory SQLite async engine with StaticPool and SQLite PRAGMAs."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Ensure all tables rewrite JSONB columns if newly added
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    import app.db.base
    orig_engine = app.db.base.engine
    orig_session = app.db.base.async_session
    app.db.base.engine = engine
    app.db.base.async_session = async_sessionmaker(
        bind=engine,
        class_=app.db.base.AppAsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    yield engine

    app.db.base.engine = orig_engine
    app.db.base.async_session = orig_session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Isolated async SQLAlchemy session bound to the in-memory test engine."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(test_engine, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client bound to FastAPI application via ASGITransport."""
    from app.main import app

    async def override_get_db():
        yield db_session

    try:
        from app.db.base import get_db
        app.dependency_overrides[get_db] = override_get_db
    except (ImportError, AttributeError):
        pass

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    try:
        from app.db.base import get_db
        app.dependency_overrides.pop(get_db, None)
    except (ImportError, AttributeError):
        pass


def create_mock_jwt(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Utility to generate valid signed HS256 JWT tokens for testing."""
    from authlib.jose import jwt
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.setdefault("exp", int(expire.timestamp()))
    to_encode.setdefault("type", "access")
    header = {"alg": "HS256"}
    secret_key = os.environ.get("JWT_SECRET_KEY", "test-secret-key-12345678901234567890123456789012")
    encoded = jwt.encode(header, to_encode, secret_key)
    if isinstance(encoded, bytes):
        return encoded.decode("utf-8")
    return str(encoded)


@pytest.fixture
def owner_token() -> str:
    return create_mock_jwt({"sub": "1", "phone": "+919876543210", "role": "OWNER"})


@pytest.fixture
def project_manager_token() -> str:
    return create_mock_jwt({"sub": "2", "phone": "+919876543211", "role": "PROJECT_MANAGER"})


@pytest.fixture
def site_engineer_token() -> str:
    return create_mock_jwt({"sub": "3", "phone": "+919876543212", "role": "SITE_ENGINEER"})


@pytest.fixture
def supervisor_token() -> str:
    return create_mock_jwt({"sub": "4", "phone": "+919876543213", "role": "SUPERVISOR"})


@pytest.fixture
def finance_head_token() -> str:
    return create_mock_jwt({"sub": "5", "phone": "+919876543214", "role": "FINANCE_HEAD"})


@pytest.fixture
async def seeded_role_users(db_session: AsyncSession) -> Dict[str, User]:
    users = {
        "OWNER": User(id=1, name="Test Owner", phone="+919876543210", email="owner@odipks.test", role=UserRole.OWNER, is_active=True),
        "PROJECT_MANAGER": User(id=2, name="Test PM", phone="+919876543211", email="pm@odipks.test", role=UserRole.PROJECT_MANAGER, is_active=True),
        "SITE_ENGINEER": User(id=3, name="Test Engineer", phone="+919876543212", email="engineer@odipks.test", role=UserRole.SITE_ENGINEER, is_active=True),
        "SUPERVISOR": User(id=4, name="Test Supervisor", phone="+919876543213", email="supervisor@odipks.test", role=UserRole.SUPERVISOR, is_active=True),
        "FINANCE_HEAD": User(id=5, name="Test Finance", phone="+919876543214", email="finance@odipks.test", role=UserRole.FINANCE_HEAD, is_active=True),
    }
    for u in users.values():
        db_session.add(u)
    await db_session.commit()
    for u in users.values():
        await db_session.refresh(u)
    return users


@pytest.fixture
def owner_headers(seeded_role_users: Dict[str, User], owner_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture
def supervisor_headers(seeded_role_users: Dict[str, User], supervisor_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {supervisor_token}"}


@pytest.fixture
def site_engineer_headers(seeded_role_users: Dict[str, User], site_engineer_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {site_engineer_token}"}


@pytest.fixture
def finance_head_headers(seeded_role_users: Dict[str, User], finance_head_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {finance_head_token}"}


@pytest.fixture
def project_manager_headers(seeded_role_users: Dict[str, User], project_manager_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {project_manager_token}"}


@pytest.fixture
async def test_user(seeded_role_users: Dict[str, User]) -> User:
    """Pre-seeded User entity (Site Engineer by default)."""
    return seeded_role_users["SITE_ENGINEER"]


@pytest.fixture
async def test_project(db_session: AsyncSession) -> Project:
    """Pre-seeded Project entity."""
    project = Project(
        name="Adani Vadodara Metro Pilot",
        code="ADANI-VAD",
        client_name="Adani Heavy Civil Infrastructure",
        location="Vadodara, Gujarat",
        contract_value=250000000.0,
        start_date=date(2026, 1, 1),
        expected_end_date=date(2027, 6, 30),
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_site(db_session: AsyncSession, test_project: Project) -> Site:
    """Pre-seeded Site entity linked to test_project."""
    site = Site(
        project_id=test_project.id,
        name="Vadodara Metro Pier Site 4",
        location_lat=22.3072,
        location_lng=73.1812,
        geofence_radius_m=500,
        status=SiteStatus.ACTIVE,
    )
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)
    return site


@pytest.fixture
async def test_worker(db_session: AsyncSession, test_site: Site) -> Worker:
    """Pre-seeded Worker entity assigned to test_site."""
    worker = Worker(
        name="Ramesh Kumar",
        phone="+919123456780",
        category=WorkerCategory.OPERATOR,
        assigned_site_id=test_site.id,
        is_active=True,
    )
    db_session.add(worker)
    await db_session.commit()
    await db_session.refresh(worker)
    return worker
