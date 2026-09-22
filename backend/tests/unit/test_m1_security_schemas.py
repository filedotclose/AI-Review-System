import pytest
from datetime import datetime, date, timedelta, timezone
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
    get_pin_hash,
    verify_pin,
    _sha256_fallback_hash,
    _sha256_fallback_verify,
)
from app.schemas.fuel import FuelRegisterCreate
from app.schemas.project import PileCreate
from app.schemas.petty_cash import ExpenseCreate
from app.schemas.attendance import GangMusterCreate
from app.models.equipment import ShiftType
from app.models.attendance import GangTrade
from app.models.petty_cash import ExpenseCategory


# ============================================================================
# 1. JWT Token Empirical Tests
# ============================================================================

def test_jwt_valid_creation_and_verification():
    """Verify that a freshly generated access token decodes correctly with valid claims."""
    token = create_access_token(data={"sub": "42", "role": "SITE_ENGINEER"})
    payload = verify_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["role"] == "SITE_ENGINEER"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_jwt_expired_token_rejection():
    """Verify that an expired token is unconditionally rejected with 401 Unauthorized."""
    # Create token expired 10 minutes ago
    expired_token = create_access_token(
        data={"sub": "42"},
        expires_delta=timedelta(minutes=-10),
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_token(expired_token, expected_type="access")
    assert exc_info.value.status_code == 401
    assert "credentials" in exc_info.value.detail.lower() or "expired" in exc_info.value.detail.lower()


def test_jwt_invalid_signature_rejection():
    """Verify that a token signed with an alien secret key is rejected with 401 Unauthorized."""
    try:
        import jwt
    except ImportError:
        from jose import jwt
    alien_payload = {
        "sub": "42",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    alien_token = jwt.encode(alien_payload, "completely-wrong-secret-key", algorithm="HS256")
    if isinstance(alien_token, bytes):
        alien_token = alien_token.decode("utf-8")

    with pytest.raises(HTTPException) as exc_info:
        verify_token(alien_token, expected_type="access")
    assert exc_info.value.status_code == 401


def test_jwt_malformed_tokens():
    """Verify that malformed, truncated, or random string tokens raise 401 Unauthorized."""
    malformed_inputs = [
        "not-a-token",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.payload",
        "",
        "Bearer something",
        "...",
    ]
    for bad_token in malformed_inputs:
        with pytest.raises(HTTPException) as exc_info:
            verify_token(bad_token, expected_type="access")
        assert exc_info.value.status_code == 401


def test_jwt_token_type_enforcement():
    """Verify that refresh tokens cannot be used as access tokens and vice-versa."""
    access_token = create_access_token(data={"sub": "1"})
    refresh_token = create_refresh_token(data={"sub": "1"})

    # Using refresh token where access token is required -> must fail
    with pytest.raises(HTTPException) as exc_info:
        verify_token(refresh_token, expected_type="access")
    assert exc_info.value.status_code == 401
    assert "Invalid token type" in exc_info.value.detail

    # Using access token where refresh token is required -> must fail
    with pytest.raises(HTTPException) as exc_info:
        verify_token(access_token, expected_type="refresh")
    assert exc_info.value.status_code == 401
    assert "Invalid token type" in exc_info.value.detail


# ============================================================================
# 2. Password & PIN Hashing Empirical Tests
# ============================================================================

def test_password_hashing_standard():
    """Verify standard password hashing and positive/negative verification."""
    password = "SuperSecretPassword#2026"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword#2026", hashed) is False


def test_password_hashing_empty_and_null():
    """Verify edge cases with empty and falsy password strings."""
    assert verify_password("", "") is False
    assert verify_password("somepassword", "") is False

    # Hashing an empty string
    empty_hash = get_password_hash("")
    assert verify_password("", empty_hash) is True
    assert verify_password("notempty", empty_hash) is False


def test_password_hashing_unicode():
    """Verify UTF-8 and unicode password handling (Hindi, emojis, accented chars)."""
    unicode_passwords = [
        "पायलट@2026_कंस्ट्रक्शन",
        "🔒ConstructionKey#999!",
        "café_naïve_bored_piling",
        "Строительство2026_Пилот",
    ]
    for pw in unicode_passwords:
        h = get_password_hash(pw)
        assert verify_password(pw, h) is True
        assert verify_password(pw + "_wrong", h) is False


def test_pin_hashing_and_verification():
    """Verify numeric field PIN hashing and verification for site supervisors."""
    pins = ["1234", "987654", "0000", "5555"]
    for pin in pins:
        h = get_pin_hash(pin)
        assert verify_pin(pin, h) is True
        assert verify_pin("9999", h) is (pin == "9999")


def test_sha256_fallback_mechanism():
    """Verify SHA-256 fallback hashing and its cross-verification in verify_password."""
    raw = "fallback_test_password"
    fb_hash = _sha256_fallback_hash(raw)
    assert fb_hash.startswith("sha256$")
    assert _sha256_fallback_verify(raw, fb_hash) is True
    assert _sha256_fallback_verify("wrong", fb_hash) is False

    # verify_password must seamlessly handle fallback hashes
    assert verify_password(raw, fb_hash) is True
    assert verify_password("wrong", fb_hash) is False


# ============================================================================
# 3. Pydantic v2 Schema Validations (Vulnerabilities 1 & 2)
# ============================================================================

def test_fuel_register_negative_dip_blocked():
    """Verify that negative closing dip is strictly blocked by Pydantic validation."""
    with pytest.raises(ValidationError) as exc_info:
        FuelRegisterCreate(
            site_id=1,
            date=date(2026, 9, 21),
            shift=ShiftType.DAY,
            opening_stock_liters=1000.0,
            received_bowser_liters=0.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=200.0,
            closing_dip_stock_liters=-50.0,  # Negative dip
        )
    # Rejection should occur via Field(ge=0.0) or model_validator
    errors = str(exc_info.value)
    assert "greater than or equal to 0" in errors or "Negative fuel dip" in errors


def test_fuel_register_ghost_issuance_blocked():
    """Verify that ghost fuel issuance (issuing more than total input) is blocked."""
    # Available = 500 + 200 + 0 = 700L, Issued = 701L
    with pytest.raises(ValidationError) as exc_info:
        FuelRegisterCreate(
            site_id=1,
            date=date(2026, 9, 21),
            shift=ShiftType.DAY,
            opening_stock_liters=500.0,
            received_bowser_liters=200.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=701.0,  # Ghost issuance
            closing_dip_stock_liters=0.0,
        )
    assert "Ghost issuance" in str(exc_info.value)


def test_fuel_register_ghost_issuance_from_empty_tank():
    """Verify that issuing fuel from a zero-stock tank is blocked."""
    with pytest.raises(ValidationError) as exc_info:
        FuelRegisterCreate(
            site_id=1,
            date=date(2026, 9, 21),
            shift=ShiftType.DAY,
            opening_stock_liters=0.0,
            received_bowser_liters=0.0,
            received_drums_liters=0.0,
            total_issued_to_equipment_liters=50.0,  # Issued from empty tank
            closing_dip_stock_liters=0.0,
        )
    assert "Ghost issuance" in str(exc_info.value)


def test_fuel_register_exact_boundary_valid():
    """Verify that exact issuance of 100% available stock with 0 closing dip is valid."""
    reg = FuelRegisterCreate(
        site_id=1,
        date=date(2026, 9, 21),
        shift=ShiftType.DAY,
        opening_stock_liters=800.0,
        received_bowser_liters=200.0,
        received_drums_liters=0.0,
        total_issued_to_equipment_liters=1000.0,  # Exactly 1000L available
        closing_dip_stock_liters=0.0,  # Exactly 0L dip
    )
    assert reg.total_issued_to_equipment_liters == 1000.0
    assert reg.closing_dip_stock_liters == 0.0


# ============================================================================
# 4. Additional Schema Guards (Pile Diameter, Expense Amount, Headcount)
# ============================================================================

def test_pile_diameter_minimum_400mm():
    """Verify that pile diameter < 400mm is rejected to prevent mm/meter confusion."""
    with pytest.raises(ValidationError):
        PileCreate(
            site_id=1,
            pier_number="P12",
            pile_number="P12-1",
            diameter_mm=350,  # Violates ge=400
        )

    # Valid pile with diameter >= 400mm
    pile = PileCreate(
        site_id=1,
        pier_number="P12",
        pile_number="P12-1",
        diameter_mm=1200,
    )
    assert pile.diameter_mm == 1200


def test_petty_cash_expense_positive_amount():
    """Verify that negative or zero expense amount is rejected."""
    with pytest.raises(ValidationError):
        ExpenseCreate(
            wallet_id=1,
            project_id=1,
            amount=0.0,  # gt=0.0 required
            category=ExpenseCategory.FUEL,
            description="Zero expense test",
            date=date(2026, 9, 21),
        )

    with pytest.raises(ValidationError):
        ExpenseCreate(
            wallet_id=1,
            project_id=1,
            amount=-250.0,  # Negative expense
            category=ExpenseCategory.FUEL,
            description="Negative expense test",
            date=date(2026, 9, 21),
        )


def test_gang_muster_headcount_strictly_positive():
    """Verify that headcount_present in gang muster must be > 0."""
    with pytest.raises(ValidationError):
        GangMusterCreate(
            site_id=1,
            date=date(2026, 9, 21),
            shift=ShiftType.DAY,
            subcontractor_name="L&T Heavy Civil Sub",
            trade=GangTrade.PILING_GANG,
            headcount_present=0,  # gt=0 required
        )
