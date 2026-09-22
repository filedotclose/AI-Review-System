import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.tasks.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def format_whatsapp_brief_message(brief_data: Dict[str, Any]) -> str:
    """Format an executive WhatsApp markdown message with construction KPIs."""
    op_date = brief_data.get("operational_date", "Today")
    piling = brief_data.get("piling", {})
    fuel = brief_data.get("fuel", {})
    petty_cash = brief_data.get("petty_cash", {})
    attendance = brief_data.get("attendance", {})
    alerts = brief_data.get("alerts", [])
    ai_review = brief_data.get("ai_review", {})

    drilled_m = piling.get("drilled_meters", 0.0)
    piles_done = piling.get("completed_piles", 0)
    concrete_m3 = piling.get("concrete_poured_m3", 0.0)
    active_rigs = piling.get("active_rigs", 0)
    delays = piling.get("delays", [])

    fuel_issued = fuel.get("total_issued", 0.0)
    fuel_closing = fuel.get("total_closing_dip", 0.0)
    fuel_var = fuel.get("total_variance", 0.0)

    cash_spent = petty_cash.get("total_spent", 0.0)
    cash_oop = petty_cash.get("out_of_pocket_spent", 0.0)
    cash_deficit = petty_cash.get("deficit_amount", 0.0)

    workers_direct = attendance.get("direct_workers_present", 0)
    workers_gang = attendance.get("gang_headcount", 0)
    total_workers = attendance.get("total_headcount", workers_direct + workers_gang)
    direct_hours = attendance.get("direct_hours", 0.0)

    lines = [
        f"🏗️ *ODIPKS EXECUTIVE DAILY BRIEF* — {op_date}",
        "═══════════════════════════",
        "",
        "📊 *PILING & SITE PROGRESS*",
        f"• Drilled Depth: *{drilled_m:.1f} m*",
        f"• Completed Piles: *{piles_done}*",
        f"• Concrete Poured: *{concrete_m3:.1f} m³*",
        f"• Active Rigs: *{active_rigs}*",
        "",
        "⛽ *FUEL & EQUIPMENT DISPATCH*",
        f"• Diesel Issued: *{fuel_issued:.1f} L*",
        f"• Closing Dip Stock: *{fuel_closing:.1f} L*",
        f"• Fuel Dip Variance: *{fuel_var:+.1f} L*",
        "",
        "💰 *PETTY CASH & SITE WALLET*",
        f"• Total Spent: *₹{cash_spent:,.2f}*",
        f"• Out-of-Pocket: *₹{cash_oop:,.2f}*",
        f"• Net Deficit Status: *{'₹' + f'{cash_deficit:,.2f}' if cash_deficit > 0 else 'Balanced (₹0)'}*",
        "",
        "👷 *MANPOWER & ATTENDANCE*",
        f"• Total Headcount: *{total_workers}*",
        f"  - Direct Workers: {workers_direct} ({direct_hours:.1f} hrs)",
        f"  - Subcontractor Gang: {workers_gang}",
        "",
    ]

    # AI Review summary (if available)
    if ai_review:
        ai_summary = ai_review.get("executive_summary", "")
        risk = ai_review.get("risk_assessment", "")
        score = ai_review.get("productivity_score", "")
        if ai_summary:
            lines.append("🤖 *AI REVIEW SUMMARY*")
            lines.append(f"• Risk: *{risk}* | Productivity: *{score}/100*")
            lines.append(f"• {ai_summary}")
            lines.append("")

    # Delays section
    if delays:
        lines.append("⏳ *ACTIVE DELAYS*")
        for d in delays[:3]:
            lines.append(f"• {d}")
        lines.append("")

    # Alerts section
    if alerts:
        lines.append(f"⚠️ *ALERTS & ANOMALIES ({len(alerts)})*")
        for alert in alerts[:4]:
            sev = alert.get("severity", "WARNING")
            msg = alert.get("message", "Attention required")
            icon = "🔴" if sev == "CRITICAL" else "🟡"
            lines.append(f"{icon} [{sev}] {msg}")
        lines.append("")
    else:
        lines.append("✅ *ALERTS*: No operational anomalies recorded.")
        lines.append("")

    lines.append(f"_Generated automatically by ODIPKS Construction OS at {datetime.now(timezone.utc).strftime('%H:%M UTC')}_")
    return "\n".join(lines)


