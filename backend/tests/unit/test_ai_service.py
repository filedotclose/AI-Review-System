import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_service import AIVerificationService, AIProvider, get_ai_service
from app.schemas.ai_schemas import RiskLevel, AIReviewResult


@pytest.mark.anyio
async def test_ai_service_rule_based_fallback():
    """Verify AI service falls back gracefully to rule-based review when unconfigured."""
    service = AIVerificationService()
    # Force provider NONE or unconfigured
    service.gemini_api_key = ""
    service.groq_api_key = ""
    
    sample_brief = {
        "operational_date": "2026-09-22",
        "piling": {"completed_piles": 2, "drilled_meters": 25.0},
        "fuel": {"total_issued": 500.0, "total_closing_dip": 3000.0},
        "petty_cash": {"total_spent": 1000.0},
        "attendance": {"total_headcount": 15},
        "alerts": [
            {"severity": "WARNING", "message": "Fuel discrepancy noted."}
        ]
    }

    result = await service.verify_daily_brief(sample_brief)
    
    assert isinstance(result, AIReviewResult)
    assert result.risk_assessment in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert "alerts" in result.executive_summary or "Rule-based" in result.executive_summary
    assert result.productivity_score >= 0
    assert len(result.recommendations) > 0


@pytest.mark.anyio
async def test_ai_service_critical_alert_escalation():
    """Verify rule-based fallback escalates risk when many alerts are present."""
    service = AIVerificationService()
    service.gemini_api_key = ""
    
    sample_brief = {
        "operational_date": "2026-09-22",
        "alerts": [{"severity": "CRITICAL", "message": f"Alert {i}"} for i in range(7)]
    }

    result = await service.verify_daily_brief(sample_brief)
    assert result.risk_assessment == RiskLevel.CRITICAL


def test_ai_service_construction_prompt_generation():
    """Verify domain-specific construction context is embedded in the prompt."""
    service = AIVerificationService()
    prompt = service._build_construction_prompt({"test_key": "test_val"})
    
    assert "bored piling" in prompt.lower()
    assert "fuel dip" in prompt.lower()
    assert "petty cash" in prompt.lower()
    assert "test_key" in prompt


@pytest.mark.anyio
async def test_ai_service_gemini_mocked_success():
    """Verify Gemini API response is correctly validated against AIReviewResult schema."""
    service = AIVerificationService()
    service.provider = AIProvider.GEMINI
    service.gemini_api_key = "AIzaSyFakeKeyForTest"

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = (
        '{"executive_summary": "Piling operations progressed efficiently with 25m drilled.", '
        '"risk_assessment": "LOW", "key_insights": ["Good drill rate", "Zero downtime"], '
        '"recommendations": ["Maintain current rig RPM"], "anomaly_analysis": "None detected", '
        '"safety_concerns": [], "productivity_score": 85, "confidence": 0.95}'
    )

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        mock_client_cls.return_value = mock_client

        result = await service._verify_with_gemini({"sample": "data"})

        assert result.executive_summary == "Piling operations progressed efficiently with 25m drilled."
        assert result.risk_assessment == RiskLevel.LOW
        assert result.productivity_score == 85
        assert result.confidence == 0.95
        assert len(result.key_insights) == 2


def test_get_ai_service_singleton():
    """Verify get_ai_service helper returns AIVerificationService instance."""
    svc = get_ai_service()
    assert isinstance(svc, AIVerificationService)
