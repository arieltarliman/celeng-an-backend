import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("CRITICAL WARNING: GEMINI_API_KEY is missing.")

PROMPT = """
You are a receipt parsing engine.
Analyze the image and return a JSON object with fields:
merchant, date, items, total_amount.
"""

def ask_gemini(image_bytes: bytes, mime_type: str = "image/jpeg"):

    if not client:
        return {
            "merchant": "CONFIG ERROR",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": "Missing GEMINI_API_KEY"
        }

    try:
        response = client.models.generate_content(
            model="models/gemini-1.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(PROMPT),
                        types.Part.from_bytes(image_bytes, mime_type)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        raw_json = response.text.strip()

        if raw_json.startswith("```json"):
            raw_json = raw_json.replace("```json", "").replace("```", "")

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
