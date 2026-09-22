import pytest
from datetime import datetime, timedelta
from app.services.anomaly_service import AnomalyDetector

def test_fuel_anomaly_zero_input():
    with pytest.raises(ValueError, match="Ghost issuance"):
        AnomalyDetector.detect_fuel_anomaly(0, 0, 100, 0)

def test_fuel_anomaly_negative_dip():
    with pytest.raises(ValueError, match="Negative fuel dip"):
        AnomalyDetector.detect_fuel_anomaly(1000, 500, 1200, -50)

def test_concrete_overbreak_massive_diameter():
    with pytest.raises(ValueError, match="Invalid diameter"):
        AnomalyDetector.detect_concrete_overbreak(1.2, 20.0, 25.0)

def test_duplicate_expense_floating_point():
    existing = [
        {'amount': 500.0000000000001, 'description': 'Diesel', 'date': datetime(2026, 9, 21)}
    ]
    is_dup, reason = AnomalyDetector.check_duplicate_expense(500.0, 'Diesel', datetime(2026, 9, 22), existing)
    assert is_dup

def test_duplicate_expense_timezone_shift():
    existing = [
        {'amount': 1200.0, 'description': 'Tractor Rent', 'date': datetime(2026, 9, 10)}
    ]
    # In the exploit, if we synced on 19th but the expense was on 11th, we must check against the expense date (11th)
    expense_date = datetime(2026, 9, 11)
    is_dup, reason = AnomalyDetector.check_duplicate_expense(1200.0, 'Tractor Rent', expense_date, existing)
    assert is_dup  # Now correctly flags it because 11th is within 7 days of 10th!

def test_petty_cash_infinite_deficit():
    with pytest.raises(ValueError, match="Infinite Deficit Blocked"):
        AnomalyDetector.process_petty_cash(5000, 1000000)