def format_email_brief_html(brief_data: Dict[str, Any]) -> str:
    """Format an executive HTML email report with complete scorecard."""
    op_date = brief_data.get("operational_date", "Today")
    piling = brief_data.get("piling", {})
    fuel = brief_data.get("fuel", {})
    petty_cash = brief_data.get("petty_cash", {})
    attendance = brief_data.get("attendance", {})
    alerts = brief_data.get("alerts", [])
    summary = brief_data.get("summary", {})
    ai_review = brief_data.get("ai_review", {})

    drilled_m = piling.get("drilled_meters", 0.0)
    piles_done = piling.get("completed_piles", 0)
    concrete_m3 = piling.get("concrete_poured_m3", 0.0)
    active_rigs = piling.get("active_rigs", 0)

    fuel_issued = fuel.get("total_issued", 0.0)
    fuel_closing = fuel.get("total_closing_dip", 0.0)
    fuel_var = fuel.get("total_variance", 0.0)

    cash_spent = petty_cash.get("total_spent", 0.0)
    cash_oop = petty_cash.get("out_of_pocket_spent", 0.0)
    cash_deficit = petty_cash.get("deficit_amount", 0.0)

    total_workers = attendance.get("total_headcount", 0)
    direct_workers = attendance.get("direct_workers_present", 0)
    gang_workers = attendance.get("gang_headcount", 0)

    alerts_html = ""
    if alerts:
        alerts_items = "".join(
            f'<li style="margin-bottom:6px; color:{"#b91c1c" if a.get("severity")=="CRITICAL" else "#b45309"};">'
            f'<strong>[{a.get("severity", "WARNING")}]</strong> {a.get("message", "")}'
            f'</li>'
            for a in alerts
        )
        alerts_html = f"""
        <div style="background-color:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:16px; margin-bottom:24px;">
            <h3 style="margin-top:0; color:#991b1b; font-size:16px;">Operational Alerts & Anomalies</h3>
            <ul style="margin-bottom:0; padding-left:20px;">{alerts_items}</ul>
        </div>
        """
    else:
        alerts_html = """
        <div style="background-color:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:12px; margin-bottom:24px; color:#166534;">
            <strong>All systems normal:</strong> No critical anomalies or delays detected.
        </div>
        """

    # AI Review section for email
    ai_review_html = ""
    if ai_review:
        ai_summary = ai_review.get("executive_summary", "")
        risk = ai_review.get("risk_assessment", "N/A")
        score = ai_review.get("productivity_score", "N/A")
        recommendations = ai_review.get("recommendations", [])
        safety = ai_review.get("safety_concerns", [])

        risk_color = {"LOW": "#166534", "MEDIUM": "#b45309", "HIGH": "#b91c1c", "CRITICAL": "#7f1d1d"}.get(risk, "#475569")

        rec_items = "".join(f'<li style="margin-bottom:4px;">{r}</li>' for r in recommendations[:5])
        safety_items = "".join(f'<li style="margin-bottom:4px; color:#b91c1c;">{s}</li>' for s in safety[:3])

        ai_review_html = f"""
        <div style="background-color:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:16px; margin-bottom:24px;">
            <h3 style="margin-top:0; color:#1e40af; font-size:16px;">🤖 AI-Powered Review</h3>
            <p style="margin:0 0 8px 0;">{ai_summary}</p>
            <div style="display:flex; gap:24px; margin-bottom:12px;">
                <div><strong>Risk:</strong> <span style="color:{risk_color}; font-weight:bold;">{risk}</span></div>
                <div><strong>Productivity:</strong> <span style="font-weight:bold;">{score}/100</span></div>
            </div>
            {"<h4 style='margin:8px 0 4px 0; font-size:14px;'>Recommendations:</h4><ul style='margin:0; padding-left:20px;'>" + rec_items + "</ul>" if rec_items else ""}
            {"<h4 style='margin:8px 0 4px 0; font-size:14px; color:#b91c1c;'>Safety Concerns:</h4><ul style='margin:0; padding-left:20px;'>" + safety_items + "</ul>" if safety_items else ""}
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>ODIPKS Executive Daily Brief - {op_date}</title>
</head>
<body style="font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color:#f8fafc; margin:0; padding:24px; color:#1e293b;">
    <div style="max-width:680px; margin:0 auto; background-color:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
        <div style="background-color:#0f172a; color:#ffffff; padding:24px 32px;">
            <h1 style="margin:0; font-size:22px; letter-spacing:-0.5px;">ODIPKS Construction OS</h1>
            <p style="margin:4px 0 0 0; color:#94a3b8; font-size:14px;">Executive Daily Operational Brief &bull; {op_date}</p>
        </div>
        <div style="padding:32px;">
            {alerts_html}
            {ai_review_html}
            
            <h2 style="font-size:16px; text-transform:uppercase; letter-spacing:0.5px; color:#64748b; margin-top:0;">Key Performance Scorecard</h2>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:24px;">
                <div style="background-color:#f1f5f9; padding:16px; border-radius:8px;">
                    <div style="font-size:12px; color:#64748b; text-transform:uppercase;">Drilled Depth</div>
                    <div style="font-size:24px; font-weight:bold; color:#0f172a; margin-top:4px;">{drilled_m:.1f} m</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">Completed Piles: {piles_done} | Active Rigs: {active_rigs}</div>
                </div>
                <div style="background-color:#f1f5f9; padding:16px; border-radius:8px;">
                    <div style="font-size:12px; color:#64748b; text-transform:uppercase;">Diesel Consumed</div>
                    <div style="font-size:24px; font-weight:bold; color:#0f172a; margin-top:4px;">{fuel_issued:.1f} L</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">Closing Dip: {fuel_closing:.1f} L | Var: {fuel_var:+.1f} L</div>
                </div>
                <div style="background-color:#f1f5f9; padding:16px; border-radius:8px;">
                    <div style="font-size:12px; color:#64748b; text-transform:uppercase;">Total Manpower</div>
                    <div style="font-size:24px; font-weight:bold; color:#0f172a; margin-top:4px;">{total_workers}</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">Direct: {direct_workers} | Subcontractor: {gang_workers}</div>
                </div>
                <div style="background-color:#f1f5f9; padding:16px; border-radius:8px;">
                    <div style="font-size:12px; color:#64748b; text-transform:uppercase;">Petty Cash Spent</div>
                    <div style="font-size:24px; font-weight:bold; color:#0f172a; margin-top:4px;">₹{cash_spent:,.2f}</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">Out-of-Pocket: ₹{cash_oop:,.2f} | Deficit: ₹{cash_deficit:,.2f}</div>
                </div>
            </div>

            <h2 style="font-size:16px; text-transform:uppercase; letter-spacing:0.5px; color:#64748b;">Concrete & Piling Details</h2>
            <table style="width:100%; border-collapse:collapse; margin-bottom:24px; font-size:14px;">
                <tr style="border-bottom:1px solid #e2e8f0; text-align:left;">
                    <th style="padding:8px 0; color:#64748b;">Metric</th>
                    <th style="padding:8px 0; text-align:right; color:#64748b;">Value</th>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:8px 0;">Total Drilled Today</td>
                    <td style="padding:8px 0; text-align:right; font-weight:600;">{drilled_m:.2f} m</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:8px 0;">Concrete Poured Today</td>
                    <td style="padding:8px 0; text-align:right; font-weight:600;">{concrete_m3:.2f} m³</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:8px 0;">Piles Completed Today</td>
                    <td style="padding:8px 0; text-align:right; font-weight:600;">{piles_done}</td>
                </tr>
            </table>

            <div style="border-top:1px solid #e2e8f0; padding-top:20px; font-size:12px; color:#94a3b8; text-align:center;">
                ODIPKS AI-Native Construction Operating System &bull; Heavy Civil Infrastructure Automated Briefing
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html


def _run_async(coro):
    """Helper to run async code from sync Celery tasks."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


