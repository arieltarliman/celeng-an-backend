import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("CRITICAL WARNING: GEMINI_API_KEY is missing.")

PROMPT = """
You are a receipt parsing engine.
Analyze the image and return a JSON object with these exact fields:
- merchant (string): Store name
- date (string): Transaction date in YYYY-MM-DD format
- items (array): Each item has {name, qty, price, total}
- total_amount (integer): Grand total in smallest currency unit

Return ONLY valid JSON. No explanations or markdown.
"""

def ask_gemini(image_bytes: bytes, mime_type: str = "image/jpeg"):
    if not GEMINI_API_KEY:
        return {
            "merchant": "CONFIG ERROR",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": "Missing GEMINI_API_KEY"
        }

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }
        
        response = model.generate_content(
            [PROMPT, image_part],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )

        raw_json = response.text.strip()

        if raw_json.startswith("```json"):
            raw_json = raw_json.replace("```json", "").replace("```", "").strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.replace("```", "").strip()

        return json.loads(raw_json)

    except Exception as e:
        print("AI PROCESSING ERROR:", e)
        return {
            "merchant": "SCAN FAILED",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": str(e)
        }