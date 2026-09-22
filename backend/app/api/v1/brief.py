from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.executive_brief import ExecutiveBrief, DeliveryStatus, DeliveryChannel
from app.schemas.brief import (
    ExecutiveBriefResponse,
    BriefGenerateRequest,
    OperationalSummary,
    MetricCard,
)
from app.tasks.brief_tasks import generate_morning_brief
from app.tasks.notification_tasks import simulate_whatsapp_delivery, simulate_email_delivery
from app.core.config import settings

router = APIRouter()


def serialize_brief_entity(brief: ExecutiveBrief) -> ExecutiveBriefResponse:
    """Transform ExecutiveBrief SQLAlchemy model into ExecutiveBriefResponse Pydantic schema."""
    bd = brief.brief_data or {}

    summary_raw = bd.get("summary")
    summary = None
    if isinstance(summary_raw, dict):
        summary = OperationalSummary(**summary_raw)

    cards_raw = bd.get("metric_cards")
    metric_cards = None
    if isinstance(cards_raw, list):
        metric_cards = []
        for c in cards_raw:
            if isinstance(c, dict):
                metric_cards.append(MetricCard(**c))
            elif isinstance(c, MetricCard):
                metric_cards.append(c)

    raw_alerts = brief.alerts or bd.get("alerts") or []
    alerts = list(raw_alerts) if isinstance(raw_alerts, list) else []

    # Extract AI review data
    ai_review_data = getattr(brief, "ai_review", None) or bd.get("ai_review")
    ai_provider = None
    if isinstance(ai_review_data, dict):
        ai_provider = ai_review_data.get("provider_used")

    now_utc = datetime.now(timezone.utc)
    return ExecutiveBriefResponse(
        id=brief.id,
        operational_date=brief.operational_date,
        generated_at=brief.generated_at or now_utc,
        delivery_status=brief.delivery_status or DeliveryStatus.SENT,
        delivery_channel=brief.delivery_channel or DeliveryChannel.BOTH,
        brief_data=bd,
        alerts=alerts,
        summary=summary,
        metric_cards=metric_cards,
        ai_review=ai_review_data,
        ai_provider=ai_provider,
        created_at=brief.created_at or now_utc,
    )


