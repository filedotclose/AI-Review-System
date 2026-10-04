import os
from google import genai

api_key = os.environ.get('GEMINI_API_KEY')
print(f"Testing Gemini client with key: {api_key[:6]}...{api_key[-4:]}")
client = genai.Client(api_key=api_key)

candidates = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-3.6-flash",
]

for model in candidates:
    try:
        resp = client.models.generate_content(
            model=model,
            contents="Say 'OK'",
        )
        print(f"✓ Model '{model}' WORKS! Response: {resp.text.strip()}")
        break
    except Exception as e:
        print(f"✗ Model '{model}' failed: {e}")
