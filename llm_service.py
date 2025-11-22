import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# 1. Securely load the API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # We just print a warning here so the app doesn't crash on boot
    # The error will be raised if someone actually tries to scan
    print("WARNING: GEMINI_API_KEY is missing.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# 2. Initialize Model
model = genai.GenerativeModel(
    "gemini-1.5-flash",  # Updated to the stable model name
    generation_config={
        "response_mime_type": "application/json"
    }
)

PROMPT = """
You are a receipt parsing engine. 
Read the receipt image and output strictly valid JSON with these fields.
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
- "total_amount" is the grand total of the receipt.
- Ignore non-item text.
"""

def ask_gemini(image_bytes: bytes, mime_type: str = "image/jpeg"):
    """
    Sends the image to Gemini and returns a JSON Dictionary.
    """
    if not GEMINI_API_KEY:
        return {"error": "Server missing API Key"}

    try:
        response = model.generate_content([
            PROMPT,
            {"mime_type": mime_type, "data": image_bytes}
        ])

        # Clean response just in case
        raw = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except Exception as e:
        print(f"Gemini Error: {e}")
        return {"error": "AI parsing failed", "details": str(e)}