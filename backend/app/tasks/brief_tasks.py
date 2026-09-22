import asyncio
import concurrent.futures
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, Union, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import async_session
from app.tasks.celery_app import celery_app
from app.tasks.notification_tasks import simulate_whatsapp_delivery, simulate_email_delivery
from app.models.executive_brief import ExecutiveBrief, DeliveryStatus, DeliveryChannel
from app.models.dpr import DailyProgressReport, PileDailyProgress, WellLog, EquipmentLog
from app.models.project import Pile, PileStatus
from app.models.equipment import SiteFuelRegister, Equipment, EquipmentType, EquipmentStatus
from app.models.petty_cash import (
    PettyCashTransaction,
    PettyCashWallet,
    TransactionType,
    ReimbursementStatus,
)
from app.models.attendance import (
    AttendanceRecord,
    GangAttendanceRecord,
    AttendanceStatus,
)


def _parse_operational_date(operational_date: Optional[Union[str, date]]) -> date:
    """Parse string or date into a datetime.date instance."""
    if operational_date is None:
        return date.today()
    if isinstance(operational_date, str):
        return date.fromisoformat(operational_date.strip())
    if isinstance(operational_date, datetime):
        return operational_date.date()
    return operational_date


def run_coro_sync(coro):
    """Execute an asynchronous coroutine synchronously, handling running event loops safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


async def _execute_generate_brief(
    session: AsyncSession,
    target_date: date,
    trigger_notifications: bool = True,
) -> Dict[str, Any]:
    """Internal async aggregator engine across DPR, Fuel, Petty Cash, and Attendance."""
    alerts: List[Dict[str, Any]] = []

    # =========================================================================
    # 1. Daily Progress Report & Piling Progress
    # =========================================================================
    dpr_stmt = select(DailyProgressReport).where(DailyProgressReport.operational_date == target_date)
    dpr_res = await session.execute(dpr_stmt)
    dprs = dpr_res.scalars().all()
    dpr_ids = [d.id for d in dprs]

    drilled_meters = 0.0
    concrete_volume_m3 = 0.0
    piles_completed = 0
    wells_sunk_cm = 0.0
    active_rigs = 0
    delays_list: List[str] = []

    # Collect DPR delays
    for d in dprs:
        if d.problems_delays and d.problems_delays.strip():
            delays_list.append(f"Site #{d.site_id} ({d.shift.value}): {d.problems_delays.strip()}")

    if dpr_ids:
        # Piling progress
        pile_stmt = select(PileDailyProgress).where(PileDailyProgress.dpr_id.in_(dpr_ids))
        pile_res = await session.execute(pile_stmt)
        pile_progresses = pile_res.scalars().all()

        drilled_meters = sum(p.depth_drilled_today_m or 0.0 for p in pile_progresses)
        concrete_volume_m3 = sum(p.concrete_volume_actual_m3 or 0.0 for p in pile_progresses)

        for p in pile_progresses:
            if p.delay_reason and p.delay_reason.strip():
                delays_list.append(f"Pile Progress #{p.id}: {p.delay_reason.strip()}")

        pile_ids = [p.pile_id for p in pile_progresses if p.pile_id is not None]
        if pile_ids:
            completed_piles_stmt = select(func.count(Pile.id)).where(
                Pile.id.in_(pile_ids),
                Pile.status.in_([PileStatus.COMPLETED, PileStatus.CAST]),
            )
            piles_completed = (await session.execute(completed_piles_stmt)).scalar() or 0

        # Well logs
        well_stmt = select(WellLog).where(WellLog.dpr_id.in_(dpr_ids))
        well_res = await session.execute(well_stmt)
        well_logs = well_res.scalars().all()
        wells_sunk_cm = sum(w.sinking_depth_today_cm or 0.0 for w in well_logs)

        # Equipment logs
        eq_stmt = select(EquipmentLog).where(EquipmentLog.dpr_id.in_(dpr_ids))
        eq_res = await session.execute(eq_stmt)
        eq_logs = eq_res.scalars().all()
        active_rigs = len(set(e.equipment_id for e in eq_logs if (e.working_hours or 0.0) > 0))

    # If no equipment logs in DPR, check operational rigs from inventory
    if active_rigs == 0:
        rig_stmt = select(func.count(Equipment.id)).where(
            Equipment.type == EquipmentType.RIG,
            Equipment.status == EquipmentStatus.OPERATIONAL,
        )
        active_rigs = (await session.execute(rig_stmt)).scalar() or 0

    # Add active delays to alerts
    for d_msg in delays_list:
        alerts.append({
            "type": "SITE_DELAY",
            "severity": "WARNING",
            "message": d_msg,
        })

    # =========================================================================
    # 2. Shift Fuel Register & Inventory
    # =========================================================================
    fuel_stmt = select(SiteFuelRegister).where(SiteFuelRegister.date == target_date)
    fuel_res = await session.execute(fuel_stmt)
    fuel_registers = fuel_res.scalars().all()

    total_opening = sum(f.opening_stock_liters or 0.0 for f in fuel_registers)
    total_received = sum((f.received_bowser_liters or 0.0) + (f.received_drums_liters or 0.0) for f in fuel_registers)
    total_issued = sum(f.total_issued_to_equipment_liters or 0.0 for f in fuel_registers)
    total_closing_dip = sum(f.closing_dip_stock_liters or 0.0 for f in fuel_registers)
    total_variance = sum(f.variance_liters or 0.0 for f in fuel_registers)

    for f in fuel_registers:
        var = f.variance_liters or 0.0
        total_in = (f.opening_stock_liters or 0.0) + (f.received_bowser_liters or 0.0) + (f.received_drums_liters or 0.0)
        var_pct = abs(var) / total_in if total_in > 0 else 0.0
        if abs(var) > 50.0 or var_pct > 0.03:
            alerts.append({
                "type": "FUEL_VARIANCE",
                "severity": "CRITICAL" if abs(var) > 100.0 or var_pct > 0.10 else "WARNING",
                "message": f"Site #{f.site_id} ({f.shift.value} Shift) fuel variance of {var:+.1f}L exceeds tolerance threshold.",
                "site_id": f.site_id,
                "variance_liters": var,
            })

    # =========================================================================
    # 3. Petty Cash Transactions & Site Wallets
    # =========================================================================
    tx_stmt = select(PettyCashTransaction).where(PettyCashTransaction.date == target_date)
    tx_res = await session.execute(tx_stmt)
    transactions = tx_res.scalars().all()

    total_spent = sum(t.amount or 0.0 for t in transactions if t.type == TransactionType.EXPENSE)
    out_of_pocket_spent = sum(
        t.amount or 0.0 for t in transactions if t.type == TransactionType.EXPENSE and t.is_out_of_pocket
    )

    pending_stmt = select(func.sum(PettyCashTransaction.amount)).where(
        PettyCashTransaction.reimbursement_status == ReimbursementStatus.DUE
    )
    pending_reimbursements = (await session.execute(pending_stmt)).scalar() or 0.0

    wallet_stmt = select(PettyCashWallet)
    wallet_res = await session.execute(wallet_stmt)
    wallets = wallet_res.scalars().all()

    wallets_data = []
    total_deficit = 0.0
    for w in wallets:
        bal = w.current_balance or 0.0
        is_deficit = bal < 0
        deficit_amt = abs(bal) if is_deficit else 0.0
        total_deficit += deficit_amt
        wallets_data.append({
            "wallet_id": w.id,
            "site_id": w.site_id,
            "current_balance": round(bal, 2),
            "is_deficit": is_deficit,
            "deficit_amount": round(deficit_amt, 2),
        })
        if is_deficit:
            alerts.append({
                "type": "WALLET_DEFICIT",
                "severity": "CRITICAL" if deficit_amt >= 25000.0 else "WARNING",
                "message": f"Site #{w.site_id} wallet in out-of-pocket deficit: ₹{deficit_amt:,.2f} (Permissive Cap: ₹50,000).",
                "site_id": w.site_id,
                "deficit_amount": deficit_amt,
            })

    for t in transactions:
        if t.anomaly_flag:
            alerts.append({
                "type": "PETTY_CASH_ANOMALY",
                "severity": "WARNING",
                "message": f"Expense #{t.id} flagged: {t.anomaly_reason or 'Expense anomaly'}",
                "transaction_id": t.id,
            })

    # =========================================================================
    # 4. Attendance & Gang Muster
    # =========================================================================
    att_stmt = select(AttendanceRecord).where(AttendanceRecord.date == target_date)
    att_res = await session.execute(att_stmt)
    attendance_records = att_res.scalars().all()

    direct_workers_present = sum(1 for a in attendance_records if a.status == AttendanceStatus.PRESENT)
    direct_hours = sum(a.hours_worked or 0.0 for a in attendance_records if a.status == AttendanceStatus.PRESENT)
    direct_ot_hours = sum(a.overtime_hours or 0.0 for a in attendance_records if a.status == AttendanceStatus.PRESENT)

    for a in attendance_records:
        if a.anomaly_flag:
            alerts.append({
                "type": "ATTENDANCE_ANOMALY",
                "severity": "WARNING",
                "message": f"Worker #{a.worker_id} attendance anomaly: {a.anomaly_reason or 'Geofence/Overtime issue'}",
                "worker_id": a.worker_id,
                "site_id": a.site_id,
            })

    gang_stmt = select(GangAttendanceRecord).where(GangAttendanceRecord.date == target_date)
    gang_res = await session.execute(gang_stmt)
    gang_records = gang_res.scalars().all()

    gang_headcount = sum(g.headcount_present or 0 for g in gang_records)
    gang_ot_hours = sum(g.total_ot_hours or 0.0 for g in gang_records)

    gangs_by_trade: Dict[str, int] = {}
    for g in gang_records:
        t_key = g.trade.value if hasattr(g.trade, "value") else str(g.trade)
        gangs_by_trade[t_key] = gangs_by_trade.get(t_key, 0) + (g.headcount_present or 0)

    total_headcount = direct_workers_present + gang_headcount

    # =========================================================================
    # 5. Build Operational Summary & Metric Cards
    # =========================================================================
    summary = {
        "piling_linear_meters": round(drilled_meters, 2),
        "wells_sunk_cm": round(wells_sunk_cm, 2),
        "total_manpower_headcount": total_headcount,
        "diesel_consumed_liters": round(total_issued, 2),
        "petty_cash_spent": round(total_spent, 2),
        "active_delays_count": len(delays_list),
        "critical_alerts_count": sum(1 for a in alerts if a.get("severity") == "CRITICAL"),
    }

    metric_cards = [
        {
            "title": "Piling Depth",
            "value": round(drilled_meters, 2),
            "target": 50.0,
            "unit": "m",
            "trend": "UP" if drilled_meters > 0 else "FLAT",
            "status": "NORMAL" if drilled_meters > 0 else "ATTENTION",
        },
        {
            "title": "Diesel Consumed",
            "value": round(total_issued, 2),
            "unit": "L",
            "status": "CRITICAL" if any(a.get("type") == "FUEL_VARIANCE" and a.get("severity") == "CRITICAL" for a in alerts) else "NORMAL",
        },
        {
            "title": "Total Manpower",
            "value": total_headcount,
            "unit": "workers",
            "status": "NORMAL" if total_headcount > 0 else "ATTENTION",
        },
        {
            "title": "Petty Cash Spent",
            "value": round(total_spent, 2),
            "unit": "₹",
            "status": "CRITICAL" if total_deficit > 0 else "NORMAL",
        },
    ]

    brief_data = {
        "operational_date": target_date.isoformat(),
        "piling": {
            "completed_piles": piles_completed,
            "drilled_meters": round(drilled_meters, 2),
            "concrete_poured_m3": round(concrete_volume_m3, 2),
            "active_rigs": active_rigs,
            "delays": delays_list,
        },
        "fuel": {
            "total_opening_stock": round(total_opening, 2),
            "total_received": round(total_received, 2),
            "total_issued": round(total_issued, 2),
            "total_closing_dip": round(total_closing_dip, 2),
            "total_variance": round(total_variance, 2),
            "registers_count": len(fuel_registers),
        },
        "petty_cash": {
            "total_spent": round(total_spent, 2),
            "out_of_pocket_spent": round(out_of_pocket_spent, 2),
            "pending_reimbursements": round(pending_reimbursements, 2),
            "wallets": wallets_data,
            "deficit_amount": round(total_deficit, 2),
            "has_deficit": total_deficit > 0,
        },
        "attendance": {
            "direct_workers_present": direct_workers_present,
            "direct_hours": round(direct_hours, 2),
            "direct_ot_hours": round(direct_ot_hours, 2),
            "gang_headcount": gang_headcount,
            "gang_ot_hours": round(gang_ot_hours, 2),
            "total_headcount": total_headcount,
            "gangs_by_trade": gangs_by_trade,
        },
        "summary": summary,
        "metric_cards": metric_cards,
        "alerts": alerts,
    }

    # =========================================================================
    # 6. AI Verification — Analyze brief_data with LLM or rule-based fallback
    # =========================================================================
    ai_review_data = None
    try:
        from app.services.ai_service import get_ai_service
        ai_service = get_ai_service()
        ai_result = await ai_service.verify_daily_brief(brief_data)
        ai_review_data = ai_result.model_dump()
        # Embed AI review into brief_data for notification templates
        brief_data["ai_review"] = ai_review_data
        # Add AI-generated safety concerns as alerts
        for concern in ai_result.safety_concerns:
            alerts.append({
                "type": "AI_SAFETY_CONCERN",
                "severity": "WARNING",
                "message": f"🤖 AI: {concern}",
            })
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"AI verification skipped: {e}")

    # =========================================================================
    # 7. Persist ExecutiveBrief Entity (with AI review)
    # =========================================================================
    brief_query = select(ExecutiveBrief).where(ExecutiveBrief.operational_date == target_date)
    existing_brief = (await session.execute(brief_query)).scalars().first()

    now_utc = datetime.now(timezone.utc)
    if existing_brief:
        existing_brief.generated_at = now_utc
        existing_brief.delivery_status = DeliveryStatus.SENT
        existing_brief.delivery_channel = DeliveryChannel.BOTH
        existing_brief.brief_data = brief_data
        existing_brief.alerts = alerts
        existing_brief.ai_review = ai_review_data
        brief_record = existing_brief
    else:
        brief_record = ExecutiveBrief(
            operational_date=target_date,
            generated_at=now_utc,
            delivery_status=DeliveryStatus.SENT,
            delivery_channel=DeliveryChannel.BOTH,
            brief_data=brief_data,
            alerts=alerts,
            ai_review=ai_review_data,
        )
        session.add(brief_record)

    await session.commit()
    await session.refresh(brief_record)

    # =========================================================================
    # 8. Trigger Notification Dispatch (Real or Simulated)
    # =========================================================================
    whatsapp_res = None
    email_res = None
    if trigger_notifications:
        phone_numbers = [getattr(settings, "WHATSAPP_OWNER_PHONE", "+919876543210")]
        emails = [getattr(settings, "SMTP_FROM_EMAIL", "management@odipks.test")]

        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2)
            result = sock.connect_ex(('127.0.0.1', 6379))
            sock.close()
            if result == 0:
                whatsapp_res = simulate_whatsapp_delivery.delay(brief_record.id, phone_numbers, brief_data)
                email_res = simulate_email_delivery.delay(brief_record.id, emails, brief_data)
            else:
                whatsapp_res = simulate_whatsapp_delivery(brief_record.id, phone_numbers, brief_data)
                email_res = simulate_email_delivery(brief_record.id, emails, brief_data)
        except Exception:
            whatsapp_res = simulate_whatsapp_delivery(brief_record.id, phone_numbers, brief_data)
            email_res = simulate_email_delivery(brief_record.id, emails, brief_data)

    return {
        "id": brief_record.id,
        "operational_date": brief_record.operational_date,
        "generated_at": brief_record.generated_at,
        "delivery_status": brief_record.delivery_status,
        "delivery_channel": brief_record.delivery_channel,
        "brief_data": brief_record.brief_data,
        "alerts": brief_record.alerts,
        "ai_review": brief_record.ai_review,
        "summary": summary,
        "metric_cards": metric_cards,
        "created_at": brief_record.created_at or now_utc,
        "whatsapp_delivery": whatsapp_res,
        "email_delivery": email_res,
    }


async def generate_morning_brief(
    operational_date: Optional[Union[str, date]] = None,
    session: Optional[AsyncSession] = None,
    trigger_notifications: bool = True,
) -> Dict[str, Any]:
    """
    Public asynchronous brief generation function.
    Can be invoked with an existing session or will create a new async_session.
    """
    target_date = _parse_operational_date(operational_date)

    if session is not None:
        return await _execute_generate_brief(session, target_date, trigger_notifications)
    else:
        async with async_session() as new_session:
            return await _execute_generate_brief(new_session, target_date, trigger_notifications)


@celery_app.task(name="app.tasks.brief_tasks.generate_morning_brief_task")
def generate_morning_brief_task(operational_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Celery task entrypoint executed daily at 8:00 AM IST.
    Wraps the async aggregator engine cleanly with run_coro_sync.
    """
    return run_coro_sync(generate_morning_brief(operational_date=operational_date))
