import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import (
    get_password_hash,
    get_pin_hash,
    create_access_token,
    create_refresh_token,
)


@pytest.fixture
async def seeded_user(db_session: AsyncSession) -> User:
    """Pre-seed user with both password and PIN."""
    user = User(
        name="Pilot Supervisor",
        phone="+919876500001",
        email="supervisor@pilot.test",
        pin_hash=get_pin_hash("4321"),
        password_hash=get_password_hash("SupervisorSecret123!"),
        role=UserRole.SUPERVISOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    """Pre-seed inactive user."""
    user = User(
        name="Inactive Worker",
        phone="+919876500099",
        email="inactive@pilot.test",
        pin_hash=get_pin_hash("9999"),
        password_hash=get_password_hash("InactivePass123!"),
        role=UserRole.SITE_ENGINEER,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ==============================================================================
# /api/v1/auth/login Stress Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_login_empty_body(client: AsyncClient):
    """Verify login returns 400 Bad Request when neither phone nor email is supplied."""
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 400
    assert "Either phone or email must be provided" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_missing_credentials(client: AsyncClient, seeded_user: User):
    """Verify login returns 401 when phone is provided without PIN or password."""
    response = await client.post("/api/v1/auth/login", json={"phone": seeded_user.phone})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_nonexistent_user(client: AsyncClient):
    """Verify login returns 401 when phone does not exist."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"phone": "+919000000000", "pin": "1234"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_wrong_pin(client: AsyncClient, seeded_user: User):
    """Verify login returns 401 when incorrect PIN is provided."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"phone": seeded_user.phone, "pin": "0000"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient, seeded_user: User):
    """Verify login returns 401 when incorrect password is provided."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_inactive_user(client: AsyncClient, inactive_user: User):
    """Verify login returns 403 Forbidden for inactive users."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"phone": inactive_user.phone, "pin": "9999"},
    )
    assert response.status_code == 403
    assert "User account is inactive" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_pin_success(client: AsyncClient, seeded_user: User):
    """Verify successful login via phone and PIN returns valid JWT tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"phone": seeded_user.phone, "pin": "4321"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_password_success(client: AsyncClient, seeded_user: User):
    """Verify successful login via email and password returns valid JWT tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "SupervisorSecret123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


# ==============================================================================
# /api/v1/auth/pin-login Stress Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_pin_login_missing_fields(client: AsyncClient):
    """Verify pin-login returns 422 Unprocessable Entity when required fields are missing."""
    # Missing pin
    res1 = await client.post("/api/v1/auth/pin-login", json={"phone": "+919876500001"})
    assert res1.status_code == 422

    # Missing phone
    res2 = await client.post("/api/v1/auth/pin-login", json={"pin": "4321"})
    assert res2.status_code == 422

    # Empty payload
    res3 = await client.post("/api/v1/auth/pin-login", json={})
    assert res3.status_code == 422


@pytest.mark.integration
@pytest.mark.anyio
async def test_pin_login_invalid_and_adversarial_pins(client: AsyncClient, seeded_user: User):
    """Verify pin-login handles wrong, empty, alphanumeric, and malicious PINs without crashing."""
    adversarial_pins = [
        "0000",
        "",
        "abcd",
        "123456789012345678901234567890",
        "' OR '1'='1",
        "<script>alert(1)</script>",
        "🎉🔥🚀",
    ]
    for bad_pin in adversarial_pins:
        res = await client.post(
            "/api/v1/auth/pin-login",
            json={"phone": seeded_user.phone, "pin": bad_pin},
        )
        assert res.status_code == 401, f"Expected 401 for PIN: {bad_pin}, got {res.status_code}"
        assert res.json()["detail"] == "Invalid phone number or PIN"


@pytest.mark.integration
@pytest.mark.anyio
async def test_pin_login_success(client: AsyncClient, seeded_user: User):
    """Verify pin-login succeeds with valid phone and PIN."""
    res = await client.post(
        "/api/v1/auth/pin-login",
        json={"phone": seeded_user.phone, "pin": "4321"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


# ==============================================================================
# /api/v1/auth/email-login Stress Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_email_login_missing_fields(client: AsyncClient):
    """Verify email-login returns 422 on missing fields."""
    res1 = await client.post("/api/v1/auth/email-login", json={"email": "test@test.com"})
    assert res1.status_code == 422

    res2 = await client.post("/api/v1/auth/email-login", json={"password": "secret"})
    assert res2.status_code == 422


@pytest.mark.integration
@pytest.mark.anyio
async def test_email_login_wrong_credentials(client: AsyncClient, seeded_user: User):
    """Verify email-login returns 401 on incorrect credentials."""
    # Unknown email
    res1 = await client.post(
        "/api/v1/auth/email-login",
        json={"email": "nobody@nowhere.com", "password": "some_password"},
    )
    assert res1.status_code == 401

    # Wrong password
    res2 = await client.post(
        "/api/v1/auth/email-login",
        json={"email": seeded_user.email, "password": "WrongPassword123!"},
    )
    assert res2.status_code == 401


# ==============================================================================
# /api/v1/auth/refresh Stress Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_refresh_token_no_input(client: AsyncClient):
    """Verify /refresh returns 400 Bad Request when no token is provided."""
    res = await client.post("/api/v1/auth/refresh")
    assert res.status_code == 400
    assert "Refresh token must be provided" in res.json()["detail"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_refresh_token_empty_json(client: AsyncClient):
    """Verify /refresh returns 422 when empty JSON body is sent."""
    res = await client.post("/api/v1/auth/refresh", json={})
    assert res.status_code == 422


@pytest.mark.integration
@pytest.mark.anyio
async def test_refresh_token_invalid_string(client: AsyncClient):
    """Verify /refresh returns 401 on malformed token."""
    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "malformed.jwt.token"},
    )
    assert res.status_code == 401


@pytest.mark.integration
@pytest.mark.anyio
async def test_refresh_token_with_access_token(client: AsyncClient, seeded_user: User):
    """Verify that providing an ACCESS token to /refresh is rejected with 401."""
    access_tok = create_access_token(data={"sub": str(seeded_user.id), "role": seeded_user.role.value})
    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_tok},
    )
    assert res.status_code == 401
    assert "Invalid token type: expected refresh" in res.json()["detail"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_refresh_token_success(client: AsyncClient, seeded_user: User):
    """Verify valid refresh token issues new tokens."""
    ref_tok = create_refresh_token(data={"sub": str(seeded_user.id), "role": seeded_user.role.value})
    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": ref_tok},
    )
    assert res.status_code == 200
    data = response = res.json()
    assert "access_token" in data
    assert "refresh_token" in data


