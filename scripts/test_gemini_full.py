import os
import json
from google import genai
from google.genai import types
from app.schemas.ai_schemas import AIReviewResult

api_key = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

sample_data = {
    "operational_date": "2026-09-23",
    "piling": {
        "depth_drilled_m": 18.5,
        "concrete_poured_m3": 23.8,
        "delays": ["40 mins delay: Bentonite slurry circulation pump electrical contactor tripped"]
    },
    "fuel": {"total_issued": 450, "variance": -12.5},
    "attendance": {"total_headcount": 22},
    "alerts": [{"type": "CONCRETE_OVERBREAK", "severity": "WARNING", "message": "16% overbreak on Pile P-101"}]
}

prompt = f"""
You are an expert AI Construction Project Manager analyzing a daily site brief.
Context: The project involves bored piling, deep well foundations, and heavy civil infrastructure.
Analyze the following daily brief data and provide a structured JSON response matching the required schema.

Daily Brief Data:
{json.dumps(sample_data, indent=2)}
"""

print("Sending request to Gemini 3.6 Flash...")
try:
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=AIReviewResult,
            temperature=0.1
        )
    )
    print("SUCCESS! Output JSON:")
    print(response.text)
    result = AIReviewResult.model_validate_json(response.text)
    print(f"\nParsed Result: Score={result.productivity_score}, Risk={result.risk_assessment}")
    print(f"Summary: {result.executive_summary}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
