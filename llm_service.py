import os
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
You are a receipt parsing engine. Analyze the receipt image and extract data.

Return ONLY a valid JSON object with this EXACT structure:
{
  "merchant": "Store Name",
  "date": "YYYY-MM-DD",
  "items": [
    {"name": "Item Name", "qty": 1, "price": 10000, "total": 10000}
  ],
  "total_amount": 10000
}

Rules:
- merchant: Store/restaurant name as string
- date: Transaction date in YYYY-MM-DD format
- items: Array of objects, each with name (string), qty (integer), price (integer per unit), total (integer = qty * price)
- total_amount: Grand total as integer
- All prices in smallest currency unit (no decimals, no currency symbols)
- If qty is not visible, assume 1
- If date is not visible, use "2025-01-01"

Return ONLY the JSON object. No markdown, no explanations.
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
            model="gemini-2.5-flash",
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

        raw_json = response.text.strip()

        if raw_json.startswith("```json"):
            raw_json = raw_json.replace("```json", "").replace("```", "").strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.replace("```", "").strip()

        parsed = json.loads(raw_json)
        
        # Normalize the response structure
        normalized = {
            "merchant": parsed.get("merchant", "Unknown"),
            "date": parsed.get("date", "2025-01-01"),
            "items": [],
            "total_amount": int(parsed.get("total_amount", 0) or 0),
            "error_details": None
        }
        
        raw_items = parsed.get("items", [])
        for item in raw_items:
            normalized["items"].append({
                "name": str(item.get("name", item.get("item_name", "Unknown"))),
                "qty": int(item.get("qty", item.get("quantity", 1)) or 1),
                "price": int(item.get("price", item.get("unit_price", 0)) or 0),
                "total": int(item.get("total", item.get("subtotal", 0)) or 0)
            })
        
        return normalized

    except json.JSONDecodeError as e:
        print("JSON PARSE ERROR:", e)
        return {
            "merchant": "PARSE ERROR",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": f"Invalid JSON from AI: {str(e)}"
        }
    except Exception as e:
        print("AI PROCESSING ERROR:", e)
        return {
            "merchant": "SCAN FAILED",
            "date": "2025-01-01",
            "items": [],
            "total_amount": 0,
            "error_details": str(e)
        }