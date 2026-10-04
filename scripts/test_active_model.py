import os
from google import genai
from google.genai import types
from app.schemas.ai_schemas import AIReviewResult

api_key = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-pro-latest",
]

for m in models_to_test:
    try:
        resp = client.models.generate_content(
            model=m,
            contents="Say 'OK'",
        )
        print(f"✓ Model '{m}' is ACTIVE and responsive! (Output: {resp.text.strip()})")
        
        # Test full structured output
        print(f"  Testing structured output on '{m}'...")
        prompt = "You are a civil engineer evaluating a daily piling report: 18.5m drilled, 23.8m3 concrete poured on Pile P-101. Output JSON."
        struct_resp = client.models.generate_content(
            model=m,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=AIReviewResult,
                temperature=0.1
            )
        )
        parsed = AIReviewResult.model_validate_json(struct_resp.text)
        print(f"  ★ STRUCTURED SUCCESS on '{m}'! Score: {parsed.productivity_score}, Summary: {parsed.executive_summary[:80]}...")
        break
    except Exception as e:
        print(f"✗ Model '{m}' failed: {e}")
