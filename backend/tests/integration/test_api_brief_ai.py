import pytest
from datetime import date
from typing import Dict
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.executive_brief import ExecutiveBrief, DeliveryStatus, DeliveryChannel


@pytest.mark.anyio
async def test_trigger_ai_review_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    owner_headers: Dict[str, str],
):
    """Verify POST /api/v1/brief/{id}/ai-review executes AI review and persists result."""
    op_date = date(2026, 9, 21)
    brief = ExecutiveBrief(
        operational_date=op_date,
        delivery_status=DeliveryStatus.SENT,
        delivery_channel=DeliveryChannel.BOTH,
        brief_data={
            "operational_date": op_date.isoformat(),
            "piling": {"drilled_meters": 40.0, "completed_piles": 2},
            "fuel": {"total_issued": 800.0, "total_closing_dip": 4200.0},
            "petty_cash": {"total_spent": 5000.0, "deficit_amount": 0.0},
            "attendance": {"total_headcount": 25},
            "alerts": []
        },
        alerts=[]
    )
    db_session.add(brief)
    await db_session.commit()
    await db_session.refresh(brief)

    res = await client.post(f"/api/v1/brief/{brief.id}/ai-review", headers=owner_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["brief_id"] == brief.id
    assert "review" in data
    assert "executive_summary" in data["review"]
    assert "risk_assessment" in data["review"]
    assert "productivity_score" in data["review"]
    assert "recommendations" in data["review"]
    assert data["latency_ms"] >= 0


@pytest.mark.anyio
async def test_brief_ai_review_persisted_in_get_daily(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    owner_headers: Dict[str, str],
):
    """Verify GET /api/v1/brief/daily includes ai_review when populated."""
    op_date = date(2026, 9, 23)
    brief = ExecutiveBrief(
        operational_date=op_date,
        delivery_status=DeliveryStatus.SENT,
        delivery_channel=DeliveryChannel.BOTH,
        brief_data={"operational_date": op_date.isoformat()},
        alerts=[],
        ai_review={
            "executive_summary": "Piling on schedule with zero safety incidents.",
            "risk_assessment": "LOW",
            "productivity_score": 90,
            "recommendations": ["Advance Pier 5 casing"],
            "provider_used": "GEMINI"
        }
    )
    db_session.add(brief)
    await db_session.commit()

    res = await client.get(f"/api/v1/brief/daily?date={op_date.isoformat()}", headers=owner_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ai_review"] is not None
    assert data["ai_review"]["risk_assessment"] == "LOW"
    assert data["ai_review"]["productivity_score"] == 90