# ==============================================================================
# /api/v1/auth/me Profile Security Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_get_me_unauthorized(client: AsyncClient):
    """Verify GET /me returns 401 when no token is supplied."""
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["detail"] == "Not authenticated"


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_me_with_refresh_token(client: AsyncClient, seeded_user: User):
    """Verify GET /me rejects a refresh token with 401."""
    ref_tok = create_refresh_token(data={"sub": str(seeded_user.id), "role": seeded_user.role.value})
    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ref_tok}"},
    )
    assert res.status_code == 401
    assert "Invalid token type: expected access" in res.json()["detail"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_get_me_success_and_no_credential_leak(client: AsyncClient, seeded_user: User):
    """Verify GET /me returns profile and NEVER leaks password_hash or pin_hash."""
    access_tok = create_access_token(data={"sub": str(seeded_user.id), "role": seeded_user.role.value})
    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_tok}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == seeded_user.id
    assert data["phone"] == seeded_user.phone
    assert data["email"] == seeded_user.email
    assert "password_hash" not in data
    assert "pin_hash" not in data


# ==============================================================================
# /api/v1/auth/register Stress Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.anyio
async def test_register_duplicate_phone(client: AsyncClient, seeded_user: User):
    """Verify register returns 400 when attempting to register an existing phone."""
    payload = {
        "name": "Another User",
        "phone": seeded_user.phone,
        "email": "newunique@email.com",
        "password": "Password123!",
        "role": "SITE_ENGINEER",
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 400
    assert "Phone number is already registered" in res.json()["detail"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_register_duplicate_email(client: AsyncClient, seeded_user: User):
    """Verify register returns 400 when attempting to register an existing email."""
    payload = {
        "name": "Another User",
        "phone": "+919988776655",
        "email": seeded_user.email,
        "password": "Password123!",
        "role": "SITE_ENGINEER",
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 400
    assert "Email is already registered" in res.json()["detail"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_register_success(client: AsyncClient):
    """Verify valid registration creates user and returns 201."""
    payload = {
        "name": "New Junior Engineer",
        "phone": "+919111222333",
        "email": "junior.eng@odipks.test",
        "pin": "5678",
        "password": "JuniorPass123!",
        "role": "SITE_ENGINEER",
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["phone"] == payload["phone"]
    assert "password_hash" not in data
    assert "pin_hash" not in data
