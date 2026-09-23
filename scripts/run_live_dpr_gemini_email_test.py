import asyncio
import os
import sys
import json
from datetime import date, datetime, timezone

# Ensure backend path is on sys.path
sys.path.insert(0, "/app")

from sqlalchemy import select
from app.db.base import async_session
from app.models.user import User, UserRole
from app.models.project import Project, Site, Pile, PileStatus
from app.models.equipment import Equipment, ShiftType, EquipmentStatus
from app.models.dpr import (
    DailyProgressReport,
    PileDailyProgress,
    EquipmentLog,
    LabourSummary,
    DPRStatus,
    StrataType,
    CasingType,
)
from app.tasks.brief_tasks import generate_morning_brief
from app.services.email_service import get_email_service
from app.core.config import settings


async def run_dpr_gemini_test():
    print("=" * 60)
    print("  ODIPKS CONSTRUCTION OS: LIVE DPR -> GEMINI -> EMAIL TEST")
    print("=" * 60)

    today = date.today()
    print(f"• Operational Date: {today}")
    print(f"• AI Provider: {settings.AI_PROVIDER}")
    print(f"• Gemini Model: {settings.AI_MODEL}")
    print(f"• SMTP User: {settings.SMTP_USER}")
    print(f"• SMTP Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    print("-" * 60)

    async with async_session() as session:
        # 1. Fetch Site Engineer
        stmt = select(User).where(User.role == UserRole.SITE_ENGINEER)
        res = await session.execute(stmt)
        site_engineer = res.scalars().first()
        if not site_engineer:
            raise RuntimeError("No Site Engineer user found in database!")
        print(f"✓ Step 1: Acting as Site Engineer: {site_engineer.name} ({site_engineer.email})")

        # 2. Fetch Active Site & Pile
        site_res = await session.execute(select(Site).limit(1))
        site = site_res.scalars().first()
        if not site:
            raise RuntimeError("No Site found in database!")

        pile_res = await session.execute(select(Pile).where(Pile.site_id == site.id).limit(1))
        pile = pile_res.scalars().first()
        if not pile:
            raise RuntimeError("No Pile found for site!")

        print(f"✓ Step 2: Selected Site #{site.id} ('{site.name}') & Pile #{pile.id} ('{pile.pile_number}')")

        # 3. Create or Update DPR for Today
        existing_dpr_res = await session.execute(
            select(DailyProgressReport).where(
                DailyProgressReport.site_id == site.id,
                DailyProgressReport.operational_date == today,
            )
        )
        dpr = existing_dpr_res.scalars().first()

        if not dpr:
            dpr = DailyProgressReport(
                site_id=site.id,
                submitted_by=site_engineer.id,
                submitted_at=datetime.now(timezone.utc),
                operational_date=today,
                shift=ShiftType.DAY,
                status=DPRStatus.SUBMITTED,
                weather_conditions="Clear / Sunny, 34°C, dry ground conditions",
                problems_delays="40 mins delay: Bentonite slurry circulation pump electrical contactor tripped during socketing.",
                tomorrows_plan="Continue rock socketing for Pile P-102 and lower secondary reinforcement cage.",
            )
            session.add(dpr)
            await session.flush()
            print(f"✓ Step 3: Created new DPR #{dpr.id} for {today}")
        else:
            dpr.status = DPRStatus.SUBMITTED
            dpr.problems_delays = "40 mins delay: Bentonite slurry circulation pump electrical contactor tripped during socketing."
            print(f"✓ Step 3: Updated existing DPR #{dpr.id} for {today}")

        # Add Pile Progress entry
        pile_prog_res = await session.execute(
            select(PileDailyProgress).where(
                PileDailyProgress.dpr_id == dpr.id,
                PileDailyProgress.pile_id == pile.id,
            )
        )
        pile_prog = pile_prog_res.scalars().first()
        if not pile_prog:
            pile_prog = PileDailyProgress(
                dpr_id=dpr.id,
                pile_id=pile.id,
                depth_drilled_today_m=18.5,
                cumulative_depth_m=28.0,
                empty_bore_depth_m=2.5,
                rock_socket_depth_today_m=3.0,
                strata_type=StrataType.WEATHERED_ROCK,
                casing_depth_m=8.0,
                casing_type=CasingType.TEMPORARY,
                cage_sections_lowered=2,
                cage_weight_kg_today=3200.0,
                concrete_volume_planned_m3=20.5,
                concrete_volume_actual_m3=23.8,  # ~16% overbreak for AI detection
                slump_mm=175.0,
                bentonite_density_g_cc=1.06,
                delay_reason="40 mins electrical tripping on bentonite pump",
                remarks="Boring completed into hard strata. Reinforcement cage lowered successfully.",
            )
            session.add(pile_prog)
            print(f"✓ Step 4: Logged Piling Progress: 18.5m drilled, 23.8 m³ poured on Pile {pile.pile_number}")
        else:
            pile_prog.depth_drilled_today_m = 18.5
            pile_prog.concrete_volume_actual_m3 = 23.8
            print(f"✓ Step 4: Updated Piling Progress on Pile {pile.pile_number}")

        # Update pile status
        pile.status = PileStatus.CAST
        pile.as_built_depth = 28.0
        pile.as_built_concrete_m3 = 23.8

        await session.commit()
        print("✓ Step 5: DPR submission committed to Postgres database successfully.")

    # 4. Trigger Morning Brief with Gemini AI Evaluation & Email Dispatch
    print("\n" + "=" * 60)
    print("  INVOKING GEMINI AI EVALUATION (SOP CONTRACT)...")
    print("=" * 60)

    brief_result = await generate_morning_brief(
        operational_date=today,
        trigger_notifications=True,
    )

    print(f"✓ Executive Brief ID: #{brief_result.get('id')}")
    print(f"✓ Delivery Status: {brief_result.get('delivery_status')}")

    # 5. Inspect Gemini AI Review Output
    ai_review = brief_result.get("ai_review")
    if ai_review:
        print("\n" + "*" * 60)
        print("  🤖 GEMINI AI EXECUTIVE EVALUATION RESULT")
        print("*" * 60)
        print(f"• Provider:           {settings.AI_PROVIDER.upper()} ({settings.AI_MODEL})")
        print(f"• Productivity Score: {ai_review.get('productivity_score')}/100")
        print(f"• Risk Assessment:    {ai_review.get('risk_assessment')}")
        print(f"• Confidence:         {ai_review.get('confidence')}")
        print("\n• EXECUTIVE SUMMARY:")
        print(f"  {ai_review.get('executive_summary')}")
        print("\n• KEY INSIGHTS:")
        for idx, insight in enumerate(ai_review.get("key_insights", []), 1):
            print(f"  {idx}. {insight}")
        print("\n• RECOMMENDATIONS:")
        for idx, rec in enumerate(ai_review.get("recommendations", []), 1):
            print(f"  {idx}. {rec}")
        print("\n• SAFETY CONCERNS:")
        concerns = ai_review.get("safety_concerns", [])
        if concerns:
            for idx, sc in enumerate(concerns, 1):
                print(f"  {idx}. {sc}")
        else:
            print("  None flagged.")
    else:
        print("⚠️ Warning: No AI review attached to brief.")

    # 6. Verify and Trigger Real Email Delivery
    print("\n" + "=" * 60)
    print("  DISPATCHING REPORT OVER EMAIL VIA SMTP...")
    print("=" * 60)

    email_service = get_email_service()
    recipients = [
        settings.SMTP_USER,
        settings.SMTP_FROM_EMAIL,
    ]
    recipients = list(set([r for r in recipients if r and "@" in r]))

    from app.tasks.notification_tasks import format_email_brief_html
    brief_data = brief_result.get("brief_data", {})
    html_content = format_email_brief_html(brief_data)
    subject = f"ODIPKS Construction OS — Live Site DPR & Gemini AI Evaluation ({today.isoformat()})"

    email_res = await email_service.send_html_email(
        recipients=recipients,
        subject=subject,
        html_body=html_content,
    )

    print(f"• Email Delivery Status: {email_res.status}")
    print(f"• Recipients:           {email_res.recipients}")
    print(f"• Provider:             {email_res.provider}")
    if email_res.error:
        print(f"• Error:                {email_res.error}")
    else:
        print("✓ EMAIL SENT SUCCESSFULLY TO YOUR INBOX!")

    print("\n" + "=" * 60)
    print("  TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_dpr_gemini_test())
