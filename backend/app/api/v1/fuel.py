from datetime import datetime, date, timezone
dt_date = date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, ConfigDict

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Site
from app.models.equipment import SiteFuelRegister, ShiftType
from app.schemas.fuel import (
    FuelIssuanceEntry,
    FuelRegisterResponse,
)
from app.services.anomaly_service import AnomalyDetector

router = APIRouter()


class ShiftFuelRegisterInput(BaseModel):
    site_id: int
    date: dt_date
    shift: ShiftType
    opening_stock_liters: float = Field(default=0.0)
    received_bowser_liters: float = Field(default=0.0)
    received_drums_liters: float = Field(default=0.0)
    total_issued_to_equipment_liters: float = Field(default=0.0)
    closing_dip_stock_liters: float
    dpr_id: Optional[int] = None
    issuances: Optional[List[FuelIssuanceEntry]] = None


class CurrentStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    site_id: int
    current_stock_liters: float
    closing_dip_stock_liters: float
    date: Optional[dt_date] = None
    shift: Optional[ShiftType] = None


@router.post(
    "/fuel-register",
    response_model=FuelRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "",
    response_model=FuelRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/",
    response_model=FuelRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_fuel_register(
    fuel_in: ShiftFuelRegisterInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a shift fuel register record.
    Enforces CheckConstraint 'check_positive_dip' and AnomalyDetector (rejects closing_dip_stock_liters < 0).
    Enforces CheckConstraint 'check_valid_issuance' and AnomalyDetector (rejects total_issued > opening + received).
    Enforces UniqueConstraint 'uix_site_date_shift_fuel'.
    Gracefully handles IntegrityError and ValueError, returning HTTP 400.
    """
    # 1. Enforce domain anomaly guards (Vulnerability 1 & 2)
    try:
        AnomalyDetector.detect_fuel_anomaly(
            opening=fuel_in.opening_stock_liters,
            received=fuel_in.received_bowser_liters + fuel_in.received_drums_liters,
            issued=fuel_in.total_issued_to_equipment_liters,
            closing_dip=fuel_in.closing_dip_stock_liters,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # 2. Check site exists
    site = await db.get(Site, fuel_in.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {fuel_in.site_id} not found.",
        )

    # 3. Check uniqueness constraint (uix_site_date_shift_fuel)
    dup_stmt = select(SiteFuelRegister).where(
        SiteFuelRegister.site_id == fuel_in.site_id,
        SiteFuelRegister.date == fuel_in.date,
        SiteFuelRegister.shift == fuel_in.shift,
    )
    existing_entry = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing_entry is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel register entry already exists for site_id {fuel_in.site_id}, date {fuel_in.date}, and shift {fuel_in.shift.value}.",
        )

    # 4. Calculate variance
    total_input = fuel_in.opening_stock_liters + fuel_in.received_bowser_liters + fuel_in.received_drums_liters
    expected_closing = total_input - fuel_in.total_issued_to_equipment_liters
    variance_liters = round(fuel_in.closing_dip_stock_liters - expected_closing, 2)

    # 5. Create database record
    register = SiteFuelRegister(
        site_id=fuel_in.site_id,
        dpr_id=fuel_in.dpr_id,
        date=fuel_in.date,
        shift=fuel_in.shift,
        opening_stock_liters=fuel_in.opening_stock_liters,
        received_bowser_liters=fuel_in.received_bowser_liters,
        received_drums_liters=fuel_in.received_drums_liters,
        total_issued_to_equipment_liters=fuel_in.total_issued_to_equipment_liters,
        closing_dip_stock_liters=fuel_in.closing_dip_stock_liters,
        variance_liters=variance_liters,
        recorded_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(register)

    # 6. Commit transaction and catch IntegrityErrors
    try:
        await db.commit()
        await db.refresh(register)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
        )

    return FuelRegisterResponse.model_validate(register)


@router.get(
    "/fuel-register/current-stock/{site_id}",
    response_model=CurrentStockResponse,
)
@router.get(
    "/current-stock/{site_id}",
    response_model=CurrentStockResponse,
    include_in_schema=False,
)
async def get_current_stock(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the latest closing dip stock for a given site.
    """
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {site_id} not found.",
        )

    stmt = (
        select(SiteFuelRegister)
        .where(SiteFuelRegister.site_id == site_id)
        .order_by(
            SiteFuelRegister.date.desc(),
            SiteFuelRegister.created_at.desc(),
            SiteFuelRegister.id.desc(),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    latest_reg = result.scalar_one_or_none()

    if not latest_reg:
        return CurrentStockResponse(
            site_id=site_id,
            current_stock_liters=0.0,
            closing_dip_stock_liters=0.0,
            date=None,
            shift=None,
        )

    return CurrentStockResponse(
        site_id=site_id,
        current_stock_liters=latest_reg.closing_dip_stock_liters,
        closing_dip_stock_liters=latest_reg.closing_dip_stock_liters,
        date=latest_reg.date,
        shift=latest_reg.shift,
    )


@router.get(
    "/fuel-register",
    response_model=List[FuelRegisterResponse],
)
@router.get(
    "",
    response_model=List[FuelRegisterResponse],
    include_in_schema=False,
)
@router.get(
    "/",
    response_model=List[FuelRegisterResponse],
    include_in_schema=False,
)
async def list_fuel_registers(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    date_filter: Optional[date] = Query(None, alias="date", description="Filter by date"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List fuel registers filtered by site_id and date.
    """
    stmt = select(SiteFuelRegister).order_by(SiteFuelRegister.date.desc(), SiteFuelRegister.id.desc())

    conditions = []
    if site_id is not None:
        conditions.append(SiteFuelRegister.site_id == site_id)
    if date_filter is not None:
        conditions.append(SiteFuelRegister.date == date_filter)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    registers = result.scalars().all()

    return [FuelRegisterResponse.model_validate(r) for r in registers]


@router.get(
    "/fuel-register/{id}",
    response_model=FuelRegisterResponse,
)
@router.get(
    "/{id}",
    response_model=FuelRegisterResponse,
    include_in_schema=False,
)
async def get_fuel_register(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single fuel register by ID.
    """
    register = await db.get(SiteFuelRegister, id)
    if not register:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fuel register with id {id} not found.",
        )
    return FuelRegisterResponse.model_validate(register)
