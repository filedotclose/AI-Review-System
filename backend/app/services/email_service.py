import asyncio
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict

from app.core.config import settings
from app.schemas.notification import EmailDeliveryResult

logger = logging.getLogger(__name__)

class EmailService:
    """Async service for sending emails via SMTP."""
    
    def __init__(self):
        """Initialize the email service with settings."""
        pass
        
    def _is_configured(self) -> bool:
        """Check if real SMTP config is set."""
        if not settings.SMTP_PASSWORD or settings.SMTP_PASSWORD in ('test', 'secret', 'test-password', 'fake_password', ''):
            return False
        if not settings.SMTP_HOST or settings.SMTP_HOST.endswith(".test") or settings.SMTP_HOST in ("smtp.test", "localhost", "127.0.0.1"):
            return False
        return True

    def _create_mime_message(self, recipients: List[str], subject: str, html_body: str, attachments: Optional[List[Dict]] = None) -> MIMEMultipart:
        """Create a MIME multipart message."""
        sender = settings.SMTP_USER if settings.SMTP_USER and "@" in settings.SMTP_USER else settings.SMTP_FROM_EMAIL
        msg = MIMEMultipart()
        msg['From'] = f"ODIPKS Construction OS <{sender}>"
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        if settings.SMTP_FROM_EMAIL and settings.SMTP_FROM_EMAIL != sender:
            msg['Reply-To'] = settings.SMTP_FROM_EMAIL

        msg.attach(MIMEText(html_body, 'html'))

        if attachments:
            for attachment in attachments:
                filename = attachment.get("filename")
                content = attachment.get("content")
                if filename and content:
                    part = MIMEApplication(content, Name=filename)
                    part['Content-Disposition'] = f'attachment; filename="{filename}"'
                    msg.attach(part)
        return msg

    def _send_sync(self, msg: MIMEMultipart, recipients: List[str]) -> None:
        """Synchronous SMTP send."""
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            sender = settings.SMTP_USER if settings.SMTP_USER and "@" in settings.SMTP_USER else settings.SMTP_FROM_EMAIL
            server.sendmail(sender, recipients, msg.as_string())

    async def send_html_email(self, recipients: List[str], subject: str, html_body: str, attachments: Optional[List[Dict]] = None) -> EmailDeliveryResult:
        """Send an HTML email asynchronously."""
        if not self._is_configured():
            logger.info("Email service not configured. Returning simulated result.")
            return EmailDeliveryResult(
                status="SIMULATED",
                recipients=recipients,
                provider="SIMULATED",
                message_id="sim_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
            )
        
        try:
            msg = self._create_mime_message(recipients, subject, html_body, attachments)
            await asyncio.to_thread(self._send_sync, msg, recipients)
            
            return EmailDeliveryResult(
                status="DELIVERED",
                recipients=recipients,
                provider="GMAIL_SMTP"
            )
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return EmailDeliveryResult(
                status="FAILED",
                recipients=recipients,
                provider="GMAIL_SMTP",
                error=str(e)
            )

_email_service_instance = None

def get_email_service() -> EmailService:
    """Get the singleton instance of the EmailService."""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