async def _deliver_whatsapp_async(
    brief_id: int,
    phone_numbers: List[str],
    brief_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Async WhatsApp delivery using the real WhatsApp service."""
    from app.services.whatsapp_service import get_whatsapp_service
    wa_service = get_whatsapp_service()

    formatted_text = format_whatsapp_brief_message(brief_data)
    now_iso = datetime.now(timezone.utc).isoformat()

    if wa_service._is_configured() and getattr(settings, "ENABLE_REAL_NOTIFICATIONS", True):
        logger.info(f"Sending real WhatsApp notifications to {len(phone_numbers)} recipients")
        results = await wa_service.send_brief_notification(phone_numbers, brief_data)
        statuses = [r.model_dump() for r in results]
        return {
            "status": "DELIVERED" if all(r.status == "DELIVERED" for r in results) else "PARTIAL",
            "channel": "WHATSAPP",
            "brief_id": brief_id,
            "recipients": phone_numbers,
            "formatted_text": formatted_text,
            "timestamp": now_iso,
            "provider": "META_CLOUD_API",
            "message_count": len(phone_numbers),
            "delivery_results": statuses,
        }
    else:
        logger.info("WhatsApp not configured — using simulation mode")
        return {
            "status": "DELIVERED",
            "channel": "WHATSAPP",
            "brief_id": brief_id,
            "recipients": phone_numbers,
            "formatted_text": formatted_text,
            "timestamp": now_iso,
            "provider": "SIMULATED_WHATSAPP_API",
            "message_count": len(phone_numbers),
        }


async def _deliver_email_async(
    brief_id: int,
    emails: List[str],
    brief_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Async Email delivery using the real Email service."""
    from app.services.email_service import get_email_service
    email_service = get_email_service()

    op_date = brief_data.get("operational_date", "Today")
    html_body = format_email_brief_html(brief_data)
    subject = f"ODIPKS Construction OS — Executive Daily Brief ({op_date})"
    now_iso = datetime.now(timezone.utc).isoformat()

    if email_service._is_configured() and getattr(settings, "ENABLE_REAL_NOTIFICATIONS", True):
        logger.info(f"Sending real email to {len(emails)} recipients")
        result = await email_service.send_html_email(
            recipients=emails,
            subject=subject,
            html_body=html_body,
        )
        return {
            "status": result.status,
            "channel": "EMAIL",
            "brief_id": brief_id,
            "recipients": emails,
            "subject": subject,
            "html_body": html_body,
            "timestamp": now_iso,
            "provider": result.provider,
            "message_count": len(emails),
            "message_id": result.message_id,
            "error": result.error,
        }
    else:
        logger.info("Email not configured — using simulation mode")
        return {
            "status": "DELIVERED",
            "channel": "EMAIL",
            "brief_id": brief_id,
            "recipients": emails,
            "subject": subject,
            "html_body": html_body,
            "timestamp": now_iso,
            "provider": "SIMULATED_SMTP",
            "message_count": len(emails),
        }


@celery_app.task(name="app.tasks.notification_tasks.simulate_whatsapp_delivery")
def simulate_whatsapp_delivery(
    brief_id: int,
    phone_numbers: List[str],
    brief_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    WhatsApp delivery task — backward-compatible function name.
    Routes to real WhatsApp Cloud API when configured, otherwise simulates.
    """
    return _run_async(_deliver_whatsapp_async(brief_id, phone_numbers, brief_data))


@celery_app.task(name="app.tasks.notification_tasks.simulate_email_delivery")
def simulate_email_delivery(
    brief_id: int,
    emails: List[str],
    brief_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Email delivery task — backward-compatible function name.
    Routes to real SMTP when configured, otherwise simulates.
    """
    return _run_async(_deliver_email_async(brief_id, emails, brief_data))
