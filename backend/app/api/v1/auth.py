from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.base import get_db
from app.models.user import User, UserRole
from app.core.security import (
    verify_password,
    verify_pin,
    get_password_hash,
    get_pin_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    oauth2_scheme,
)
from app.schemas.auth import (
    LoginRequest,
    PinLoginRequest,
    PasswordLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    UserCreate,
)

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user via phone or email, with password or 4-6 digit PIN.
    Returns access and refresh JWT tokens.
    """
    if not login_data.phone and not login_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either phone or email must be provided",
        )

    user: Optional[User] = None
    if login_data.phone:
        stmt = select(User).where(User.phone == login_data.phone)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
    elif login_data.email:
        stmt = select(User).where(User.email == login_data.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Validate credential
    authenticated = False
    secret = login_data.password or login_data.pin
    if secret:
        if user.pin_hash and verify_pin(secret, user.pin_hash):
            authenticated = True
        elif user.password_hash and verify_password(secret, user.password_hash):
            authenticated = True
    elif login_data.pin and user.pin_hash and verify_pin(login_data.pin, user.pin_hash):
        authenticated = True
    elif login_data.password and user.password_hash and verify_password(login_data.password, user.password_hash):
        authenticated = True

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "phone": user.phone}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )

@router.post("/pin-login", response_model=TokenResponse)
async def pin_login(
    payload: PinLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Specialized PIN login for field workers using phone and 4-6 digit PIN.
    """
    stmt = select(User).where(User.phone == payload.phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.pin_hash or not verify_pin(payload.pin, user.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or PIN",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "phone": user.phone}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )

@router.post("/email-login", response_model=TokenResponse)
async def email_login(
    payload: PasswordLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Email and password login for management.
    """
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "email": user.email}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: Optional[RefreshTokenRequest] = None,
    token_auth: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Renew access token using a valid refresh token.
    Token can be provided in JSON body or Authorization header.
    """
    token = (body.refresh_token if body and body.refresh_token else None) or token_auth
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token must be provided in body or Authorization header",
        )

    payload = verify_token(token, expected_type="refresh")
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject format",
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "phone": user.phone}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve authenticated user profile.
    """
    return current_user

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Explicitly terminate user session on this device.
    """
    return {"message": "Session terminated successfully", "user_id": current_user.id}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user (for administrative / seeding / test purposes).
    """
    stmt = select(User).where(User.phone == user_in.phone)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already registered",
        )

    if user_in.email:
        stmt = select(User).where(User.email == user_in.email)
        existing_email = (await db.execute(stmt)).scalar_one_or_none()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered",
            )

    pwd_hash = get_password_hash(user_in.password) if user_in.password else None
    pin_hash = get_pin_hash(user_in.pin) if user_in.pin else None

    new_user = User(
        name=user_in.name,
        phone=user_in.phone,
        email=user_in.email,
        password_hash=pwd_hash,
        pin_hash=pin_hash,
        role=user_in.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
