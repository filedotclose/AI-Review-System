import os
import json
from google import genai
from google.genai import types
from app.schemas.ai_schemas import AIReviewResult

api_key = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

# Test with a sanitized construction operational payload
compact_brief = {
    "operational_date": "2026-09-23",
    "site": "Vadakara AVRP Flyover Package 4",
    "piling": {
        "drilled_meters": 18.5,
        "concrete_poured_m3": 23.8,
        "planned_concrete_m3": 20.5,
        "piles_completed": 1,
        "delays": ["40 mins delay: Bentonite slurry pump electrical contactor tripped"]
    },
    "fuel": {
        "total_issued_liters": 450.0,
        "closing_dip_liters": 1850.0,
        "variance_liters": -12.5
    },
    "manpower": {
        "total_headcount": 22,
        "direct_workers": 8,
        "subcontractor_gang": 14
    },
    "petty_cash": {
        "total_spent_inr": 4650.0,
        "deficit_amount": 0.0
    },
    "alerts": [
        {"type": "CONCRETE_OVERBREAK", "severity": "WARNING", "message": "16% overbreak on Pile P-101"},
        {"type": "EQUIPMENT_DELAY", "severity": "WARNING", "message": "40 mins bentonite pump tripping"}
    ]
}

prompt = f"""You are an expert AI Construction Project Manager analyzing this daily site brief.
Return a structured JSON review matching the required schema.

Brief Data:
{json.dumps(compact_brief, indent=2)}"""

print(f"Prompt length: {len(prompt)} chars. Sending to Gemini 3.6 Flash...")
try:
    resp = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=AIReviewResult,
            temperature=0.1
        )
    )
    print("SUCCESS!")
    res = AIReviewResult.model_validate_json(resp.text)
    print(f"Executive Summary: {res.executive_summary}")
    print(f"Productivity Score: {res.productivity_score}/100")
    print(f"Risk Assessment: {res.risk_assessment}")
    print(f"Key Insights: {res.key_insights}")
    print(f"Safety Concerns: {res.safety_concerns}")
except Exception as e:
    print(f"FAILED: {e}")
