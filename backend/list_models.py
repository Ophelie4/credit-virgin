"""Print the Gemini models this key can use for generateContent. Run: .venv/bin/python list_models.py"""
from dotenv import load_dotenv; load_dotenv()
import os
from google import genai
c = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
for m in c.models.list():
    if "generateContent" in (m.supported_actions or []):
        print(m.name.removeprefix("models/"))
