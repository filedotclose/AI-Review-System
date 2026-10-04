import os
from google import genai

api_key = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

print("Listing all accessible Gemini models:")
try:
    for m in client.models.list():
        # print model name if supported
        if "generateContent" in (m.supported_actions or []):
            print(" -", m.name)
except Exception as e:
    print(f"Error listing: {e}")
