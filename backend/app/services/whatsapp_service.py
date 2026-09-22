import logging
import httpx
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.schemas.notification import WhatsAppDeliveryResult

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None
    logger.warning("twilio not installed")

class WhatsAppService:
    """Async service for sending WhatsApp messages via Meta Cloud API or Twilio fallback."""

    def __init__(self):
        """Initialize the WhatsApp service with settings."""
        pass

    def _is_configured(self) -> bool:
        """Check if WhatsApp Cloud API config is valid."""
        token = getattr(settings, "WHATSAPP_API_TOKEN", "")
        phone_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        if not token or token == 'fake_token' or not phone_id:
            return False
        return True

    def _is_twilio_configured(self) -> bool:
        """Check if Twilio fallback is configured."""
        sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        if not sid or sid == 'fake_sid' or not token or token == 'fake_token':
            return False
        return True

    async def _send_via_twilio(self, phone_number: str, text: str) -> WhatsAppDeliveryResult:
        """Fallback method to send WhatsApp message via Twilio."""
        if not TwilioClient or not self._is_twilio_configured():
             return WhatsAppDeliveryResult(
                status="FAILED",
                phone_number=phone_number,
                provider="TWILIO",
                error="Twilio not configured or installed"
            )
        try:
            client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
            to_number = f"whatsapp:{phone_number}"
            
            def send():
                return client.messages.create(body=text, from_=from_number, to=to_number)
                
            message = await asyncio.to_thread(send)
            
            return WhatsAppDeliveryResult(
                status="DELIVERED",
                phone_number=phone_number,
                provider="TWILIO",
                message_id=message.sid
            )
        except Exception as e:
            logger.error(f"Failed to send Twilio WhatsApp message: {str(e)}")
            return WhatsAppDeliveryResult(
                status="FAILED",
                phone_number=phone_number,
                provider="TWILIO",
                error=str(e)
            )

    async def send_template_message(self, phone_number: str, template_name: str, template_params: List[str], language: str = 'en') -> WhatsAppDeliveryResult:
        """Send a WhatsApp template message."""
        if not self._is_configured():
            logger.info("WhatsApp service not configured. Returning simulated result.")
            return WhatsAppDeliveryResult(
                status="SIMULATED",
                phone_number=phone_number,
                provider="SIMULATED",
                message_id="sim_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
            )
        
        api_version = getattr(settings, "WHATSAPP_API_VERSION", "v21.0")
        url = f"https://graph.facebook.com/{api_version}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        parameters = [{"type": "text", "text": param} for param in template_params]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                
                return WhatsAppDeliveryResult(
                    status="DELIVERED",
                    phone_number=phone_number,
                    provider="META_CLOUD_API",
                    message_id=message_id
                )
        except httpx.HTTPStatusError as e:
            error_msg = e.response.text
            logger.error(f"WhatsApp API HTTP error: {error_msg}")
            
            if getattr(settings, "USE_TWILIO_FALLBACK", False):
                 fallback_text = f"Template: {template_name}\nParams: {', '.join(template_params)}"
                 return await self._send_via_twilio(phone_number, fallback_text)
                 
            return WhatsAppDeliveryResult(
                status="FAILED",
                phone_number=phone_number,
                provider="META_CLOUD_API",
                error=error_msg
            )
        except Exception as e:
            logger.error(f"WhatsApp API error: {str(e)}")
            return WhatsAppDeliveryResult(
                status="FAILED",
                phone_number=phone_number,
                provider="META_CLOUD_API",
                error=str(e)
            )

    async def send_text_message(self, phone_number: str, text: str) -> WhatsAppDeliveryResult:
        """Send a standard text message (24h session window)."""
        if not self._is_configured():
            logger.info("WhatsApp service not configured. Returning simulated result.")
            return WhatsAppDeliveryResult(
                status="SIMULATED",
                phone_number=phone_number,
                provider="SIMULATED",
                message_id="sim_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
            )
            
        api_version = getattr(settings, "WHATSAPP_API_VERSION", "v21.0")
        url = f"https://graph.facebook.com/{api_version}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": text
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                
                return WhatsAppDeliveryResult(
                    status="DELIVERED",
                    phone_number=phone_number,
                    provider="META_CLOUD_API",
                    message_id=message_id
                )
        except Exception as e:
            logger.error(f"WhatsApp API text error: {str(e)}")
            if getattr(settings, "USE_TWILIO_FALLBACK", False):
                 return await self._send_via_twilio(phone_number, text)
                 
            return WhatsAppDeliveryResult(
                status="FAILED",
                phone_number=phone_number,
                provider="META_CLOUD_API",
                error=str(e)
            )

    async def send_brief_notification(self, phone_numbers: List[str], brief_data: dict, report_url: Optional[str] = None) -> List[WhatsAppDeliveryResult]:
        """Send a brief notification to multiple phone numbers."""
        results = []
        client_name = brief_data.get("client_name", "Client")
        site_name = brief_data.get("site_name", "Site")
        
        template_name = getattr(settings, "WHATSAPP_TEMPLATE_NAME", "construction_report_ready")
        template_params = [client_name, site_name]
        if report_url:
            template_params.append(report_url)
            
        for phone in phone_numbers:
            result = await self.send_template_message(phone, template_name, template_params)
            results.append(result)
            
        return results

_whatsapp_service_instance = None

def get_whatsapp_service() -> WhatsAppService:
    """Get the singleton instance of the WhatsAppService."""
    global _whatsapp_service_instance
    if _whatsapp_service_instance is None:
        _whatsapp_service_instance = WhatsAppService()
    return _whatsapp_service_instance
