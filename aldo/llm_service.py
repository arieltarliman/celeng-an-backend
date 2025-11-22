import google.generativeai as genai
import json
from app.config import GEMINI_API_KEY

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-flash-latest", 
    generation_config={
        "response_mime_type": "application/json"
    }
)

PROMPT = """
You are a receipt parsing engine. 
Read the receipt image and output strictly valid JSON with fields:

{
  "merchant": "",
  "address": "",
  "date": "",
  "items": [
      {
        "name": "",
        "qty": 0,
        "unit_price": 0,
        "subtotal": 0
      }
  ],
  "modifiers": []
  "tax": 0,
  "service_charge": 0,
  "total": 0,
  "payment_method": "",
  "notes": ""
}

Make sure:
- numbers become integers
- subtotal = qty * unit_price if possible
- ignore text not part of receipt
- if the unit price is 0, list as modifiers
"""

def ask_gemini(image_bytes: bytes):
    try:
        response = model.generate_content([
            PROMPT,
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])

        raw = response.text
        raw = raw.replace("```json", "").replace("```", "").strip()

        return json.loads(raw)

    except Exception as e:
        return {"error": "LLM parsing failed", "details": str(e)}
