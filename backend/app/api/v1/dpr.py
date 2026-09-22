from datetime import datetime, date, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Site, Pile
from app.models.equipment import ShiftType
from app.models.dpr import (
    DailyProgressReport,
    PileDailyProgress,
    WellLog,
    EquipmentLog,
    LabourSummary,
    MaterialConsumption,
    TestReport,
    DPRStatus,
    StrataType,
    CasingType,
)
from app.schemas.dpr import (
    DPRCreate,
    DPRResponse,
    DPRVerifyRequest,
    PilingProgressCreate,
    PilingProgressResponse,
    WellLogResponse,
    EquipmentShiftResponse,
    ManpowerEntryResponse,
    MaterialConsumptionResponse,
    TestReportResponse,
)
from app.services.anomaly_service import AnomalyDetector

router = APIRouter()


class PileProgressLogRequest(BaseModel):
    dpr_id: Optional[int] = None
    pile_id: int
    depth_drilled_today_m: float = Field(default=0.0, ge=0.0)
    cumulative_depth_m: Optional[float] = 0.0
    diameter_mm: Optional[float] = None
    empty_bore_depth_m: Optional[float] = 0.0
    rock_socket_depth_today_m: Optional[float] = 0.0
    strata_type: Optional[StrataType] = StrataType.SOIL
    casing_depth_m: Optional[float] = 0.0
    casing_type: Optional[CasingType] = CasingType.TEMPORARY
    cage_sections_lowered: Optional[int] = 0
    cage_weight_kg_today: Optional[float] = 0.0
    concrete_volume_planned_m3: Optional[float] = 0.0
    concrete_volume_actual_m3: Optional[float] = 0.0
    slump_mm: Optional[float] = None
    bentonite_density_g_cc: Optional[float] = None
    boring_start_time: Optional[datetime] = None
    boring_end_time: Optional[datetime] = None
    delay_reason: Optional[str] = None
    remarks: Optional[str] = None
    photos: Optional[List[str]] = None


async def _build_dpr_response(db: AsyncSession, dpr: DailyProgressReport) -> DPRResponse:
    pile_res = await db.execute(
        select(PileDailyProgress).where(PileDailyProgress.dpr_id == dpr.id)
    )
    piles = [PilingProgressResponse.model_validate(p) for p in pile_res.scalars().all()]

    well_res = await db.execute(
        select(WellLog).where(WellLog.dpr_id == dpr.id)
    )
    wells = [WellLogResponse.model_validate(w) for w in well_res.scalars().all()]

    eq_res = await db.execute(
        select(EquipmentLog).where(EquipmentLog.dpr_id == dpr.id)
    )
    equipment = [EquipmentShiftResponse.model_validate(e) for e in eq_res.scalars().all()]

    labour_res = await db.execute(
        select(LabourSummary).where(LabourSummary.dpr_id == dpr.id)
    )
    labour = [ManpowerEntryResponse.model_validate(l) for l in labour_res.scalars().all()]

    mat_res = await db.execute(
        select(MaterialConsumption).where(MaterialConsumption.dpr_id == dpr.id)
    )
    materials = [MaterialConsumptionResponse.model_validate(m) for m in mat_res.scalars().all()]

    test_res = await db.execute(
        select(TestReport).where(TestReport.dpr_id == dpr.id)
    )
    tests = [TestReportResponse.model_validate(t) for t in test_res.scalars().all()]

    return DPRResponse(
        id=dpr.id,
        site_id=dpr.site_id,
        operational_date=dpr.operational_date,
        shift=dpr.shift,
        submitted_by=dpr.submitted_by,
        submitted_at=dpr.submitted_at,
        status=dpr.status,
        weather_conditions=dpr.weather_conditions,
        problems_delays=dpr.problems_delays,
        tomorrows_plan=dpr.tomorrows_plan,
        verified_by=dpr.verified_by,
        verified_at=dpr.verified_at,
        created_at=dpr.created_at or datetime.now(timezone.utc),
        pile_progress=piles,
        well_logs=wells,
        equipment_logs=equipment,
        labour_summaries=labour,
        material_consumptions=materials,
        test_reports=tests,
    )


