import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
_backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    CELERY_TIMEZONE: str = "Asia/Kolkata"
    CELERY_ENABLE_UTC: bool = False
    
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str
    
    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    WHATSAPP_API_URL: str
    WHATSAPP_API_TOKEN: str
    WHATSAPP_OWNER_PHONE: str
    
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    USE_TWILIO_FALLBACK: bool = True
    
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    
    PIN_MAX_ATTEMPTS: int = 5
    PIN_LOCKOUT_MINUTES: int = 30

    # AI Provider Configuration
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    AI_PROVIDER: str = "gemini"              # "gemini" | "groq" | "none"
    AI_MODEL: str = "gemini-2.0-flash"       # Model identifier for primary provider
    AI_TEMPERATURE: float = 0.1
    AI_MAX_TOKENS: int = 4096
    AI_TIMEOUT_SECONDS: int = 30
    AI_FALLBACK_TO_RULES: bool = True        # If AI call fails, use rule-based fallback

    # WhatsApp Cloud API (additional fields for Meta direct)
    WHATSAPP_PHONE_NUMBER_ID: str = ""       # Meta Phone Number ID
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""   # WhatsApp Business Account ID
    WHATSAPP_TEMPLATE_NAME: str = "construction_report_ready"
    WHATSAPP_API_VERSION: str = "v21.0"

    # Notification Control
    ENABLE_REAL_NOTIFICATIONS: bool = True   # Master switch for real dispatch

    # Anomaly thresholds
    FUEL_WARNING_THRESHOLD: float = 0.03
    FUEL_CRITICAL_THRESHOLD: float = 0.15
    EQUIPMENT_FUEL_BURN_MULTIPLIER: float = 1.25
    BINDING_WIRE_BENCHMARK_KG_PER_MT: float = 10.0
    ELECTRODES_BENCHMARK_PKTS_PER_SPLICE: int = 3
    CONSUMABLE_VARIANCE_THRESHOLD: float = 0.15
    CONCRETE_OVERBREAK_THRESHOLD: float = 0.20
    WELL_TILT_TOLERANCE: float = 0.01
    WELL_SHIFT_TOLERANCE_MM: int = 150
    ATTENDANCE_DPR_DISCREPANCY_THRESHOLD: float = 0.10

    model_config = SettingsConfigDict(env_file=[".env", _backend_env, _root_env], env_file_encoding='utf-8', extra='ignore')

settings = Settings()
