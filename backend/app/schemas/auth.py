from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.user import UserRole

class LoginRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None

class PinLoginRequest(BaseModel):
    phone: str
    pin: str

class PasswordLoginRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None
    exp: Optional[int] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: UserRole
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    role: UserRole = UserRole.SITE_ENGINEER
