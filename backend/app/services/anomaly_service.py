from datetime import datetime, timedelta
import math

class AnomalyDetector:
    @staticmethod
    def detect_fuel_anomaly(opening, received, issued, closing_dip, tolerance_pct=0.03):
        if closing_dip < 0:
            raise ValueError("Negative fuel dip is physically impossible.")
        
        total_input = opening + received
        if issued > total_input:
            raise ValueError("Ghost issuance: Cannot issue more fuel than is physically in the tank.")
            
        expected_closing = total_input - issued
        variance = closing_dip - expected_closing
        
        if total_input == 0:
            return False, 0.0
            
        variance_pct = abs(variance) / total_input
        is_anomalous = variance_pct > tolerance_pct
        return is_anomalous, variance_pct

    @staticmethod
    def detect_concrete_overbreak(diameter_mm, drilled_depth_m, actual_volume_m3, tolerance_pct=0.20):
        if diameter_mm < 400:
            raise ValueError("Invalid diameter: Minimum pile diameter is 400mm.")
            
        radius_m = (diameter_mm / 2) / 1000.0
        theoretical_volume = math.pi * (radius_m ** 2) * drilled_depth_m
        
        if theoretical_volume == 0:
            return False, 0.0
            
        overbreak = (actual_volume_m3 - theoretical_volume) / theoretical_volume
        is_anomalous = overbreak > tolerance_pct
        return is_anomalous, overbreak

    @staticmethod
    def check_duplicate_expense(new_amount, new_desc, new_date, existing_expenses):
        for exp in existing_expenses:
            # Fix: Calculate days difference based on the expense date (new_date), NOT sync submission date
            # Assuming new_date is the actual expense date and exp['date'] is the existing expense date
            days_diff = abs((new_date - exp['date']).days)
            
            # 1. Exact amount within 7 days
            if days_diff <= 7 and abs(new_amount - exp['amount']) < 0.01:
                return True, "Duplicate amount within 7 days"
            
            # 2. Same description within 48 hours
            if days_diff <= 2 and new_desc.lower().strip() == exp['description'].lower().strip():
                return True, "Duplicate description within 48 hours"
                
        return False, None

    @staticmethod
    def process_petty_cash(wallet_balance, expense_amount, max_deficit=50000.0):
        new_balance = wallet_balance - expense_amount
        is_out_of_pocket = new_balance < 0
        
        if is_out_of_pocket and abs(new_balance) > max_deficit:
            raise ValueError(f"Infinite Deficit Blocked: Max allowed deficit is {max_deficit}. Requested deficit is {abs(new_balance)}.")
            
        return new_balance, is_out_of_pocket
