from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class EmailDeliveryResult(BaseModel):
    """Result of an email delivery attempt."""
    status: str
    channel: str = "EMAIL"
    message_id: Optional[str] = None
    recipients: List[str]
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: str

class WhatsAppDeliveryResult(BaseModel):
    """Result of a WhatsApp delivery attempt."""
    status: str
    channel: str = "WHATSAPP"
    message_id: Optional[str] = None
    phone_number: str
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: str
