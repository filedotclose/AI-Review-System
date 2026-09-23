import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, ProjectStatus, SiteStatus, PileStatus
from app.models.equipment import (
    Equipment,
    EquipmentType,
    EquipmentStatus,
    SiteFuelRegister,
    SiteInventory,
    ShiftType,
)
from app.models.petty_cash import (
    PettyCashWallet,
    PettyCashTransaction,
    TransactionType,
    ExpenseCategory,
    ApprovalStatus,
    ReimbursementStatus,
)
from app.models.attendance import (
    Worker,
    WorkerCategory,
    AttendanceRecord,
    AttendanceStatus,
    GangAttendanceRecord,
    GangTrade,
)
from app.models.dpr import (
    DailyProgressReport,
    DPRStatus,
    PileDailyProgress,
    EquipmentLog,
    LabourSummary,
    MaterialConsumption,
    TestReport,
    StrataType,
    CasingType,
    TestType,
    PassFail,
)
from app.models.executive_brief import (
    ExecutiveBrief,
    DeliveryStatus,
    DeliveryChannel,
)
from app.core.security import get_password_hash, get_pin_hash

logger = logging.getLogger(__name__)


async def seed_database(session: AsyncSession, force: bool = False) -> Dict[str, int]:
    """
    Populate the database with comprehensive, realistic operational data
    for ODIPKS Infra's civil infrastructure packages.
    """
    # 1. Check if database already has users/data
    stmt = select(User).limit(1)
    res = await session.execute(stmt)
    existing_user = res.scalar_one_or_none()

    if existing_user and not force:
        logger.info("Database already contains data. Skipping seeding (pass force=True to wipe and reseed).")
        return {"status": "skipped", "message": "Database already populated."}

    if force:
        logger.info("Force re-seeding requested: Purging existing operational records in reverse dependency order...")
        # Clean down in proper foreign key order
        await session.execute(delete(TestReport))
        await session.execute(delete(MaterialConsumption))
        await session.execute(delete(LabourSummary))
        await session.execute(delete(EquipmentLog))
        await session.execute(delete(PileDailyProgress))
        await session.execute(delete(SiteFuelRegister))
        await session.execute(delete(DailyProgressReport))
        await session.execute(delete(ExecutiveBrief))
        await session.execute(delete(AttendanceRecord))
        await session.execute(delete(GangAttendanceRecord))
        await session.execute(delete(Worker))
        await session.execute(delete(PettyCashTransaction))
        await session.execute(delete(PettyCashWallet))
        await session.execute(delete(SiteInventory))
        await session.execute(delete(Equipment))
        await session.execute(delete(Pile))
        await session.execute(delete(Site))
        await session.execute(delete(Project))
        await session.execute(delete(User))
        await session.flush()
        logger.info("Purge complete. Proceeding to seed realistic dataset...")

    now_utc = datetime.now(timezone.utc)
    today = date.today()
    d_m4 = today - timedelta(days=4)
    d_m3 = today - timedelta(days=3)
    d_m2 = today - timedelta(days=2)
    d_m1 = today - timedelta(days=1)
    d_0 = today

    # -------------------------------------------------------------------------
    # 1. USER ACCOUNTS & CREDENTIALS
    # -------------------------------------------------------------------------
    pwd_hash = get_password_hash("password123")
    pin_1234 = get_pin_hash("1234")
    pin_9999 = get_pin_hash("9999")

    users = [
        User(
            name="Pradeep K. Sharma",
            email="owner@odipks.com",
            phone="9800000001",
            role=UserRole.OWNER,
            password_hash=pwd_hash,
            pin_hash=pin_1234,
            is_active=True,
        ),
        User(
            name="Ananya Sen",
            email="finance@odipks.com",
            phone="9800000002",
            role=UserRole.FINANCE_HEAD,
            password_hash=pwd_hash,
            pin_hash=pin_1234,
            is_active=True,
        ),
        User(
            name="Vikram Mehta",
            email="engineer@odipks.com",
            phone="9811122233",
            role=UserRole.PROJECT_MANAGER,
            password_hash=pwd_hash,
            pin_hash=pin_9999,
            is_active=True,
        ),
        User(
            name="Rajesh Sharma",
            email="rajesh@odipks.com",
            phone="9876543210",
            role=UserRole.SITE_ENGINEER,
            password_hash=pwd_hash,
            pin_hash=pin_1234,
            is_active=True,
        ),
        User(
            name="Sunil Varma",
            email="supervisor@odipks.com",
            phone="9876543211",
            role=UserRole.SUPERVISOR,
            password_hash=pwd_hash,
            pin_hash=pin_1234,
            is_active=True,
        ),
        User(
            name="Amit Patel",
            email="amit@odipks.com",
            phone="9876543212",
            role=UserRole.SITE_ENGINEER,
            password_hash=pwd_hash,
            pin_hash=pin_1234,
            is_active=True,
        ),
    ]
    session.add_all(users)
    await session.flush()

    user_owner = users[0]
    user_fin = users[1]
    user_pm = users[2]
    user_se_vadakara = users[3]
    user_sup_vadakara = users[4]
    user_se_kochi = users[5]

    # -------------------------------------------------------------------------
    # 2. PROJECTS & SITES
    # -------------------------------------------------------------------------
    proj1 = Project(
        name="ADANI-ODIPKS AVRP Flyover Package",
        code="AVRP-FLYOVER-01",
        client_name="Adani Road Transport Ltd / NHAI",
        location="Vadakara Bypass, Kerala",
        contract_value=485000000.0,
        start_date=today - timedelta(days=160),
        expected_end_date=today + timedelta(days=320),
        status=ProjectStatus.ACTIVE,
    )
    proj2 = Project(
        name="KMRL Metro Rail Phase II Viaduct Piling",
        code="KMRL-P2-04",
        client_name="Kochi Metro Rail Limited (KMRL)",
        location="Kakkanad, Kochi, Kerala",
        contract_value=320000000.0,
        start_date=today - timedelta(days=75),
        expected_end_date=today + timedelta(days=450),
        status=ProjectStatus.ACTIVE,
    )
    session.add_all([proj1, proj2])
    await session.flush()

    site1 = Site(
        project_id=proj1.id,
        name="Vadakara AVRP Flyover Site Office (Pier P10 - P24)",
        location_lat=11.6086,
        location_lng=75.5912,
        geofence_radius_m=500,
        status=SiteStatus.ACTIVE,
    )
    site2 = Site(
        project_id=proj2.id,
        name="Kakkanad Metro Junction Pier Site (P01 - P15)",
        location_lat=10.0159,
        location_lng=76.3419,
        geofence_radius_m=450,
        status=SiteStatus.ACTIVE,
    )
    session.add_all([site1, site2])
    await session.flush()

    # -------------------------------------------------------------------------
    # 3. PILES & FOUNDATIONS (Pier P11 to P14)
    # -------------------------------------------------------------------------
    piles: List[Pile] = []
    # Pier P11 (All 4 Completed)
    for p_idx in range(1, 5):
        piles.append(
            Pile(
                site_id=site1.id,
                pier_number="P11",
                pile_number=f"P11-0{p_idx}",
                diameter_mm=1200,
                cutoff_level_m=+3.25,
                ground_level_m=+6.50,
                planned_depth_m=26.0,
                planned_rock_socket_m=2.5,
                status=PileStatus.COMPLETED,
            )
        )

    # Pier P12 (Active & Progressing)
    piles.extend([
        Pile(
            site_id=site1.id,
            pier_number="P12",
            pile_number="P-101",
            diameter_mm=1000,
            cutoff_level_m=+3.10,
            ground_level_m=+6.40,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.COMPLETED,
        ),
        Pile(
            site_id=site1.id,
            pier_number="P12",
            pile_number="P-102",
            diameter_mm=1000,
            cutoff_level_m=+3.10,
            ground_level_m=+6.40,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.CAST,
        ),
        Pile(
            site_id=site1.id,
            pier_number="P12",
            pile_number="P-103",
            diameter_mm=1000,
            cutoff_level_m=+3.10,
            ground_level_m=+6.40,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.CAGED,
        ),
        Pile(
            site_id=site1.id,
            pier_number="P12",
            pile_number="P-104",
            diameter_mm=1000,
            cutoff_level_m=+3.10,
            ground_level_m=+6.40,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.SOCKETING,
        ),
    ])

    # Pier P13 (Boring & Planned)
    piles.extend([
        Pile(
            site_id=site1.id,
            pier_number="P13",
            pile_number="P-105",
            diameter_mm=1000,
            cutoff_level_m=+3.15,
            ground_level_m=+6.45,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.BORING,
        ),
        Pile(
            site_id=site1.id,
            pier_number="P13",
            pile_number="P-106",
            diameter_mm=1000,
            cutoff_level_m=+3.15,
            ground_level_m=+6.45,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.PLANNED,
        ),
        Pile(
            site_id=site1.id,
            pier_number="P13",
            pile_number="P-107",
            diameter_mm=1000,
            cutoff_level_m=+3.15,
            ground_level_m=+6.45,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.PLANNED,
        ),
        Pile(
            site_id=site1.id,
            pier_number="P13",
            pile_number="P-108",
            diameter_mm=1000,
            cutoff_level_m=+3.15,
            ground_level_m=+6.45,
            planned_depth_m=24.0,
            planned_rock_socket_m=2.0,
            status=PileStatus.PLANNED,
        ),
    ])

    # Pier P14 (Planned)
    for p_idx in range(1, 5):
        piles.append(
            Pile(
                site_id=site1.id,
                pier_number="P14",
                pile_number=f"P14-0{p_idx}",
                diameter_mm=1000,
                cutoff_level_m=+3.20,
                ground_level_m=+6.50,
                planned_depth_m=24.0,
                planned_rock_socket_m=2.0,
                status=PileStatus.PLANNED,
            )
        )

    # Site 2 Piles (Kochi Metro)
    for p_idx in range(1, 5):
        piles.append(
            Pile(
                site_id=site2.id,
                pier_number="KM-P01",
                pile_number=f"KP-0{p_idx}",
                diameter_mm=1200,
                cutoff_level_m=+2.80,
                ground_level_m=+5.90,
                planned_depth_m=28.0,
                planned_rock_socket_m=3.0,
                status=PileStatus.COMPLETED if p_idx <= 2 else PileStatus.BORING,
            )
        )

    session.add_all(piles)
    await session.flush()

    # Create mapping for convenience
    pile_p102 = next(p for p in piles if p.pile_number == "P-102")
    pile_p103 = next(p for p in piles if p.pile_number == "P-103")
    pile_p104 = next(p for p in piles if p.pile_number == "P-104")
    pile_p105 = next(p for p in piles if p.pile_number == "P-105")

    # -------------------------------------------------------------------------
    # 4. HEAVY EQUIPMENT FLEET
    # -------------------------------------------------------------------------
    equipments = [
        # Site 1 Heavy Equipment
        Equipment(
            name="Bauer BG-28 Rotary Rig #1",
            registration_number="EQ-RIG-01",
            type=EquipmentType.RIG,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=24.0,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Sany SR-285 Rotary Rig #2",
            registration_number="EQ-RIG-02",
            type=EquipmentType.RIG,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=26.0,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Sany SCC-500 Crawler Crane 50T",
            registration_number="EQ-CRANE-01",
            type=EquipmentType.CRANE,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=12.0,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Kobelco SK210 Heavy Excavator",
            registration_number="EQ-EXC-01",
            type=EquipmentType.EXCAVATOR,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=14.0,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Putzmeister BSA 1409 D Concrete Pump",
            registration_number="EQ-PUMP-01",
            type=EquipmentType.PUMP,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=11.0,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Kirloskar 125 kVA Silent DG Set #1",
            registration_number="EQ-DG-01",
            type=EquipmentType.GENERATOR,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=9.5,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Kirloskar 125 kVA Silent DG Set #2",
            registration_number="EQ-DG-02",
            type=EquipmentType.GENERATOR,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=9.5,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Ashok Leyland 9KL Diesel Bowser",
            registration_number="EQ-BOWSER-01",
            type=EquipmentType.OTHER,
            site_id=site1.id,
            fuel_benchmark_liters_per_hour=4.0,
            status=EquipmentStatus.OPERATIONAL,
        ),
        # Site 2 Equipment
        Equipment(
            name="Mait HR-180 Rotary Drilling Rig",
            registration_number="EQ-RIG-03",
            type=EquipmentType.RIG,
            site_id=site2.id,
            fuel_benchmark_liters_per_hour=21.0,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Tata Hitachi ZX220 Crawler Crane",
            registration_number="EQ-CRANE-02",
            type=EquipmentType.CRANE,
            site_id=site2.id,
            fuel_benchmark_liters_per_hour=11.5,
            status=EquipmentStatus.OPERATIONAL,
        ),
        Equipment(
            name="Cummins 100 kVA Standby DG Set",
            registration_number="EQ-DG-03",
            type=EquipmentType.GENERATOR,
            site_id=site2.id,
            fuel_benchmark_liters_per_hour=8.5,
            status=EquipmentStatus.OPERATIONAL,
        ),
    ]
    session.add_all(equipments)
    await session.flush()

    eq_rig1 = equipments[0]
    eq_rig2 = equipments[1]
    eq_crane1 = equipments[2]
    eq_exc1 = equipments[3]
    eq_pump1 = equipments[4]
    eq_dg1 = equipments[5]

    # -------------------------------------------------------------------------
    # 5. SITE INVENTORY & CONSUMABLES
    # -------------------------------------------------------------------------
    inventories = [
        SiteInventory(
            site_id=site1.id,
            material_name="OPC 53 Grade Cement",
            unit="MT",
            current_stock=42.5,
            reorder_threshold=15.0,
        ),
        SiteInventory(
            site_id=site1.id,
            material_name="Fe550D TMT Steel Rebar",
            unit="MT",
            current_stock=68.0,
            reorder_threshold=20.0,
        ),
        SiteInventory(
            site_id=site1.id,
            material_name="Bentonite Slurry Polymer",
            unit="Bags",
            current_stock=380.0,
            reorder_threshold=100.0,
        ),
        SiteInventory(
            site_id=site1.id,
            material_name="High Speed Diesel (HSD)",
            unit="Liters",
            current_stock=4200.0,
            reorder_threshold=1500.0,
        ),
        SiteInventory(
            site_id=site1.id,
            material_name="Tremie Pipes 250mm ID",
            unit="Nos",
            current_stock=18.0,
            reorder_threshold=10.0,
        ),
        SiteInventory(
            site_id=site1.id,
            material_name="Rig Bullet Teeth (Tungsten)",
            unit="Pcs",
            current_stock=85.0,
            reorder_threshold=30.0,
        ),
        # Site 2
        SiteInventory(
            site_id=site2.id,
            material_name="OPC 53 Grade Cement",
            unit="MT",
            current_stock=31.0,
            reorder_threshold=12.0,
        ),
        SiteInventory(
            site_id=site2.id,
            material_name="High Speed Diesel (HSD)",
            unit="Liters",
            current_stock=2450.0,
            reorder_threshold=1000.0,
        ),
    ]
    session.add_all(inventories)

    # -------------------------------------------------------------------------
    # 6. PETTY CASH WALLETS & EXPENSE TRANSACTIONS
    # -------------------------------------------------------------------------
    wallet1 = PettyCashWallet(
        site_id=site1.id,
        current_balance=26450.0,
        last_replenishment_date=now_utc - timedelta(days=6),
        last_reconciliation_date=now_utc - timedelta(days=7),
    )
    wallet2 = PettyCashWallet(
        site_id=site2.id,
        current_balance=18500.0,
        last_replenishment_date=now_utc - timedelta(days=5),
        last_reconciliation_date=now_utc - timedelta(days=7),
    )
    session.add_all([wallet1, wallet2])
    await session.flush()

    transactions = [
        # Wallet Replenishment
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.REPLENISHMENT,
            amount=50000.0,
            category=ExpenseCategory.OTHER,
            description="Head Office petty cash imprest tranche #08 via NEFT",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_fin.id,
            approved_by=user_owner.id,
            date=d_m4,
        ),
        # Day -4
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=3200.0,
            category=ExpenseCategory.FUEL,
            description="Emergency diesel for standby DG Set 125kVA (35L)",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_se_vadakara.id,
            approved_by=user_pm.id,
            date=d_m4,
        ),
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=2750.0,
            category=ExpenseCategory.WELDING_REPAIR,
            description="Industrial oxygen (2 cyl) & dissolved acetylene (1 cyl) for cage fabrication",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_sup_vadakara.id,
            approved_by=user_pm.id,
            date=d_m4,
        ),
        # Day -3
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=4850.0,
            category=ExpenseCategory.TOOLS,
            description="Bauer BG-28 hydraulic high-pressure seals & pilot valve O-ring kit",
            has_physical_bill=True,
            is_out_of_pocket=True,
            reimbursement_status=ReimbursementStatus.DUE,
            approval_status=ApprovalStatus.APPROVED,
            recorded_by=user_se_vadakara.id,
            approved_by=user_pm.id,
            date=d_m3,
        ),
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=1800.0,
            category=ExpenseCategory.FOOD_WATER,
            description="Site drinking water tanker (6,000L RO purified) for piling workforce colony",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_sup_vadakara.id,
            approved_by=user_pm.id,
            date=d_m3,
        ),
        # Day -2
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=6200.0,
            category=ExpenseCategory.TOOLS,
            description="Tungsten carbide bullet drill teeth (20 pcs) for hard rock core barrel",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_se_vadakara.id,
            approved_by=user_pm.id,
            date=d_m2,
        ),
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=1200.0,
            category=ExpenseCategory.TRANSPORT,
            description="Local roundtrip vehicle hire for QA engineer carrying concrete test cubes to NABL lab",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_se_vadakara.id,
            approved_by=user_pm.id,
            date=d_m2,
        ),
        # Day -1 (Yesterday)
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=3500.0,
            category=ExpenseCategory.MATERIAL,
            description="Heavy-duty wire rope lubricant spray & grease buckets for crawler crane winches",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.APPROVED,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_sup_vadakara.id,
            approved_by=user_pm.id,
            date=d_m1,
        ),
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=4100.0,
            category=ExpenseCategory.TOOLS,
            description="Exide 12V 100Ah heavy commercial battery replacement for Sany Crane starter",
            has_physical_bill=True,
            is_out_of_pocket=True,
            reimbursement_status=ReimbursementStatus.DUE,
            approval_status=ApprovalStatus.PENDING,
            recorded_by=user_se_vadakara.id,
            date=d_m1,
        ),
        # Intentional Anomaly Expense: Duplicate bill detected by OCR / invoice audit
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=8500.0,
            category=ExpenseCategory.TOOLS,
            description="Rotary rig hydraulic filter & return line assembly [INV-HYD-9921]",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.PENDING,
            duplicate_flag=True,
            anomaly_flag=True,
            anomaly_reason="Duplicate Invoice #INV-HYD-9921 detected; already submitted on tranche #07",
            recorded_by=user_sup_vadakara.id,
            date=d_m1,
        ),
        # Day 0 (Today)
        PettyCashTransaction(
            wallet_id=wallet1.id,
            project_id=proj1.id,
            type=TransactionType.EXPENSE,
            amount=2150.0,
            category=ExpenseCategory.FOOD_WATER,
            description="Site drinking water replenishment & ice blocks for slurry testing cooler",
            has_physical_bill=True,
            is_out_of_pocket=False,
            approval_status=ApprovalStatus.PENDING,
            reimbursement_status=ReimbursementStatus.NOT_APPLICABLE,
            recorded_by=user_sup_vadakara.id,
            date=d_0,
        ),
    ]
    session.add_all(transactions)

    # -------------------------------------------------------------------------
    # 7. WORKFORCE & MANPOWER ROSTER
    # -------------------------------------------------------------------------
    workers = [
        # Site 1 Direct Staff
        Worker(name="Ramesh Kumar", category=WorkerCategory.OPERATOR, phone="9876500001", assigned_site_id=site1.id),
        Worker(name="Suresh Yadav", category=WorkerCategory.WELDER, phone="9876500002", assigned_site_id=site1.id),
        Worker(name="Manoj Singh", category=WorkerCategory.RIG_HELPER, phone="9876500003", assigned_site_id=site1.id),
        Worker(name="Anil Pillai", category=WorkerCategory.FITTER, phone="9876500004", assigned_site_id=site1.id),
        Worker(name="Vikram Das", category=WorkerCategory.LABOURER, phone="9876500005", assigned_site_id=site1.id),
        Worker(name="Dinesh Sharma", category=WorkerCategory.OPERATOR, phone="9876500006", assigned_site_id=site1.id),
        Worker(name="Santosh Gond", category=WorkerCategory.RIG_HELPER, phone="9876500007", assigned_site_id=site1.id),
        Worker(name="Harish Nair", category=WorkerCategory.DRIVER, phone="9876500008", assigned_site_id=site1.id),
        Worker(name="Jagdish Prasad", category=WorkerCategory.WELDER, phone="9876500009", assigned_site_id=site1.id),
        Worker(name="Mohammad Rafiq", category=WorkerCategory.FITTER, phone="9876500010", assigned_site_id=site1.id),
        Worker(name="Brijesh Yadav", category=WorkerCategory.LABOURER, phone="9876500011", assigned_site_id=site1.id),
        Worker(name="Pradeep G.", category=WorkerCategory.OPERATOR, phone="9876500012", assigned_site_id=site1.id),
        # Site 2 Direct Staff
        Worker(name="Kishore Babu", category=WorkerCategory.OPERATOR, phone="9876500021", assigned_site_id=site2.id),
        Worker(name="Tomy Joseph", category=WorkerCategory.FITTER, phone="9876500022", assigned_site_id=site2.id),
    ]
    session.add_all(workers)
    await session.flush()

    # -------------------------------------------------------------------------
    # 8. ATTENDANCE & GANG MUSTER (Multi-day)
    # -------------------------------------------------------------------------
    att_records: List[AttendanceRecord] = []
    gang_records: List[GangAttendanceRecord] = []

    date_series = [d_m4, d_m3, d_m2, d_m1, d_0]

    for d_idx, cur_date in enumerate(date_series):
        # 12 site1 workers
        for w_idx, w in enumerate(workers[:12]):
            # Set realistic check-in / check-out times
            base_morning = datetime(cur_date.year, cur_date.month, cur_date.day, 7, 45, tzinfo=timezone.utc)
            base_evening = datetime(cur_date.year, cur_date.month, cur_date.day, 17, 30, tzinfo=timezone.utc)
            c_in = base_morning + timedelta(minutes=(w_idx * 2))
            c_out = (base_evening + timedelta(minutes=(w_idx * 2))) if cur_date < d_0 else None
            hours = 9.0 + (w_idx % 3) * 0.5 if cur_date < d_0 else 4.5
            ot = 1.0 if (w_idx % 4 == 0 and cur_date < d_0) else 0.0

            # Vadakara site GPS coordinates: 11.6086, 75.5912
            lat = 11.6086 + (w_idx * 0.0001)
            lng = 75.5912 - (w_idx * 0.0001)
            in_geofence = True
            anomaly = False
            anomaly_msg = None

            # On d_m1, create 1 real geofence anomaly for Manoj Singh (w_idx=2)
            if cur_date == d_m1 and w.name == "Manoj Singh":
                lat = 11.6320  # ~2.6 km North
                lng = 75.6080
                in_geofence = False
                anomaly = True
                anomaly_msg = "Check-in GPS location 2.6 km outside site geofence boundary"

            att_records.append(
                AttendanceRecord(
                    site_id=site1.id,
                    worker_id=w.id,
                    date=cur_date,
                    shift=ShiftType.DAY,
                    check_in_time=c_in,
                    check_out_time=c_out,
                    check_in_lat=lat,
                    check_in_lng=lng,
                    within_geofence=in_geofence,
                    hours_worked=hours,
                    overtime_hours=ot,
                    verified_by_supervisor=user_sup_vadakara.id,
                    verified_at=c_in + timedelta(hours=1),
                    status=AttendanceStatus.PRESENT,
                    anomaly_flag=anomaly,
                    anomaly_reason=anomaly_msg,
                )
            )

        # Subcontractor Gang Muster for each day
        gang_records.extend([
            GangAttendanceRecord(
                site_id=site1.id,
                date=cur_date,
                shift=ShiftType.DAY,
                subcontractor_name="Maa Durga Infra Piling Gang",
                trade=GangTrade.PILING_GANG,
                headcount_present=16,
                total_ot_hours=18.0 if cur_date < d_0 else 0.0,
                muster_roll_photo_url="https://minio.odipks.internal/muster/maa_durga_piling.jpg",
                verified_by=user_sup_vadakara.id,
            ),
            GangAttendanceRecord(
                site_id=site1.id,
                date=cur_date,
                shift=ShiftType.DAY,
                subcontractor_name="Shree Ram Rebar Fabrication",
                trade=GangTrade.STEEL_BENDING,
                headcount_present=12,
                total_ot_hours=12.0 if cur_date < d_0 else 0.0,
                muster_roll_photo_url="https://minio.odipks.internal/muster/shree_ram_rebar.jpg",
                verified_by=user_sup_vadakara.id,
            ),
            GangAttendanceRecord(
                site_id=site1.id,
                date=cur_date,
                shift=ShiftType.DAY,
                subcontractor_name="Kerala Ready-Mix Concreting Crew",
                trade=GangTrade.CONCRETING,
                headcount_present=14,
                total_ot_hours=14.0 if cur_date < d_0 else 0.0,
                muster_roll_photo_url="https://minio.odipks.internal/muster/kerala_concreting.jpg",
                verified_by=user_sup_vadakara.id,
            ),
        ])

    session.add_all(att_records)
    session.add_all(gang_records)

    # -------------------------------------------------------------------------
    # 9. DAILY PROGRESS REPORTS (DPR) & SUB-ENTRIES
    # -------------------------------------------------------------------------
    dprs = [
        # Day -4 (P12-1 Concreting & Testing)
        DailyProgressReport(
            site_id=site1.id,
            operational_date=d_m4,
            shift=ShiftType.DAY,
            submitted_by=user_se_vadakara.id,
            submitted_at=datetime(d_m4.year, d_m4.month, d_m4.day, 19, 30, tzinfo=timezone.utc),
            status=DPRStatus.VERIFIED,
            weather_conditions="Clear sunny skies, 32°C, humidity 74%. Normal sea breeze.",
            problems_delays="Minor 20-minute wait for transit mixer arrival from batching plant.",
            tomorrows_plan="Mobilize Bauer BG-28 rig to Pier P12 Pile P-102. Set up temporary casing.",
            verified_by=user_pm.id,
            verified_at=datetime(d_m4.year, d_m4.month, d_m4.day, 21, 0, tzinfo=timezone.utc),
        ),
        # Day -3 (P12-2 Boring)
        DailyProgressReport(
            site_id=site1.id,
            operational_date=d_m3,
            shift=ShiftType.DAY,
            submitted_by=user_se_vadakara.id,
            submitted_at=datetime(d_m3.year, d_m3.month, d_m3.day, 19, 45, tzinfo=timezone.utc),
            status=DPRStatus.VERIFIED,
            weather_conditions="Partly cloudy, 30°C. Piling conditions favorable.",
            problems_delays="Bauer BG-28 hydraulic seal weeping; maintenance team serviced in 45 minutes.",
            tomorrows_plan="Complete boring through weathered rock and penetrate hard granite socket.",
            verified_by=user_pm.id,
            verified_at=datetime(d_m3.year, d_m3.month, d_m3.day, 21, 15, tzinfo=timezone.utc),
        ),
        # Day -2 (P12-2 Rock Socketing & Cage Lowering)
        DailyProgressReport(
            site_id=site1.id,
            operational_date=d_m2,
            shift=ShiftType.DAY,
            submitted_by=user_se_vadakara.id,
            submitted_at=datetime(d_m2.year, d_m2.month, d_m2.day, 19, 50, tzinfo=timezone.utc),
            status=DPRStatus.VERIFIED,
            weather_conditions="Overcast, 29°C. Light intermittent drizzle.",
            problems_delays="Hard rock core extraction required tungsten bullet replacement (1 hr pause).",
            tomorrows_plan="Execute tremie concrete pour for P-102; commence boring on P-103.",
            verified_by=user_pm.id,
            verified_at=datetime(d_m2.year, d_m2.month, d_m2.day, 21, 10, tzinfo=timezone.utc),
        ),
        # Day -1 (Yesterday - P12-2 Cast & P12-3 Boring & Rain Delay)
        DailyProgressReport(
            site_id=site1.id,
            operational_date=d_m1,
            shift=ShiftType.DAY,
            submitted_by=user_se_vadakara.id,
            submitted_at=datetime(d_m1.year, d_m1.month, d_m1.day, 20, 15, tzinfo=timezone.utc),
            status=DPRStatus.SUBMITTED,
            weather_conditions="Heavy coastal monsoon squall in late afternoon, 27°C.",
            problems_delays="Heavy monsoon downpour delayed concrete transit mixer by 1.5 hrs. Tremie seal maintained under constant supervision.",
            tomorrows_plan="Advance boring on P-104 with Sany rig; complete caging inspection on P-103.",
            verified_by=user_pm.id,
            verified_at=datetime(d_m1.year, d_m1.month, d_m1.day, 22, 0, tzinfo=timezone.utc),
        ),
        # Day 0 (Today - Active Progress)
        DailyProgressReport(
            site_id=site1.id,
            operational_date=d_0,
            shift=ShiftType.DAY,
            submitted_by=user_se_vadakara.id,
            submitted_at=datetime(d_0.year, d_0.month, d_0.day, 12, 30, tzinfo=timezone.utc),
            status=DPRStatus.DRAFT,
            weather_conditions="Clear skies, 31°C, calm wind.",
            problems_delays="None. Dual rigs operating concurrently on Pier P12 & P13.",
            tomorrows_plan="Pour tremie concrete on P-103; terminate rock socketing on P-104.",
        ),
    ]
    session.add_all(dprs)
    await session.flush()

    dpr_m4, dpr_m3, dpr_m2, dpr_m1, dpr_0 = dprs[0], dprs[1], dprs[2], dprs[3], dprs[4]

    # Pile Daily Progresses
    pile_progresses = [
        # Day -3 on P-102
        PileDailyProgress(
            dpr_id=dpr_m3.id,
            pile_id=pile_p102.id,
            depth_drilled_today_m=12.5,
            cumulative_depth_m=12.5,
            empty_bore_depth_m=3.3,
            rock_socket_depth_today_m=0.0,
            strata_type=StrataType.WEATHERED_ROCK,
            casing_depth_m=6.0,
            casing_type=CasingType.TEMPORARY,
            cage_sections_lowered=0,
            cage_weight_kg_today=0.0,
            concrete_volume_planned_m3=0.0,
            concrete_volume_actual_m3=0.0,
            slump_mm=None,
            bentonite_density_g_cc=1.06,
            remarks="Boring progressed smoothly through marine clay into weathered gneiss rock.",
        ),
        # Day -2 on P-102
        PileDailyProgress(
            dpr_id=dpr_m2.id,
            pile_id=pile_p102.id,
            depth_drilled_today_m=11.5,
            cumulative_depth_m=24.0,
            empty_bore_depth_m=3.3,
            rock_socket_depth_today_m=2.0,
            strata_type=StrataType.HARD_ROCK,
            casing_depth_m=6.0,
            casing_type=CasingType.TEMPORARY,
            cage_sections_lowered=2,
            cage_weight_kg_today=3250.0,
            concrete_volume_planned_m3=0.0,
            concrete_volume_actual_m3=0.0,
            slump_mm=None,
            bentonite_density_g_cc=1.08,
            remarks="Bored depth 24.0m reached. 2.0m hard rock socketing verified with client consultant.",
        ),
        # Day -1 on P-102 (Concreted)
        PileDailyProgress(
            dpr_id=dpr_m1.id,
            pile_id=pile_p102.id,
            depth_drilled_today_m=0.0,
            cumulative_depth_m=24.0,
            empty_bore_depth_m=3.3,
            rock_socket_depth_today_m=2.0,
            strata_type=StrataType.HARD_ROCK,
            casing_depth_m=6.0,
            casing_type=CasingType.TEMPORARY,
            cage_sections_lowered=1,
            cage_weight_kg_today=1620.0,
            concrete_volume_planned_m3=18.8,
            concrete_volume_actual_m3=20.9,
            slump_mm=190.0,
            bentonite_density_g_cc=1.09,
            delay_reason="Heavy monsoon squall delayed transit mixer dispatch by 1.5 hrs.",
            remarks="Full tremie concrete pour successfully concluded. 11% normal overbreak observed.",
        ),
        # Day 0 on P-104 (Hard Rock Socketing)
        PileDailyProgress(
            dpr_id=dpr_0.id,
            pile_id=pile_p104.id,
            depth_drilled_today_m=8.4,
            cumulative_depth_m=22.8,
            empty_bore_depth_m=3.3,
            rock_socket_depth_today_m=1.2,
            strata_type=StrataType.HARD_ROCK,
            casing_depth_m=6.0,
            casing_type=CasingType.TEMPORARY,
            cage_sections_lowered=0,
            cage_weight_kg_today=0.0,
            concrete_volume_planned_m3=0.0,
            concrete_volume_actual_m3=0.0,
            slump_mm=None,
            bentonite_density_g_cc=1.08,
            remarks="Rock auger with bullet teeth penetrating hard charnockite bed.",
        ),
    ]
    session.add_all(pile_progresses)

    # Equipment Logs
    eq_logs = [
        # Day -1 Equipment Usage
        EquipmentLog(
            dpr_id=dpr_m1.id,
            equipment_id=eq_rig1.id,
            opening_hours=1420.5,
            closing_hours=1429.5,
            working_hours=9.0,
            breakdown_hours=0.0,
            idle_hours=1.0,
            fuel_liters=216.0,
        ),
        EquipmentLog(
            dpr_id=dpr_m1.id,
            equipment_id=eq_crane1.id,
            opening_hours=2105.0,
            closing_hours=2113.5,
            working_hours=8.5,
            breakdown_hours=0.0,
            idle_hours=1.5,
            fuel_liters=102.0,
        ),
        EquipmentLog(
            dpr_id=dpr_m1.id,
            equipment_id=eq_dg1.id,
            opening_hours=3250.0,
            closing_hours=3260.0,
            working_hours=10.0,
            breakdown_hours=0.0,
            idle_hours=0.0,
            fuel_liters=95.0,
        ),
        # Day 0 Equipment Usage
        EquipmentLog(
            dpr_id=dpr_0.id,
            equipment_id=eq_rig1.id,
            opening_hours=1429.5,
            closing_hours=1435.5,
            working_hours=6.0,
            breakdown_hours=0.0,
            idle_hours=0.5,
            fuel_liters=144.0,
        ),
        EquipmentLog(
            dpr_id=dpr_0.id,
            equipment_id=eq_crane1.id,
            opening_hours=2113.5,
            closing_hours=2118.5,
            working_hours=5.0,
            breakdown_hours=0.0,
            idle_hours=1.0,
            fuel_liters=60.0,
        ),
    ]
    session.add_all(eq_logs)

    # Material Consumptions
    mats = [
        MaterialConsumption(
            dpr_id=dpr_m1.id,
            material_name="OPC 53 Grade Cement",
            unit="MT",
            quantity_used=8.2,
            remarks="M35 tremie mix for pile P-102",
        ),
        MaterialConsumption(
            dpr_id=dpr_m1.id,
            material_name="Fe550D TMT Steel Rebar",
            unit="MT",
            quantity_used=4.87,
            remarks="Pile cage reinforcement P-102 & P-103",
        ),
        MaterialConsumption(
            dpr_id=dpr_m1.id,
            material_name="Bentonite Powder",
            unit="Bags",
            quantity_used=25.0,
            remarks="Borehole stabilization & desanding mud cycle",
        ),
    ]
    session.add_all(mats)

    # Quality Test Reports
    tests = [
        TestReport(
            dpr_id=dpr_m1.id,
            test_type=TestType.SLUMP_TEST,
            result_value="190",
            result_unit="mm",
            pass_fail=PassFail.PASS,
            remarks="Tremie concrete workability compliant with IS:2911 specifications (180-200mm).",
        ),
        TestReport(
            dpr_id=dpr_m1.id,
            test_type=TestType.BENTONITE_TEST,
            result_value="1.08",
            result_unit="g/cc",
            pass_fail=PassFail.PASS,
            remarks="Mud density prior to concreting within 1.05-1.10 g/cc limit.",
        ),
        TestReport(
            dpr_id=dpr_m1.id,
            test_type=TestType.CUBE_CASTING,
            result_value="6 Cubes (M35)",
            result_unit="Sets",
            pass_fail=PassFail.PASS,
            remarks="3 cubes for 7-day compressive test, 3 cubes for 28-day compliance.",
        ),
    ]
    session.add_all(tests)

    # -------------------------------------------------------------------------
    # 10. SHIFT FUEL REGISTERS (Past 5 Days)
    # -------------------------------------------------------------------------
    fuel_regs = [
        # Day -4
        SiteFuelRegister(
            site_id=site1.id,
            dpr_id=dpr_m4.id,
            date=d_m4,
            shift=ShiftType.DAY,
            opening_stock_liters=3800.0,
            received_bowser_liters=3500.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=1180.0,
            closing_dip_stock_liters=6112.0,
            variance_liters=-8.0,
            recorded_by=user_se_vadakara.id,
        ),
        SiteFuelRegister(
            site_id=site1.id,
            date=d_m4,
            shift=ShiftType.NIGHT,
            opening_stock_liters=6112.0,
            received_bowser_liters=0.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=450.0,
            closing_dip_stock_liters=5665.0,
            variance_liters=+3.0,
            recorded_by=user_sup_vadakara.id,
        ),
        # Day -3
        SiteFuelRegister(
            site_id=site1.id,
            dpr_id=dpr_m3.id,
            date=d_m3,
            shift=ShiftType.DAY,
            opening_stock_liters=5665.0,
            received_bowser_liters=0.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=1240.0,
            closing_dip_stock_liters=4420.0,
            variance_liters=-5.0,
            recorded_by=user_se_vadakara.id,
        ),
        SiteFuelRegister(
            site_id=site1.id,
            date=d_m3,
            shift=ShiftType.NIGHT,
            opening_stock_liters=4420.0,
            received_bowser_liters=0.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=380.0,
            closing_dip_stock_liters=4042.0,
            variance_liters=+2.0,
            recorded_by=user_sup_vadakara.id,
        ),
        # Day -2
        SiteFuelRegister(
            site_id=site1.id,
            dpr_id=dpr_m2.id,
            date=d_m2,
            shift=ShiftType.DAY,
            opening_stock_liters=4042.0,
            received_bowser_liters=3000.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=1310.0,
            closing_dip_stock_liters=5726.0,
            variance_liters=-6.0,
            recorded_by=user_se_vadakara.id,
        ),
        # Day -1 (Yesterday: Day Shift Normal, Night Shift with Flagged Fuel Anomaly)
        SiteFuelRegister(
            site_id=site1.id,
            dpr_id=dpr_m1.id,
            date=d_m1,
            shift=ShiftType.DAY,
            opening_stock_liters=5726.0,
            received_bowser_liters=0.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=1285.0,
            closing_dip_stock_liters=4435.0,
            variance_liters=-6.0,
            recorded_by=user_se_vadakara.id,
        ),
        SiteFuelRegister(
            site_id=site1.id,
            date=d_m1,
            shift=ShiftType.NIGHT,
            opening_stock_liters=4435.0,
            received_bowser_liters=0.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=750.0,
            closing_dip_stock_liters=3616.5,
            # Flagged Anomaly: -68.5L variance triggers fuel audit warning (>50L tolerance)
            variance_liters=-68.5,
            recorded_by=user_sup_vadakara.id,
        ),
        # Day 0 (Today)
        SiteFuelRegister(
            site_id=site1.id,
            dpr_id=dpr_0.id,
            date=d_0,
            shift=ShiftType.DAY,
            opening_stock_liters=3616.5,
            received_bowser_liters=2000.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=620.0,
            closing_dip_stock_liters=4992.5,
            variance_liters=-4.0,
            recorded_by=user_se_vadakara.id,
        ),
    ]
    session.add_all(fuel_regs)

    # -------------------------------------------------------------------------
    # 11. EXECUTIVE BRIEFS (Historical & Today)
    # -------------------------------------------------------------------------
    brief_data_yesterday = {
        "summary": {
            "piling_linear_meters": 11.5,
            "wells_sunk_cm": 0.0,
            "total_manpower_headcount": 54,
            "diesel_consumed_liters": 2035.0,
            "petty_cash_spent": 16100.0,
            "active_delays_count": 1,
            "critical_alerts_count": 1,
        },
        "metric_cards": [
            {
                "title": "Piling Depth",
                "value": 11.5,
                "target": 12.0,
                "unit": "m",
                "trend": "UP",
                "status": "NORMAL",
            },
            {
                "title": "Diesel Consumed",
                "value": 2035.0,
                "unit": "L",
                "status": "CRITICAL",
            },
            {
                "title": "Total Manpower",
                "value": 54,
                "unit": "workers",
                "status": "NORMAL",
            },
            {
                "title": "Petty Cash Spent",
                "value": 16100.0,
                "unit": "₹",
                "status": "ATTENTION",
            },
        ],
        "piling": {
            "completed_piles": 5,
            "drilled_meters": 11.5,
            "concrete_poured_m3": 20.9,
            "active_rigs": 2,
            "delays": [
                "Heavy coastal monsoon squall delayed transit mixer dispatch by 1.5 hrs. Tremie seal maintained under constant supervision."
            ],
        },
        "fuel": {
            "total_opening_stock": 5726.0,
            "total_received": 0.0,
            "total_issued": 2035.0,
            "total_closing_dip": 3616.5,
            "total_variance": -74.5,
            "registers_count": 2,
        },
        "petty_cash": {
            "total_spent_today": 16100.0,
            "out_of_pocket_spent_today": 4100.0,
            "pending_reimbursements_total": 8950.0,
            "wallets": [
                {
                    "wallet_id": wallet1.id,
                    "site_id": site1.id,
                    "current_balance": 26450.0,
                    "is_deficit": False,
                    "deficit_amount": 0.0,
                }
            ],
        },
        "attendance": {
            "direct_workers_present": 12,
            "direct_hours_total": 108.0,
            "direct_ot_hours_total": 3.0,
            "gang_headcount_total": 42,
            "gang_ot_hours_total": 44.0,
            "total_manpower_headcount": 54,
            "gangs_by_trade": {
                "PILING_GANG": 16,
                "STEEL_BENDING": 12,
                "CONCRETING": 14,
            },
        },
    }

    alerts_yesterday = [
        {
            "type": "FUEL_VARIANCE",
            "severity": "CRITICAL",
            "message": "Site #1 (NIGHT Shift) fuel variance of -68.5L exceeds tolerance threshold.",
            "site_id": site1.id,
            "variance_liters": -68.5,
        },
        {
            "type": "SITE_DELAY",
            "severity": "WARNING",
            "message": "Heavy monsoon squall delayed transit mixer dispatch by 1.5 hrs.",
        },
        {
            "type": "ATTENDANCE_ANOMALY",
            "severity": "WARNING",
            "message": "Worker #3 (Manoj Singh) attendance anomaly: Check-in GPS location 2.6 km outside site geofence boundary",
            "worker_id": 3,
            "site_id": site1.id,
        },
        {
            "type": "PETTY_CASH_ANOMALY",
            "severity": "WARNING",
            "message": "Expense #10 flagged: Duplicate Invoice #INV-HYD-9921 detected; already submitted on tranche #07",
            "transaction_id": 10,
        },
    ]

    ai_review_yesterday = {
        "provider_used": "claude-3-5-sonnet",
        "verified_at": (now_utc - timedelta(days=1)).isoformat(),
        "summary": "Vadakara package operations achieved critical milestone with P-102 casting (20.9 m3 M35 concrete). Immediate fuel variance of -68.5L on night shift requires physical bowser calibration inspection. Manpower muster is at full capacity (54 total headcount) with excellent steel fabrication throughput.",
        "risk_level": "MEDIUM",
        "action_items": [
            "Dispatch mechanical supervisor to calibrate diesel storage flow meter and dipstick.",
            "Confirm NABL 7-day cube testing schedule for P-102 casting.",
            "Review duplicate tool invoice voucher #INV-HYD-9921 with site engineer.",
        ],
    }

    brief_yesterday = ExecutiveBrief(
        operational_date=d_m1,
        generated_at=now_utc - timedelta(days=1),
        delivery_status=DeliveryStatus.SENT,
        delivery_channel=DeliveryChannel.BOTH,
        brief_data=brief_data_yesterday,
        alerts=alerts_yesterday,
        ai_review=ai_review_yesterday,
    )

    # Today's Brief
    brief_data_today = {
        "summary": {
            "piling_linear_meters": 8.4,
            "wells_sunk_cm": 0.0,
            "total_manpower_headcount": 54,
            "diesel_consumed_liters": 620.0,
            "petty_cash_spent": 2150.0,
            "active_delays_count": 0,
            "critical_alerts_count": 0,
        },
        "metric_cards": [
            {
                "title": "Piling Depth",
                "value": 8.4,
                "target": 10.0,
                "unit": "m",
                "trend": "UP",
                "status": "NORMAL",
            },
            {
                "title": "Diesel Consumed",
                "value": 620.0,
                "unit": "L",
                "status": "NORMAL",
            },
            {
                "title": "Total Manpower",
                "value": 54,
                "unit": "workers",
                "status": "NORMAL",
            },
            {
                "title": "Petty Cash Spent",
                "value": 2150.0,
                "unit": "₹",
                "status": "NORMAL",
            },
        ],
        "piling": {
            "completed_piles": 5,
            "drilled_meters": 8.4,
            "concrete_poured_m3": 0.0,
            "active_rigs": 2,
            "delays": [],
        },
        "fuel": {
            "total_opening_stock": 3616.5,
            "total_received": 2000.0,
            "total_issued": 620.0,
            "total_closing_dip": 4992.5,
            "total_variance": -4.0,
            "registers_count": 1,
        },
        "petty_cash": {
            "total_spent_today": 2150.0,
            "out_of_pocket_spent_today": 0.0,
            "pending_reimbursements_total": 8950.0,
            "wallets": [
                {
                    "wallet_id": wallet1.id,
                    "site_id": site1.id,
                    "current_balance": 24300.0,
                    "is_deficit": False,
                    "deficit_amount": 0.0,
                }
            ],
        },
        "attendance": {
            "direct_workers_present": 12,
            "direct_hours_total": 54.0,
            "direct_ot_hours_total": 0.0,
            "gang_headcount_total": 42,
            "gang_ot_hours_total": 0.0,
            "total_manpower_headcount": 54,
            "gangs_by_trade": {
                "PILING_GANG": 16,
                "STEEL_BENDING": 12,
                "CONCRETING": 14,
            },
        },
    }

    ai_review_today = {
        "provider_used": "gemini-1.5-pro",
        "verified_at": now_utc.isoformat(),
        "summary": "Vadakara site operations running smoothly on Day shift. Bauer rig advancing rock socketing on P-104 (22.8m). Diesel stock replenished with 2,000L bowser delivery; variance within normal range (-4.0L). Zero unresolved site stoppages.",
        "risk_level": "LOW",
        "action_items": [
            "Proceed with reinforcement cage lowering on P-103 once QA inspection signoff is recorded.",
            "Maintain mud desanding cycle for deep charnockite rock strata.",
        ],
    }

    brief_today = ExecutiveBrief(
        operational_date=d_0,
        generated_at=now_utc,
        delivery_status=DeliveryStatus.SENT,
        delivery_channel=DeliveryChannel.BOTH,
        brief_data=brief_data_today,
        alerts=[],
        ai_review=ai_review_today,
    )

    session.add_all([brief_yesterday, brief_today])

    await session.commit()
    logger.info("Successfully populated database with realistic ODIPKS Infra operations data!")

    return {
        "users": len(users),
        "projects": 2,
        "sites": 2,
        "piles": len(piles),
        "equipments": len(equipments),
        "inventory_items": len(inventories),
        "workers": len(workers),
        "attendance_records": len(att_records),
        "gang_records": len(gang_records),
        "dprs": len(dprs),
        "fuel_registers": len(fuel_regs),
        "petty_cash_transactions": len(transactions),
        "executive_briefs": 2,
    }
