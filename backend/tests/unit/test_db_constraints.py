import pytest
from datetime import date, datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import (
    SiteFuelRegister as ShiftFuelRegister,
    SiteFuelRegister,
    SiteInventory,
    Equipment,
    EquipmentType,
    ShiftType,
)
from app.models.dpr import (
    DailyProgressReport,
    PileDailyProgress,
    WellLog,
    EquipmentLog,
    DPRStatus,
    StrataType,
    CasingType,
)
from app.models.attendance import (
    AttendanceRecord as WorkerAttendance,
    AttendanceRecord,
    GangAttendanceRecord,
    GangTrade,
    AttendanceStatus,
    Worker,
)
from app.models.project import Site, Project, Pile, PileStatus, ProjectStatus
from app.models.user import User, UserRole


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_positive_dip_constraint_valid(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify that valid closing dip values (0.0 and positive values) satisfy check_positive_dip."""
    # Zero dip boundary
    register_zero = ShiftFuelRegister(
        site_id=test_site.id,
        date=date(2026, 9, 21),
        shift=ShiftType.DAY,
        opening_stock_liters=500.0,
        received_bowser_liters=0.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=500.0,
        closing_dip_stock_liters=0.0,
        variance_liters=0.0,
        recorded_by=test_user.id,
    )
    db_session.add(register_zero)
    await db_session.commit()
    assert register_zero.id is not None
    assert register_zero.closing_dip_stock_liters == 0.0

    # Positive dip value
    register_pos = ShiftFuelRegister(
        site_id=test_site.id,
        date=date(2026, 9, 22),
        shift=ShiftType.DAY,
        opening_stock_liters=1000.0,
        received_bowser_liters=500.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=400.0,
        closing_dip_stock_liters=1100.0,
        variance_liters=0.0,
        recorded_by=test_user.id,
    )
    db_session.add(register_pos)
    await db_session.commit()
    assert register_pos.id is not None
    assert register_pos.closing_dip_stock_liters == 1100.0


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_positive_dip_constraint_violating(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify that negative closing dip violates check_positive_dip CheckConstraint."""
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            bad_register = ShiftFuelRegister(
                site_id=test_site.id,
                date=date(2026, 9, 21),
                shift=ShiftType.NIGHT,
                opening_stock_liters=1000.0,
                received_bowser_liters=0.0,
                received_drums_liters=0.0,
                total_issued_to_equipment_liters=200.0,
                closing_dip_stock_liters=-10.0,  # Violates closing_dip_stock_liters >= 0
                variance_liters=0.0,
                recorded_by=test_user.id,
            )
            db_session.add(bad_register)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_valid_issuance_constraint_valid(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify that issuance <= total available fuel satisfies check_valid_issuance CheckConstraint."""
    # Exact boundary: total_issued == opening + bowser + drums
    boundary_register = ShiftFuelRegister(
        site_id=test_site.id,
        date=date(2026, 9, 23),
        shift=ShiftType.DAY,
        opening_stock_liters=800.0,
        received_bowser_liters=200.0,
        received_drums_liters=100.0,
        total_issued_to_equipment_liters=1100.0,  # Exact 1100.0
        closing_dip_stock_liters=0.0,
        variance_liters=0.0,
        recorded_by=test_user.id,
    )
    db_session.add(boundary_register)
    await db_session.commit()
    assert boundary_register.id is not None
    assert boundary_register.total_issued_to_equipment_liters == 1100.0


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_valid_issuance_constraint_violating(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify that issuance > total available fuel violates check_valid_issuance CheckConstraint."""
    # Available = 1000 + 500 + 0 = 1500L, Issued = 1501L
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            excess_register = ShiftFuelRegister(
                site_id=test_site.id,
                date=date(2026, 9, 24),
                shift=ShiftType.DAY,
                opening_stock_liters=1000.0,
                received_bowser_liters=500.0,
                received_drums_liters=0.0,
                total_issued_to_equipment_liters=1501.0,  # Violates check_valid_issuance
                closing_dip_stock_liters=0.0,
                variance_liters=0.0,
                recorded_by=test_user.id,
            )
            db_session.add(excess_register)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_ghost_issuance_violating(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify ghost issuance (issuing fuel from an empty tank) violates check_valid_issuance."""
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            ghost_register = ShiftFuelRegister(
                site_id=test_site.id,
                date=date(2026, 9, 25),
                shift=ShiftType.DAY,
                opening_stock_liters=0.0,
                received_bowser_liters=0.0,
                received_drums_liters=0.0,
                total_issued_to_equipment_liters=100.0,  # 100 > 0
                closing_dip_stock_liters=0.0,
                variance_liters=0.0,
                recorded_by=test_user.id,
            )
            db_session.add(ghost_register)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_unique_site_date_shift_constraint(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify uix_site_date_shift_fuel UniqueConstraint prevents duplicate shift logs for same site and date."""
    target_date = date(2026, 9, 26)
    
    first_reg = ShiftFuelRegister(
        site_id=test_site.id,
        date=target_date,
        shift=ShiftType.DAY,
        opening_stock_liters=500.0,
        received_bowser_liters=0.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=100.0,
        closing_dip_stock_liters=400.0,
        variance_liters=0.0,
        recorded_by=test_user.id,
    )
    db_session.add(first_reg)
    await db_session.commit()

    # Night shift on same date and site is valid
    night_reg = ShiftFuelRegister(
        site_id=test_site.id,
        date=target_date,
        shift=ShiftType.NIGHT,
        opening_stock_liters=400.0,
        received_bowser_liters=0.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=50.0,
        closing_dip_stock_liters=350.0,
        variance_liters=0.0,
        recorded_by=test_user.id,
    )
    db_session.add(night_reg)
    await db_session.commit()

    # Duplicate day shift on same date and site must violate uix_site_date_shift_fuel
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_reg = ShiftFuelRegister(
                site_id=test_site.id,
                date=target_date,
                shift=ShiftType.DAY,
                opening_stock_liters=500.0,
                received_bowser_liters=0.0,
                received_drums_liters=0.0,
                total_issued_to_equipment_liters=100.0,
                closing_dip_stock_liters=400.0,
                variance_liters=0.0,
                recorded_by=test_user.id,
            )
            db_session.add(duplicate_reg)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_dpr_unique_site_date_shift_constraint(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify uix_site_date_shift_dpr UniqueConstraint prevents multiple DPRs for same site, date, and shift."""
    target_date = date(2026, 9, 21)

    dpr_day = DailyProgressReport(
        site_id=test_site.id,
        operational_date=target_date,
        shift=ShiftType.DAY,
        submitted_by=test_user.id,
        status=DPRStatus.SUBMITTED,
        weather_conditions="Clear 32C",
        problems_delays="None",
        tomorrows_plan="Continue pile P12-2",
    )
    db_session.add(dpr_day)
    await db_session.commit()
    assert dpr_day.id is not None

    # Different shift (NIGHT) for same site and date succeeds
    dpr_night = DailyProgressReport(
        site_id=test_site.id,
        operational_date=target_date,
        shift=ShiftType.NIGHT,
        submitted_by=test_user.id,
        status=DPRStatus.SUBMITTED,
        weather_conditions="Clear 26C",
        problems_delays="None",
        tomorrows_plan="Cage lowering P12-2",
    )
    db_session.add(dpr_night)
    await db_session.commit()
    assert dpr_night.id is not None

    # Duplicate DAY shift for same site and date must violate uix_site_date_shift_dpr
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_dpr = DailyProgressReport(
                site_id=test_site.id,
                operational_date=target_date,
                shift=ShiftType.DAY,
                submitted_by=test_user.id,
                status=DPRStatus.DRAFT,
                weather_conditions="Duplicate submission attempt",
            )
            db_session.add(duplicate_dpr)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_worker_attendance_unique_worker_date_shift_constraint(
    db_session: AsyncSession, test_site: Site, test_worker: Worker
):
    """Verify uix_worker_date_shift_att UniqueConstraint prevents duplicate attendance for same worker, date, and shift."""
    target_date = date(2026, 9, 21)
    now_utc = datetime.now(timezone.utc)

    att_day = WorkerAttendance(
        site_id=test_site.id,
        worker_id=test_worker.id,
        date=target_date,
        shift=ShiftType.DAY,
        check_in_time=now_utc,
        within_geofence=True,
        status=AttendanceStatus.PRESENT,
    )
    db_session.add(att_day)
    await db_session.commit()
    assert att_day.id is not None

    # Different shift (NIGHT) for same worker and date succeeds
    att_night = WorkerAttendance(
        site_id=test_site.id,
        worker_id=test_worker.id,
        date=target_date,
        shift=ShiftType.NIGHT,
        check_in_time=now_utc,
        within_geofence=True,
        status=AttendanceStatus.PRESENT,
    )
    db_session.add(att_night)
    await db_session.commit()
    assert att_night.id is not None

    # Duplicate DAY shift for same worker and date must violate uix_worker_date_shift_att
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_att = WorkerAttendance(
                site_id=test_site.id,
                worker_id=test_worker.id,
                date=target_date,
                shift=ShiftType.DAY,
                check_in_time=now_utc,
                within_geofence=True,
                status=AttendanceStatus.PRESENT,
            )
            db_session.add(duplicate_att)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_pile_unique_pier_pile_constraint(
    db_session: AsyncSession, test_site: Site
):
    """Verify uix_site_pier_pile UniqueConstraint prevents duplicate pile identifiers within a site."""
    pile1 = Pile(
        site_id=test_site.id,
        pier_number="P12",
        pile_number="P12-1",
        diameter_mm=1200,
        planned_depth_m=24.5,
        status=PileStatus.PLANNED,
    )
    db_session.add(pile1)
    await db_session.commit()

    # Duplicate pier_number + pile_number on same site violates uix_site_pier_pile
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup_pile = Pile(
                site_id=test_site.id,
                pier_number="P12",
                pile_number="P12-1",
                diameter_mm=1200,
                planned_depth_m=24.5,
                status=PileStatus.PLANNED,
            )
            db_session.add(dup_pile)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_gang_attendance_unique_site_date_shift_subcontractor_trade(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify uix_site_date_shift_gang UniqueConstraint prevents duplicate gang attendance submissions."""
    target_date = date(2026, 9, 21)

    gang1 = GangAttendanceRecord(
        site_id=test_site.id,
        date=target_date,
        shift=ShiftType.DAY,
        subcontractor_name="L&T Heavy Civil Sub",
        trade=GangTrade.PILING_GANG,
        headcount_present=12,
        total_ot_hours=4.0,
        verified_by=test_user.id,
    )
    db_session.add(gang1)
    await db_session.commit()

    # Duplicate record with exact matching (site_id, date, shift, subcontractor, trade)
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_gang = GangAttendanceRecord(
                site_id=test_site.id,
                date=target_date,
                shift=ShiftType.DAY,
                subcontractor_name="L&T Heavy Civil Sub",
                trade=GangTrade.PILING_GANG,
                headcount_present=10,
                total_ot_hours=0.0,
                verified_by=test_user.id,
            )
            db_session.add(duplicate_gang)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_pile_progress_unique_dpr_pile_constraint(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify uix_dpr_pile UniqueConstraint prevents duplicate progress entries for the same pile on a DPR."""
    target_date = date(2026, 9, 22)
    dpr = DailyProgressReport(
        site_id=test_site.id,
        operational_date=target_date,
        shift=ShiftType.DAY,
        submitted_by=test_user.id,
        status=DPRStatus.SUBMITTED,
    )
    db_session.add(dpr)
    await db_session.commit()

    pile = Pile(
        site_id=test_site.id,
        pier_number="P15",
        pile_number="P15-1",
        diameter_mm=1000,
        planned_depth_m=20.0,
        status=PileStatus.BORING,
    )
    db_session.add(pile)
    await db_session.commit()

    prog1 = PileDailyProgress(
        dpr_id=dpr.id,
        pile_id=pile.id,
        depth_drilled_today_m=6.0,
        cumulative_depth_m=6.0,
        empty_bore_depth_m=0.0,
        rock_socket_depth_today_m=0.0,
        strata_type=StrataType.SOIL,
        casing_depth_m=3.0,
        casing_type=CasingType.TEMPORARY,
        cage_sections_lowered=1,
        cage_weight_kg_today=300.0,
        concrete_volume_planned_m3=12.0,
        concrete_volume_actual_m3=12.5,
    )
    db_session.add(prog1)
    await db_session.commit()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_prog = PileDailyProgress(
                dpr_id=dpr.id,
                pile_id=pile.id,
                depth_drilled_today_m=2.0,
                cumulative_depth_m=8.0,
                empty_bore_depth_m=0.0,
                rock_socket_depth_today_m=0.0,
                strata_type=StrataType.SOIL,
                casing_depth_m=3.0,
                casing_type=CasingType.TEMPORARY,
                cage_sections_lowered=0,
                cage_weight_kg_today=0.0,
                concrete_volume_planned_m3=0.0,
                concrete_volume_actual_m3=0.0,
            )
            db_session.add(duplicate_prog)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_well_log_unique_dpr_well_constraint(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify uix_dpr_well UniqueConstraint prevents duplicate well log entries on the same DPR."""
    target_date = date(2026, 9, 23)
    dpr = DailyProgressReport(
        site_id=test_site.id,
        operational_date=target_date,
        shift=ShiftType.DAY,
        submitted_by=test_user.id,
        status=DPRStatus.SUBMITTED,
    )
    db_session.add(dpr)
    await db_session.commit()

    well1 = WellLog(
        dpr_id=dpr.id,
        well_number="W-01",
        steining_lift_number=1,
        sinking_depth_today_cm=30.0,
        cumulative_sinking_depth_m=3.5,
        tilt_longitudinal_mm=8.0,
        tilt_transverse_mm=4.0,
        shift_mm=10.0,
        soil_type_at_cutting_edge="Stiff Clay",
        water_level_m=1.8,
        remarks="Normal sinking",
    )
    db_session.add(well1)
    await db_session.commit()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_well = WellLog(
                dpr_id=dpr.id,
                well_number="W-01",
                steining_lift_number=2,
                sinking_depth_today_cm=15.0,
                cumulative_sinking_depth_m=3.65,
                tilt_longitudinal_mm=12.0,
                tilt_transverse_mm=6.0,
                shift_mm=15.0,
                soil_type_at_cutting_edge="Stiff Clay",
                water_level_m=1.8,
                remarks="Duplicate entry attempt",
            )
            db_session.add(duplicate_well)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_equipment_log_unique_dpr_equipment_constraint(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify uix_dpr_equipment UniqueConstraint prevents duplicate logs for same equipment on same DPR."""
    target_date = date(2026, 9, 24)
    dpr = DailyProgressReport(
        site_id=test_site.id,
        operational_date=target_date,
        shift=ShiftType.DAY,
        submitted_by=test_user.id,
        status=DPRStatus.SUBMITTED,
    )
    db_session.add(dpr)
    await db_session.commit()

    rig = Equipment(
        name="Hydraulic Rig 01",
        type=EquipmentType.RIG,
        registration_number="HR-01",
        site_id=test_site.id,
    )
    db_session.add(rig)
    await db_session.commit()

    eq_log1 = EquipmentLog(
        dpr_id=dpr.id,
        equipment_id=rig.id,
        opening_hours=200.0,
        closing_hours=208.0,
        working_hours=8.0,
        breakdown_hours=0.0,
        idle_hours=0.0,
        fuel_liters=100.0,
    )
    db_session.add(eq_log1)
    await db_session.commit()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_eq_log = EquipmentLog(
                dpr_id=dpr.id,
                equipment_id=rig.id,
                opening_hours=208.0,
                closing_hours=210.0,
                working_hours=2.0,
                breakdown_hours=0.0,
                idle_hours=0.0,
                fuel_liters=25.0,
            )
            db_session.add(duplicate_eq_log)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_site_inventory_unique_site_material_constraint(
    db_session: AsyncSession, test_site: Site
):
    """Verify uix_site_material UniqueConstraint prevents duplicate material records for same site."""
    inv1 = SiteInventory(
        site_id=test_site.id,
        material_name="OPC 53 Cement",
        unit="BAGS",
        current_stock=500.0,
        reorder_threshold=100.0,
    )
    db_session.add(inv1)
    await db_session.commit()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_inv = SiteInventory(
                site_id=test_site.id,
                material_name="OPC 53 Cement",
                unit="BAGS",
                current_stock=200.0,
                reorder_threshold=50.0,
            )
            db_session.add(duplicate_inv)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_dip_boundary_extremes(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify extreme negative dip values fail check_positive_dip, while zero and tiny positive succeed."""
    # Tiny negative (-0.0001) must fail
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            reg_neg_tiny = ShiftFuelRegister(
                site_id=test_site.id,
                date=date(2026, 9, 27),
                shift=ShiftType.DAY,
                opening_stock_liters=500.0,
                received_bowser_liters=0.0,
                received_drums_liters=0.0,
                total_issued_to_equipment_liters=100.0,
                closing_dip_stock_liters=-0.0001,
                variance_liters=0.0,
                recorded_by=test_user.id,
            )
            db_session.add(reg_neg_tiny)
            await db_session.flush()

    # Huge negative (-1000000.0) must fail
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            reg_neg_huge = ShiftFuelRegister(
                site_id=test_site.id,
                date=date(2026, 9, 27),
                shift=ShiftType.DAY,
                opening_stock_liters=500.0,
                received_bowser_liters=0.0,
                received_drums_liters=0.0,
                total_issued_to_equipment_liters=100.0,
                closing_dip_stock_liters=-1000000.0,
                variance_liters=0.0,
                recorded_by=test_user.id,
            )
            db_session.add(reg_neg_huge)
            await db_session.flush()

    # Tiny positive (0.0001) must succeed
    reg_pos_tiny = ShiftFuelRegister(
        site_id=test_site.id,
        date=date(2026, 9, 27),
        shift=ShiftType.DAY,
        opening_stock_liters=500.0,
        received_bowser_liters=0.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=100.0,
        closing_dip_stock_liters=0.0001,
        variance_liters=0.0,
        recorded_by=test_user.id,
    )
    db_session.add(reg_pos_tiny)
    await db_session.commit()
    assert reg_pos_tiny.closing_dip_stock_liters == 0.0001


@pytest.mark.unit
@pytest.mark.anyio
async def test_fuel_register_issuance_boundary_extremes(
    db_session: AsyncSession, test_site: Site, test_user: User
):
    """Verify check_valid_issuance constraint at exact float boundary (available + 0.001 fails)."""
    # Total available = 200 + 100 + 50 = 350.0 L
    # Issuing 350.001 L must fail
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            reg_over = ShiftFuelRegister(
                site_id=test_site.id,
                date=date(2026, 9, 28),
                shift=ShiftType.DAY,
                opening_stock_liters=200.0,
                received_bowser_liters=100.0,
                received_drums_liters=50.0,
                total_issued_to_equipment_liters=350.001,
                closing_dip_stock_liters=0.0,
                variance_liters=0.0,
                recorded_by=test_user.id,
            )
            db_session.add(reg_over)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_user_unique_phone_and_email_constraint(
    db_session: AsyncSession, test_user: User
):
    """Verify User unique constraints prevent duplicate phone and duplicate email at DB level."""
    # Duplicate phone must fail
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup_phone_user = User(
                name="Duplicate Phone User",
                phone=test_user.phone,  # Matches existing test_user phone
                email="distinct.email@test.com",
                role=UserRole.SITE_ENGINEER,
            )
            db_session.add(dup_phone_user)
            await db_session.flush()

    # Duplicate email must fail
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup_email_user = User(
                name="Duplicate Email User",
                phone="+919999888877",
                email=test_user.email,  # Matches existing test_user email
                role=UserRole.SITE_ENGINEER,
            )
            db_session.add(dup_email_user)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_user_not_null_constraints(db_session: AsyncSession):
    """Verify NOT NULL constraints on critical user columns."""
    # Missing name must fail
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            bad_user_no_name = User(
                name=None,
                phone="+919876543299",
                role=UserRole.SITE_ENGINEER,
            )
            db_session.add(bad_user_no_name)
            await db_session.flush()

    # Missing phone must fail
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            bad_user_no_phone = User(
                name="Valid Name",
                phone=None,
                role=UserRole.SITE_ENGINEER,
            )
            db_session.add(bad_user_no_phone)
            await db_session.flush()


@pytest.mark.unit
@pytest.mark.anyio
async def test_project_unique_code_constraint(
    db_session: AsyncSession, test_project: Project
):
    """Verify Project code uniqueness constraint prevents duplicate project codes."""
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup_proj = Project(
                name="Another Project",
                code=test_project.code,  # Matches existing test_project.code
                client_name="Another Client",
                location="Surat",
                contract_value=1000000.0,
                start_date=date(2026, 1, 1),
                status=ProjectStatus.ACTIVE,
            )
            db_session.add(dup_proj)
            await db_session.flush()
