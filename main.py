import os
import time
from typing import List, Annotated

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import Supabase (Database) and Gemini (AI) logic
from database import get_user_client, supabase 
from llm_service import ask_gemini

load_dotenv()

app = FastAPI(title="Celeng-an Backend")

# 1. CORS - Allow Vercel to talk to this Backend
origins = [
    "http://localhost:3000",
    "https://celeng-an.vercel.app",
    "https://celeng-an-backend.koyeb.app" # Add your own URL just in case
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. AUTHENTICATION
async def get_current_user_db(authorization: Annotated[str | None, Header()] = None):
    if not authorization:
        print("Warning: No Token provided. Using anonymous client.")
        return supabase 
    try:
        token = authorization.replace("Bearer ", "")
        return get_user_client(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Authentication Token")

# 3. DATA MODELS
# Updated to match what the AI returns
class ReceiptItem(BaseModel):
    name: str
    qty: int
    price: int  # Unit price
    total: int  # Subtotal (qty * price)

class ScanResult(BaseModel):
    merchant: str
    date: str
    items: List[ReceiptItem]
    total_amount: int
    error_details: str | None = None  

# 4. ENDPOINTS

@app.get("/")
def read_root():
    return {"status": "API is running", "ai_model": "Gemini Flash"}

# --- REAL AI SCANNER ---
@app.post("/scan", response_model=ScanResult)
async def scan_receipt(
    file: UploadFile = File(...), 
    user_db = Depends(get_current_user_db)
):
    """
    Real Endpoint: Accepts an image -> Sends to Gemini AI -> Returns JSON
    """
    # 1. Validate File Type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WEBP images allowed")

    # 2. Read the file bytes
    content = await file.read()

    # 3. Send to Gemini (The AI Team's Logic)
    # We pass the content_type so Gemini knows if it's PNG or JPG
    ai_result = ask_gemini(content, mime_type=file.content_type)

    # 4. Check for errors
    if "error" in ai_result:
        raise HTTPException(status_code=500, detail=ai_result["details"])

    # 5. Return the result (FastAPI automatically validates it against ScanResult model)
    return ai_result

# --- MOCK SCANNER (Keep this for testing) ---
@app.post("/scan/mock", response_model=ScanResult)
async def mock_ocr_scan(file: UploadFile = File(...)):
    time.sleep(2) 
    return {
        "merchant": "INDOMARET POINT (MOCK)",
        "date": "2025-11-21",
        "items": [
            {"name": "Aqua 600ml", "qty": 2, "price": 3500, "total": 7000},
            {"name": "Sari Roti", "qty": 1, "price": 12000, "total": 12000},
        ],
        "total_amount": 19000
    }