@router.post("", response_model=DPRResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DPRResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_dpr(
    dpr_in: DPRCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a Daily Progress Report (DPR) with nested linked entries
    (piling progress, well logs, equipment shifts, delays, manpower, tests).
    Enforces uniqueness per (site_id, operational_date, shift).
    """
    # 1. Enforce unique constraint check (uix_site_date_shift_dpr)
    dup_stmt = select(DailyProgressReport).where(
        DailyProgressReport.site_id == dpr_in.site_id,
        DailyProgressReport.operational_date == dpr_in.operational_date,
        DailyProgressReport.shift == dpr_in.shift,
    )
    existing_dpr = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing_dpr is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DPR already exists for site_id {dpr_in.site_id}, date {dpr_in.operational_date}, and shift {dpr_in.shift.value}.",
        )

    # 2. Check site exists
    site = await db.get(Site, dpr_in.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {dpr_in.site_id} not found.",
        )

    # 3. Create DailyProgressReport header
    now_utc = datetime.now(timezone.utc)
    dpr = DailyProgressReport(
        site_id=dpr_in.site_id,
        operational_date=dpr_in.operational_date,
        shift=dpr_in.shift,
        submitted_by=current_user.id,
        submitted_at=now_utc,
        status=DPRStatus.SUBMITTED,
        weather_conditions=dpr_in.weather_conditions or "",
        problems_delays=dpr_in.problems_delays or "",
        tomorrows_plan=dpr_in.tomorrows_plan or "",
        created_at=now_utc,
    )
    db.add(dpr)
    await db.flush()

    # 4. Handle nested pile progress with diameter check
    if dpr_in.pile_progress:
        for p_item in dpr_in.pile_progress:
            pile = await db.get(Pile, p_item.pile_id)
            if pile is not None and pile.diameter_mm is not None:
                try:
                    AnomalyDetector.detect_concrete_overbreak(
                        diameter_mm=pile.diameter_mm,
                        drilled_depth_m=p_item.depth_drilled_today_m,
                        actual_volume_m3=p_item.concrete_volume_actual_m3,
                    )
                except ValueError as e:
                    await db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e),
                    )

            p_record = PileDailyProgress(
                dpr_id=dpr.id,
                pile_id=p_item.pile_id,
                depth_drilled_today_m=p_item.depth_drilled_today_m,
                cumulative_depth_m=p_item.cumulative_depth_m,
                empty_bore_depth_m=p_item.empty_bore_depth_m,
                rock_socket_depth_today_m=p_item.rock_socket_depth_today_m,
                strata_type=p_item.strata_type,
                casing_depth_m=p_item.casing_depth_m,
                casing_type=p_item.casing_type,
                cage_sections_lowered=p_item.cage_sections_lowered,
                cage_weight_kg_today=p_item.cage_weight_kg_today,
                concrete_volume_planned_m3=p_item.concrete_volume_planned_m3,
                concrete_volume_actual_m3=p_item.concrete_volume_actual_m3,
                slump_mm=p_item.slump_mm,
                bentonite_density_g_cc=p_item.bentonite_density_g_cc,
                boring_start_time=p_item.boring_start_time,
                boring_end_time=p_item.boring_end_time,
                delay_reason=p_item.delay_reason,
                remarks=p_item.remarks,
                photos=p_item.photos,
            )
            db.add(p_record)

    # 5. Handle nested well logs
    if dpr_in.well_logs:
        for w_item in dpr_in.well_logs:
            w_record = WellLog(
                dpr_id=dpr.id,
                well_number=w_item.well_number,
                steining_lift_number=w_item.steining_lift_number,
                sinking_depth_today_cm=w_item.sinking_depth_today_cm,
                cumulative_sinking_depth_m=w_item.cumulative_sinking_depth_m,
                tilt_longitudinal_mm=w_item.tilt_longitudinal_mm,
                tilt_transverse_mm=w_item.tilt_transverse_mm,
                shift_mm=w_item.shift_mm,
                soil_type_at_cutting_edge=w_item.soil_type_at_cutting_edge,
                water_level_m=w_item.water_level_m,
                remarks=w_item.remarks or "",
                photos=w_item.photos,
            )
            db.add(w_record)

    # 6. Handle nested equipment shifts / logs
    eq_list = dpr_in.equipment_logs or dpr_in.equipment_shifts or []
    for eq_item in eq_list:
        eq_record = EquipmentLog(
            dpr_id=dpr.id,
            equipment_id=eq_item.equipment_id,
            opening_hours=eq_item.opening_hours,
            closing_hours=eq_item.closing_hours,
            working_hours=eq_item.working_hours,
            breakdown_hours=eq_item.breakdown_hours,
            idle_hours=eq_item.idle_hours,
            fuel_liters=eq_item.fuel_liters,
            breakdown_reason=eq_item.breakdown_reason,
        )
        db.add(eq_record)

    # 7. Handle nested labour / manpower summaries
    labour_list = dpr_in.labour_summaries or dpr_in.manpower_entries or []
    for l_item in labour_list:
        l_record = LabourSummary(
            dpr_id=dpr.id,
            category=l_item.category,
            count=l_item.count,
            shift=l_item.shift,
            hours_worked=l_item.hours_worked,
        )
        db.add(l_record)

    # 8. Handle material consumptions
    if dpr_in.material_consumptions:
        for m_item in dpr_in.material_consumptions:
            m_record = MaterialConsumption(
                dpr_id=dpr.id,
                material_name=m_item.material_name,
                unit=m_item.unit,
                quantity_used=m_item.quantity_used,
                remarks=m_item.remarks,
            )
            db.add(m_record)

    # 9. Handle test reports
    if dpr_in.test_reports:
        for t_item in dpr_in.test_reports:
            t_record = TestReport(
                dpr_id=dpr.id,
                pile_progress_id=t_item.pile_progress_id,
                test_type=t_item.test_type,
                result_value=t_item.result_value,
                result_unit=t_item.result_unit,
                pass_fail=t_item.pass_fail,
                photo_url=t_item.photo_url,
                remarks=t_item.remarks or "",
            )
            db.add(t_record)

    # 10. Commit transaction
    try:
        await db.commit()
        await db.refresh(dpr)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error creating DPR: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
        )

    return await _build_dpr_response(db, dpr)


@router.get("", response_model=List[DPRResponse])
@router.get("/", response_model=List[DPRResponse], include_in_schema=False)
async def list_dprs(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    start_date: Optional[date] = Query(None, description="Filter from start date"),
    end_date: Optional[date] = Query(None, description="Filter until end date"),
    status_filter: Optional[DPRStatus] = Query(None, alias="status", description="Filter by DPR status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List DPRs with optional filters for site_id, start_date, end_date, and status.
    """
    stmt = select(DailyProgressReport).order_by(DailyProgressReport.operational_date.desc(), DailyProgressReport.id.desc())

    conditions = []
    if site_id is not None:
        conditions.append(DailyProgressReport.site_id == site_id)
    if start_date is not None:
        conditions.append(DailyProgressReport.operational_date >= start_date)
    if end_date is not None:
        conditions.append(DailyProgressReport.operational_date <= end_date)
    if status_filter is not None:
        conditions.append(DailyProgressReport.status == status_filter)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    dprs = result.scalars().all()

    return [await _build_dpr_response(db, d) for d in dprs]


@router.post("/pile-progress", response_model=PilingProgressResponse, status_code=status.HTTP_201_CREATED)
async def log_pile_progress(
    progress_in: PileProgressLogRequest,
    dpr_id: Optional[int] = Query(None, description="Optional DPR ID in query param"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log or update piling progress for a pile within a DPR.
    Enforces concrete overbreak anomaly check using AnomalyDetector.detect_concrete_overbreak,
    strictly requiring diameter_mm >= 400 (Vulnerability 3 prevention).
    """
    target_dpr_id = progress_in.dpr_id or dpr_id
    if target_dpr_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dpr_id must be provided in request body or query parameter.",
        )

    # 1. Determine diameter to validate
    pile = await db.get(Pile, progress_in.pile_id)
    diameter = progress_in.diameter_mm
    if diameter is None and pile is not None:
        diameter = pile.diameter_mm

    # 2. Enforce Vulnerability 3: pile diameter must be >= 400mm
    if diameter is not None:
        try:
            AnomalyDetector.detect_concrete_overbreak(
                diameter_mm=diameter,
                drilled_depth_m=progress_in.depth_drilled_today_m,
                actual_volume_m3=progress_in.concrete_volume_actual_m3 or 0.0,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

    # 3. Verify DPR and Pile existence
    dpr = await db.get(DailyProgressReport, target_dpr_id)
    if not dpr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DPR with id {target_dpr_id} not found.",
        )

    if not pile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pile with id {progress_in.pile_id} not found.",
        )

    # 4. Upsert PileDailyProgress
    find_stmt = select(PileDailyProgress).where(
        PileDailyProgress.dpr_id == target_dpr_id,
        PileDailyProgress.pile_id == progress_in.pile_id,
    )
    existing_record = (await db.execute(find_stmt)).scalar_one_or_none()

    if existing_record:
        existing_record.depth_drilled_today_m = progress_in.depth_drilled_today_m
        if progress_in.cumulative_depth_m is not None:
            existing_record.cumulative_depth_m = progress_in.cumulative_depth_m
        if progress_in.empty_bore_depth_m is not None:
            existing_record.empty_bore_depth_m = progress_in.empty_bore_depth_m
        if progress_in.rock_socket_depth_today_m is not None:
            existing_record.rock_socket_depth_today_m = progress_in.rock_socket_depth_today_m
        if progress_in.strata_type is not None:
            existing_record.strata_type = progress_in.strata_type
        if progress_in.casing_depth_m is not None:
            existing_record.casing_depth_m = progress_in.casing_depth_m
        if progress_in.casing_type is not None:
            existing_record.casing_type = progress_in.casing_type
        if progress_in.cage_sections_lowered is not None:
            existing_record.cage_sections_lowered = progress_in.cage_sections_lowered
        if progress_in.cage_weight_kg_today is not None:
            existing_record.cage_weight_kg_today = progress_in.cage_weight_kg_today
        if progress_in.concrete_volume_planned_m3 is not None:
            existing_record.concrete_volume_planned_m3 = progress_in.concrete_volume_planned_m3
        if progress_in.concrete_volume_actual_m3 is not None:
            existing_record.concrete_volume_actual_m3 = progress_in.concrete_volume_actual_m3
        if progress_in.slump_mm is not None:
            existing_record.slump_mm = progress_in.slump_mm
        if progress_in.bentonite_density_g_cc is not None:
            existing_record.bentonite_density_g_cc = progress_in.bentonite_density_g_cc
        if progress_in.boring_start_time is not None:
            existing_record.boring_start_time = progress_in.boring_start_time
        if progress_in.boring_end_time is not None:
            existing_record.boring_end_time = progress_in.boring_end_time
        if progress_in.delay_reason is not None:
            existing_record.delay_reason = progress_in.delay_reason
        if progress_in.remarks is not None:
            existing_record.remarks = progress_in.remarks
        if progress_in.photos is not None:
            existing_record.photos = progress_in.photos
        record = existing_record
    else:
        record = PileDailyProgress(
            dpr_id=target_dpr_id,
            pile_id=progress_in.pile_id,
            depth_drilled_today_m=progress_in.depth_drilled_today_m,
            cumulative_depth_m=progress_in.cumulative_depth_m or 0.0,
            empty_bore_depth_m=progress_in.empty_bore_depth_m or 0.0,
            rock_socket_depth_today_m=progress_in.rock_socket_depth_today_m or 0.0,
            strata_type=progress_in.strata_type or StrataType.SOIL,
            casing_depth_m=progress_in.casing_depth_m or 0.0,
            casing_type=progress_in.casing_type or CasingType.TEMPORARY,
            cage_sections_lowered=progress_in.cage_sections_lowered or 0,
            cage_weight_kg_today=progress_in.cage_weight_kg_today or 0.0,
            concrete_volume_planned_m3=progress_in.concrete_volume_planned_m3 or 0.0,
            concrete_volume_actual_m3=progress_in.concrete_volume_actual_m3 or 0.0,
            slump_mm=progress_in.slump_mm,
            bentonite_density_g_cc=progress_in.bentonite_density_g_cc,
            boring_start_time=progress_in.boring_start_time,
            boring_end_time=progress_in.boring_end_time,
            delay_reason=progress_in.delay_reason,
            remarks=progress_in.remarks,
            photos=progress_in.photos,
        )
        db.add(record)

    try:
        await db.commit()
        await db.refresh(record)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
        )

    return PilingProgressResponse.model_validate(record)


@router.get("/{id}", response_model=DPRResponse)
async def get_dpr(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Detailed view of a single DPR by ID with all nested children.
    """
    dpr = await db.get(DailyProgressReport, id)
    if not dpr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DPR with id {id} not found.",
        )
    return await _build_dpr_response(db, dpr)


@router.post("/{id}/verify", response_model=DPRResponse)
async def verify_dpr(
    id: int,
    verify_req: Optional[DPRVerifyRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verify DPR: updates verification status, verified_by, and verified_at timestamp.
    """
    dpr = await db.get(DailyProgressReport, id)
    if not dpr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DPR with id {id} not found.",
        )

    dpr.status = verify_req.status if verify_req else DPRStatus.VERIFIED
    dpr.verified_by = current_user.id
    dpr.verified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(dpr)
    return await _build_dpr_response(db, dpr)
