import pytest
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus
from datetime import date


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_db_rollback_on_unhandled_exception(test_engine):
    """Verify that get_db rolls back uncommitted changes when an exception is raised."""
    # We will use get_db generator directly to emulate FastAPI dependency execution
    gen = get_db()
    session: AsyncSession = await gen.asend(None)

    unique_phone = "+919999000001"
    staged_user = User(
        name="Staged User In Transaction",
        phone=unique_phone,
        email="staged.user@test.com",
        role=UserRole.SITE_ENGINEER,
        is_active=True,
    )
    session.add(staged_user)
    await session.flush()  # Staged in DB transaction, but not committed

    # Simulate an unhandled exception thrown back into the generator by FastAPI
    with pytest.raises(RuntimeError, match="Simulated endpoint failure"):
        await gen.athrow(RuntimeError("Simulated endpoint failure"))

    # Verify with a brand new, isolated session that staged_user was rolled back
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession)
    async with session_factory() as verify_session:
        stmt = select(User).where(User.phone == unique_phone)
        result = await verify_session.execute(stmt)
        found = result.scalar_one_or_none()
        assert found is None, "Staged user was unexpectedly committed; rollback failed!"


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_db_explicit_commit_persists(test_engine):
    """Verify that get_db successfully persists data when the endpoint calls commit."""
    gen = get_db()
    session: AsyncSession = await gen.asend(None)

    unique_code = "PROJ-PERSIST-01"
    project = Project(
        name="Committed Project",
        code=unique_code,
        client_name="Test Client",
        location="Mumbai",
        contract_value=500000.0,
        start_date=date(2026, 9, 21),
        status=ProjectStatus.ACTIVE,
    )
    session.add(project)
    await session.commit()

    # Generator terminates normally
    with pytest.raises(StopAsyncIteration):
        await gen.asend(None)

    # Verify persistence in a separate session
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession)
    async with session_factory() as verify_session:
        stmt = select(Project).where(Project.code == unique_code)
        result = await verify_session.execute(stmt)
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.code == unique_code


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_db_session_closed_after_normal_exit():
    """Verify that get_db closes the session when iteration finishes normally."""
    gen = get_db()
    session: AsyncSession = await gen.asend(None)
    assert session.is_active is True

    # Complete the generator
    with pytest.raises(StopAsyncIteration):
        await gen.asend(None)

    # The session should now be closed / inactive
    assert not session.is_active


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_db_session_closed_after_exception():
    """Verify that get_db closes the session even after an exception is caught and re-raised."""
    gen = get_db()
    session: AsyncSession = await gen.asend(None)
    assert session.is_active is True

    with pytest.raises(ValueError, match="Boom"):
        await gen.athrow(ValueError("Boom"))

    assert not session.is_active
