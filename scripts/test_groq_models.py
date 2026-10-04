import os
from groq import Groq

api_key = os.environ.get('GROQ_API_KEY')
print(f"Testing Groq with key length: {len(api_key) if api_key else 0}")
client = Groq(api_key=api_key)
models = [m.id for m in client.models.list().data]
print("Available Groq Models:")
for m in models:
    print(" -", m)
