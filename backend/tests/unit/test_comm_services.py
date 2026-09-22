import pytest
from unittest.mock import patch, MagicMock
from app.services.email_service import EmailService, get_email_service
from app.services.whatsapp_service import WhatsAppService, get_whatsapp_service
from app.schemas.notification import EmailDeliveryResult, WhatsAppDeliveryResult


@pytest.mark.anyio
async def test_email_service_simulated_when_unconfigured():
    """Verify EmailService returns SIMULATED when SMTP is not configured."""
    svc = EmailService()
    result = await svc.send_html_email(
        recipients=["test@example.com"],
        subject="Test Report",
        html_body="<p>Test</p>"
    )
    assert isinstance(result, EmailDeliveryResult)
    assert result.status == "SIMULATED"
    assert "test@example.com" in result.recipients


def test_email_service_mime_construction():
    """Verify MIME structure and attachment handling."""
    svc = EmailService()
    msg = svc._create_mime_message(
        recipients=["client@test.com"],
        subject="Daily Brief",
        html_body="<h1>Daily Brief</h1>",
        attachments=[{"filename": "report.pdf", "content": b"%PDF-1.4 test content"}]
    )
    assert msg["To"] == "client@test.com"
    assert msg["Subject"] == "Daily Brief"
    # Payload contains text and attachment
    parts = msg.get_payload()
    assert len(parts) == 2


@pytest.mark.anyio
async def test_whatsapp_service_simulated_when_unconfigured():
    """Verify WhatsAppService returns SIMULATED when token or phone ID is not set."""
    svc = WhatsAppService()
    result = await svc.send_template_message(
        phone_number="+919876543210",
        template_name="construction_report_ready",
        template_params=["Client A", "Site 1", "https://reports.odipks.com/123"]
    )
    assert isinstance(result, WhatsAppDeliveryResult)
    assert result.status == "SIMULATED"
    assert result.phone_number == "+919876543210"


@pytest.mark.anyio
async def test_whatsapp_service_text_message_simulation():
    """Verify session text messages also return SIMULATED when unconfigured."""
    svc = WhatsAppService()
    result = await svc.send_text_message(
        phone_number="+919876543210",
        text="Concrete slump test: 140mm (Approved)"
    )
    assert result.status == "SIMULATED"
    assert result.channel == "WHATSAPP"


@pytest.mark.anyio
async def test_whatsapp_send_brief_notification():
    """Verify send_brief_notification iterates over recipients."""
    svc = WhatsAppService()
    results = await svc.send_brief_notification(
        phone_numbers=["+919876543210", "+919876543211"],
        brief_data={"client_name": "Metro Rail Corp", "site_name": "Pier 4"}
    )
    assert len(results) == 2
    assert all(r.status == "SIMULATED" for r in results)


def test_service_singletons():
    """Verify helper functions return service singletons."""
    assert isinstance(get_email_service(), EmailService)
    assert isinstance(get_whatsapp_service(), WhatsAppService)
