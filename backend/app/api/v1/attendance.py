from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Site
from app.models.equipment import ShiftType
from app.models.attendance import (
    Worker,
    WorkerCategory,
    AttendanceRecord,
    AttendanceStatus,
    GangAttendanceRecord,
    GangTrade,
)
from app.schemas.attendance import (
    WorkerCreate,
    WorkerResponse,
    CheckInRequest,
    CheckOutRequest,
    GangMusterCreate,
    GangMusterResponse,
    WorkerAttendanceResponse,
    AttendanceVerifyRequest,
    AnomalyAlertResponse,
)

router = APIRouter()


def calculate_haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


# ==============================================================================
# 1. Direct Worker Check-In & Check-Out
# ==============================================================================

@router.post(
    "/check-in",
    response_model=WorkerAttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/attendance/check-in",
    response_model=WorkerAttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def check_in_worker(
    check_in: CheckInRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Direct worker check-in with GPS validation.
    Enforces:
    - UniqueConstraint 'uix_worker_date_shift_att': rejects duplicate check-in with HTTP 400.
    - Geofence calculation against Site.location_lat/lng: flags anomaly if outside geofence radius.
    """
    # 1. Verify Site exists
    site = await db.get(Site, check_in.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {check_in.site_id} not found.",
        )

    # 2. Verify Worker exists
    worker = await db.get(Worker, check_in.worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with id {check_in.worker_id} not found.",
        )

    # 3. Enforce UniqueConstraint 'uix_worker_date_shift_att' at application boundary
    dup_stmt = select(AttendanceRecord).where(
        AttendanceRecord.worker_id == check_in.worker_id,
        AttendanceRecord.date == check_in.date,
        AttendanceRecord.shift == check_in.shift,
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Worker {check_in.worker_id} is already checked in for date {check_in.date} and shift {check_in.shift.value}.",
        )

    # 4. Geofence evaluation
    within_geofence = True
    anomaly_flag = False
    anomaly_reason = None

    if (
        check_in.check_in_lat is not None
        and check_in.check_in_lng is not None
        and site.location_lat is not None
        and site.location_lng is not None
    ):
        dist = calculate_haversine_distance_m(
            check_in.check_in_lat,
            check_in.check_in_lng,
            site.location_lat,
            site.location_lng,
        )
        radius = site.geofence_radius_m or 500
        if dist > radius:
            within_geofence = False
            anomaly_flag = True
            anomaly_reason = f"Check-in location is {int(dist)}m from site center (geofence radius: {radius}m)"

    # 5. Create Attendance Record
    now_ts = datetime.now(timezone.utc)
    record = AttendanceRecord(
        site_id=check_in.site_id,
        worker_id=check_in.worker_id,
        date=check_in.date,
        shift=check_in.shift,
        check_in_time=now_ts,
        check_in_lat=check_in.check_in_lat,
        check_in_lng=check_in.check_in_lng,
        within_geofence=within_geofence,
        hours_worked=None,
        overtime_hours=0.0,
        status=AttendanceStatus.PRESENT,
        anomaly_flag=anomaly_flag,
        anomaly_reason=anomaly_reason,
    )
    db.add(record)

    try:
        await db.commit()
        await db.refresh(record)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate check-in violates unique constraint: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
        )

    return WorkerAttendanceResponse.model_validate(record)


@router.post(
    "/check-out",
    response_model=WorkerAttendanceResponse,
)
@router.post(
    "/attendance/check-out",
    response_model=WorkerAttendanceResponse,
    include_in_schema=False,
)
async def check_out_worker(
    check_out: CheckOutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record worker check-out time and compute hours worked.
    Flags anomaly if shift duration exceeds 14 hours.
    """
    record = None
    if check_out.record_id is not None:
        record = await db.get(AttendanceRecord, check_out.record_id)
    elif check_out.worker_id is not None:
        stmt = (
            select(AttendanceRecord)
            .where(
                AttendanceRecord.worker_id == check_out.worker_id,
                AttendanceRecord.check_out_time.is_(None),
            )
            .order_by(AttendanceRecord.check_in_time.desc())
        )
        record = (await db.execute(stmt)).scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active attendance record not found for check-out.",
        )

    now_ts = datetime.now(timezone.utc)
    record.check_out_time = now_ts
    record.check_out_lat = check_out.check_out_lat
    record.check_out_lng = check_out.check_out_lng

    # Compute shift duration (normalize timezones for sqlite compat)
    check_in_dt = record.check_in_time
    if check_in_dt.tzinfo is not None:
        calc_now = now_ts
    else:
        calc_now = now_ts.replace(tzinfo=None)
    delta_seconds = (calc_now - check_in_dt).total_seconds()
    hours_worked = round(max(0.0, delta_seconds / 3600.0), 2)
    record.hours_worked = hours_worked

    # Compute OT hours (> 8 hours standard shift)
    if hours_worked > 8.0:
        record.overtime_hours = round(hours_worked - 8.0, 2)

    # Anomaly detection: shift > 14 hours
    if hours_worked > 14.0:
        record.anomaly_flag = True
        reasons = [record.anomaly_reason] if record.anomaly_reason else []
        reasons.append(f"Excessive shift duration: {hours_worked} hours (> 14h limit)")
        record.anomaly_reason = "; ".join(reasons)

    await db.commit()
    await db.refresh(record)

    return WorkerAttendanceResponse.model_validate(record)


# ==============================================================================
# 2. Subcontractor Gang Muster
# ==============================================================================

@router.post(
    "/gang-muster",
    response_model=GangMusterResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/attendance/gang-muster",
    response_model=GangMusterResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/gang",
    response_model=GangMusterResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/attendance/gang",
    response_model=GangMusterResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_gang_muster(
    gang_in: GangMusterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record subcontractor gang muster headcount and trade.
    Enforces UniqueConstraint 'uix_site_date_shift_gang': rejects duplicates with HTTP 400.
    """
    # 1. Verify site exists
    site = await db.get(Site, gang_in.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {gang_in.site_id} not found.",
        )

    # 2. Enforce UniqueConstraint 'uix_site_date_shift_gang' at application level
    dup_stmt = select(GangAttendanceRecord).where(
        GangAttendanceRecord.site_id == gang_in.site_id,
        GangAttendanceRecord.date == gang_in.date,
        GangAttendanceRecord.shift == gang_in.shift,
        GangAttendanceRecord.subcontractor_name == gang_in.subcontractor_name,
        GangAttendanceRecord.trade == gang_in.trade,
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Gang muster already recorded for site {gang_in.site_id}, date {gang_in.date}, "
                f"shift {gang_in.shift.value}, subcontractor '{gang_in.subcontractor_name}', trade {gang_in.trade.value}."
            ),
        )

    # 3. Create GangAttendanceRecord
    gang_record = GangAttendanceRecord(
        site_id=gang_in.site_id,
        date=gang_in.date,
        shift=gang_in.shift,
        subcontractor_name=gang_in.subcontractor_name,
        trade=gang_in.trade,
        headcount_present=gang_in.headcount_present,
        total_ot_hours=gang_in.total_ot_hours,
        muster_roll_photo_url=gang_in.muster_roll_photo_url,
        verified_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(gang_record)

    try:
        await db.commit()
        await db.refresh(gang_record)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate gang muster violates unique constraint: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
        )

    return GangMusterResponse.model_validate(gang_record)


# ==============================================================================
# 3. Site Attendance Listing & Anomalies
# ==============================================================================

@router.get(
    "/site/{site_id}",
)
@router.get(
    "/attendance/site/{site_id}",
    include_in_schema=False,
)
async def get_site_attendance(
    site_id: int,
    date_filter: Optional[date] = Query(None, alias="date", description="Filter by date"),
    shift: Optional[ShiftType] = Query(None, description="Filter by shift"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List both worker check-ins and subcontractor gang muster entries for a site."""
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {site_id} not found.",
        )

    # Query worker attendance
    att_stmt = select(AttendanceRecord).where(AttendanceRecord.site_id == site_id)
    if date_filter is not None:
        att_stmt = att_stmt.where(AttendanceRecord.date == date_filter)
    if shift is not None:
        att_stmt = att_stmt.where(AttendanceRecord.shift == shift)
    att_res = await db.execute(att_stmt)
    workers = att_res.scalars().all()

    # Query gang muster records
    gang_stmt = select(GangAttendanceRecord).where(GangAttendanceRecord.site_id == site_id)
    if date_filter is not None:
        gang_stmt = gang_stmt.where(GangAttendanceRecord.date == date_filter)
    if shift is not None:
        gang_stmt = gang_stmt.where(GangAttendanceRecord.shift == shift)
    gang_res = await db.execute(gang_stmt)
    gangs = gang_res.scalars().all()

    return {
        "site_id": site_id,
        "date": date_filter,
        "shift": shift,
        "worker_count": len(workers),
        "total_gang_headcount": sum(g.headcount_present for g in gangs),
        "workers": [WorkerAttendanceResponse.model_validate(w) for w in workers],
        "gangs": [GangMusterResponse.model_validate(g) for g in gangs],
    }


@router.get(
    "/anomalies",
    response_model=List[AnomalyAlertResponse],
)
@router.get(
    "/attendance/anomalies",
    response_model=List[AnomalyAlertResponse],
    include_in_schema=False,
)
async def get_attendance_anomalies(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    date_filter: Optional[date] = Query(None, alias="date", description="Filter by date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List attendance anomalies (geofence breaches, excessive hours > 14h, ghost worker flags).
    """
    conditions = [
        (AttendanceRecord.anomaly_flag == True)
        | (AttendanceRecord.within_geofence == False)
        | (AttendanceRecord.hours_worked > 14.0)
    ]
    if site_id is not None:
        conditions.append(AttendanceRecord.site_id == site_id)
    if date_filter is not None:
        conditions.append(AttendanceRecord.date == date_filter)

    stmt = (
        select(AttendanceRecord)
        .where(and_(*conditions))
        .order_by(AttendanceRecord.date.desc(), AttendanceRecord.id.desc())
    )
    result = await db.execute(stmt)
    anomalous_records = result.scalars().all()

    alerts: List[AnomalyAlertResponse] = []
    for rec in anomalous_records:
        anomaly_type = "GEOFENCE_BREACH" if not rec.within_geofence else "EXCESSIVE_HOURS"
        severity = "CRITICAL" if (rec.hours_worked and rec.hours_worked > 14.0) else "WARNING"
        desc = rec.anomaly_reason or f"Attendance anomaly detected on worker {rec.worker_id}."

        alerts.append(
            AnomalyAlertResponse(
                id=rec.id,
                anomaly_type=anomaly_type,
                site_id=rec.site_id,
                date=rec.date,
                shift=rec.shift,
                worker_id=rec.worker_id,
                subcontractor_name=None,
                description=desc,
                severity=severity,
                detected_at=rec.check_in_time,
            )
        )

    return alerts


# ==============================================================================
# 4. Worker Master Management
# ==============================================================================

@router.get(
    "/workers",
    response_model=List[WorkerResponse],
)
@router.get(
    "/attendance/workers",
    response_model=List[WorkerResponse],
    include_in_schema=False,
)
async def list_workers(
    site_id: Optional[int] = Query(None, description="Filter by assigned site ID"),
    category: Optional[WorkerCategory] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List registered field laborers."""
    stmt = select(Worker).where(Worker.is_active == True)
    if site_id is not None:
        stmt = stmt.where(Worker.assigned_site_id == site_id)
    if category is not None:
        stmt = stmt.where(Worker.category == category)

    stmt = stmt.order_by(Worker.name.asc())
    result = await db.execute(stmt)
    workers = result.scalars().all()
    return [WorkerResponse.model_validate(w) for w in workers]


@router.post(
    "/workers",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/attendance/workers",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def register_worker(
    worker_in: WorkerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new field laborer."""
    site = await db.get(Site, worker_in.assigned_site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {worker_in.assigned_site_id} not found.",
        )

    worker = Worker(
        name=worker_in.name,
        phone=worker_in.phone,
        category=worker_in.category,
        assigned_site_id=worker_in.assigned_site_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)

    return WorkerResponse.model_validate(worker)
