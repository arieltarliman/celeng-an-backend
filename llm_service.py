import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 1. Setup the Client (New SDK Way)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("CRITICAL WARNING: GEMINI_API_KEY is missing in Environment Variables.")

# 2. Define the Schema for stricter output
PROMPT = """
You are a receipt parsing engine. 
Analyze the image and return a JSON object with exactly these fields:
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
- "price" is the unit price (integer).
- "total" is qty * price (integer).
- If date is missing, use today's date.
- Ignore tax/service charge in the item list.
"""

def ask_gemini(image_bytes: bytes, mime_type: str = "image/jpeg"):
    # 1. Check API Key
    if not client:
        return {
            "merchant": "CONFIG ERROR",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": "GEMINI_API_KEY not found on Server"
        }

    try:
        # 2. Call the AI (New 'generate_content' syntax)
        response = client.models.generate_content(
            model="gemini-1.5-flash", # The stable flash model
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(text=PROMPT),
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # 3. Parse Response
        # The new SDK returns .text directly
        raw_json = response.text.strip()
        
        # Clean up potential markdown formatting just in case
        if raw_json.startswith("```json"):
            raw_json = raw_json.replace("```json", "").replace("```", "")
            
        return json.loads(raw_json)

    except Exception as e:
        print(f"AI PROCESSING ERROR: {str(e)}")
        # Return the ERROR inside the JSON so you can see it in Swagger/Frontend
        return {
            "merchant": "SCAN FAILED",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": str(e) # <--- This will tell us exactly why it failed
        }