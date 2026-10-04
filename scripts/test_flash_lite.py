import os
from google import genai
from google.genai import types
from app.schemas.ai_schemas import AIReviewResult

client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

for model_name in ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']:
    try:
        print(f"Testing {model_name}...")
        resp = client.models.generate_content(
            model=model_name,
            contents="Civil engineering evaluation: 18.5m drilled, 23.8m3 concrete on Pile P-101. Provide structured JSON review.",
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=AIReviewResult,
                temperature=0.1
            )
        )
        print(f"SUCCESS on {model_name}!")
        res = AIReviewResult.model_validate_json(resp.text)
        print(f"Result: Score={res.productivity_score}, Summary: {res.executive_summary[:120]}...")
        break
    except Exception as e:
        print(f"Failed {model_name}: {e}")
