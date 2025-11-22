import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is missing.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- CHANGE IS HERE ---
# Use "gemini-1.5-flash-latest" or "gemini-pro" if Flash keeps failing
model = genai.GenerativeModel(
    "gemini-1.5-flash-latest", 
    generation_config={
        "response_mime_type": "application/json"
    }
)

PROMPT = """
You are a receipt parsing engine. 
Read the receipt image and output strictly valid JSON.
Ensure numbers are integers (no decimals).

{
  "merchant": "Store Name",
  "date": "YYYY-MM-DD",
  "items": [
      {
        "name": "Item Name",
        "qty": 1,
        "price": 1000, 
        "total": 1000
      }
  ],
  "total_amount": 0
}

Rules:
- "price" is the unit price.
- "total" is qty * price.
- "total_amount" is the grand total.
- Ignore non-item text.
"""

def ask_gemini(image_bytes: bytes, mime_type: str = "image/jpeg"):
    if not GEMINI_API_KEY:
        return {"error": "Server missing API Key"}

    try:
        # 1.5 Flash handles standard image types well
        response = model.generate_content([
            PROMPT,
            {"mime_type": mime_type, "data": image_bytes}
        ])

        # Clean response
        raw = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except Exception as e:
        print(f"Gemini Error: {e}")
        # Fallback error message so the frontend doesn't crash
        return {
            "merchant": "SCAN FAILED",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": str(e)
        }