@router.get("/daily", response_model=ExecutiveBriefResponse)
@router.get("/today", response_model=ExecutiveBriefResponse, include_in_schema=False)
@router.get("", response_model=ExecutiveBriefResponse)
@router.get("/", response_model=ExecutiveBriefResponse, include_in_schema=False)
async def get_daily_brief(
    date_filter: Optional[date] = Query(None, alias="date", description="Target operational date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve executive daily brief for a given operational date, or the latest available brief.
    """
    if date_filter:
        stmt = select(ExecutiveBrief).where(ExecutiveBrief.operational_date == date_filter)
        res = await db.execute(stmt)
        brief = res.scalars().first()
        if not brief:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Executive brief not found for date {date_filter}.",
            )
    else:
        stmt = select(ExecutiveBrief).order_by(
            ExecutiveBrief.operational_date.desc(),
            ExecutiveBrief.generated_at.desc(),
        )
        res = await db.execute(stmt)
        brief = res.scalars().first()
        if not brief:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No executive briefs found in the system.",
            )

    return serialize_brief_entity(brief)


@router.get("/history", response_model=List[ExecutiveBriefResponse])
async def get_brief_history(
    limit: int = Query(30, ge=1, le=100, description="Max number of past briefs to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve historical executive briefs ordered by operational date descending.
    """
    stmt = (
        select(ExecutiveBrief)
        .order_by(ExecutiveBrief.operational_date.desc(), ExecutiveBrief.generated_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    briefs = res.scalars().all()
    return [serialize_brief_entity(b) for b in briefs]


@router.post("/generate", response_model=ExecutiveBriefResponse, status_code=status.HTTP_200_OK)
async def trigger_brief_generation(
    payload: Optional[BriefGenerateRequest] = None,
    target_date: Optional[date] = Query(None, alias="date", description="Operational date if not in body"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger executive brief generation for a given operational date.
    Aggregates multi-table operational data across DPR, Fuel, Petty Cash, and Attendance,
    persists the ExecutiveBrief record, and dispatches simulated notifications.
    """
    op_date = payload.operational_date if payload and payload.operational_date else (target_date or date.today())
    delivery_channel = payload.delivery_channel if payload and payload.delivery_channel else DeliveryChannel.BOTH

    # Run aggregation engine with current DB session
    result = await generate_morning_brief(
        operational_date=op_date,
        session=db,
        trigger_notifications=True,
    )

    # Fetch fresh ExecutiveBrief entity from DB
    stmt = select(ExecutiveBrief).where(ExecutiveBrief.id == result["id"])
    res = await db.execute(stmt)
    brief = res.scalars().first()

    if not brief:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generated executive brief.",
        )

    return serialize_brief_entity(brief)


@router.post("/{brief_id}/deliver", response_model=Dict[str, Any])
async def resend_brief_notifications(
    brief_id: int,
    channel: DeliveryChannel = Query(DeliveryChannel.BOTH, description="Delivery channel to trigger"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulate re-delivery of an existing executive brief via WhatsApp and/or Email.
    """
    stmt = select(ExecutiveBrief).where(ExecutiveBrief.id == brief_id)
    res = await db.execute(stmt)
    brief = res.scalars().first()
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Executive brief #{brief_id} not found.",
        )

    phone_numbers = [getattr(settings, "WHATSAPP_OWNER_PHONE", "+919876543210")]
    emails = [getattr(settings, "SMTP_FROM_EMAIL", "management@odipks.test")]

    deliveries = {}
    if channel in (DeliveryChannel.WHATSAPP, DeliveryChannel.BOTH):
        deliveries["whatsapp"] = simulate_whatsapp_delivery(brief.id, phone_numbers, brief.brief_data or {})
    if channel in (DeliveryChannel.EMAIL, DeliveryChannel.BOTH):
        deliveries["email"] = simulate_email_delivery(brief.id, emails, brief.brief_data or {})

    brief.delivery_status = DeliveryStatus.SENT
    brief.delivery_channel = channel
    await db.commit()
    await db.refresh(brief)

    return {
        "brief_id": brief.id,
        "operational_date": brief.operational_date,
        "delivery_status": brief.delivery_status,
        "channel": channel,
        "deliveries": deliveries,
    }


@router.post("/{brief_id}/ai-review", response_model=Dict[str, Any])
async def trigger_ai_review(
    brief_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run AI verification on an existing executive brief.
    Returns structured AI insights including risk assessment, recommendations,
    safety concerns, and productivity score.
    """
    stmt = select(ExecutiveBrief).where(ExecutiveBrief.id == brief_id)
    res = await db.execute(stmt)
    brief = res.scalars().first()
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Executive brief #{brief_id} not found.",
        )

    from app.services.ai_service import get_ai_service
    import time

    ai_service = get_ai_service()
    brief_data = brief.brief_data or {}

    start_time = time.time()
    ai_result = await ai_service.verify_daily_brief(brief_data)
    latency_ms = int((time.time() - start_time) * 1000)

    ai_review_dict = ai_result.model_dump()

    # Persist AI review to the brief record
    brief.ai_review = ai_review_dict
    await db.commit()
    await db.refresh(brief)

    provider = settings.AI_PROVIDER if ai_service._is_configured() else "rule_based"
    model_name = settings.AI_MODEL if ai_service._is_configured() else "deterministic"

    return {
        "brief_id": brief.id,
        "operational_date": str(brief.operational_date),
        "review": ai_review_dict,
        "provider_used": provider,
        "model_name": model_name,
        "latency_ms": latency_ms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
